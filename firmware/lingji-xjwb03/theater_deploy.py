"""Deploy the three bounded theater performances through the existing board APIs."""
from __future__ import annotations

import asyncio
import importlib.util
import json
import time
from pathlib import Path

import av

THEATER_ROOT = Path(__file__).resolve().parents[2] / 'design/robot_theater/actions_r03'
THEATER_ACTIONS = ('hold_that_compliment', 'gossip_radar', 'compliment_receipt')
EYE_MODE_COUNT = 17
EYE_MODES = {
    'normal': 8, 'calm': 9, 'squint': 10, 'heart': 11, 'spark': 12,
    'check': 13, 'inbox': 14, 'pupil_left': 15, 'pupil_right': 16,
    'smile': 4, 'wide': 5,
}


def action_module():
    path = THEATER_ROOT / 'source/actions.py'
    spec = importlib.util.spec_from_file_location('theater_actions', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def encode_aiff(path):
    codec = av.CodecContext.create('libopus', 'w')
    codec.sample_rate = 16000
    codec.layout = 'mono'
    codec.format = 's16'
    codec.bit_rate = 16000
    codec.options = {'application': 'voip', 'frame_duration': '20'}
    codec.open()
    resampler = av.AudioResampler(format='s16', layout='mono', rate=16000)
    pending = bytearray()
    packets = []

    def encode_frames():
        while len(pending) >= 640:
            frame = av.AudioFrame(format='s16', layout='mono', samples=320)
            frame.sample_rate = 16000
            frame.planes[0].update(bytes(pending[:640]))
            del pending[:640]
            packets.extend(bytes(packet) for packet in codec.encode(frame))

    with av.open(str(path)) as container:
        for frame in container.decode(audio=0):
            for pcm in resampler.resample(frame):
                pending.extend(bytes(pcm.planes[0])[:pcm.samples * 2])
                encode_frames()
    for pcm in resampler.resample(None):
        pending.extend(bytes(pcm.planes[0])[:pcm.samples * 2])
    if pending:
        pending.extend(bytes((-len(pending)) % 640))
    encode_frames()
    packets.extend(bytes(packet) for packet in codec.encode(None))
    if not packets or any(not 1 <= len(packet) <= 255 for packet in packets):
        raise ValueError(f'Invalid encoded audio: {path.name}')
    return tuple(packets)


def voice_records(action_id):
    manifest = json.loads((THEATER_ROOT / 'voice_manifest.json').read_text())
    records = [record for record in manifest if record['action'] == action_id]
    if len(records) != 2:
        raise ValueError('Each theater action must have exactly two voice cues')
    return [{'start': record['start_seconds'], 'packets': encode_aiff(THEATER_ROOT / record['file'])}
            for record in records]


def eye_records(action):
    module = action_module()
    previous = None
    records = []
    for index in range(round(action['seconds'] * module.FPS)):
        started = index / module.FPS
        state = module.eyes(action, started)
        current = (state['left'], state['right'])
        if current != previous:
            modes = {}
            for side in ('left', 'right'):
                pattern = state[side]
                candidates = list(module.PATTERNS.items()) + [
                    ('pupil_left', module.shift(module.PATTERNS['pupil'], -2)),
                    ('pupil_right', module.shift(module.PATTERNS['pupil'], 2)),
                ]
                name, _ = min(candidates, key=lambda item: sum(
                    a != b for row_a, row_b in zip(pattern, item[1]) for a, b in zip(row_a, row_b)))
                if name not in EYE_MODES:
                    raise ValueError(f'Unsupported eye pattern on {side}')
                modes[side + 'Mode'] = EYE_MODES[name]
            records.append({'start': started, **modes})
            previous = current
    return records


class TheaterDeployment:
    def __init__(self, owner, clock=time.monotonic, sleep=asyncio.sleep):
        self.owner = owner
        self.clock = clock
        self.sleep = sleep
        self.task = None
        self.cancel_event = None
        self._status = {'state': 'idle', 'action': None, 'error': '',
                      'physicalCompletion': False}

    def status(self):
        return dict(self._status)

    async def start(self, action):
        if action not in THEATER_ACTIONS:
            raise ValueError('Unknown theater action')
        if self.task is not None:
            return {'ok': False, 'status': 'busy', 'message': '已有表演正在进行'}
        if self.owner.board_state != 1:
            return {'ok': False, 'status': 'voice_unavailable', 'message': '请先唤醒灵机板，再启动配音表演'}
        self.cancel_event = asyncio.Event()
        self._status = {'state': 'accepted', 'action': action, 'error': '',
                        'physicalCompletion': False}
        self.task = asyncio.create_task(self._run(action, self.owner.generation))
        return {'ok': True, 'status': 'accepted', 'action': action,
                'message': '表演已接受，等待底盘回执'}

    async def stop(self):
        if self.task is None:
            return {'ok': True, 'status': 'idle'}
        self.cancel_event.set()
        self._status.update(state='cancelling')
        await self.task
        return self.status()

    async def _wait_until(self, target):
        while True:
            self._check_cancelled()
            remaining = target - self.clock()
            if remaining <= 0:
                return
            await self.sleep(min(.05, remaining))

    def _check_cancelled(self):
        if self.cancel_event is not None and self.cancel_event.is_set():
            raise asyncio.CancelledError()

    async def _eyes(self, records, generation):
        for record in records:
            await self._wait_until(self._started + record['start'])
            self._check_cancelled()
            for side in ('left', 'right'):
                payload = json.dumps({'mode': record[side + 'Mode'], 'durationMs': 1000,
                                      'contrast': 127}).encode()
                code, _ = await self.owner.request('POST', '/api/eyes', payload)
                if code != 202:
                    raise RuntimeError(f'Eye command rejected ({code})')

    async def _voice(self, records, generation):
        for record in records:
            await self._wait_until(self._started + record['start'])
            await self._play_line(generation, record['packets'])

    async def _play_line(self, generation, packets):
        await self.owner.down(generation, 1)
        for index in range(0, len(packets), 10):
            self._check_cancelled()
            batch = packets[index:index + 10]
            started = self.clock()
            await self.owner.down(generation, 2, batch)
            await self.sleep(max(0, len(batch) * .020 - (self.clock() - started)))
        await self.owner.down(generation, 3)
        until = self.clock() + 12
        while self.clock() < until:
            self._check_cancelled()
            code, raw = await self.owner.request('GET', '/api/status')
            if code != 200:
                raise RuntimeError('Cannot confirm audio playback state')
            status = json.loads(raw)
            if status.get('audioGeneration') != generation:
                raise RuntimeError('Audio generation changed during performance')
            if status.get('audioState') == 1:
                return
            if status.get('audioState') == 0:
                raise RuntimeError('Board became idle before playback completed')
            await self.sleep(.1)
        raise TimeoutError('Audio playback confirmation timed out')

    async def _restore_auto_eyes(self):
        payload = json.dumps({'mode': -1, 'durationMs': 100, 'contrast': 127}).encode()
        await self.owner.request('POST', '/api/eyes', payload)

    async def _run(self, action_id, generation):
        try:
            action = next(item for item in action_module().ACTIONS if item['id'] == action_id)
            voices = voice_records(action_id)
            eyes = eye_records(action)
            await self.owner.stop_conversation()
            self.owner.failed_generation = generation
            motion = await self.owner.move(action_id)
            self._status['motion'] = motion
            if not motion.get('ok'):
                raise RuntimeError(motion.get('message', 'Motion was not accepted'))
            self._started = self.clock()
            self._status.update(state='running', startedAt=self._started)
            await asyncio.gather(self._eyes(eyes, generation), self._voice(voices, generation))
            await self.owner.down(generation, 5)
            await self._restore_auto_eyes()
            self._status.update(state='completed', completedAt=self.clock())
        except asyncio.CancelledError:
            self._status.update(state='cancelled', completedAt=self.clock())
            await self.owner.move('stop')
            await self.owner.down(generation, 5)
            await self._restore_auto_eyes()
        except Exception as error:
            self._status.update(state='failed', error=str(error), completedAt=self.clock())
            await self.owner.move('stop')
            await self.owner.down(generation, 5)
            await self._restore_auto_eyes()
        finally:
            self.task = None
