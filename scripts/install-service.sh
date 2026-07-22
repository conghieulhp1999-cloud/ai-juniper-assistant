#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/juniper-ai-assistant}"
ETC_DIR="${ETC_DIR:-/etc/juniper-ai-assistant}"
SERVICE_USER="${SERVICE_USER:-juniper-ai}"
SERVICE_NAME="juniper-ai-assistant.service"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root: sudo $0" >&2
  exit 1
fi

install -d -m 0755 "${APP_DIR}"
install -d -m 0750 "${APP_DIR}/config"
install -d -m 0750 "${ETC_DIR}"

if ! id "${SERVICE_USER}" >/dev/null 2>&1; then
  useradd --system --home "${APP_DIR}" --shell /usr/sbin/nologin "${SERVICE_USER}"
fi

python3 -m venv "${APP_DIR}/.venv"
"${APP_DIR}/.venv/bin/pip" install --upgrade pip
"${APP_DIR}/.venv/bin/pip" install .

for file in devices juniper-access ai-providers accounts; do
  if [[ ! -f "${APP_DIR}/config/${file}.local.json" ]]; then
    install -m 0640 "config/${file}.example.json" "${APP_DIR}/config/${file}.local.json"
  fi
done

if [[ ! -f "${ETC_DIR}/juniper-ai-assistant.env" ]]; then
  install -m 0640 deploy/juniper-ai-assistant.env.example "${ETC_DIR}/juniper-ai-assistant.env"
fi

install -m 0644 deploy/juniper-ai-assistant.service "/etc/systemd/system/${SERVICE_NAME}"
chown -R "${SERVICE_USER}:${SERVICE_USER}" "${APP_DIR}" "${ETC_DIR}"

systemctl daemon-reload
echo "Installed ${SERVICE_NAME}."
echo "Edit ${APP_DIR}/config/*.local.json and ${ETC_DIR}/juniper-ai-assistant.env, then run:"
echo "  sudo systemctl enable --now ${SERVICE_NAME}"
