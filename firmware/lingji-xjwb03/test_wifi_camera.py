import json
import unittest
from collections import deque

from wifi_camera import CameraWifi


class WifiCameraTests(unittest.TestCase):
    def make_camera(self):
        camera = CameraWifi.__new__(CameraWifi)
        camera.asr_events = deque(maxlen=8)
        camera.agent_events = deque(maxlen=8)
        camera._asr_sequence = None
        return camera

    def test_asr_event_is_delivered_once_after_sequence_changes(self):
        camera = self.make_camera()
        statuses = iter([
            {"protocol": 1, "asrSequence": 10, "asrText": "旧的请求"},
            {"protocol": 1, "asrSequence": 11, "asrText": "请看当前画面"},
            {"protocol": 1, "asrSequence": 11, "asrText": "请看当前画面"},
        ])
        camera._request = lambda *_args, **_kwargs: json.dumps(next(statuses)).encode()
        camera._status()
        self.assertEqual(camera.pop_asr_events(), [])
        camera._status()
        camera._status()
        self.assertEqual(camera.pop_asr_events(), ["请看当前画面"])

    def test_invalid_jpeg_is_rejected_before_vision_api(self):
        camera = self.make_camera()
        camera._request = lambda *_args, **_kwargs: b"not a jpeg"
        with self.assertRaisesRegex(RuntimeError, "JPEG"):
            camera.capture_jpeg()

    def test_motion_is_blocked_when_robot_is_offline(self):
        camera = self.make_camera()
        camera._status = lambda: {"robot": {"online": False}}
        camera._request = lambda *_args, **_kwargs: self.fail("offline motion was sent")
        with self.assertRaisesRegex(RuntimeError, "串口未连接"):
            camera.robot_action("forward")


if __name__ == "__main__":
    unittest.main()
