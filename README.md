# AI Juniper Assistant

An English-language reference project for integrating an AI assistant with Juniper QFX switches using read-only operational access.

The project is designed for network operations teams that want an AI interface for troubleshooting tasks such as route checks, BGP summaries, interface health, Junos version inventory, and PFE forwarding verification while keeping strict operational guardrails.

## Goals

- Provide a safe AI-assisted workflow for Juniper QFX troubleshooting.
- Execute only approved read-only Junos `show` commands.
- Keep device credentials, logs, private keys, and production configuration out of the public repository.
- Produce concise evidence-based summaries that distinguish control-plane state from forwarding-plane state.

## Architecture

```text
User / ChatOps
    |
    v
AI Orchestrator
    |
    v
Read-only command policy
    |
    v
SSH collector
    |
    v
Juniper QFX devices
```

## Repository Contents

- `src/juniper_ai_assistant/collector.py` - SSH command runner with read-only command validation.
- `src/juniper_ai_assistant/cli.py` - CLI entrypoint for collecting command output.
- `config/devices.example.json` - Example device inventory with placeholder values.
- `prompts/system-readonly.md` - AI system prompt for strict read-only Juniper operations.
- `docs/operations.md` - Suggested operating model and safety checks.

## Quick Start

Create a local inventory file from the example:

```bash
cp config/devices.example.json config/devices.local.json
```

Edit `config/devices.local.json` with your device hostnames, users, and private key paths. Do not commit `config/devices.local.json`.

Run a read-only command:

```bash
python3 -m juniper_ai_assistant.cli \
  --inventory config/devices.local.json \
  --device lab-qfx-01 \
  --command "show version | no-more"
```

## Safety Model

This project intentionally rejects commands that can modify device state, including:

- `configure`
- `commit`
- `clear`
- `request`
- `restart`
- `reboot`
- `file`
- `start shell`
- `load`
- `delete`
- `set`
- `edit`

Only commands starting with `show` are accepted by default.

## Public Repository Hygiene

Before publishing:

- Do not include `.ssh/`, private keys, tokens, session dumps, debug dumps, or device configuration reports.
- Replace real device IPs, hostnames, usernames, VRF names, and customer prefixes with examples.
- Keep operational reports in a private repository or secure artifact storage.

## License

MIT
