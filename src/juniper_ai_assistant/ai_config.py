from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


SUPPORTED_PROVIDERS = {"codex", "claude", "gemini", "openai", "openrouter"}


@dataclass(frozen=True)
class AIProvider:
    name: str
    provider: str
    model: str
    api_key_env: str
    base_url: str | None = None


def load_ai_providers(path: str | Path) -> dict[str, AIProvider]:
    config_path = Path(path).expanduser()
    with config_path.open("r", encoding="utf-8") as fh:
        raw = json.load(fh)

    providers: dict[str, AIProvider] = {}
    for name, config in raw.get("providers", {}).items():
        provider = config["provider"]
        if provider not in SUPPORTED_PROVIDERS:
            raise ValueError(f"Unsupported AI provider: {provider}")
        providers[name] = AIProvider(
            name=name,
            provider=provider,
            model=config["model"],
            api_key_env=config["api_key_env"],
            base_url=config.get("base_url"),
        )
    return providers


def write_ai_provider_config(
    path: str | Path,
    default_provider: str,
    default_model: str,
    default_api_key_env: str,
    provider_name: str = "default",
    base_url: str | None = None,
) -> None:
    if default_provider not in SUPPORTED_PROVIDERS:
        raise ValueError(f"Unsupported AI provider: {default_provider}")

    config_path = Path(path).expanduser()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    provider: dict[str, str] = {
        "provider": default_provider,
        "model": default_model,
        "api_key_env": default_api_key_env,
    }
    if base_url:
        provider["base_url"] = base_url

    data = {
        "default_provider": provider_name,
        "providers": {
            provider_name: provider,
        },
    }
    with config_path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
        fh.write("\n")
    config_path.chmod(0o600)
