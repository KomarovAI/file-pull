#!/usr/bin/env bash
set -euo pipefail

# Директории
MERGER_MOUNT_POINT=${MERGER_MOUNT_POINT:-/data/unified}
LOCAL_STORAGE_PATH=${LOCAL_STORAGE_PATH:-/data/local}

mkdir -p /mnt/webdav /mnt/rclone /mnt/hpn-remote "$MERGER_MOUNT_POINT" "$LOCAL_STORAGE_PATH"

# Генерация SSH ключа для HPN (если отсутствует)
if [[ "${HPN_ENABLED:-false}" == "true" ]]; then
  if [[ ! -f /app/configs/hpn_key ]]; then
    echo "🔑 Генерируем SSH ключ для HPN..."
    ssh-keygen -t ed25519 -f /app/configs/hpn_key -N "" -C "file-pull-hpn" >/dev/null 2>&1 || true
    chmod 600 /app/configs/hpn_key
    chmod 644 /app/configs/hpn_key.pub
  fi
fi

# WebDAV mount (через davfs2)
if [[ -n "${WEBDAV_URL:-}" ]]; then
  echo "Монтируем WebDAV: $WEBDAV_URL"
  mkdir -p /home/app/.davfs2
  echo "$WEBDAV_URL $WEBDAV_USER $WEBDAV_PASSWORD" > /home/app/.davfs2/secrets
  chmod 600 /home/app/.davfs2/secrets
  sudo mount.davfs "$WEBDAV_URL" /mnt/webdav -o noexec,ro || true
fi

# Пример rclone mount (опционально)
if [[ -f "/app/configs/rclone.conf" ]]; then
  echo "Пробуем монтировать rclone remote: gdrive:"
  rclone mount gdrive:/ /mnt/rclone \
    --config /app/configs/rclone.conf \
    --allow-other \
    --vfs-cache-mode writes \
    --daemon || true
fi

# Собираем список источников для mergerfs
MERGER_SOURCES=""
# Локальное RW пространство
[[ -d "$LOCAL_STORAGE_PATH" ]] && MERGER_SOURCES+="$LOCAL_STORAGE_PATH=rw"
# HPN SSH монтирование подключается позже из приложения, но включим его как ro, если смонтирован
if mount | grep -q "/mnt/hpn-remote"; then
  MERGER_SOURCES+="${MERGER_SOURCES:+:}/mnt/hpn-remote=ro"
fi
# Удаленные источники только ro
[[ -d /mnt/webdav ]] && MERGER_SOURCES+="${MERGER_SOURCES:+:}/mnt/webdav=ro"
[[ -d /mnt/rclone ]] && MERGER_SOURCES+="${MERGER_SOURCES:+:}/mnt/rclone=ro"

# Объединяем mergerfs
if [[ -n "$MERGER_SOURCES" ]]; then
  echo "Запускаем mergerfs для: $MERGER_SOURCES"
  sudo mergerfs -o allow_other,use_ino,category.create=${MERGER_POLICY:-mfs},minfreespace=10G "$MERGER_SOURCES" "$MERGER_MOUNT_POINT" || true
fi
