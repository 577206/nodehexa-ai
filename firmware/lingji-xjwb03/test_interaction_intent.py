"""Contract tests for the model-to-robot boundary."""

import unittest
from unittest.mock import patch

from interaction_intent import Intent, classify, parse_intent


def reply(kind: str, action: str) -> dict:
    return {"choices": [{"message": {"content":
            f'{{"kind":"{kind}","action":"{action}"}}'}}]}


class IntentContractTest(unittest.TestCase):
    def test_allowlisted_motion_and_vision(self):
        self.assertEqual(parse_intent(reply("motion", "forward")),
                         Intent("motion", "forward"))
        self.assertEqual(parse_intent(reply("vision", "")), Intent("vision"))

    def test_model_cannot_supply_raw_command_or_speed(self):
        for bad in (reply("motion", "forward_fast"),
                    reply("motion", '{"movementMode":2}'),
                    reply("chat", "forward"),
                    {"choices": [{"message": {"content":
                        '{"kind":"motion","action":"forward","speed":10}'}}]}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                parse_intent(bad)

    def test_short_stop_is_local(self):
        with patch("interaction_intent.urllib.request.urlopen") as request:
            self.assertEqual(classify("停下！", "unused", "https://example.com/v1", "model"),
                             Intent("motion", "stop"))
            request.assert_not_called()

    def test_invalid_json_fails_closed(self):
        with self.assertRaises(ValueError):
            parse_intent({"choices": [{"message": {"content": "```json\n{}\n```"}}]})


if __name__ == "__main__":
    unittest.main()
