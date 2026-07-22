import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from juniper_ai_assistant.accounts import AccountStore, authorize_device
from juniper_ai_assistant.access_config import load_access_profiles, write_access_config
from juniper_ai_assistant.collector import (
    load_inventory_and_access,
    resolve_credential,
    validate_command,
    validate_readonly_command,
)


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


class AccessConfigTest(unittest.TestCase):
    def test_setup_writes_two_juniper_roles(self):
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "juniper-access.local.json"
            write_access_config(
                path=path,
                readonly_username="readonly-user",
                readonly_identity_file="~/.ssh/readonly",
                superuser_username="admin-user",
                superuser_identity_file="~/.ssh/admin",
            )

            profiles = load_access_profiles(path)
            self.assertEqual(
                profiles["default"].credential_for_role("readonly").username,
                "readonly-user",
            )
            self.assertEqual(
                profiles["default"].credential_for_role("superuser").username,
                "admin-user",
            )

    def test_device_uses_access_profile_for_role_credential(self):
        with TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            inventory_path = tmp_path / "devices.local.json"
            access_path = tmp_path / "juniper-access.local.json"
            inventory_path.write_text(
                json.dumps(
                    {
                        "devices": {
                            "lab-qfx-01": {
                                "host": "192.0.2.31",
                                "access_profile": "default",
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            write_access_config(
                path=access_path,
                readonly_username="readonly-user",
                readonly_identity_file="~/.ssh/readonly",
                superuser_username="admin-user",
                superuser_identity_file="~/.ssh/admin",
            )

            devices, profiles = load_inventory_and_access(inventory_path, access_path)
            credential = resolve_credential(
                devices["lab-qfx-01"],
                profiles,
                "superuser",
            )
            self.assertEqual(credential.username, "admin-user")


if __name__ == "__main__":
    unittest.main()
