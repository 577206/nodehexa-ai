#!/usr/bin/env python3
"""Request one BF3901 JPEG over the XJWB03 debug serial port."""

from __future__ import annotations

import argparse
import base64
from collections import deque
import re
import time
from pathlib import Path

import serial
from serial.tools import list_ports


def base64_fragment(line: bytes) -> bytes:
    """Keep a JPEG chunk even when a debug log interrupts its UART line."""
    match = re.match(rb"[A-Za-z0-9+/]*={0,2}", line)
    fragment = match.group() if match else b""
    remainder = line[len(fragment):]
    if re.match(rb" \([0-9]+\) ", remainder) and fragment[-1:] in (b"I", b"W", b"E", b"D", b"V"):
        fragment = fragment[:-1]
        remainder = line[len(fragment):]
    if remainder and not (remainder.startswith(b"[") or remainder.startswith(b"\x1b") or
                          re.match(rb"[IWEDV] \([0-9]+\) ", remainder)):
        return b""
    return fragment if len(fragment) <= 64 else b""


class CameraSerial:
    """Keep the serial link open for repeated snapshots without resetting the board."""

    def __init__(self, port: str):
        match = next((p for p in list_ports.comports() if p.device == port), None)
        if match is None or (match.vid, match.pid) != (0x1A86, 0x55D3):
            raise RuntimeError("Port is not the verified XJWB03 USB bridge")
        self.device = serial.Serial(port, 115200, timeout=0.5)
        self.asr_events: deque[str] = deque(maxlen=8)
        self.device.dtr = False
        self.device.rts = False
        # Opening the USB-UART bridge can reset the ESP32-S3.
        time.sleep(2.0)
        self.device.reset_input_buffer()

    def _readline(self) -> bytes:
        line = self.device.readline()
        match = re.search(rb"VISION-ASR ([A-Za-z0-9+/=]{4,256})", line)
        if match:
            try:
                raw = base64.b64decode(match.group(1), validate=True)
                text = raw.decode("utf-8")
                if 0 < len(raw) <= 180 and not any(ord(ch) < 32 for ch in text):
                    self.asr_events.append(text)
            except (ValueError, UnicodeDecodeError):
                pass
        return line

    def pop_asr_events(self) -> list[str]:
        events = list(self.asr_events)
        self.asr_events.clear()
        return events

    def close(self) -> None:
        self.device.close()

    def __enter__(self) -> CameraSerial:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def capture_jpeg(self, timeout: float = 35.0) -> bytes:
        expected = None
        chunks: list[bytes] = []
        self.device.write(b"camera snap\r")
        self.device.flush()
        attempts = 1
        last_request = time.monotonic()
        deadline = last_request + timeout
        while time.monotonic() < deadline:
            line = self._readline().strip()
            if not line:
                if expected is None and attempts < 3 and time.monotonic() - last_request > 6.0:
                    self.device.write(b"camera snap\r")
                    self.device.flush()
                    attempts += 1
                    last_request = time.monotonic()
                continue
            if b"CAMJPEG-BEGIN " in line:
                expected = int(line.split(b"CAMJPEG-BEGIN ", 1)[1].split()[0])
                chunks.clear()
                continue
            if b"CAMJPEG-ERROR" in line:
                raise RuntimeError("Camera reported a JPEG transfer error")
            if b"CAMJPEG-END" in line and expected is not None:
                try:
                    raw = base64.b64decode(b"".join(chunks), validate=True)
                except ValueError as exc:
                    raise RuntimeError("JPEG base64 transfer was corrupted") from exc
                if len(raw) != expected or not raw.startswith(b"\xff\xd8") or not raw.endswith(b"\xff\xd9"):
                    raise RuntimeError("JPEG transfer was truncated or corrupted")
                return raw
            if b"camera capture failed:" in line:
                raise RuntimeError(line.decode("utf-8", "replace"))
            if expected is not None:
                fragment = base64_fragment(line)
                if fragment:
                    chunks.append(fragment)
        raise TimeoutError("No complete camera JPEG received; check camera and serial logs")

    def send_vision_text(self, text: str, timeout: float = 6.0) -> None:
        """Queue a short UTF-8 observation for the firmware voice Agent."""
        raw = text.encode("utf-8")
        if not raw or len(raw) > 160 or any(ch < 0x20 or ch == 0x7f for ch in raw):
            raise ValueError("Visual description must be 1–160 UTF-8 bytes without control characters")
        self.device.write(b"vision " + base64.b64encode(raw) + b"\r")
        self.device.flush()
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            line = self._readline()
            if b"VISION-QUEUED" in line:
                return
            if b"VISION-UNAVAILABLE" in line:
                raise RuntimeError("灵机语音 Agent 尚未连云，或当前固件没有视觉桥接功能")
            if b"VISION-BUSY" in line:
                raise RuntimeError("灵机语音 Agent 正在处理上一条视觉消息")
            if b"VISION-ERROR" in line:
                raise RuntimeError("灵机板拒绝了视觉消息")
        raise TimeoutError("灵机板未确认视觉消息；请检查是否烧录了视觉与语音合并固件")

    def check_vision_bridge(self, timeout: float = 3.0) -> None:
        self.device.write(b"vision ping\r")
        self.device.flush()
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            line = self._readline()
            if b"VISION-READY" in line:
                return
            if b"VISION-UNAVAILABLE" in line:
                raise RuntimeError("灵机语音 Agent 尚未连云")
        raise RuntimeError("当前板上固件还没有启用视觉到语音 Agent 的桥接")

    def audio_status(self, timeout: float = 2.0) -> dict[str, bool]:
        self.device.write(b"vision status\r")
        self.device.flush()
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            line = self._readline()
            match = re.search(rb"VISION-STATUS cloud=([01]) active=([01]) uplink=([01])", line)
            if match:
                return {"cloud": match.group(1) == b"1",
                        "active": match.group(2) == b"1",
                        "uplink": match.group(3) == b"1"}
        raise TimeoutError("灵机板未返回语音隐私状态")

    def robot_action(self, action: str, timeout: float = 5.0) -> str:
        """Ask the Lingji board to execute one firmware-owned preset."""
        from interaction_intent import MOTION_ACTIONS

        if action not in MOTION_ACTIONS:
            raise ValueError("Action is outside the preset allowlist")
        self.device.write(f"robot action {action}\r".encode("ascii"))
        self.device.flush()
        deadline = time.monotonic() + timeout
        queued = False
        while time.monotonic() < deadline:
            line = self._readline()
            if b"ROBOT-OFFLINE" in line:
                raise RuntimeError("机器人串口未连接")
            if b"ROBOT-BENCH" in line:
                return "bench"
            if b"ROBOT-BUSY" in line:
                raise RuntimeError("机器人正在处理上一条动作")
            if b"ROBOT-INVALID-ACTION" in line:
                raise RuntimeError("机器人拒绝了未知动作")
            if b"ROBOT-QUEUED" in line:
                queued = True
            if b"ROBOT-ACK" in line and b"action=" + action.encode("ascii") in line:
                if b"status=success" in line:
                    return "accepted"
                if b"status=timeout" in line:
                    raise TimeoutError("机器人动作未得到确认；请检查串口和供电")
                raise RuntimeError("机器人拒绝了动作")
        raise TimeoutError("机器人未确认动作" if queued else "灵机板未确认机器人指令")

    def send_agent_feedback(self, text: str, timeout: float = 6.0) -> None:
        """Queue a confirmed action outcome for the existing voice Agent."""
        raw = text.encode("utf-8")
        if not raw or len(raw) > 160 or any(ch < 0x20 or ch == 0x7f for ch in raw):
            raise ValueError("Voice feedback must be 1–160 UTF-8 bytes")
        self.device.write(b"feedback " + base64.b64encode(raw) + b"\r")
        self.device.flush()
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            line = self._readline()
            if b"FEEDBACK-QUEUED" in line:
                return
            if b"VISION-UNAVAILABLE" in line:
                raise RuntimeError("灵犀 Agent 尚未连云")
            if b"VISION-BUSY" in line:
                raise RuntimeError("灵犀 Agent 正在处理上一条反馈")
            if line.strip().startswith(b"VISION-ERROR"):
                raise RuntimeError("灵机板拒绝了语音反馈")
        raise TimeoutError("灵机板未确认语音反馈")


def capture(port: str, output: Path, timeout: float) -> Path:
    with CameraSerial(port) as camera:
        raw = camera.capture_jpeg(timeout)
    output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    output.parent.chmod(0o700)
    output.touch(mode=0o600, exist_ok=True)
    output.chmod(0o600)
    output.write_bytes(raw)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("port", help="Explicit /dev/cu.* port for XJWB03")
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "captures" / "latest.jpg")
    parser.add_argument("--timeout", type=float, default=35.0)
    args = parser.parse_args()
    image = capture(args.port, args.output, args.timeout)
    print(f"Captured JPEG: {image} ({image.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
