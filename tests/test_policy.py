import unittest

from juniper_ai_assistant.collector import validate_readonly_command


class ReadOnlyPolicyTest(unittest.TestCase):
    def test_allows_show_commands(self):
        validate_readonly_command("show route 192.0.2.0/24 extensive | no-more")

    def test_rejects_non_show_commands(self):
        with self.assertRaises(ValueError):
            validate_readonly_command("configure")

    def test_rejects_state_changing_tokens(self):
        with self.assertRaises(ValueError):
            validate_readonly_command("show system users | clear")


if __name__ == "__main__":
    unittest.main()
