from __future__ import annotations

import argparse
import getpass
import json
import sys

from .accounts import AccountStore, authorize_device
from .collector import collect, load_inventory


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Authorize users and run Junos commands through role-based SSH credentials."
    )
    subparsers = parser.add_subparsers(dest="action", required=True)

    register = subparsers.add_parser("register-user", help="Register a Hermes user.")
    register.add_argument("--accounts", required=True, help="Path to local accounts JSON.")
    register.add_argument("--username", required=True, help="Hermes login username.")
    register.add_argument(
        "--role",
        required=True,
        choices=["readonly", "superuser"],
        help="Role assigned after login.",
    )
    register.add_argument(
        "--device",
        action="append",
        required=True,
        help="Allowed device name. May be repeated. Use '*' for all devices.",
    )

    run = subparsers.add_parser("run-command", help="Run a command as a logged-in user.")
    run.add_argument("--inventory", required=True, help="Path to inventory JSON.")
    run.add_argument("--accounts", required=True, help="Path to local accounts JSON.")
    run.add_argument("--username", required=True, help="Hermes login username.")
    run.add_argument("--device", required=True, help="Device name from inventory.")
    run.add_argument(
        "--command",
        action="append",
        required=True,
        help="Junos command. May be repeated.",
    )
    run.add_argument(
        "--allow-state-changing",
        action="store_true",
        help="Allow non-show commands for authenticated superuser accounts.",
    )
    run.add_argument(
        "--json",
        action="store_true",
        help="Print structured JSON instead of plain command output.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.action == "register-user":
        password = getpass.getpass("Password: ")
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("Passwords do not match.", file=sys.stderr)
            return 1
        try:
            AccountStore(args.accounts).register(
                username=args.username,
                password=password,
                role=args.role,
                devices=args.device,
            )
        except Exception as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(f"Registered {args.username} as {args.role}.")
        return 0

    devices = load_inventory(args.inventory)
    if args.device not in devices:
        print(f"Unknown device: {args.device}", file=sys.stderr)
        return 2

    password = getpass.getpass("Password: ")
    try:
        account = AccountStore(args.accounts).authenticate(args.username, password)
        authorize_device(account, args.device)
        result = collect(
            devices[args.device],
            args.command,
            role=account.role,
            allow_state_changing=args.allow_state_changing,
        )
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result, indent=2))
        return 0

    for item in result["results"]:
        print(f"$ {item['command']}")
        print(item["output"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
