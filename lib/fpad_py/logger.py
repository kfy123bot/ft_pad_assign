# lib/fpad_py/logger.py

import sys

class Logger:
    def info(self, msg):
        print(f"[INFO] {msg}")

    def warn(self, msg):
        print(f"[WARN] {msg}")

    def error(self, msg):
        print(f"[ERROR] {msg}", file=sys.stderr)

    def fatal(self, msg):
        print(f"[FATAL] {msg}", file=sys.stderr)
        sys.exit(1)
