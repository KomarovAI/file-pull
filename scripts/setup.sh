#!/usr/bin/env bash
set -euo pipefail

mkdir -p /mnt/webdav /mnt/rclone "$MERGER_MOUNT_POINT" "$LOCAL_STORAGE_PATH"

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

# Объединяем mergerfs
MERGER_SOURCES=""
[[ -d /data/local ]] && MERGER_SOURCES+="/data/local"
[[ -d /mnt/webdav ]] && MERGER_SOURCES+="${MERGER_SOURCES:+:}/mnt/webdav"
[[ -d /mnt/rclone ]] && MERGER_SOURCES+="${MERGER_SOURCES:+:}/mnt/rclone"

if [[ -n "$MERGER_SOURCES" ]]; then
  echo "Запускаем mergerfs для: $MERGER_SOURCES"
  sudo mergerfs -o defaults,allow_other,use_ino,category.create=${MERGER_POLICY:-mfs} "$MERGER_SOURCES" "$MERGER_MOUNT_POINT" || true
fi

