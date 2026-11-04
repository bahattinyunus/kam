#!/usr/bin/env python3
"""
KAM // %100 Yerel Masaüstü Komuta Merkezi Başlatıcısı (PyQt6 Native UI)
Tarayıcı veya web sunucusu gerektirmeden doğrudan işletim sistemi üzerinde çalışır.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "python"))

from kam.desktop_app import run_desktop_app

if __name__ == "__main__":
    run_desktop_app()
