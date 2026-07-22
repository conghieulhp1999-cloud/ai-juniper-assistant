from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from dataclasses import dataclass
from pathlib import Path


PBKDF2_ITERATIONS = 390000


@dataclass(frozen=True)
class Account:
    username: str
    role: str
    devices: set[str]


def hash_password(password: str, salt: bytes | None = None) -> str:
    if salt is None:
        salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    return "pbkdf2_sha256${}${}${}".format(
        PBKDF2_ITERATIONS,
        base64.b64encode(salt).decode("ascii"),
        base64.b64encode(digest).decode("ascii"),
    )


def verify_password(password: str, stored_hash: str) -> bool:
    algorithm, iterations, salt_b64, digest_b64 = stored_hash.split("$", 3)
    if algorithm != "pbkdf2_sha256":
        raise ValueError(f"Unsupported password hash algorithm: {algorithm}")

    salt = base64.b64decode(salt_b64)
    expected = base64.b64decode(digest_b64)
    actual = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        int(iterations),
    )
    return hmac.compare_digest(actual, expected)


class AccountStore:
    def __init__(self, path: str | Path):
        self.path = Path(path).expanduser()

    def load_raw(self) -> dict:
        if not self.path.exists():
            return {"accounts": {}}
        with self.path.open("r", encoding="utf-8") as fh:
            return json.load(fh)

    def save_raw(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
            fh.write("\n")
        self.path.chmod(0o600)

    def register(self, username: str, password: str, role: str, devices: list[str]) -> None:
        if role not in {"readonly", "superuser"}:
            raise ValueError("Role must be readonly or superuser.")

        data = self.load_raw()
        accounts = data.setdefault("accounts", {})
        if username in accounts:
            raise ValueError(f"Account already exists: {username}")

        accounts[username] = {
            "password_hash": hash_password(password),
            "role": role,
            "devices": sorted(set(devices)),
        }
        self.save_raw(data)

    def authenticate(self, username: str, password: str) -> Account:
        data = self.load_raw()
        raw_account = data.get("accounts", {}).get(username)
        if not raw_account:
            raise PermissionError("Invalid username or password.")
        if not verify_password(password, raw_account["password_hash"]):
            raise PermissionError("Invalid username or password.")
        return Account(
            username=username,
            role=raw_account["role"],
            devices=set(raw_account.get("devices", [])),
        )


def authorize_device(account: Account, device_name: str) -> None:
    if "*" in account.devices or device_name in account.devices:
        return
    raise PermissionError(f"Account {account.username} is not allowed on {device_name}.")
