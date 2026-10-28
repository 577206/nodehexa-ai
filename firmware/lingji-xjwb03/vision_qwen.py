#!/usr/bin/env python3
"""Ask Qwen to describe one local JPEG in natural language."""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

DEFAULT_BASE_URL = "https://cn-beijing.maas.qianwenaiapi.com/compatible-mode/v1"
DEFAULT_MODEL = "qwen3.8-flash"
LOCAL_CONFIG = Path(__file__).with_name(".env.local")
MAX_IMAGE_BYTES = 5 * 1024 * 1024

SYSTEM_PROMPT = """你是桌面陪伴机器人的视觉观察模块。请用一小段通顺的中文描述这张照片中直接看得到的场景、主要物体和明显颜色。看不清的部分就说不确定，不要猜测画面外的事、人物身份或情绪。只描述画面，不给坐姿评价或行动建议。不要使用 Markdown、标题、列表或星号。"""
BRIEF_PROMPT = """你是桌面陪伴机器人的视觉观察模块。请用一句不超过45个汉字的自然中文概括照片里直接可见的场景和主要物体。看不清就说不确定，不猜测身份、情绪或画面外的事，不给行动建议。不要使用 Markdown。"""
VOICE_QUESTION_PROMPT = """你是桌面陪伴机器人的视觉观察模块。根据这张实时照片回答用户提出的画面相关问题，用一句简短自然的中文，只说能直接看见的内容。看不清就明确说不确定；不要猜测身份、情绪或画面外的事，不要使用 Markdown。"""


def load_jpeg(path: Path) -> bytes:
    data = path.read_bytes()
    if not 4 <= len(data) <= MAX_IMAGE_BYTES:
        raise ValueError("JPEG size is invalid or exceeds 5 MiB")
    if not data.startswith(b"\xff\xd8") or not data.endswith(b"\xff\xd9"):
        raise ValueError("Input is not a complete JPEG")
    return data


def endpoint(base_url: str) -> str:
    parsed = urlparse(base_url)
    host = parsed.hostname or ""
    trusted_host = host == "cn-beijing.maas.qianwenaiapi.com" or host.endswith(".aliyuncs.com")
    if (parsed.scheme != "https" or not trusted_host or
            parsed.username or parsed.password or parsed.query or parsed.fragment or
            parsed.path.rstrip("/") != "/compatible-mode/v1"):
        raise ValueError("Base URL must be a supported HTTPS compatible-mode/v1 endpoint")
    return base_url.rstrip("/") + "/chat/completions"


def load_local_config(path: Path = LOCAL_CONFIG) -> dict[str, str]:
    """Read only the three expected settings; never execute a secrets file."""
    if not path.exists():
        return {}
    allowed = {"DASHSCOPE_API_KEY", "DASHSCOPE_BASE_URL", "DASHSCOPE_VISION_MODEL"}
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        name, sep, value = line.partition("=")
        if not sep or name.strip() not in allowed:
            raise ValueError(f"Invalid setting in {path.name}; use NAME=value")
        result[name.strip()] = value.strip().strip('"\'')
    return result


def request_payload(jpeg: bytes, model: str, brief: bool = False,
                    question: str | None = None) -> dict:
    image_data = base64.b64encode(jpeg).decode("ascii")
    if question is not None and len(question.encode("utf-8")) > 180:
        raise ValueError("Visual question exceeds 180 UTF-8 bytes")
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": VOICE_QUESTION_PROMPT if question else
             (BRIEF_PROMPT if brief else SYSTEM_PROMPT)},
            {"role": "user", "content": [
                {"type": "text", "text": question or "请描述当前这张摄像头画面里看到了什么。"},
                {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + image_data}},
            ]},
        ],
        "temperature": 0.2,
        "max_tokens": 120 if brief else 500,
        "enable_thinking": False,
        "stream": False,
    }


def parse_result(response: dict) -> str:
    content = response["choices"][0]["message"]["content"]
    if not isinstance(content, str):
        raise ValueError("Qwen returned a non-text response")
    content = content.strip()
    if not content:
        raise ValueError("Qwen returned an empty description")
    return content


def analyze(jpeg: bytes, api_key: str, base_url: str, model: str,
            brief: bool = False, question: str | None = None) -> str:
    body = json.dumps(request_payload(jpeg, model, brief, question), ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        endpoint(base_url), data=body, method="POST",
        headers={"Authorization": "Bearer " + api_key, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as reply:
            response = json.load(reply)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Qwen HTTP {exc.code}; check API key, region and model access") from None
    return parse_result(response)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path, help="A local JPEG captured from BF3901")
    parser.add_argument("--dry-run", action="store_true", help="Validate request without sending the image")
    args = parser.parse_args()

    jpeg = load_jpeg(args.image)
    local = load_local_config()
    base_url = local.get("DASHSCOPE_BASE_URL") or os.environ.get("DASHSCOPE_BASE_URL", DEFAULT_BASE_URL)
    url = endpoint(base_url)
    model = local.get("DASHSCOPE_VISION_MODEL") or os.environ.get("DASHSCOPE_VISION_MODEL", DEFAULT_MODEL)
    if args.dry_run:
        print(json.dumps({"ready": True, "bytes": len(jpeg), "model": model, "endpoint": url}, ensure_ascii=False))
        return 0

    local_key = local.get("DASHSCOPE_API_KEY", "").strip()
    if local_key == "REPLACE_WITH_YOUR_KEY":
        local_key = ""
    api_key = local_key or os.environ.get("DASHSCOPE_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Fill DASHSCOPE_API_KEY in .env.local; never paste it in chat")
    print(analyze(jpeg, api_key, base_url, model))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, IndexError, RuntimeError) as exc:
        print(f"Vision analysis failed: {exc}", file=sys.stderr)
        sys.exit(1)
