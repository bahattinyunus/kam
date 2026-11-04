#!/usr/bin/env python3
"""
KAM // %100 Yerel Masaüstü Komuta Merkezi Başlatıcısı (PyQt6 Native UI)
Tarayıcı veya web sunucusu gerektirmeden doğrudan işletim sistemi üzerinde çalışır.
"""
import ctypes
import os
import sys


def _ensure_default_desktop():
    """
    Eğer süreç izole bir masaüstünden (örn. exebox sandbox) başlatıldıysa,
    pencerenin kullanıcının gerçek ekranında (WinSta0\\Default) görünmesi için
    süreci WinSta0\\Default masaüstünde yeniden başlatır.
    """
    if sys.platform != "win32" or os.environ.get("KAM_ON_DEFAULT_DESKTOP") == "1":
        return

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    buf = ctypes.create_unicode_buffer(256)
    hdesk = user32.GetThreadDesktop(kernel32.GetCurrentThreadId())
    user32.GetUserObjectInformationW(hdesk, 2, buf, 512, None)

    if buf.value.lower() != "default":
        class STARTUPINFOW(ctypes.Structure):
            _fields_ = [
                ("cb", ctypes.c_ulong),
                ("lpReserved", ctypes.c_wchar_p),
                ("lpDesktop", ctypes.c_wchar_p),
                ("lpTitle", ctypes.c_wchar_p),
                ("dwX", ctypes.c_ulong),
                ("dwY", ctypes.c_ulong),
                ("dwXSize", ctypes.c_ulong),
                ("dwYSize", ctypes.c_ulong),
                ("dwXCountChars", ctypes.c_ulong),
                ("dwYCountChars", ctypes.c_ulong),
                ("dwFillAttribute", ctypes.c_ulong),
                ("dwFlags", ctypes.c_ulong),
                ("wShowWindow", ctypes.c_ushort),
                ("cbReserved2", ctypes.c_ushort),
                ("lpReserved2", ctypes.c_void_p),
                ("hStdInput", ctypes.c_void_p),
                ("hStdOutput", ctypes.c_void_p),
                ("hStdError", ctypes.c_void_p),
            ]

        class PROCESS_INFORMATION(ctypes.Structure):
            _fields_ = [
                ("hProcess", ctypes.c_void_p),
                ("hThread", ctypes.c_void_p),
                ("dwProcessId", ctypes.c_ulong),
                ("dwThreadId", ctypes.c_ulong),
            ]

        os.environ["KAM_ON_DEFAULT_DESKTOP"] = "1"
        si = STARTUPINFOW()
        si.cb = ctypes.sizeof(si)
        si.lpDesktop = "WinSta0\\Default"
        si.dwFlags = 1  # STARTF_USESHOWWINDOW
        si.wShowWindow = 1  # SW_SHOWNORMAL
        pi = PROCESS_INFORMATION()

        script_path = os.path.abspath(__file__)
        cmd_buf = ctypes.create_unicode_buffer(f'"{sys.executable}" "{script_path}"')
        ok = kernel32.CreateProcessW(
            sys.executable,
            cmd_buf,
            None,
            None,
            False,
            0,
            None,
            os.path.dirname(script_path),
            ctypes.byref(si),
            ctypes.byref(pi),
        )
        if ok:
            kernel32.WaitForSingleObject(pi.hProcess, 0xFFFFFFFF)
            sys.exit(0)


_ensure_default_desktop()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "python"))

from kam.desktop_app import run_desktop_app

if __name__ == "__main__":
    run_desktop_app()
