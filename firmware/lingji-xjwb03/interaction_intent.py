"""Route one wake-triggered utterance to chat, camera, or a fixed robot action.

Qwen only chooses a symbolic intent. It cannot supply UART JSON, speed, or
movement duration; those are fixed in the XJWB03 firmware.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import urllib.error
import urllib.request

from vision_qwen import endpoint

MOTION_ACTIONS = frozenset({
    "forward", "backward", "turn_left", "turn_right",
    "shift_left", "shift_right", "stop",
})
STOP_UTTERANCES = frozenset({
    "停", "停下", "停下来", "停住", "停止", "别动", "不要动了", "别走了",
})
PROMPT = (
    "你是桌面六足机器人唤醒后的意图路由器。只输出一个 JSON 对象，"
    "格式为 {\"kind\":\"chat|vision|motion\",\"action\":\"...\"}。"
    "用户要求当前摄像头看物体、环境、外观、坐姿等，kind=vision、action为空字符串。"
    "明确要求机器人本体移动时 kind=motion，action 只能是 forward、backward、"
    "turn_left、turn_right、shift_left、shift_right、stop 之一。"
    "停止、别动、不要再走优先选择 stop，即使同时提到其他动作。"
    "询问运动方法、讲故事、回忆旧画面、描述别人的运动、否定移动命令等属于 chat。"
    "用户要你自己走但方向不明时属于 chat。不要输出代码、解释、距离或速度。"
)


@dataclass(frozen=True)
class Intent:
    kind: str
    action: str = ""


def parse_intent(response: dict) -> Intent:
    content = response["choices"][0]["message"]["content"]
    if not isinstance(content, str):
        raise ValueError("Qwen returned a non-text intent")
    raw = json.loads(content)
    if not isinstance(raw, dict) or set(raw) != {"kind", "action"}:
        raise ValueError("Qwen intent shape is invalid")
    kind, action = raw["kind"], raw["action"]
    if not isinstance(kind, str) or not isinstance(action, str):
        raise ValueError("Qwen intent field type is invalid")
    if kind in ("chat", "vision") and action == "":
        return Intent(kind)
    if kind == "motion" and action in MOTION_ACTIONS:
        return Intent(kind, action)
    raise ValueError("Qwen intent is outside the action allowlist")


def classify(text: str, api_key: str, base_url: str, model: str) -> Intent:
    if not text or len(text.encode("utf-8")) > 180:
        raise ValueError("ASR text must be 1–180 UTF-8 bytes")
    normalized = text.strip().rstrip("。！!，, ")
    if normalized in STOP_UTTERANCES:
        return Intent("motion", "stop")
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": PROMPT},
            {"role": "user", "content": text},
        ],
        "temperature": 0,
        "max_tokens": 80,
        "enable_thinking": False,
        "stream": False,
    }
    request = urllib.request.Request(
        endpoint(base_url),
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers={"Authorization": "Bearer " + api_key,
                 "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as reply:
            response = json.load(reply)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Qwen intent HTTP {exc.code}") from None
    return parse_intent(response)
