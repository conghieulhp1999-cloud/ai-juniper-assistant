# Operations Guide

## Recommended Workflow

1. Receive an operator request through chat or CLI.
2. Translate the request into one or more approved Junos `show` commands.
3. Validate the commands against the read-only policy.
4. Collect output over SSH using a dedicated low-privilege account.
5. Summarize evidence and identify gaps.

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

Map Hermes users to these device accounts through `config/devices.local.json` and `config/accounts.local.json`.

## Hermes Account Flow

1. Register a Hermes user with `register-user`.
2. Assign the user a role: `readonly` or `superuser`.
3. Assign the user to one or more device names.
4. At login, authenticate the Hermes user.
5. Authorize the requested device.
6. Select the matching Juniper SSH credential for that role.
7. Validate the command against the role policy before executing it.

Superuser accounts should still require an explicit approval or flag before running state-changing commands from a chat workflow.

## Data Handling

Keep the following out of public repositories:

- Private SSH keys
- Raw device configurations
- Customer prefixes
- Internal hostnames
- Session dumps
- Chat transcripts
- Provider tokens

## Failure Handling

If SSH authentication fails:

- Verify the key path inside the runtime environment.
- Use `IdentitiesOnly=yes` to avoid trying unrelated keys.
- Confirm the public key installed on the Junos user.
- Stop after a single clear failure instead of repeated retries.
