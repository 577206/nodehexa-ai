import asyncio
import json
import math
import struct
import base64

import pytest

from omni_audio import MicrophoneDecoder, SpeakerEncoder
from omni_protocol import pack_downlink, unpack_uplink, validate_action, validate_board_url
from omni_bridge import Controller, Conversation


def config():
    return {'LINGXI_BOARD_URL': 'http://192.168.31.186:8766',
            'LINGXI_BRIDGE_TOKEN': 'a' * 64, 'DASHSCOPE_API_KEY': 'fake-test-key'}


def test_transport_rejects_truncated_and_idle_audio():
    header = struct.pack('<4sIBBH', b'LXA1', 42, 1, 0, 1)
    data = header + b'\x03\x00abc'
    assert unpack_uplink(data) == (42, 1, [b'abc'])
    for bad in (data[:-1], data+b'x', data[:10], data[:8]+b'\x00'+data[9:],
                header+b'\x00\x01'+bytes(256)):
        with pytest.raises(ValueError):
            unpack_uplink(bad)
    assert pack_downlink(42, 2, [b'abc']) == struct.pack('<IBH', 42, 2, 3)+b'abc'
    for command, packets in ((2, []), (1, [b'x']), (2, [b'x'*256]), (7, [])):
        with pytest.raises(ValueError):
            pack_downlink(1, command, packets)


def test_only_private_board_and_fixed_actions():
    assert validate_action({'action': 'stop'}) == 'stop'
    for payload in ({'action': 'forward', 'duration': 999}, {'action': 'jump'}, ['forward']):
        with pytest.raises(ValueError):
            validate_action(payload)
    for url in ('http://127.0.0.1:8766', 'http://8.8.8.8:8766', 'http://192.168.1.2:80',
                'http://user:secret@192.168.1.2:8766', 'http://192.168.1.2:8766/admin'):
        with pytest.raises(ValueError):
            validate_board_url(url)


def test_real_codec_roundtrip_has_right_duration_and_no_padding():
    # One second, 440 Hz at 24 kHz -> packet Opus -> exactly 16 kHz PCM.
    raw = struct.pack('<24000h', *(int(5000*math.sin(2*math.pi*440*i/24000)) for i in range(24000)))
    encoder = SpeakerEncoder()
    packets = []
    for offset in range(0, len(raw), 1920):
        packets.extend(encoder.encode(raw[offset:offset+1920]))
    packets.extend(encoder.finish())
    assert 50 <= len(packets) <= 52
    assert all(1 <= len(p) <= 255 for p in packets)
    decoder = MicrophoneDecoder()
    pcm = b''.join(decoder.decode(p) for p in packets)
    assert 31500 <= len(pcm) <= 33500
    samples = struct.unpack('<'+str(len(pcm)//2)+'h', pcm)
    assert sum(s*s for s in samples)/len(samples) > 100000


def test_movement_is_disarmed_without_network_call():
    async def run():
        owner = Controller(config())
        async def forbidden(*args, **kwargs):
            raise AssertionError('Disarmed command reached the board')
        owner.request = forbidden
        result = await owner.move('forward')
        assert result['ok'] is False and result['status'] == 'disabled'
    asyncio.run(run())


def test_stale_generation_cannot_send_audio():
    async def run():
        owner = Controller(config())
        owner.generation = 10
        with pytest.raises(asyncio.CancelledError):
            await owner.down(9, 1)
    asyncio.run(run())


def test_camera_tool_attaches_one_image_to_same_session_after_silent_audio():
    async def run():
        owner = Controller(config())
        owner.generation = 11
        frames, sent = [], []
        async def frame():
            frames.append(1)
            return b'\xff\xd8jpeg\xff\xd9'
        async def down(*args):
            pass
        owner.frame, owner.down = frame, down
        session = Conversation(owner, 11)
        async def send(payload):
            sent.append(payload)
        session.send = send
        await session.run_tools([{'call_id': 'c1', 'name': 'look', 'arguments': '{}'}])
        kinds = [s['type'] for s in sent]
        assert len(frames) == 1
        assert kinds.index('input_audio_buffer.append') < kinds.index('input_image_buffer.append') < kinds.index('input_audio_buffer.commit')
        assert kinds.count('input_image_buffer.append') == 1
        assert sent[0]['item']['type'] == 'function_call_output'
        assert session.image_commit_pending
        assert 'response.create' not in kinds  # only after the server commits the frame
    asyncio.run(run())


def test_errors_never_expose_config_secrets():
    owner = Controller(config())
    error = ExceptionGroup('network', [RuntimeError('fake-test-key'), RuntimeError('a'*64)])
    assert 'fake-test-key' not in owner.safe_error(error)
    assert 'a'*64 not in owner.safe_error(error)


def test_provisional_speech_with_tool_is_not_played_or_saved():
    async def run():
        owner = Controller(config())
        owner.generation = 12
        async def down(*args):
            pass
        owner.down = down
        session = Conversation(owner, 12)
        sent = []
        async def send(payload):
            sent.append(payload)
        session.send = send
        events = [
            {'type': 'response.created'},
            {'type': 'response.audio.delta', 'delta': base64.b64encode(bytes(9600)).decode()},
            {'type': 'response.audio.done'},
            {'type': 'response.audio_transcript.done', 'transcript': '我这就往前走'},
            {'type': 'response.function_call_arguments.done', 'call_id': 'move1', 'name': 'move', 'arguments': '{"action":"forward"}'},
            {'type': 'response.done', 'response': {'status': 'completed'}},
        ]
        class Socket:
            def __aiter__(self):
                return self
            async def __anext__(self):
                if events:
                    return json.dumps(events.pop(0))
                raise StopAsyncIteration
        session.ws = Socket()
        await session.receive()
        assert session.output.empty()
        assert owner.answer == '' and list(owner.history) == []
        result = json.loads(sent[0]['item']['output'])
        assert result['status'] == 'disabled'
        assert sent[-1]['type'] == 'response.create'
    asyncio.run(run())

@pytest.mark.parametrize('network_delays', ([0, 0, 0], [.6, 0, 0]))
def test_speaker_batches_are_paced_without_catchup_burst(monkeypatch, network_delays):
    import omni_bridge
    async def run():
        clock = [0.0]
        sent = []
        owner = Controller(config())
        session = Conversation(owner, 99)
        async def down(generation, command, packets=()):
            sent.append((command, clock[0], len(packets)))
            if command == 2:
                clock[0] += network_delays[sum(x[0] == 2 for x in sent)-1]
            if command == 3:
                raise asyncio.CancelledError()
        async def sleep(delay):
            clock[0] += delay
        monkeypatch.setattr(omni_bridge.time, 'monotonic', lambda: clock[0])
        monkeypatch.setattr(omni_bridge.asyncio, 'sleep', sleep)
        owner.down = down
        session.queue(1)
        session.queue(2, [b'opus'] * 25)
        session.queue(3)
        with pytest.raises(asyncio.CancelledError):
            await session.playback()
        assert [entry[2] for entry in sent] == [0, 10, 10, 5, 0]
        audio = sent[1:]
        for before, after in zip(audio, audio[1:]):
            assert after[1] - before[1] >= before[2] * .02 - 1e-9
    asyncio.run(run())
