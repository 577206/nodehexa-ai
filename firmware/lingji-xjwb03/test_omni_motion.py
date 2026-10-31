"""Manual controls share the bounded voice path; no real hardware is contacted."""
import asyncio
import json

from aiohttp.test_utils import TestClient, TestServer
from omni_bridge import Controller, Conversation, create_app
from omni_protocol import ACTIONS
from test_omni import config


def fake_robot(owner):
    state = {'online': True, 'bench': False, 'ackSequence': 0, 'actions': ACTIONS}
    sent = []
    async def request(method, path, data=None):
        if method == 'POST':
            assert path == '/api/motion'
            action = json.loads(data)['action']
            sent.append(action)
            state.update(ackSequence=state['ackSequence']+1, ackAction=action, ackSuccess=True)
            return 202, b'{}'
        return 200, json.dumps({'robot': state}).encode()
    owner.board_status = {'robot': state}
    owner.request = request
    return state, sent


def test_manual_endpoint_validation_disarm_and_ack():
    async def run():
        owner = Controller(config())
        state, sent = fake_robot(owner)
        async with TestClient(TestServer(create_app(owner))) as client:
            headers = {'Host': '127.0.0.1:8765'}
            for invalid in ([], {'action': 'jump'}, {'action': 'forward', 'cycles': 100}):
                r = await client.post('/api/motion', headers=headers, json=invalid)
                assert r.status == 400
            r = await client.post('/api/motion', headers={**headers, 'Origin': 'https://example.com'}, json={'action':'forward'})
            assert r.status == 403
            r = await client.post('/api/motion', headers=headers, json={'action':'forward'})
            assert (await r.json())['status'] == 'disabled' and sent == []
            r = await client.post('/api/motion-enable', headers=headers, json={'enabled':True})
            assert r.status == 200
            r = await client.post('/api/motion', headers=headers, json={'action':'forward'})
            result = await r.json()
            assert result['ok'] and result['action'] == 'forward' and result['status'] == 'acknowledged'
            assert sent == ['forward']
            r = await client.post('/api/stop', headers=headers, json={})
            assert (await r.json())['ok'] and not owner.motion_enabled
            assert sent == ['forward', 'stop']
    asyncio.run(run())


def test_offline_and_bench_block_dispatch():
    async def run():
        owner = Controller(config())
        owner.motion_enabled = True
        state, sent = fake_robot(owner)
        for online, bench in ((False, False), (True, True)):
            state.update(online=online, bench=bench)
            result = await owner.move('forward')
            assert result['status'] == 'unavailable' and not sent
    asyncio.run(run())


def test_stop_supersedes_preflight_and_duplicate_is_not_queued():
    async def run():
        owner = Controller(config())
        owner.motion_enabled = True
        state, sent = fake_robot(owner)
        underlying = owner.request
        entered, release = asyncio.Event(), asyncio.Event()
        async def request(method, path, data=None):
            if method == 'GET' and not entered.is_set():
                entered.set()
                await release.wait()
            return await underlying(method, path, data)
        owner.request = request
        pending = asyncio.create_task(owner.move('forward'))
        await entered.wait()
        assert (await owner.move('backward'))['status'] == 'busy'
        stop = await owner.move('stop')
        assert stop['ok'] and sent == ['stop']
        release.set()
        assert (await pending)['status'] == 'superseded'
        assert owner.motion_result['action'] == 'stop'
        assert not owner.motion_pending
    asyncio.run(run())


def test_timeout_does_not_retry_or_claim_success():
    async def run():
        owner = Controller(config())
        owner.motion_enabled = True
        _, sent = fake_robot(owner)
        request = owner.request
        async def timeout(method, path, data=None):
            if method == 'POST':
                sent.append(json.loads(data)['action'])
                raise asyncio.TimeoutError()
            return await request(method, path, data)
        owner.request = timeout
        result = await owner.move('forward')
        assert not result['ok'] and result['status'] == 'transport_error'
        assert sent == ['forward'] and not owner.motion_pending
    asyncio.run(run())


def test_posture_actions_use_only_fixed_in_place_presets():
    async def run():
        owner = Controller(config())
        owner.motion_enabled = True
        _, sent = fake_robot(owner)
        expected = {'good': 'beat_sway', 'head_tilt': 'rotate_z',
                    'forward_lean': 'rotate_x', 'slouch': 'twist'}
        for posture, action in expected.items():
            result = await owner.posture_action(posture)
            assert result['ok'] and result['action'] == action and result['posture'] == posture
        assert sent == list(expected.values())
    asyncio.run(run())


def test_away_uncertain_and_disarmed_posture_do_not_dispatch():
    async def run():
        owner = Controller(config())
        async def forbidden(*args):
            raise AssertionError('Unexpected board request')
        owner.request = forbidden
        for posture in ('away', 'uncertain'):
            result = await owner.posture_action(posture)
            assert result['ok'] and result['status'] == 'no_motion'
        result = await owner.posture_action('good')
        assert not result['ok'] and result['status'] == 'disabled'
    asyncio.run(run())


def test_look_then_posture_action_runs_two_stage_chain():
    async def run():
        owner = Controller(config())
        owner.motion_enabled = True
        _, sent = fake_robot(owner)
        async def frame():
            return b'\xff\xd8jpeg\xff\xd9'
        async def down(*args):
            pass
        owner.frame, owner.down = frame, down
        session = Conversation(owner, 31)
        events = []
        async def send(payload):
            events.append(payload)
        session.send = send
        await session.run_tools([{'call_id': 'look1', 'name': 'look', 'arguments': '{}'}])
        assert session.image_commit_pending and sent == []
        await session.run_tools([{'call_id': 'posture1', 'name': 'posture_action',
                                  'arguments': '{"posture":"head_tilt"}'}])
        assert sent == ['rotate_z']
        result = json.loads(events[-2]['item']['output'])
        assert result['ok'] and result['posture'] == 'head_tilt'
        assert events[-1]['type'] == 'response.create'
    asyncio.run(run())
