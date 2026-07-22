from __future__ import annotations

import argparse
import getpass
import json
import sys

from .accounts import AccountStore, authorize_device
from .access_config import write_access_config
from .ai_config import SUPPORTED_PROVIDERS, write_ai_provider_config
from .collector import collect, load_inventory_and_access


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Authorize users and run Junos commands through role-based SSH credentials."
    )
    subparsers = parser.add_subparsers(dest="action", required=True)

    setup = subparsers.add_parser(
        "setup-service",
        help="Create the Juniper access config used by the Hermes service.",
    )
    setup.add_argument(
        "--access-config",
        required=True,
        help="Path to write the Juniper access config JSON.",
    )
    setup.add_argument(
        "--profile",
        default="default",
        help="Access profile name used by devices. Default: default.",
    )

    setup_ai = subparsers.add_parser(
        "setup-ai",
        help="Create the AI provider config used by the Hermes service.",
    )
    setup_ai.add_argument(
        "--ai-config",
        required=True,
        help="Path to write the AI provider config JSON.",
    )
    setup_ai.add_argument(
        "--profile",
        default="default",
        help="AI provider profile name. Default: default.",
    )

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
    run.add_argument(
        "--access-config",
        required=True,
        help="Path to Juniper access config JSON.",
    )
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

    if args.action == "setup-service":
        print("Juniper read-only account")
        readonly_username = input("Username: ").strip()
        readonly_identity_file = input("SSH private key path: ").strip()
        print("Juniper superuser account")
        superuser_username = input("Username: ").strip()
        superuser_identity_file = input("SSH private key path: ").strip()
        try:
            write_access_config(
                path=args.access_config,
                readonly_username=readonly_username,
                readonly_identity_file=readonly_identity_file,
                superuser_username=superuser_username,
                superuser_identity_file=superuser_identity_file,
                profile_name=args.profile,
            )
        except Exception as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(f"Wrote Juniper access config to {args.access_config}.")
        return 0

    if args.action == "setup-ai":
        print("AI provider configuration")
        provider = input(
            "Provider (codex, claude, gemini, openai, openrouter): "
        ).strip()
        if provider not in SUPPORTED_PROVIDERS:
            print(f"Unsupported AI provider: {provider}", file=sys.stderr)
            return 1
        model = input("Model name: ").strip()
        api_key_env = input("API key environment variable name: ").strip()
        base_url = input("Base URL (optional): ").strip() or None
        try:
            write_ai_provider_config(
                path=args.ai_config,
                default_provider=provider,
                default_model=model,
                default_api_key_env=api_key_env,
                provider_name=args.profile,
                base_url=base_url,
            )
        except Exception as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(f"Wrote AI provider config to {args.ai_config}.")
        return 0

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

    devices, access_profiles = load_inventory_and_access(args.inventory, args.access_config)
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
            access_profiles=access_profiles,
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
