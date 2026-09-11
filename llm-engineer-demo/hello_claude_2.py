#!/usr/bin/env python3
# Cai dat truoc khi chay tren may moi:
#   npm install -g @anthropic-ai/claude-code
#   claude login
import shutil
import subprocess
import sys
import time
import datetime

# (HH, MM)
SCHEDULE = [
    (5, 0),
    (10, 1),
    (15, 2),
    (20, 3),
]

if shutil.which("claude") is None:
    sys.exit("Khong tim thay lenh 'claude'. Chay: npm install -g @anthropic-ai/claude-code")


def say_hello():
    result = subprocess.run(["claude", "-p", "hello"], capture_output=True, text=True)
    print(f"[{datetime.datetime.now()}] {result.stdout.strip() or result.stderr.strip()}")


def main():
    say_hello()

    fired_today: set[tuple[int, int]] = set()
    last_date = datetime.date.today()

    while True:
        now = datetime.datetime.now()

        if now.date() != last_date:
            fired_today.clear()
            last_date = now.date()

        slot = (now.hour, now.minute)
        if slot in SCHEDULE and slot not in fired_today:
            say_hello()
            fired_today.add(slot)

        time.sleep(30)


if __name__ == "__main__":
    main()
