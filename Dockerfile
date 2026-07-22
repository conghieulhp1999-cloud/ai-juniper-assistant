FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends openssh-client \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --system --create-home --home-dir /app --shell /usr/sbin/nologin juniper-ai

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY config ./config
COPY prompts ./prompts
COPY docs ./docs

RUN pip install --no-cache-dir . \
    && mkdir -p /app/config /app/.ssh \
    && chown -R juniper-ai:juniper-ai /app

USER juniper-ai

ENV JUNIPER_AI_INVENTORY=/app/config/devices.local.json
ENV JUNIPER_AI_ACCESS_CONFIG=/app/config/juniper-access.local.json
ENV JUNIPER_AI_ACCOUNTS=/app/config/accounts.local.json
ENV JUNIPER_AI_PROVIDERS=/app/config/ai-providers.local.json
ENV JUNIPER_AI_SERVICE_INTERVAL=60
ENV JUNIPER_AI_LOG_LEVEL=INFO

HEALTHCHECK --interval=60s --timeout=10s --start-period=10s --retries=3 \
  CMD python -m juniper_ai_assistant.service --check || exit 1

CMD ["python", "-m", "juniper_ai_assistant.service"]
