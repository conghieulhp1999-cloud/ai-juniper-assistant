import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from juniper_ai_assistant.accounts import AccountStore, authorize_device
from juniper_ai_assistant.collector import validate_command, validate_readonly_command


class ReadOnlyPolicyTest(unittest.TestCase):
    def test_allows_show_commands(self):
        validate_readonly_command("show route 192.0.2.0/24 extensive | no-more")

    def test_rejects_non_show_commands(self):
        with self.assertRaises(ValueError):
            validate_readonly_command("configure")

    def test_rejects_state_changing_tokens(self):
        with self.assertRaises(ValueError):
            validate_readonly_command("show system users | clear")

    def test_superuser_requires_explicit_state_changing_flag(self):
        with self.assertRaises(ValueError):
            validate_command("configure private", role="superuser")
        validate_command(
            "configure private",
            role="superuser",
            allow_state_changing=True,
        )


class AccountStoreTest(unittest.TestCase):
    def test_register_authenticate_and_authorize_device(self):
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "accounts.local.json"
            store = AccountStore(path)
            store.register("noc-viewer", "secret", "readonly", ["lab-qfx-01"])

            account = store.authenticate("noc-viewer", "secret")
            self.assertEqual(account.role, "readonly")
            authorize_device(account, "lab-qfx-01")

            with self.assertRaises(PermissionError):
                authorize_device(account, "lab-qfx-02")

    def test_rejects_wrong_password(self):
        with TemporaryDirectory() as tmpdir:
            store = AccountStore(Path(tmpdir) / "accounts.local.json")
            store.register("network-admin", "secret", "superuser", ["*"])

            with self.assertRaises(PermissionError):
                store.authenticate("network-admin", "wrong")


if __name__ == "__main__":
    unittest.main()
