FROM debian:12-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates fuse3 fuse3-libs \
    python3 python3-pip \
    rclone davfs2 mergerfs curl gnupg nano procps && \
    echo 'user_allow_other' >> /etc/fuse.conf && \
    rm -rf /var/lib/apt/lists/*

# Создадим пользователя
RUN useradd -m -u 1000 app && mkdir -p /app /data/local /data/unified /mnt/webdav /mnt/rclone && chown -R app:app /app /data /mnt

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip3 install --no-cache-dir -r /app/requirements.txt

COPY src/ /app/src/
COPY scripts/ /app/scripts/
COPY configs/ /app/configs/

RUN chmod +x /app/scripts/*.sh

USER root

# Разрешить не-root пользователю монтировать FUSE
RUN echo 'app ALL=(ALL) NOPASSWD: /usr/bin/mount, /usr/bin/umount, /usr/bin/mount.davfs, /usr/bin/fusermount3' >> /etc/sudoers

USER app

CMD ["/bin/bash","-lc","/app/scripts/setup.sh && python /app/src/main.py"]
