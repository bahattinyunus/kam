#!/usr/bin/env python3
import sys
import os

# Windows konsolunda UTF-8 desteğini etkinleştir
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Python path'ine repo kökünü ekle
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "python"))

from kam.cli import main

if __name__ == "__main__":
    main()
