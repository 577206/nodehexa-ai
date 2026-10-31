"""CPU-side codecs. The ESP32 transports its existing 16 kHz/20 ms Opus."""
import av


class MicrophoneDecoder:
    def __init__(self):
        self.codec = av.CodecContext.create('opus', 'r')
        self.codec.open()
        self.resampler = av.AudioResampler(format='s16', layout='mono', rate=16000)

    def decode(self, packet):
        result = bytearray()
        for frame in self.codec.decode(av.Packet(packet)):
            for pcm in self.resampler.resample(frame):
                # AV planes include alignment padding, which must never become audio.
                result.extend(bytes(pcm.planes[0])[:pcm.samples * 2])
        return bytes(result)


class SpeakerEncoder:
    def __init__(self):
        self.codec = av.CodecContext.create('libopus', 'w')
        self.codec.sample_rate = 16000
        self.codec.layout = 'mono'
        self.codec.format = 's16'
        self.codec.bit_rate = 16000
        self.codec.options = {'application': 'voip', 'frame_duration': '20'}
        self.codec.open()
        self.resampler = av.AudioResampler(format='s16', layout='mono', rate=16000)
        self.pending = bytearray()

    def _frames(self):
        packets = []
        while len(self.pending) >= 640:
            frame = av.AudioFrame(format='s16', layout='mono', samples=320)
            frame.sample_rate = 16000
            frame.planes[0].update(bytes(self.pending[:640]))
            del self.pending[:640]
            packets.extend(bytes(p) for p in self.codec.encode(frame))
        return packets

    def encode(self, pcm24):
        if len(pcm24) % 2:
            raise ValueError('Unaligned PCM24 chunk')
        if not pcm24:
            return []
        frame = av.AudioFrame(format='s16', layout='mono', samples=len(pcm24)//2)
        frame.sample_rate = 24000
        frame.planes[0].update(pcm24)
        for pcm in self.resampler.resample(frame):
            self.pending.extend(bytes(pcm.planes[0])[:pcm.samples*2])
        return self._frames()

    def finish(self):
        for pcm in self.resampler.resample(None):
            self.pending.extend(bytes(pcm.planes[0])[:pcm.samples*2])
        if self.pending:
            self.pending.extend(bytes((-len(self.pending)) % 640))
        packets = self._frames()
        packets.extend(bytes(p) for p in self.codec.encode(None))
        return packets
