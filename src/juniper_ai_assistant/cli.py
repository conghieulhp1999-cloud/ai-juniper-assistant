from __future__ import annotations

import argparse
import json
import sys

from .collector import collect, load_inventory


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run approved read-only Junos show commands over SSH."
    )
    parser.add_argument("--inventory", required=True, help="Path to inventory JSON.")
    parser.add_argument("--device", required=True, help="Device name from inventory.")
    parser.add_argument(
        "--command",
        action="append",
        required=True,
        help="Read-only Junos show command. May be repeated.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print structured JSON instead of plain command output.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    devices = load_inventory(args.inventory)
    if args.device not in devices:
        print(f"Unknown device: {args.device}", file=sys.stderr)
        return 2

    try:
        result = collect(devices[args.device], args.command)
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
