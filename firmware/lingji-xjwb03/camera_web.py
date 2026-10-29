#!/usr/bin/env python3
"""Loopback-only BF3901 preview; Qwen runs only after a button click."""

from __future__ import annotations

import argparse
import json
import queue
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from capture_camera import CameraSerial
from interaction_intent import classify
from vision_qwen import DEFAULT_BASE_URL, DEFAULT_MODEL, analyze, load_local_config

PAGE = Path(__file__).with_name("camera_dashboard.html")
STALE_SECONDS = 12.0


class CameraState:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.serial_lock = threading.Lock()
        self.camera: CameraSerial | None = None
        self.frame: bytes | None = None
        self.frame_at = 0.0
        self.sequence = 0
        self.error = "等待摄像头启动"
        self.analyzing = False
        self.last_analysis_at = 0.0
        self.result: str | None = None
        self.asr_queue: queue.Queue[str] = queue.Queue(maxsize=4)
        self.voice_vision_status = "待机：唤醒后才判断视觉请求"
        self.agent_delivery = "尚无主动播报请求"
        self.audio_status: dict[str, bool] | None = None
        self.last_asr_at = 0.0
        self.last_asr_text = ""

    def publish(self, frame: bytes) -> None:
        with self.lock:
            self.frame = frame
            self.frame_at = time.time()
            self.sequence += 1
            self.error = ""

    def fail(self, message: str) -> None:
        with self.lock:
            self.error = message[:180]

    def status(self) -> dict:
        with self.lock:
            age = round(time.time() - self.frame_at, 1) if self.frame is not None else None
            return {
                "ready": age is not None and age < STALE_SECONDS,
                "sequence": self.sequence,
                "age_seconds": age,
                "bytes": len(self.frame) if self.frame is not None else 0,
                "error": self.error,
                "analyzing": self.analyzing,
                "last_analysis_at": self.last_analysis_at,
                "result": self.result,
                "voice_vision_status": self.voice_vision_status,
                "agent_delivery": self.agent_delivery,
                "audio_status": self.audio_status,
                "last_wake_text": self.last_asr_text if time.monotonic() - self.last_asr_at < 60 else "",
            }

    def submit_asr(self, text: str) -> None:
        now = time.monotonic()
        with self.lock:
            if text == self.last_asr_text and now - self.last_asr_at < 3.0:
                return
            self.last_asr_text = text
            self.last_asr_at = now
        try:
            self.asr_queue.put_nowait(text)
        except queue.Full:
            with self.lock:
                self.voice_vision_status = "语音请求过多，请稍后再试"

    def set_voice_status(self, value: str) -> None:
        with self.lock:
            self.voice_vision_status = value

    def set_agent_delivery(self, value: str) -> None:
        with self.lock:
            self.agent_delivery = value

    def begin_analysis(self) -> bool:
        with self.lock:
            if self.analyzing:
                return False
            self.analyzing = True
            return True

    def end_analysis(self) -> None:
        with self.lock:
            self.analyzing = False

    def current_frame(self) -> bytes | None:
        with self.lock:
            if self.frame is None or time.time() - self.frame_at >= STALE_SECONDS:
                return None
            return self.frame

    def send_to_agent(self, description: str) -> None:
        with self.serial_lock:
            if self.camera is None:
                raise RuntimeError("灵机板串口尚未连接")
            self.camera.send_vision_text(description)

    def require_agent_bridge(self) -> None:
        with self.serial_lock:
            if self.camera is None:
                raise RuntimeError("灵机板串口尚未连接")
            self.camera.check_vision_bridge()

    def send_robot_action(self, action: str) -> str:
        with self.serial_lock:
            if self.camera is None:
                raise RuntimeError("灵机板串口尚未连接")
            return self.camera.robot_action(action)

    def send_agent_feedback(self, text: str) -> None:
        with self.serial_lock:
            if self.camera is None:
                raise RuntimeError("灵机板串口尚未连接")
            self.camera.send_agent_feedback(text)


def spoken_answer(answer: str) -> str:
    """The board's speak endpoint reads this text literally, so send only an answer."""
    clean = " ".join(answer.split())
    if not clean or any(marker in clean for marker in
                        ("【视觉结果】", "问题：", "依据：", "请针对原问题")):
        raise ValueError("视觉模型没有给出可直接播报的答案")
    raw = clean.encode("utf-8")
    if len(raw) <= 160:
        return clean
    return raw[:157].decode("utf-8", "ignore").rstrip("，、。 ") + "…"


def capture_loop(state: CameraState, port: str, stop: threading.Event) -> None:
    while not stop.is_set():
        try:
            with CameraSerial(port) as camera:
                with state.serial_lock:
                    state.camera = camera
                try:
                    frames = 0
                    while not stop.is_set():
                        frame = None
                        with state.serial_lock:
                            try:
                                frame = camera.capture_jpeg(timeout=18)
                            except RuntimeError as exc:
                                if "camera capture failed: ESP_ERR_INVALID_STATE" not in str(exc):
                                    raise
                                state.fail("摄像头流尚未就绪，等待开发板完成初始化")
                            finally:
                                events = camera.pop_asr_events()
                                agent_events = camera.pop_agent_events()
                        for text in events:
                            state.submit_asr(text)
                        for event in agent_events:
                            state.set_agent_delivery(event)
                        if frame is None:
                            try:
                                with state.serial_lock:
                                    audio = camera.audio_status()
                                    events = camera.pop_asr_events()
                                    agent_events = camera.pop_agent_events()
                                with state.lock:
                                    state.audio_status = audio
                                for text in events:
                                    state.submit_asr(text)
                                for event in agent_events:
                                    state.set_agent_delivery(event)
                            except TimeoutError:
                                with state.lock:
                                    state.audio_status = None
                            stop.wait(2.0)
                            continue
                        state.publish(frame)
                        frames += 1
                        if frames % 5 == 0:
                            try:
                                with state.serial_lock:
                                    audio = camera.audio_status()
                                    events = camera.pop_asr_events()
                                    agent_events = camera.pop_agent_events()
                                with state.lock:
                                    state.audio_status = audio
                                for text in events:
                                    state.submit_asr(text)
                                for event in agent_events:
                                    state.set_agent_delivery(event)
                            except TimeoutError:
                                with state.lock:
                                    state.audio_status = None
                        stop.wait(0.2)
                finally:
                    with state.serial_lock:
                        state.camera = None
        except (OSError, RuntimeError, TimeoutError, ValueError) as exc:
            state.fail(str(exc))
            stop.wait(2.0)


def voice_intent_loop(state: CameraState, stop: threading.Event) -> None:
    while not stop.is_set():
        try:
            utterance = state.asr_queue.get(timeout=0.5)
        except queue.Empty:
            continue
        state.set_voice_status("正在判断语音请求…")
        try:
            settings = load_local_config()
            key = settings.get("DASHSCOPE_API_KEY", "").strip()
            if not key or key == "REPLACE_WITH_YOUR_KEY":
                raise RuntimeError("请先在 .env.local 填写千问 API Key")
            base_url = settings.get("DASHSCOPE_BASE_URL") or DEFAULT_BASE_URL
            model = settings.get("DASHSCOPE_VISION_MODEL") or DEFAULT_MODEL
            intent = classify(utterance, key, base_url, model)
            if intent.kind == "chat":
                state.set_voice_status("普通对话：无需摄像头或机器人动作")
                continue
            if intent.kind == "motion":
                state.set_voice_status(f"识别到机器人动作：{intent.action}，等待执行确认…")
                names = {
                    "forward": "前进", "backward": "后退", "turn_left": "左转",
                    "turn_right": "右转", "shift_left": "左移",
                    "shift_right": "右移", "stop": "停止",
                }
                name = names[intent.action]
                try:
                    outcome = state.send_robot_action(intent.action)
                    if outcome == "bench":
                        result = f"用户要求{name}；机器人在台架模式，舵机关闭，本次没有移动"
                        spoken = "现在是台架模式，舵机已关闭，我还不能移动。"
                    elif intent.action == "stop":
                        result = "用户要求停止；机器人板已确认停止指令"
                        spoken = "收到，机器人已经停止。"
                    else:
                        result = f"用户要求{name}；机器人板已接受有限周期预设动作，尚未确认完成"
                        spoken = f"收到，机器人已开始{name}，动作完成情况还在确认。"
                except (OSError, RuntimeError, ValueError, TimeoutError) as exc:
                    result = f"用户要求{name}；机器人动作未确认，本次不要声称已经移动"
                    spoken = "我还没收到机器人板的确认，这次先不移动。"
                    state.set_voice_status(f"机器人动作未确认：{str(exc)[:90]}")
                state.send_agent_feedback(spoken)
                state.set_agent_delivery("动作状态已排队，等待语音 Agent 回执")
                state.set_voice_status(f"机器人动作状态：{result}")
                continue
            state.set_voice_status("识别到视觉请求，正在查看当前画面…")
            state.require_agent_bridge()
            deadline = time.monotonic() + 15.0
            while not state.begin_analysis():
                if stop.wait(0.2) or time.monotonic() >= deadline:
                    raise RuntimeError("上一项视觉识别尚未结束")
            try:
                frame = state.current_frame()
                if frame is None:
                    raise RuntimeError("摄像头尚无新鲜画面")
                result = analyze(frame, key, base_url, model,
                                 brief=True, question=utterance)
                state.send_to_agent(spoken_answer(result))
                state.set_agent_delivery("画面短答已排队，等待喇叭播报回执")
                with state.lock:
                    state.result = result
                    state.last_analysis_at = time.time()
                state.set_voice_status("画面识别完成，等待短答播报")
            finally:
                state.end_analysis()
        except (OSError, RuntimeError, ValueError, KeyError, IndexError) as exc:
            state.set_voice_status(f"视觉请求未完成：{str(exc)[:100]}")
        finally:
            state.asr_queue.task_done()


def handler_for(state: CameraState) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def respond(self, status: int, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; img-src 'self' data:")
            self.end_headers()
            self.wfile.write(body)

        def send_json(self, status: int, value: dict) -> None:
            self.respond(status, json.dumps(value, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

        def do_GET(self) -> None:
            path = self.path.split("?", 1)[0]
            if path == "/":
                self.respond(200, PAGE.read_bytes(), "text/html; charset=utf-8")
            elif path == "/status":
                self.send_json(200, state.status())
            elif path == "/frame.jpg":
                frame = state.current_frame()
                if frame is None:
                    self.send_json(503, {"error": "还没有新鲜画面"})
                else:
                    self.respond(200, frame, "image/jpeg")
            else:
                self.send_json(404, {"error": "未找到页面"})

        def do_POST(self) -> None:
            if self.path not in ("/analyze", "/talk"):
                self.send_json(404, {"error": "未找到接口"})
                return
            allowed_origins = (None,
                               f"http://127.0.0.1:{self.server.server_port}",
                               f"http://localhost:{self.server.server_port}")
            if self.headers.get("Origin") not in allowed_origins:
                self.send_json(403, {"error": "仅允许本机页面发起识别"})
                return
            frame = state.current_frame()
            if frame is None:
                self.send_json(409, {"error": "摄像头尚无新鲜画面"})
                return
            if not state.begin_analysis():
                self.send_json(409, {"error": "上一次识别还在进行"})
                return
            result = None
            try:
                talk = self.path == "/talk"
                if talk:
                    state.require_agent_bridge()
                settings = load_local_config()
                key = settings.get("DASHSCOPE_API_KEY", "").strip()
                if not key or key == "REPLACE_WITH_YOUR_KEY":
                    raise RuntimeError("请先在 .env.local 填写模型 API Key")
                base_url = settings.get("DASHSCOPE_BASE_URL") or DEFAULT_BASE_URL
                model = settings.get("DASHSCOPE_VISION_MODEL") or DEFAULT_MODEL
                result = analyze(frame, key, base_url, model, brief=talk)
                with state.lock:
                    state.result = result
                    state.last_analysis_at = time.time()
                if talk:
                    state.send_to_agent(spoken_answer(result))
                self.send_json(200, {"result": result, "agent_queued": talk})
            except (OSError, RuntimeError, ValueError, KeyError, IndexError) as exc:
                self.send_json(502, {"error": str(exc)[:180], "result": result})
            finally:
                state.end_analysis()

        def log_message(self, format: str, *args: object) -> None:
            # Do not log captured images, keys, or model response bodies.
            if self.path.split("?", 1)[0] not in ("/status", "/frame.jpg"):
                super().log_message(format, *args)

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("port", help="Explicit /dev/cu.* XJWB03 serial port")
    parser.add_argument("--http-port", type=int, default=8765)
    args = parser.parse_args()
    state = CameraState()
    stop = threading.Event()
    worker = threading.Thread(target=capture_loop, args=(state, args.port, stop), daemon=True)
    intent_worker = threading.Thread(target=voice_intent_loop, args=(state, stop), daemon=True)
    server = ThreadingHTTPServer(("127.0.0.1", args.http_port), handler_for(state))
    worker.start()
    intent_worker.start()
    print(f"Camera preview: http://127.0.0.1:{args.http_port}/", flush=True)
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        server.server_close()


if __name__ == "__main__":
    main()
