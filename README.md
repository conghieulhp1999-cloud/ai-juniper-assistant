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

- `src/juniper_ai_assistant/collector.py` - SSH command runner with role-based command validation.
- `src/juniper_ai_assistant/access_config.py` - Juniper device access profiles for service setup.
- `src/juniper_ai_assistant/ai_config.py` - AI provider configuration for Codex, Claude, Gemini, and compatible providers.
- `src/juniper_ai_assistant/accounts.py` - Local account registration, login, role, and device authorization.
- `src/juniper_ai_assistant/cli.py` - CLI entrypoint for collecting command output.
- `config/devices.example.json` - Example device inventory with placeholder values.
- `config/juniper-access.example.json` - Example Juniper access credentials file created during service setup.
- `config/ai-providers.example.json` - Example AI provider config using environment variable names instead of secrets.
- `config/accounts.example.json` - Example account and role model.
- `prompts/system-readonly.md` - AI system prompt for strict read-only Juniper operations.
- `docs/operations.md` - Suggested operating model and safety checks.

## Quick Start

Create a local inventory file from the example:

```bash
cp config/devices.example.json config/devices.local.json
cp config/juniper-access.example.json config/juniper-access.local.json
cp config/ai-providers.example.json config/ai-providers.local.json
cp config/accounts.example.json config/accounts.local.json
```

During service installation, create the Juniper access config interactively:

```bash
python3 -m juniper_ai_assistant.cli setup-service \
  --access-config config/juniper-access.local.json
```

The setup asks for two Juniper device accounts:

| Juniper access role | Expected Junos permissions | Purpose |
|---|---|---|
| `readonly` | `view` and `view-configuration` | Troubleshooting and configuration review |
| `superuser` | `super-user` | Configuration workflows |

If the operator skips setup, edit `config/juniper-access.local.json` later. Devices reference an access profile, so the same Juniper role credentials can be shared across many switches.

Configure the AI provider used by Hermes:

```bash
python3 -m juniper_ai_assistant.cli setup-ai \
  --ai-config config/ai-providers.local.json
```

The setup asks for:

| Field | Example | Notes |
|---|---|---|
| Provider | `codex`, `claude`, `gemini`, `openai`, `openrouter` | Match the provider enabled in your Hermes deployment |
| Model | `your-model-name` | Use the model name supported by that provider |
| API key environment variable | `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY` | Store the real key in the service environment, not in Git |
| Base URL | optional | Use only for compatible gateways or self-hosted endpoints |

If the operator skips AI setup, edit `config/ai-providers.local.json` later. Do not put API keys directly into the JSON file.

Edit `config/devices.local.json` with your device hostnames and access profile names. Do not commit `config/devices.local.json`, `config/juniper-access.local.json`, `config/ai-providers.local.json`, or `config/accounts.local.json`.

Register a read-only Hermes user:

```bash
python3 -m juniper_ai_assistant.cli register-user \
  --accounts config/accounts.local.json \
  --username noc-viewer \
  --role readonly \
  --device lab-qfx-01 \
  --device lab-qfx-02
```

Register a superuser Hermes user:

```bash
python3 -m juniper_ai_assistant.cli register-user \
  --accounts config/accounts.local.json \
  --username network-admin \
  --role superuser \
  --device "*"
```

Run a read-only command:

```bash
python3 -m juniper_ai_assistant.cli run-command \
  --inventory config/devices.local.json \
  --access-config config/juniper-access.local.json \
  --accounts config/accounts.local.json \
  --username noc-viewer \
  --device lab-qfx-01 \
  --command "show version | no-more"
```

Run a state-changing command as a superuser only when the workflow explicitly allows it:

```bash
python3 -m juniper_ai_assistant.cli run-command \
  --inventory config/devices.local.json \
  --access-config config/juniper-access.local.json \
  --accounts config/accounts.local.json \
  --username network-admin \
  --device lab-qfx-01 \
  --allow-state-changing \
  --command "configure private"
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

Only commands starting with `show` are accepted by default. Superuser accounts can use the superuser SSH credential for a device, but non-`show` commands still require the explicit `--allow-state-changing` flag. This prevents accidental privilege escalation from a chat session.

## Role Mapping

Hermes users are assigned one of two roles. That role selects the matching Juniper credential from `config/juniper-access.local.json`.

| Hermes user role | Juniper access credential | Default command policy |
|---|---|---|
| `readonly` | `profiles.<name>.credentials.readonly` | `show` commands only |
| `superuser` | `profiles.<name>.credentials.superuser` | `show` commands unless explicitly allowed |

## AI Provider Mapping

Hermes should load the active AI provider from `config/ai-providers.local.json`. The file stores provider metadata and the environment variable name that contains the secret.

```json
{
  "default_provider": "codex",
  "providers": {
    "codex": {
      "provider": "codex",
      "model": "your-codex-model",
      "api_key_env": "OPENAI_API_KEY"
    }
  }
}
```

At runtime, the service reads `api_key_env`, then resolves the actual secret from the process environment. This keeps API keys out of the repository and out of chat transcripts.

## Public Repository Hygiene

Before publishing:

- Do not include `.ssh/`, private keys, tokens, session dumps, debug dumps, or device configuration reports.
- Replace real device IPs, hostnames, usernames, VRF names, and customer prefixes with examples.
- Keep operational reports in a private repository or secure artifact storage.

## License

MIT
