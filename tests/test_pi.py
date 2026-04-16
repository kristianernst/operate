import unittest

from operate.pi import extract_final_assistant_message, parse_json_events


class PiEventTests(unittest.TestCase):
    def test_extracts_final_message_from_agent_end(self) -> None:
        stream = "\n".join(
            [
                '{"type":"session","version":3}',
                '{"type":"agent_end","messages":[{"role":"assistant","content":[{"type":"text","text":"Final report with https://example.com"}]}]}',
            ]
        )

        events = parse_json_events(stream)
        message = extract_final_assistant_message(events)

        self.assertIn("Final report", message)
        self.assertIn("https://example.com", message)

    def test_extracts_text_deltas_as_fallback(self) -> None:
        events = parse_json_events(
            "\n".join(
                [
                    '{"type":"message_update","assistantMessageEvent":{"type":"text_delta","delta":"Hello "}}',
                    '{"type":"message_update","assistantMessageEvent":{"type":"text_delta","delta":"world"}}',
                ]
            )
        )

        self.assertEqual(extract_final_assistant_message(events), "Hello world")


if __name__ == "__main__":
    unittest.main()
