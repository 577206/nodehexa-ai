"""The speak endpoint receives final speech, never instructions or context wrappers."""

import unittest

from camera_web import spoken_answer


class SpokenAnswerTest(unittest.TestCase):
    def test_short_visual_answer_is_sent_unchanged(self):
        self.assertEqual(spoken_answer("画面里有一盏灯和一根红色管道。"),
                         "画面里有一盏灯和一根红色管道。")

    def test_context_wrapper_is_rejected(self):
        with self.assertRaises(ValueError):
            spoken_answer("【视觉结果】问题：有什么；依据：一盏灯")

    def test_long_answer_stays_within_serial_limit(self):
        answer = spoken_answer("画面里有很多书和一盏灯。" * 12)
        self.assertLessEqual(len(answer.encode("utf-8")), 160)


if __name__ == "__main__":
    unittest.main()
