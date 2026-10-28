"""Serial command acknowledgement contract without opening a real USB port."""

import unittest

from capture_camera import CameraSerial


class FakeSerial:
    def __init__(self):
        self.writes = []

    def write(self, data):
        self.writes.append(data)

    def flush(self):
        pass


def camera_with(*lines):
    camera = CameraSerial.__new__(CameraSerial)
    camera.device = FakeSerial()
    responses = iter(lines)
    camera._readline = lambda: next(responses, b"")
    return camera


class CameraCommandTest(unittest.TestCase):
    def test_bench_reply_does_not_claim_movement(self):
        camera = camera_with(b"ROBOT-BENCH action=forward\r\n")
        self.assertEqual(camera.robot_action("forward"), "bench")
        self.assertEqual(camera.device.writes, [b"robot action forward\r"])

    def test_stop_requires_robot_ack(self):
        camera = camera_with(b"ROBOT-QUEUED action=stop\r\n",
                             b"ROBOT-ACK seq=7 status=success action=stop\r\n")
        self.assertEqual(camera.robot_action("stop"), "accepted")

    def test_feedback_log_does_not_override_queue_ack(self):
        camera = camera_with(b"[007420]<W> VISION-ERROR agent ret=-12\r\n",
                             b"FEEDBACK-QUEUED\r\n")
        camera.send_agent_feedback("台架模式")
        self.assertTrue(camera.device.writes[0].startswith(b"feedback "))

    def test_unknown_action_is_never_sent(self):
        camera = camera_with()
        with self.assertRaises(ValueError):
            camera.robot_action("arbitrary_pwm")
        self.assertEqual(camera.device.writes, [])


if __name__ == "__main__":
    unittest.main()
