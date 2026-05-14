#!/usr/bin/env python
"""
Entry point for scheduled jobs: copy env from PID 1, then exec manage.py.

Debian cron runs with a minimal environment; PID 1 (supervisord) holds
docker-compose env_file variables such as APP_CREDENTIALS.
"""
import os
import sys


def _load_pid1_environ():
    try:
        with open("/proc/1/environ", "rb") as f:
            blob = f.read()
    except OSError:
        return
    for raw in blob.split(b"\0"):
        if not raw or b"=" not in raw:
            continue
        key_b, _, val_b = raw.partition(b"=")
        key = key_b.decode("utf-8", errors="surrogateescape")
        val = val_b.decode("utf-8", errors="surrogateescape")
        os.environ[key] = val


def main():
    _load_pid1_environ()
    os.chdir("/application")
    os.execve(
        sys.executable,
        [sys.executable, "manage.py", *sys.argv[1:]],
        os.environ,
    )


if __name__ == "__main__":
    main()
