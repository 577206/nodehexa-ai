"""Authenticated LAN transport for the XJWB03 camera and voice bridge."""

from __future__ import annotations

import ipaddress
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import deque


class CameraWifi:
    def __init__(self, base_url: str, token: str):
        parsed = urllib.parse.urlsplit(base_url)
        try:
            address = ipaddress.ip_address(parsed.hostname or "")
        except ValueError as exc:
            raise ValueError("灵机板地址必须是局域网 IPv4 地址") from exc
        if (parsed.scheme != "http" or not address.is_private or address.is_loopback or
                parsed.port != 8766 or parsed.path not in ("", "/") or
                parsed.query or parsed.fragment or parsed.username or parsed.password):
            raise ValueError("灵机板地址应为 http://局域网IP:8766")
        if len(token) != 64 or any(ch not in "0123456789abcdef" for ch in token):
            raise ValueError("本机局域网鉴权令牌无效")
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        self.asr_events: deque[str] = deque(maxlen=8)
        self.agent_events: deque[str] = deque(maxlen=8)
        self._asr_sequence: int | None = None
        self._status()

    def __enter__(self) -> CameraWifi:
        return self

    def __exit__(self, *_args: object) -> None:
        pass

    def _request(self, path: str, payload: dict | None = None, timeout: float = 8) -> bytes:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(
            self.base_url + path,
            data=body,
            method="POST" if body is not None else "GET",
            headers={"X-Lingxi-Token": self.token,
                     "Content-Type": "application/json"} if body is not None else
                    {"X-Lingxi-Token": self.token},
        )
        try:
            with self.opener.open(request, timeout=timeout) as reply:
                data = reply.read(300_000)
                if len(data) >= 300_000:
                    raise ValueError("灵机板响应过大")
                return data
        except urllib.error.HTTPError as exc:
            if exc.code == 403:
                raise RuntimeError("灵机板拒绝局域网鉴权，请重新核对令牌") from None
            raise RuntimeError(f"灵机板接口返回 HTTP {exc.code}") from None

    def _status(self) -> dict:
        data = json.loads(self._request("/api/status", timeout=3))
        if data.get("protocol") != 1:
            raise RuntimeError("灵机板 Wi-Fi 桥接协议不兼容")
        sequence = data.get("asrSequence", 0)
        text = data.get("asrText", "")
        if self._asr_sequence is not None and sequence != self._asr_sequence and isinstance(text, str) and text:
            self.asr_events.append(text)
        self._asr_sequence = sequence
        return data

    def capture_jpeg(self, timeout: float = 18) -> bytes:
        raw = self._request("/api/frame.jpg", timeout=timeout)
        if not (4 <= len(raw) <= 256 * 1024 and raw.startswith(b"\xff\xd8") and raw.endswith(b"\xff\xd9")):
            raise RuntimeError("灵机板返回的 JPEG 不完整")
        return raw

    def pop_asr_events(self) -> list[str]:
        events = list(self.asr_events)
        self.asr_events.clear()
        return events

    def pop_agent_events(self) -> list[str]:
        events = list(self.agent_events)
        self.agent_events.clear()
        return events

    def audio_status(self) -> dict[str, bool]:
        state = self._status()
        return {key: bool(state.get(key)) for key in ("cloud", "active", "uplink", "auth")}

    def check_vision_bridge(self) -> None:
        if not self._status().get("cloud"):
            raise RuntimeError("灵机语音 Agent 尚未连云")

    def send_vision_text(self, text: str) -> None:
        self._speak(text)

    def send_agent_feedback(self, text: str) -> None:
        self._speak(text)

    def _speak(self, text: str) -> None:
        raw = text.encode("utf-8")
        if not raw or len(raw) > 160 or any(ch < 0x20 or ch == 0x7F for ch in raw):
            raise ValueError("播报文字须为 1–160 字节且不能含控制字符")
        response = json.loads(self._request("/api/speak", {"text": text}, timeout=6))
        if response.get("status") != "queued":
            raise RuntimeError("灵机板未接受播报请求")

    def robot_action(self, action: str, timeout: float = 5) -> str:
        from interaction_intent import MOTION_ACTIONS

        if action not in MOTION_ACTIONS:
            raise ValueError("动作不在板端预设名单中")
        before = self._status()
        robot = before.get("robot") or {}
        if not robot.get("online"):
            raise RuntimeError("机器人串口未连接")
        if robot.get("bench") and action != "stop":
            return "bench"
        ack_sequence = robot.get("ackSequence", 0)
        response = json.loads(self._request("/api/motion", {"action": action}, timeout=3))
        if response.get("status") != "queued":
            raise RuntimeError("机器人动作没有进入发送队列")
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            current = (self._status().get("robot") or {})
            if current.get("ackSequence") != ack_sequence and current.get("ackAction") == action:
                if current.get("ackSuccess"):
                    return "accepted"
                raise RuntimeError("机器人板拒绝了动作")
            time.sleep(0.15)
        raise TimeoutError("机器人动作未得到确认")
