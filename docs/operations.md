# Operations Guide

## Recommended Workflow

1. Receive an operator request through chat or CLI.
2. Translate the request into one or more approved Junos `show` commands.
3. Validate the commands against the read-only policy.
4. Collect output over SSH using a dedicated low-privilege account.
5. Summarize evidence and identify gaps.

## Service Lifecycle

Install the systemd service with `scripts/install-service.sh`, then edit the generated local config files under `/opt/juniper-ai-assistant/config` and `/etc/juniper-ai-assistant`.

Before enabling the service, run:

```bash
juniper-ai-assistant-service --check
```

The check validates:

- Device inventory JSON
- Juniper access profiles
- Hermes account file
- AI provider file
- Whether configured AI provider API key environment variables are present

Missing AI key environment variables are reported as a warning in the JSON summary so operators can decide whether to use a different provider or update the service environment.

## Example Checks

```text
show version | no-more
show chassis hardware | no-more
show interfaces terse | no-more
show route summary | no-more
show bgp summary | no-more
show route <prefix> extensive | no-more
show ethernet-switching table | no-more
```

## Device Account

Use separate Junos users for AI roles. Example intent:

```text
class ai-readonly {
    permissions [ view view-configuration ];
}

user readonly-user {
    class ai-readonly;
}

user admin-user {
    class super-user;
}
```

Store these Juniper device accounts in `config/juniper-access.local.json`. If the operator skips the interactive service setup, copy `config/juniper-access.example.json` and edit the local file later.

## Hermes Account Flow

1. Register a Hermes user with `register-user`.
2. Assign the user a role: `readonly` or `superuser`.
3. Assign the user to one or more device names.
4. At login, authenticate the Hermes user.
5. Authorize the requested device.
6. Load the device access profile from `config/juniper-access.local.json`.
7. Select the matching Juniper SSH credential for that role.
8. Validate the command against the role policy before executing it.

Superuser accounts should still require an explicit approval or flag before running state-changing commands from a chat workflow.

## AI Provider Setup

Configure AI providers during service installation with `setup-ai`. If that step is skipped, copy `config/ai-providers.example.json` to `config/ai-providers.local.json` and edit it later.

The provider file should contain only metadata:

- Provider name, such as `codex`, `claude`, `gemini`, `openai`, or `openrouter`
- Model name
- Environment variable name containing the API key
- Optional base URL

The actual API key must stay in the service environment, secret manager, or deployment platform. Do not store the key in Git or in chat history.

## Data Handling

Keep the following out of public repositories:

- Private SSH keys
- Raw device configurations
- Customer prefixes
- Internal hostnames
- Session dumps
- Chat transcripts
- Provider tokens
- AI API keys

## Failure Handling

If SSH authentication fails:

- Verify the key path inside the runtime environment.
- Use `IdentitiesOnly=yes` to avoid trying unrelated keys.
- Confirm the public key installed on the Junos user.
- Stop after a single clear failure instead of repeated retries.
