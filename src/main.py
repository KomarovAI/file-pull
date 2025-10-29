#!/usr/bin/env python3
import os, time, subprocess, sys
from loguru import logger

MERGER_MOUNT_POINT = os.environ.get("MERGER_MOUNT_POINT", "/data/unified")
CHECK_PATHS = [MERGER_MOUNT_POINT, "/mnt/webdav", "/mnt/rclone", "/data/local"]

logger.add("/var/log/file-pull/app.log", rotation="10 MB")


def is_mounted(path: str) -> bool:
    try:
        out = subprocess.check_output(["mount"]).decode()
        return any(path in line for line in out.splitlines())
    except Exception:
        return False


def ensure_mounts():
    ok = True
    for p in CHECK_PATHS:
        if os.path.isdir(p):
            mounted = is_mounted(p)
            logger.info(f"{p} mounted={mounted}")
            if p == MERGER_MOUNT_POINT and not mounted:
                logger.warning("MergerFS не смонтирован, пытаемся повторить setup.sh")
                subprocess.call(["/bin/bash", "-lc", "/app/scripts/setup.sh"]) 
                time.sleep(3)
                mounted = is_mounted(p)
                if not mounted:
                    ok = False
        else:
            logger.warning(f"{p} отсутствует")
    return ok


def main():
    logger.info("FILE-PULL стартует")
    while True:
        ok = ensure_mounts()
        if not ok:
            logger.error("Не удалось восстановить монтирование пулов")
        time.sleep(15)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
