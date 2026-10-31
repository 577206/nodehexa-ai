"""Bounded native Opus transport; independent from network/model clients."""
import struct
import ipaddress
import json
from pathlib import Path
from urllib.parse import urlsplit

MAX_PACKET = 255
MAX_BATCH = 12
PRESETS = json.loads(Path(__file__).with_name('motion_presets.json').read_text())
ACTIONS = tuple(preset['id'] for preset in PRESETS)
LEGACY_ACTIONS = ('forward', 'backward', 'turn_left', 'turn_right', 'shift_left', 'shift_right', 'stop')


def validate_board_url(url):
    parsed = urlsplit(url)
    address = ipaddress.IPv4Address(parsed.hostname or '')
    if (parsed.scheme != 'http' or not address.is_private or address.is_loopback or address.is_unspecified
            or parsed.port != 8766 or parsed.path not in ('', '/') or parsed.query or parsed.fragment
            or parsed.username or parsed.password):
        raise ValueError('Board address must be a private IPv4 HTTP endpoint on port 8766')
    return url.rstrip('/')


def unpack_uplink(data: bytes):
    if len(data) < 12:
        raise ValueError('Short audio header')
    magic, generation, state, reserved, count = struct.unpack_from('<4sIBBH', data)
    if magic != b'LXA1' or state > 3 or reserved or count > MAX_BATCH:
        raise ValueError('Invalid audio header')
    offset, packets = 12, []
    for _ in range(count):
        if offset + 2 > len(data):
            raise ValueError('Truncated packet length')
        n, = struct.unpack_from('<H', data, offset)
        offset += 2
        if not 1 <= n <= MAX_PACKET or offset + n > len(data):
            raise ValueError('Invalid Opus packet length')
        packets.append(data[offset:offset+n])
        offset += n
    if offset != len(data) or (state != 1 and packets):
        raise ValueError('Trailing or idle microphone data')
    return generation, state, packets


def pack_downlink(generation: int, command: int, packets=()):
    if command not in range(1, 7) or not 0 <= generation <= 0xffffffff:
        raise ValueError('Invalid command or generation')
    if (command == 2) != bool(packets) or len(packets) > MAX_BATCH:
        raise ValueError('Invalid command packet count')
    result = bytearray(struct.pack('<IB', generation, command))
    for packet in packets:
        if not 1 <= len(packet) <= MAX_PACKET:
            raise ValueError('Invalid Opus packet size')
        result += struct.pack('<H', len(packet)) + packet
    return bytes(result)


def validate_action(arguments):
    if not isinstance(arguments, dict) or set(arguments) != {'action'} or arguments['action'] not in ACTIONS:
        raise ValueError('Only named, bounded movement presets are allowed')
    return arguments['action']
