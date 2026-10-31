import asyncio
import json

import pytest
from aiohttp.test_utils import TestClient, TestServer

from theater_deploy import (EYE_MODE_COUNT, THEATER_ACTIONS, THEATER_ROOT, TheaterDeployment,
                            action_module, encode_aiff, eye_records, voice_records)
from omni_bridge import Controller, create_app
from test_omni import config


class FakeOwner:
    def __init__(self, motion_ok=True):
        self.board_state = 1
        self.generation = 42
        self.failed_generation = None
        self.motion_ok = motion_ok
        self.moves = []
        self.down_calls = []
        self.requests = []
        self.stopped = False

    async def stop_conversation(self):
        self.stopped = True

    async def move(self, action):
        self.moves.append(action)
        if action == 'stop':
            return {'ok': True, 'action': action}
        return {'ok': self.motion_ok, 'action': action,
                'message': '' if self.motion_ok else '运动未启用'}


def owner_with_clock(motion_ok=True):
    owner = FakeOwner(motion_ok)
    clock = [0.0]

    async def sleep(delay):
        clock[0] += delay
        await asyncio.sleep(0)

    async def request(method, path, data=None):
        payload = json.loads(data) if data else None
        owner.requests.append((clock[0], method, path, payload))
        if path == '/api/status':
            return 200, json.dumps({'audioGeneration': 42, 'audioState': 1}).encode()
        return 202, b'{}'

    async def down(generation, command, packets=()):
        assert generation == 42
        owner.down_calls.append((clock[0], command, len(packets)))

    owner.request = request
    owner.down = down
    return owner, clock, sleep


def test_all_voice_files_encode_to_bounded_opus_packets():
    manifest = json.loads((THEATER_ROOT / 'voice_manifest.json').read_text())
    assert len(manifest) == 6
    for record in manifest:
        packets = encode_aiff(THEATER_ROOT / record['file'])
        assert packets and all(1 <= len(packet) <= 255 for packet in packets)


def test_eye_cues_use_real_modes_and_keep_action_lengths():
    for action in action_module().ACTIONS:
        records = eye_records(action)
        assert records[0]['start'] == 0
        assert records[-1]['start'] < action['seconds']
        assert all(0 <= record[side + 'Mode'] < EYE_MODE_COUNT
                   for record in records for side in ('left', 'right'))


def test_three_actions_complete_with_synchronized_audio_and_eyes():
    async def run():
        for action in action_module().ACTIONS:
            owner, clock, sleep = owner_with_clock()
            deployment = TheaterDeployment(owner, lambda: clock[0], sleep)
            accepted = await deployment.start(action['id'])
            assert accepted['ok']
            await asyncio.wait_for(deployment.task, 2)
            status = deployment.status()
            assert status['state'] == 'completed' and not status['physicalCompletion']
            assert owner.stopped and owner.failed_generation == 42
            assert owner.moves == [action['id']]
            voice = voice_records(action['id'])
            starts = [entry[0] for entry in owner.down_calls if entry[1] == 1]
            assert starts == pytest.approx([record['start'] for record in voice], abs=.051)
            assert owner.down_calls[-1][1] == 5
            eye_calls = [entry for entry in owner.requests if entry[2] == '/api/eyes']
            assert len(eye_calls) == len(eye_records(action)) * 2 + 1
            assert eye_calls[-1][3]['mode'] == -1
            assert clock[0] <= action['seconds'] + 1
    asyncio.run(run())


def test_motion_rejection_and_idle_board_do_not_start_performance():
    async def run():
        owner, clock, sleep = owner_with_clock(motion_ok=False)
        deployment = TheaterDeployment(owner, lambda: clock[0], sleep)
        await deployment.start('gossip_radar')
        await asyncio.wait_for(deployment.task, 2)
        assert deployment.status()['state'] == 'failed'
        assert not [entry for entry in owner.down_calls if entry[1] == 1]
        owner.board_state = 0
        result = await deployment.start('gossip_radar')
        assert result['status'] == 'voice_unavailable' and deployment.task is None
    asyncio.run(run())


def test_stop_cancels_pending_cues_and_dispatches_stop():
    async def run():
        owner, clock, sleep = owner_with_clock()
        deployment = TheaterDeployment(owner, lambda: clock[0], sleep)
        await deployment.start('hold_that_compliment')
        for _ in range(10000):
            if clock[0] >= .5:
                break
            await asyncio.sleep(0)
        assert clock[0] >= .5
        busy = await deployment.start('gossip_radar')
        assert busy['status'] == 'busy'
        result = await asyncio.wait_for(deployment.stop(), 2)
        assert result['state'] == 'cancelled'
        assert 'stop' in owner.moves
        assert owner.down_calls[-1][1] == 5
    asyncio.run(run())


def test_theater_api_exposes_named_start_and_status():
    async def run():
        owner = Controller(config())
        owner.board_state = 1
        owner.generation = 42
        async with TestClient(TestServer(create_app(owner))) as client:
            headers = {'Host': '127.0.0.1:8765'}
            response = await client.post('/api/theater', headers=headers,
                                         json={'action': 'invalid'})
            assert response.status == 400
            response = await client.post('/api/theater', headers=headers,
                                         json={'action': 'gossip_radar'})
            assert response.status == 200
            assert (await response.json())['status'] == 'accepted'
            await owner.theater.stop()
            response = await client.get('/api/status', headers=headers)
            assert 'theater' in await response.json()
    asyncio.run(run())
