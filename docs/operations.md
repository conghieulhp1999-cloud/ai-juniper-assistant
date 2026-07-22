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

Use a dedicated Junos login class with view-only permissions. Example intent:

```text
class ai-readonly {
    permissions [ view view-configuration ];
}
```

Do not use privileged automation accounts for AI-assisted troubleshooting.

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
