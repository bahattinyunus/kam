#!/usr/bin/env python3
"""
KAM Grafiksel Web Arayüzü Başlatıcı
Kullanıcının terminale ihtiyaç duymadan sistemi görsel olarak yönetmesini sağlar.
"""

import sys
import os

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "python"))

from kam.web_server import run_gui

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="KAM Web Arayüzü")
    parser.add_argument("--port", type=int, default=8080, help="Web portu (varsayılan: 8080)")
    parser.add_argument("--no-browser", action="store_true", help="Tarayıcıyı otomatik açma")
    args = parser.parse_args()

    run_gui(port=args.port, open_browser=not args.no_browser)
