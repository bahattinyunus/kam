import os
import sys
import re
import html
import json
import time
import base64
import shutil
import socket
import ctypes
import platform
import threading
import traceback
import subprocess
import urllib.parse
import urllib.request
from io import StringIO
from pathlib import Path
from contextlib import redirect_stdout, redirect_stderr
from typing import Dict, Any, List, Optional, Tuple

from .mcp_server import McpServer
from .code_mutator import CodeMutator

_CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000) if sys.platform == "win32" else 0
_MISSING = object()


def _ps_escape_single_quoted(value: str) -> str:
    """PowerShell tek tırnak içi string kaçışı (' -> '')."""
    return str(value).replace("'", "''")


def _ps_build_command(script: str) -> List[str]:
    """
    Windows PowerShell için %100 UTF-8 / Türkçe karakter kayıpsız -EncodedCommand (UTF-16LE Base64)
    komut satırı oluşturur; kod sayfası (CP857/CP1254) bozulmalarını ve tırnak kaçış hatalarını önler.
    """
    utf8_preamble = (
        "[Console]::InputEncoding = [System.Text.Encoding]::UTF8; "
        "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
        "$OutputEncoding = [System.Text.Encoding]::UTF8; "
    )
    full_script = utf8_preamble + script
    encoded = base64.b64encode(full_script.encode("utf-16-le")).decode("ascii")
    return ["powershell", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded]


def _safe_relpath(path: str, start: str) -> str:
    """Windows'ta farklı sürücü harfleri (örn. C: ve G:) arasında relpath ValueError hatasını önler."""
    try:
        return os.path.relpath(path, start)
    except ValueError:
        return path


def _to_float(val: str) -> Any:
    s = str(val).strip()
    try:
        return float(s)
    except ValueError:
        return s


def _strip_code_fences(code: str) -> str:
    """LLM'in <codeact> veya execute_python_code içine yanlışlıkla koyduğu markdown çitlerini temizler."""
    s = code.strip()
    m = re.match(r"^```[a-zA-Z0-9_+-]*\s*\n(.*?)\n?```$", s, re.DOTALL)
    if m:
        return m.group(1).strip()
    return s


class HostSafetyShield:
    """
    KAM Otonom Bilgisayar Ajanı Güvenlik Kalkanı (Host CBF & AST Barrier).
    Kullanıcının bilgisayarına tam hükümranlık sağlarken, işletim sistemini veya
    disk bölümünü geri döndürülemez biçimde yok edebilecek yıkıcı komutları engeller.
    """

    FORBIDDEN_SHELL_PATTERNS = (
        r"\brm\s+-[a-z]*r[a-z]*f[a-z]*\s+(?:--no-preserve-root\s+)?/(?:\s|$|\*)",
        r"\brm\s+-[a-z]*f[a-z]*r[a-z]*\s+(?:--no-preserve-root\s+)?/(?:\s|$|\*)",
        r"\bformat-volume\b",
        r"\bclear-disk\b",
        r"\binitialize-disk\b",
        r"\bremove-partition\b",
        r"\bformat(?:\.com)?\s+[a-z]:",
        r"\b(?:del|erase|rd|rmdir)\s+.*(?:c:\\+windows|c:\\+system32|c:\\+\*(?:\s|$)|c:\\+(?:\s|$|['\"]))",
        r"\b(?:remove-item|ri)\s+.*(?:c:\\+windows|c:\\+system32)",
        r"\b(?:remove-item|ri)\s+.*(?:-recurse|-r)\b.*c:\\+(?:\s|$|\*|['\"])",
        r":\(\)\{\s*:\|:&\s*\};:",
        r"\bcipher\s+/w:[a-z]:",
        r"\bdiskpart\b",
        r"\bbcdedit\s+/delete\b",
        r"\bvssadmin\s+delete\s+shadows\b",
        r"\bwbadmin\s+delete\s+catalog\b",
        r"\breg\s+delete\s+hklm\\(?:system|software\\microsoft\\windows)\b",
        r"\bmkfs(?:\.[a-z0-9]+)?\s+/dev/",
        r"\bdd\s+.*of=/dev/(?:sd|nvme|hd|vd)",
    )

    PROTECTED_PROCESS_NAMES = frozenset({
        "system", "smss", "csrss", "wininit", "winlogon", "services", "lsass",
    })

    @classmethod
    def verify_command(cls, command: str) -> Tuple[bool, str]:
        cmd_low = str(command or "").lower().strip()
        for pattern in cls.FORBIDDEN_SHELL_PATTERNS:
            if re.search(pattern, cmd_low):
                return (
                    False,
                    f"CBF Güvenlik Kalkanı İhlali: '{pattern}' yıkıcı sistem imha örüntüsü tespit edildi ve engellendi.",
                )
        return True, "SAFE"

    @classmethod
    def verify_delete_path(cls, path: str) -> Tuple[bool, str]:
        norm = os.path.normcase(os.path.abspath(path)).rstrip("\\/")
        # Sürücü kökleri (örn. C:, D:, /) ve kritik Windows sistem dizinleri korunur
        if not norm or re.fullmatch(r"[a-z]:", norm) or norm in ("/", "\\"):
            return False, f"CBF Güvenlik Kalkanı İhlali: Kök dizin silinemez ({path})."
        protected_prefixes = (
            os.path.normcase(os.path.abspath("C:\\Windows")),
            os.path.normcase(os.path.abspath("C:\\System32")),
        )
        for pref in protected_prefixes:
            if norm == pref or norm.startswith(pref + os.sep):
                return False, f"CBF Güvenlik Kalkanı İhlali: Kritik işletim sistemi dizini silinemez ({path})."
        return True, "SAFE"


class Win32ComputerUseController:
    """
    Microsoft UFO² & Anthropic Computer-Use Sınıfı Doğrudan Masaüstü/Donanım Denetleyicisi.
    Win32 User32/Kernel32 API'leri ve Windows UI Automation (UIA) üzerinden:
      - Fare (Mouse): Konum okuma, taşıma, sol/sağ/çift tıklama, sürükle-bırak (drag), tekerlek kaydırma (scroll)
      - Klavye (Keyboard): Aktif pencereye Türkçe/UTF-8 metin yazma, kısayol tuşları (Ctrl+C, Alt+Tab, Enter, Win+D vb.)
      - Pencere Geometrisi & UIA: Pencere listeleme (koordinat ve PID ile), odaklama, büyütme, küçültme, taşıma, kapatma ve UIA denetim ağacı
      - İşletim Sistemi Donanımı: Ses kontrolü (Volume Up/Down/Mute), batarya/güç durumu, servisler, kurulu yazılımlar
    """

    MOUSEEVENTF_LEFTDOWN = 0x0002
    MOUSEEVENTF_LEFTUP = 0x0004
    MOUSEEVENTF_RIGHTDOWN = 0x0008
    MOUSEEVENTF_RIGHTUP = 0x0010
    MOUSEEVENTF_WHEEL = 0x0800

    VK_MAP = {
        "enter": 0x0D,
        "return": 0x0D,
        "tab": 0x09,
        "esc": 0x1B,
        "escape": 0x1B,
        "space": 0x20,
        "backspace": 0x08,
        "delete": 0x2E,
        "up": 0x26,
        "down": 0x28,
        "left": 0x25,
        "right": 0x27,
        "home": 0x24,
        "end": 0x23,
        "pageup": 0x21,
        "pagedown": 0x22,
        "ctrl": 0x11,
        "control": 0x11,
        "alt": 0x12,
        "shift": 0x10,
        "win": 0x5B,
        "lwin": 0x5B,
        "volume_mute": 0xAD,
        "volume_down": 0xAE,
        "volume_up": 0xAF,
        "volume-mute": 0xAD,
        "volume-down": 0xAE,
        "volume-up": 0xAF,
        "insert": 0x2D,
        "printscreen": 0x2C,
        "prtsc": 0x2C,
        "capslock": 0x14,
        "numlock": 0x90,
        "play_pause": 0xB3,
        "next_track": 0xB0,
        "prev_track": 0xB1,
        "f1": 0x70, "f2": 0x71, "f3": 0x72, "f4": 0x73, "f5": 0x74, "f6": 0x75,
        "f7": 0x76, "f8": 0x77, "f9": 0x78, "f10": 0x79, "f11": 0x7A, "f12": 0x7B,
    }

    @classmethod
    def get_screen_and_cursor(cls) -> Dict[str, Any]:
        if sys.platform != "win32":
            return {"status": "unsupported_platform", "screen_width": 1920, "screen_height": 1080, "cursor_x": 0, "cursor_y": 0}

        class POINT(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

        user32 = ctypes.windll.user32
        pt = POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        sw = int(user32.GetSystemMetrics(0))
        sh = int(user32.GetSystemMetrics(1))
        return {
            "status": "success",
            "screen_width": sw,
            "screen_height": sh,
            "cursor_x": int(pt.x),
            "cursor_y": int(pt.y),
        }

    @classmethod
    def mouse_action(cls, args: Dict[str, Any]) -> Dict[str, Any]:
        action = str(args.get("action", "position")).lower().strip()
        info = cls.get_screen_and_cursor()
        if sys.platform != "win32" or action == "position":
            return info

        user32 = ctypes.windll.user32
        x = int(args["x"]) if args.get("x") is not None else int(info["cursor_x"])
        y = int(args["y"]) if args.get("y") is not None else int(info["cursor_y"])

        if action == "move":
            user32.SetCursorPos(x, y)
            return {"status": "success", "action": "move", "x": x, "y": y}

        elif action in ("click", "left_click"):
            user32.SetCursorPos(x, y)
            time.sleep(0.02)
            user32.mouse_event(cls.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            user32.mouse_event(cls.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            return {"status": "success", "action": "left_click", "x": x, "y": y}

        elif action == "double_click":
            user32.SetCursorPos(x, y)
            time.sleep(0.02)
            for _ in range(2):
                user32.mouse_event(cls.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                user32.mouse_event(cls.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                time.sleep(0.04)
            return {"status": "success", "action": "double_click", "x": x, "y": y}

        elif action == "right_click":
            user32.SetCursorPos(x, y)
            time.sleep(0.02)
            user32.mouse_event(cls.MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
            user32.mouse_event(cls.MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
            return {"status": "success", "action": "right_click", "x": x, "y": y}

        elif action == "drag":
            end_x = int(args["end_x"]) if args.get("end_x") is not None else x + 100
            end_y = int(args["end_y"]) if args.get("end_y") is not None else y + 100
            user32.SetCursorPos(x, y)
            time.sleep(0.03)
            user32.mouse_event(cls.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            steps = 10
            for i in range(1, steps + 1):
                ix = int(x + (end_x - x) * i / steps)
                iy = int(y + (end_y - y) * i / steps)
                user32.SetCursorPos(ix, iy)
                time.sleep(0.01)
            user32.mouse_event(cls.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            return {"status": "success", "action": "drag", "from": [x, y], "to": [end_x, end_y]}

        elif action == "scroll":
            delta = int(args["delta"]) if args.get("delta") is not None else -120
            user32.mouse_event(cls.MOUSEEVENTF_WHEEL, 0, 0, delta, 0)
            return {"status": "success", "action": "scroll", "delta": delta}

        return {"status": "error", "error": f"Bilinmeyen fare eylemi: {action}"}

    @classmethod
    def _parse_hotkey_combo(cls, raw_keys: str) -> List[str]:
        s = raw_keys.strip().lower()
        if not s:
            return []
        if s in cls.VK_MAP:
            return [s]
        if "+" in s:
            return [k.strip() for k in s.split("+") if k.strip()]
        # "ctrl-c" / "alt-tab" gibi tireli kombinasyonları destekle ama "volume-up" gibi tekil tuşları bölme
        parts = [k.strip() for k in s.split("-") if k.strip()]
        if len(parts) > 1 and parts[0] in ("ctrl", "control", "alt", "shift", "win", "lwin"):
            return parts
        return [s]

    @classmethod
    def keyboard_action(cls, args: Dict[str, Any]) -> Dict[str, Any]:
        action = str(args.get("action", "type")).lower().strip()
        text = str(args.get("text", ""))
        keys = str(args.get("keys", "")).strip()
        press_enter = bool(args.get("press_enter", False))

        if sys.platform != "win32":
            return {"status": "unsupported_platform", "action": action}

        user32 = ctypes.windll.user32

        if action == "type" and text:
            # Türkçe, UTF-8 ve çok satırlı metinleri bozmadan -EncodedCommand ile panoya koyup Ctrl+V ile yapıştır
            escaped = _ps_escape_single_quoted(text)
            ps_cmd = _ps_build_command(f"Set-Clipboard -Value '{escaped}'")
            try:
                proc = subprocess.run(
                    ps_cmd,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=5.0,
                    creationflags=_CREATE_NO_WINDOW,
                )
                if proc.returncode != 0:
                    return {
                        "status": "error",
                        "action": "type_text",
                        "error": (proc.stderr or "Set-Clipboard başarısız oldu.").strip(),
                    }
            except subprocess.TimeoutExpired:
                return {"status": "timeout", "action": "type_text", "error": "Pano yazma zaman aşımına uğradı."}
            time.sleep(0.05)
            # Ctrl + V
            user32.keybd_event(0x11, 0, 0, 0)       # CTRL down
            user32.keybd_event(ord("V"), 0, 0, 0)   # V down
            user32.keybd_event(ord("V"), 0, 2, 0)   # V up
            user32.keybd_event(0x11, 0, 2, 0)       # CTRL up
            if press_enter:
                time.sleep(0.04)
                user32.keybd_event(0x0D, 0, 0, 0)
                user32.keybd_event(0x0D, 0, 2, 0)
            return {
                "status": "success",
                "action": "type_text",
                "typed_length": len(text),
                "preview": text[:120],
                "press_enter": press_enter,
            }

        elif action in ("hotkey", "key_press", "key") and (keys or text):
            combo = cls._parse_hotkey_combo(keys or text)
            vks = []
            for k in combo:
                if k in cls.VK_MAP:
                    vks.append(cls.VK_MAP[k])
                elif len(k) == 1 and k.isascii() and k.isalnum():
                    vks.append(ord(k.upper()))
            if not vks:
                return {"status": "error", "error": f"Geçersiz tuş dizisi: {keys or text}"}

            for vk in vks:
                user32.keybd_event(vk, 0, 0, 0)
                time.sleep(0.015)
            for vk in reversed(vks):
                user32.keybd_event(vk, 0, 2, 0)
                time.sleep(0.015)

            return {"status": "success", "action": "hotkey", "keys": combo}

        return {"status": "error", "error": f"Geçersiz klavye eylemi veya boş metin: {action}"}

    @classmethod
    def enumerate_windows_detailed(cls) -> List[Dict[str, Any]]:
        windows: List[Dict[str, Any]] = []
        if sys.platform != "win32":
            return windows

        user32 = ctypes.windll.user32

        class RECT(ctypes.Structure):
            _fields_ = [
                ("left", ctypes.c_long),
                ("top", ctypes.c_long),
                ("right", ctypes.c_long),
                ("bottom", ctypes.c_long),
            ]

        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

        def enum_cb(hwnd, lparam):
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buf = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buf, length + 1)
                    title = buf.value.strip()
                    if title and title not in ("Program Manager", "Windows Giriş Deneyimi", "Microsoft Text Input Application"):
                        rc = RECT()
                        user32.GetWindowRect(hwnd, ctypes.byref(rc))
                        pid = ctypes.c_ulong()
                        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                        windows.append({
                            "hwnd": int(hwnd),
                            "pid": int(pid.value),
                            "title": title,
                            "bounds": {
                                "x": int(rc.left),
                                "y": int(rc.top),
                                "width": max(0, int(rc.right - rc.left)),
                                "height": max(0, int(rc.bottom - rc.top)),
                            },
                        })
            return True

        user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
        return windows


class WebResearchEngine:
    """
    Manus-AI Sınıfı Otonom Web Araştırma, Sayfa İçeriği Kazıma (DOM->Text) ve Dosya İndirme Motoru.
    Ücretli API anahtarına ihtiyaç duymadan açık web üzerinde arama yapar, sayfaları okur ve dosya indirir.
    """

    @staticmethod
    def search_web(query: str, max_results: int = 6) -> Dict[str, Any]:
        q = query.strip()
        if not q:
            return {"status": "error", "error": "Boş arama sorgusu."}

        results = []
        # DuckDuckGo HTML Lite üzerinden gerçek zamanlı arama
        try:
            url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(q)
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                },
            )
            with urllib.request.urlopen(req, timeout=8.0) as resp:
                raw_html = resp.read().decode("utf-8", errors="replace")

            for match in re.finditer(
                r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
                raw_html,
                re.DOTALL,
            ):
                href = html.unescape(match.group(1))
                if "uddg=" in href:
                    parsed_qs = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                    href = parsed_qs.get("uddg", [href])[0]
                title = re.sub(r"<[^>]+>", "", html.unescape(match.group(2))).strip()
                if title and href.startswith("http"):
                    results.append({"title": title, "url": href})
                if len(results) >= max_results:
                    break
        except Exception as exc:
            return {"status": "network_unavailable", "query": q, "note": str(exc), "results": results}

        return {"status": "success", "query": q, "results_count": len(results), "results": results}

    @staticmethod
    def fetch_webpage_clean(url: str, max_chars: int = 4000) -> Dict[str, Any]:
        clean_url = str(url or "").strip()
        if not clean_url.lower().startswith(("http://", "https://")):
            return {"status": "error", "url": clean_url, "error": "Yalnızca http:// veya https:// adresleri desteklenir."}
        try:
            req = urllib.request.Request(
                clean_url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) KAM-Autonomous-Agent/3.5"
                },
            )
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                raw = resp.read(250_000).decode("utf-8", errors="replace")
                status_code = resp.status
        except Exception as exc:
            return {"status": "error", "url": clean_url, "error": str(exc)}

        title_m = re.search(r"<title[^>]*>(.*?)</title>", raw, re.IGNORECASE | re.DOTALL)
        title = html.unescape(title_m.group(1)).strip() if title_m else clean_url

        cleaned = re.sub(r"<(script|style|noscript|svg|head)[^>]*>.*?</\1>", " ", raw, flags=re.IGNORECASE | re.DOTALL)
        cleaned = re.sub(r"<[^>]+>", " ", cleaned)
        cleaned = html.unescape(cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        return {
            "status": "success",
            "url": clean_url,
            "http_status": status_code,
            "title": title,
            "text_content": cleaned[:max_chars],
            "total_extracted_chars": len(cleaned),
        }


class HostBridgeAPI:
    """
    CodeAct çalışma zamanı içerisinden doğrudan `host.*` olarak çağrılabilen yüksek seviyeli köprü.
    """

    def __init__(self, agent: "KamAutonomousAgent"):
        self._agent = agent

    def shell(self, command: str, cwd: Optional[str] = None, timeout: float = 25.0) -> Dict[str, Any]:
        args: Dict[str, Any] = {"command": command, "timeout": timeout}
        if cwd:
            args["cwd"] = cwd
        return self._agent.execute_tool("run_shell_command", args)

    def sysinfo(self) -> Dict[str, Any]:
        return self._agent.execute_tool("get_real_system_telemetry", {})

    def windows(self) -> Dict[str, Any]:
        return self._agent.execute_tool("desktop_window_manager", {"action": "list_windows"})

    def focus(self, title: str) -> Dict[str, Any]:
        return self._agent.execute_tool("desktop_window_manager", {"action": "focus_window", "value": title})

    def click(self, x: int, y: int, double: bool = False, right: bool = False) -> Dict[str, Any]:
        act = "right_click" if right else ("double_click" if double else "click")
        return self._agent.execute_tool("mouse_control", {"action": act, "x": x, "y": y})

    def move_mouse(self, x: int, y: int) -> Dict[str, Any]:
        return self._agent.execute_tool("mouse_control", {"action": "move", "x": x, "y": y})

    def type_text(self, text: str, press_enter: bool = False) -> Dict[str, Any]:
        return self._agent.execute_tool(
            "keyboard_control",
            {"action": "type", "text": text, "press_enter": press_enter},
        )

    def hotkey(self, keys: str) -> Dict[str, Any]:
        return self._agent.execute_tool("keyboard_control", {"action": "hotkey", "keys": keys})

    def open_app(self, target: str, arguments: str = "") -> Dict[str, Any]:
        return self._agent.execute_tool("launch_application", {"target": target, "arguments": arguments})

    def write_file(self, path: str, content: str, append: bool = False) -> Dict[str, Any]:
        return self._agent.execute_tool("write_file", {"path": path, "content": content, "append": append})

    def read_file(self, path: str, start_line: int = 1, end_line: int = 200) -> Dict[str, Any]:
        return self._agent.execute_tool(
            "read_file", {"path": path, "start_line": start_line, "end_line": end_line}
        )

    def edit_file(self, path: str, target: str, replacement: str) -> Dict[str, Any]:
        return self._agent.execute_tool(
            "edit_file", {"path": path, "target": target, "replacement": replacement}
        )

    def list_dir(self, path: str = "", pattern: str = "*") -> Dict[str, Any]:
        return self._agent.execute_tool("list_directory", {"path": path, "pattern": pattern})

    def search_files(self, query: str, path: str = "", file_pattern: str = "*") -> Dict[str, Any]:
        return self._agent.execute_tool(
            "search_in_files", {"query": query, "path": path, "file_pattern": file_pattern}
        )

    def processes(self, action: str = "list", target: str = "") -> Dict[str, Any]:
        return self._agent.execute_tool("manage_processes", {"action": action, "target": target})

    def clipboard(self, text: Optional[str] = None) -> Dict[str, Any]:
        if text is None:
            return self._agent.execute_tool("clipboard_manager", {"action": "get"})
        return self._agent.execute_tool("clipboard_manager", {"action": "set", "text": text})

    def clipboard_manager(self, action: str = "get", text: str = "") -> Dict[str, Any]:
        return self._agent.execute_tool("clipboard_manager", {"action": action, "text": text})

    def smart_search(
        self,
        query: str,
        path: str = "",
        file_pattern: str = "*",
        case_sensitive: bool = False,
        max_results: int = 40,
        context_lines: int = 0,
    ) -> Dict[str, Any]:
        return self._agent.execute_tool(
            "smart_workspace_search",
            {
                "query": query,
                "path": path,
                "file_pattern": file_pattern,
                "case_sensitive": case_sensitive,
                "max_results": max_results,
                "context_lines": context_lines,
            },
        )

    def smart_workspace_search(
        self,
        query: str,
        path: str = "",
        file_pattern: str = "*",
        case_sensitive: bool = False,
        max_results: int = 40,
        context_lines: int = 0,
    ) -> Dict[str, Any]:
        return self.smart_search(
            query=query,
            path=path,
            file_pattern=file_pattern,
            case_sensitive=case_sensitive,
            max_results=max_results,
            context_lines=context_lines,
        )

    def notify(
        self,
        message: str,
        title: str = "KAM // Otonom Ajan",
        level: str = "info",
        duration_ms: int = 4000,
    ) -> Dict[str, Any]:
        return self._agent.execute_tool(
            "system_notification",
            {"title": title, "message": message, "level": level, "duration_ms": duration_ms},
        )

    def system_notification(
        self,
        message: str,
        title: str = "KAM // Otonom Ajan",
        level: str = "info",
        duration_ms: int = 4000,
    ) -> Dict[str, Any]:
        return self.notify(message=message, title=title, level=level, duration_ms=duration_ms)

    def hardware(self, action: str = "battery", steps: int = 5) -> Dict[str, Any]:
        return self._agent.execute_tool("os_hardware_control", {"action": action, "steps": steps})

    def network(self, action: str = "status", target: str = "") -> Dict[str, Any]:
        return self._agent.execute_tool("network_probe", {"action": action, "target": target})

    def file_ops(self, action: str, source: str, destination: str = "") -> Dict[str, Any]:
        return self._agent.execute_tool(
            "file_power_ops", {"action": action, "source": source, "destination": destination}
        )

    def web_search(self, query: str) -> Dict[str, Any]:
        return self._agent.execute_tool("web_research", {"action": "search", "query": query})

    def fetch_url(self, url: str) -> Dict[str, Any]:
        return self._agent.execute_tool("web_research", {"action": "fetch", "url": url})

    def screenshot(self, path: str = "") -> Dict[str, Any]:
        return self._agent.execute_tool("desktop_window_manager", {"action": "screenshot", "value": path})

    def speak(self, text: str) -> Dict[str, Any]:
        return self._agent.execute_tool("voice_tts", {"text": text})

    def analyze_codebase(self, path: str = "") -> Dict[str, Any]:
        return self._agent.execute_tool("analyze_codebase", {"path": path})

    def build_webapp(self, title: str = "KAM Otonom Siber Kokpit", launch: bool = True) -> Dict[str, Any]:
        return self._agent.execute_tool("build_interactive_webapp", {"title": title, "launch": launch})

    def remember(self, note: str, category: str = "sovereign_directive") -> Dict[str, Any]:
        return self._agent.remember_fact(note, category=category)

    def recall(self, query: str = "") -> Dict[str, Any]:
        return self._agent.recall_memories(query=query)

    def call_tool(self, name: str, args: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self._agent.execute_tool(name, args or {})


class KamAutonomousAgent:
    """
    KAM // Manus-AI & Microsoft UFO² Sınıfı Otonom Bilgisayar Hükümranlığı Çekirdeği
    (Planner -> CodeAct / Multi-Tool Executor -> Self-Verification Loop).
    Bilgisayarın dosya sistemine, kabuğuna (PowerShell/Bash), çalışan süreçlerine,
    masaüstü pencerelerine, fare ve klavyesine (Win32 Computer-Use), ses/güç donanımına,
    panosuna (clipboard), ekran görüntüsüne, durum-korumalı (stateful) Python CodeAct
    çalışma zamanına, açık web araştırmasına ve 18 taktik savunma aracına doğrudan hükmeder.
    """

    def __init__(self, workspace_root: Optional[str] = None):
        self.workspace_root = os.path.abspath(
            workspace_root or os.path.join(os.path.dirname(__file__), "..", "..")
        )
        self.mcp = McpServer()
        self.full_permissions = True
        self.permission_level = "SOVEREIGN_FULL_ADMIN_ACCESS"
        self.memory_path = os.path.join(self.workspace_root, "data", "kam_episodic_memory.json")
        self.episodic_memory: List[Dict[str, Any]] = self._load_episodic_memory()
        self.execution_history: List[Dict[str, Any]] = []
        self.mission_plan_history: List[Dict[str, Any]] = []
        self._codeact_lock = threading.Lock()
        self.host_bridge = HostBridgeAPI(self)
        # Durum-Korumalı (Stateful) CodeAct Python Oturum Belleği (Tam Yetkili)
        self.codeact_globals: Dict[str, Any] = {
            "__name__": "__kam_codeact__",
            "os": os,
            "sys": sys,
            "re": re,
            "glob": __import__("glob"),
            "math": __import__("math"),
            "json": json,
            "time": time,
            "ctypes": ctypes,
            "socket": socket,
            "Path": Path,
            "shutil": shutil,
            "platform": platform,
            "subprocess": subprocess,
            "urllib": urllib,
            "host": self.host_bridge,
            "WORKSPACE": self.workspace_root,
            "DESKTOP": os.path.join(os.path.expanduser("~"), "Desktop"),
            "DOWNLOADS": os.path.join(os.path.expanduser("~"), "Downloads"),
        }

    def _load_episodic_memory(self) -> List[Dict[str, Any]]:
        if os.path.isfile(self.memory_path):
            try:
                with open(self.memory_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("memories", [])
            except Exception:
                pass
        return []

    def remember_fact(self, note: str, category: str = "sovereign_directive") -> Dict[str, Any]:
        entry = {
            "id": len(self.episodic_memory) + 1,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "category": category,
            "note": note.strip(),
        }
        self.episodic_memory.append(entry)
        try:
            os.makedirs(os.path.dirname(self.memory_path), exist_ok=True)
            with open(self.memory_path, "w", encoding="utf-8") as f:
                json.dump({"memories": self.episodic_memory[-100:]}, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
        return {"status": "success", "stored_memory": entry, "total_memories": len(self.episodic_memory)}

    def recall_memories(self, query: str = "") -> Dict[str, Any]:
        q_low = query.lower().strip()
        if not q_low:
            matched = self.episodic_memory[-20:]
        else:
            matched = [m for m in self.episodic_memory if q_low in m.get("note", "").lower()]
        return {"status": "success", "total_memories": len(self.episodic_memory), "memories": matched}

    # ------------------------------------------------------------------
    # 1. ARAÇ ŞEMALARI (TOOL REGISTRY — 17 ANA BİLGİSAYAR + 18 SAVUNMA ARACI)
    # ------------------------------------------------------------------
    def list_agent_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "run_shell_command",
                "description": "İşletim sistemi kabuğunda (Windows PowerShell / Linux Bash) gerçek komut çalıştırır ve çıktısını döndürür.",
                "parameters": {"command": "Kabuk komutu", "cwd": "Opsiyonel çalışma dizini"},
            },
            {
                "name": "get_real_system_telemetry",
                "description": "Bilgisayarın gerçek zamanlı CPU, fiziksel RAM, Disk, GPU (NVIDIA CUDA), Ekran çözünürlüğü, Fare konumu, Ağ ve İşletim Sistemi verilerini okur.",
                "parameters": {},
            },
            {
                "name": "list_directory",
                "description": "Belirtilen dizindeki dosya ve klasörleri boyutları ve türleriyle listeler.",
                "parameters": {"path": "Dizin yolu", "pattern": "Opsiyonel filtre (örn. '*.py')"},
            },
            {
                "name": "read_file",
                "description": "Bilgisayardaki herhangi bir dosyanın içeriğini satır numaralarıyla okur.",
                "parameters": {"path": "Dosya yolu", "start_line": 1, "end_line": 120},
            },
            {
                "name": "write_file",
                "description": "Bilgisayarda yeni bir dosya oluşturur veya mevcut dosyanın içeriğini yazar.",
                "parameters": {"path": "Dosya yolu", "content": "Metin içeriği", "append": False},
            },
            {
                "name": "edit_file",
                "description": "Mevcut bir dosyadaki hedef metin bloğunu yeni metinle değiştirir.",
                "parameters": {"path": "Dosya yolu", "target": "Eski metin", "replacement": "Yeni metin"},
            },
            {
                "name": "search_in_files",
                "description": "Dosyalar içinde metin veya düzenli ifade (regex) araması yapar.",
                "parameters": {"query": "Aranacak ifade", "path": "Dizin", "file_pattern": "*.py"},
            },
            {
                "name": "execute_python_code",
                "description": "Manus-AI tarzı Durum-Korumalı (Stateful) CodeAct Python çalışma zamanı. `host.*` köprüsüyle doğrudan bilgisayara, dosyalara, fareye, klavyeye ve kabuğa erişebilir.",
                "parameters": {"code": "Çalıştırılacak Python CodeAct kaynak kodu"},
            },
            {
                "name": "manage_processes",
                "description": "Bilgisayarda çalışan süreçleri (uygulamaları) listeler, filtreler veya belirtilen süreci (PID/isim) sonlandırır.",
                "parameters": {"action": "'list', 'find' veya 'kill'", "target": "Süreç adı veya PID"},
            },
            {
                "name": "launch_application",
                "description": "Bilgisayarda bir uygulamayı (örn. notepad, calc, explorer, code, paint, taskmgr), dosyayı, klasörü veya web adresini (URL) açar.",
                "parameters": {"target": "Uygulama adı, dosya yolu veya URL", "arguments": "Opsiyonel argümanlar"},
            },
            {
                "name": "desktop_window_manager",
                "description": "Masaüstündeki açık pencereleri koordinatlarıyla listeler, pencereyi öne getirir (focus), büyütür (maximize), küçültür (minimize), kapatır (close), panoyu (clipboard) okur/yazar veya ekran görüntüsü alır.",
                "parameters": {
                    "action": "'list_windows', 'focus_window', 'minimize_window', 'maximize_window', 'restore_window', 'close_window', 'get_clipboard', 'set_clipboard' veya 'screenshot'",
                    "value": "Pencere başlığı, pano metni veya ekran görüntüsü dosya yolu",
                },
            },
            {
                "name": "mouse_control",
                "description": "Bilgisayarın fare imlecine doğrudan hükmeder: konum okur, taşır (move), sol/sağ/çift tıklar (click/right_click/double_click), sürükler (drag) veya kaydırır (scroll).",
                "parameters": {
                    "action": "'position', 'move', 'click', 'double_click', 'right_click', 'drag' veya 'scroll'",
                    "x": "Hedef X piksel koordinatı",
                    "y": "Hedef Y piksel koordinatı",
                    "end_x": "Sürükleme bitiş X koordinatı",
                    "end_y": "Sürükleme bitiş Y koordinatı",
                    "delta": "Tekerlek kaydırma miktarı (örn. -120 veya 120)",
                },
            },
            {
                "name": "keyboard_control",
                "description": "Aktif pencereye Türkçe/UTF-8 metin yazar (type) veya sistem klavye kısayollarını (hotkey: 'ctrl+s', 'alt+tab', 'win+d', 'enter' vb.) basar.",
                "parameters": {
                    "action": "'type' veya 'hotkey'",
                    "text": "Yazılacak metin",
                    "keys": "Basılacak tuş kombinasyonu (örn. 'ctrl+s', 'alt+tab', 'enter')",
                    "press_enter": "Metin yazdıktan sonra Enter tuşuna basılsın mı (True/False)",
                },
            },
            {
                "name": "os_hardware_control",
                "description": "Bilgisayarın ses seviyesini (volume_up, volume_down, volume_mute), batarya/güç durumunu (battery), Windows servislerini (services), kurulu programları (installed_apps) veya ortam değişkenlerini (env_vars) yönetir.",
                "parameters": {
                    "action": "'volume_up', 'volume_down', 'volume_mute', 'battery', 'services', 'installed_apps' veya 'env_vars'",
                    "steps": "Ses değişim kademesi (varsayılan: 5)",
                },
            },
            {
                "name": "web_research",
                "description": "Açık web üzerinde canlı arama yapar (search), herhangi bir web sayfasının temiz metin içeriğini okur (fetch) veya dosya indirir (download).",
                "parameters": {
                    "action": "'search', 'fetch' veya 'download'",
                    "query": "Arama sorgusu",
                    "url": "Hedef web adresi (URL)",
                    "save_path": "İndirilecek dosya kayıt yolu",
                },
            },
            {
                "name": "network_probe",
                "description": "Ağ bağlantılarını, açık portları, yerel IP adresini veya bir sunucuya ping/HTTP erişimini denetler.",
                "parameters": {"action": "'status', 'http_get' veya 'ping'", "target": "Hedef adres"},
            },
            {
                "name": "analyze_codebase",
                "description": "Proje veya klasördeki tüm kaynak kodlarını analiz eder: dillere göre dosya ve satır sayıları (.py, .cpp, .hpp, .js, .html, .md), sınıf/fonksiyon sayısı ve en büyük modülleri çıkarır.",
                "parameters": {"path": "Analiz edilecek dizin (varsayılan: çalışma alanı)"},
            },
            {
                "name": "file_power_ops",
                "description": "Gelişmiş dosya sistemi işlemleri: klasör oluşturma (mkdir), kopyalama (copy), taşıma (move), silme (delete), ZIP arşivleme (zip) ve ZIP açma (unzip).",
                "parameters": {"action": "'mkdir', 'copy', 'move', 'delete', 'zip' veya 'unzip'", "source": "Kaynak yol", "destination": "Hedef yol"},
            },
            {
                "name": "voice_tts",
                "description": "Windows SAPI Ses Sentezleyici (Text-to-Speech) üzerinden bilgisayar hoparlöründen sesli olarak konuşur.",
                "parameters": {"text": "Seslendirilecek Türkçe veya İngilizce metin"},
            },
            {
                "name": "build_interactive_webapp",
                "description": "Manus-AI tarzı interaktif HTML5/CSS3/JS canlı gösterge paneli ve masaüstü web uygulaması üretip ekranda açar.",
                "parameters": {"title": "Uygulama başlığı", "output_path": "Kaydedilecek HTML yolu", "launch": True},
            },
            {
                "name": "smart_workspace_search",
                "description": "Çalışma alanında .git/__pycache__/node_modules ve ikili dosyaları atlayarak hızlı regex/metin araması yapar ve file:line parçacıkları döndürür.",
                "parameters": {
                    "query": "Aranacak metin veya regex",
                    "path": "Opsiyonel hedef dizin",
                    "file_pattern": "Opsiyonel dosya filtresi (örn. '*.py' veya '*.py,*.js')",
                    "case_sensitive": "Büyük/küçük harf duyarlılığı (False)",
                    "max_results": "Maksimum eşleşme sayısı (varsayılan: 40)",
                    "context_lines": "Eşleşme etrafındaki bağlam satır sayısı (0-3)",
                },
            },
            {
                "name": "clipboard_manager",
                "description": "Windows panosunu (clipboard) UTF-8/Türkçe ve çok satırlı metinleri bozmadan güvenilir biçimde okur (get), yazar (set) veya temizler (clear).",
                "parameters": {"action": "'get', 'set' veya 'clear'", "text": "Panoya yazılacak metin"},
            },
            {
                "name": "system_notification",
                "description": "Windows masaüstünde yerel sistem bildirimi (balloon/toast) gösterir (bloklamayan, penceresiz arka plan yürütmesi).",
                "parameters": {
                    "title": "Bildirim başlığı",
                    "message": "Bildirim metni",
                    "level": "'info', 'warning' veya 'error'",
                    "duration_ms": "Gösterim süresi ms (varsayılan: 4000)",
                },
            },
            {
                "name": "kam_defense_tool",
                "description": "KAM'ın 18 yerleşik siber-fiziksel savunma, Aktif Çıkarım (EFE), C++20 JIT, Lyapunov CLF, CBF, EW Radar, TRN, FSO Lazer ve HJI Füze Kaçınma aracını çalıştırır.",
                "parameters": {"tool_name": "MCP araç adı", "arguments": "Araç argüman sözlüğü"},
            },
        ]

    # ------------------------------------------------------------------
    # 2. GERÇEK BİLGİSAYAR VE İŞLETİM SİSTEMİ ARAÇ İCRACILARI
    # ------------------------------------------------------------------
    def execute_tool(self, name: str, args: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        args = args or {}
        t0 = time.perf_counter()
        try:
            if name == "run_shell_command":
                res = self._tool_run_shell(args)
            elif name == "get_real_system_telemetry":
                res = self._tool_system_telemetry()
            elif name == "list_directory":
                res = self._tool_list_directory(args)
            elif name == "read_file":
                res = self._tool_read_file(args)
            elif name == "write_file":
                res = self._tool_write_file(args)
            elif name == "edit_file":
                res = self._tool_edit_file(args)
            elif name == "search_in_files":
                res = self._tool_search_in_files(args)
            elif name == "smart_workspace_search":
                res = self._tool_smart_workspace_search(args)
            elif name == "clipboard_manager":
                res = self._tool_clipboard_manager(args)
            elif name == "system_notification":
                res = self._tool_system_notification(args)
            elif name in ("execute_python_code", "codeact"):
                res = self._tool_execute_python(args)
            elif name == "manage_processes":
                res = self._tool_manage_processes(args)
            elif name == "launch_application":
                res = self._tool_launch_application(args)
            elif name == "desktop_window_manager":
                res = self._tool_desktop_window_manager(args)
            elif name == "mouse_control":
                res = Win32ComputerUseController.mouse_action(args)
            elif name == "keyboard_control":
                res = Win32ComputerUseController.keyboard_action(args)
            elif name == "os_hardware_control":
                res = self._tool_os_hardware_control(args)
            elif name == "web_research":
                res = self._tool_web_research(args)
            elif name == "network_probe":
                res = self._tool_network_probe(args)
            elif name == "analyze_codebase":
                res = self._tool_analyze_codebase(args)
            elif name == "file_power_ops":
                res = self._tool_file_power_ops(args)
            elif name == "voice_tts":
                res = self._tool_voice_tts(args)
            elif name == "build_interactive_webapp":
                res = self._tool_build_interactive_webapp(args)
            elif name == "kam_defense_tool":
                sub_name = args.get("tool_name", "read_telemetry")
                sub_args = args.get("arguments", {})
                res = self.mcp.call_tool(sub_name, sub_args)
            elif name in {t["name"] for t in self.mcp.list_tools()["tools"]}:
                res = self.mcp.call_tool(name, args)
            else:
                res = {"status": "error", "error": f"Bilinmeyen araç: {name}"}
        except Exception as exc:
            res = {
                "status": "error",
                "tool": name,
                "error": str(exc),
                "trace": traceback.format_exc(limit=3),
            }

        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        if isinstance(res, dict):
            res["execution_time_ms"] = elapsed_ms
        record = {
            "timestamp": time.strftime("%H:%M:%S"),
            "tool": name,
            "arguments": args,
            "result": res,
            "duration_ms": elapsed_ms,
        }
        self.execution_history.append(record)
        if len(self.execution_history) > 500:
            self.execution_history = self.execution_history[-500:]
        return res

    def _resolve_path(self, raw_path: str) -> str:
        if not raw_path:
            return self.workspace_root
        expanded = os.path.expanduser(os.path.expandvars(raw_path.strip().strip('"').strip("'")))
        if expanded.lower() in ("masaustu", "masaüstü", "desktop"):
            return os.path.join(os.path.expanduser("~"), "Desktop")
        if expanded.lower() in ("indirilenler", "downloads"):
            return os.path.join(os.path.expanduser("~"), "Downloads")
        if expanded.lower() in ("belgeler", "documents"):
            return os.path.join(os.path.expanduser("~"), "Documents")
        if os.path.isabs(expanded):
            return os.path.abspath(expanded)
        return os.path.abspath(os.path.join(self.workspace_root, expanded))

    def _tool_run_shell(self, args: Dict[str, Any]) -> Dict[str, Any]:
        command = str(args.get("command", "")).strip()
        if not command:
            return {"status": "error", "error": "Boş komut gönderildi."}

        safe, reason = HostSafetyShield.verify_command(command)
        if not safe:
            return {"status": "blocked_by_safety_shield", "reason": reason, "command": command}

        cwd = self._resolve_path(args.get("cwd", self.workspace_root))
        if not os.path.isdir(cwd):
            cwd = self.workspace_root

        try:
            timeout_sec = max(1.0, min(120.0, float(args.get("timeout", 25.0))))
        except (TypeError, ValueError):
            timeout_sec = 25.0

        if sys.platform == "win32":
            full_cmd = _ps_build_command(command)
        else:
            full_cmd = ["/bin/bash", "-c", command]

        try:
            proc = subprocess.run(
                full_cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_sec,
                creationflags=_CREATE_NO_WINDOW,
            )
        except subprocess.TimeoutExpired as exc:
            out_partial = exc.stdout.decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            err_partial = exc.stderr.decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
            return {
                "status": "timeout",
                "command": command,
                "cwd": cwd,
                "timeout_sec": timeout_sec,
                "error": f"Komut {timeout_sec}s zaman aşımına uğradı.",
                "stdout": out_partial.strip()[:3000],
                "stderr": err_partial.strip()[:2000],
            }

        stdout = (proc.stdout or "").strip()
        stderr = (proc.stderr or "").strip()
        if len(stdout) > 6000:
            stdout = stdout[:6000] + "\n...[ÇIKTI KISALTILDI]..."
        if len(stderr) > 3000:
            stderr = stderr[:3000] + "\n...[HATA ÇIKTISI KISALTILDI]..."

        return {
            "status": "success" if proc.returncode == 0 else "non_zero_exit",
            "command": command,
            "cwd": cwd,
            "exit_code": proc.returncode,
            "stdout": stdout,
            "stderr": stderr,
        }

    def _tool_system_telemetry(self) -> Dict[str, Any]:
        screen_info = Win32ComputerUseController.get_screen_and_cursor()
        info: Dict[str, Any] = {
            "status": "success",
            "hostname": socket.gethostname(),
            "os_platform": f"{platform.system()} {platform.release()} ({platform.version()})",
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "cpu_logical_cores": os.cpu_count() or 1,
            "python_version": sys.version.split()[0],
            "workspace_root": self.workspace_root,
            "display_and_cursor": {
                "resolution": f"{screen_info.get('screen_width', 1920)}x{screen_info.get('screen_height', 1080)}",
                "cursor_xy": [screen_info.get("cursor_x", 0), screen_info.get("cursor_y", 0)],
            },
        }

        if sys.platform == "win32":
            try:
                class MEMORYSTATUSEX(ctypes.Structure):
                    _fields_ = [
                        ("dwLength", ctypes.c_ulong),
                        ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong),
                        ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong),
                        ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong),
                        ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                    ]

                mem = MEMORYSTATUSEX()
                mem.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
                ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem))
                total_gb = round(mem.ullTotalPhys / (1024 ** 3), 2)
                avail_gb = round(mem.ullAvailPhys / (1024 ** 3), 2)
                used_gb = round(total_gb - avail_gb, 2)
                info["ram"] = {
                    "total_gb": total_gb,
                    "used_gb": used_gb,
                    "available_gb": avail_gb,
                    "usage_percent": int(mem.dwMemoryLoad),
                }
            except Exception:
                pass

        try:
            usage = shutil.disk_usage(self.workspace_root)
            info["disk"] = {
                "drive": os.path.splitdrive(self.workspace_root)[0] or "/",
                "total_gb": round(usage.total / (1024 ** 3), 2),
                "used_gb": round(usage.used / (1024 ** 3), 2),
                "free_gb": round(usage.free / (1024 ** 3), 2),
                "usage_percent": round((usage.used / max(1, usage.total)) * 100.0, 1),
            }
        except Exception:
            pass

        try:
            smi = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=name,temperature.gpu,utilization.gpu,memory.used,memory.total,power.draw",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=3.0,
                creationflags=_CREATE_NO_WINDOW,
            )
            if smi.returncode == 0 and smi.stdout.strip():
                parts = [p.strip() for p in smi.stdout.strip().splitlines()[0].split(",")]
                if len(parts) >= 5:
                    info["gpu"] = {
                        "name": parts[0],
                        "temp_c": _to_float(parts[1]),
                        "utilization_pct": _to_float(parts[2]),
                        "vram_used_mb": _to_float(parts[3]),
                        "vram_total_mb": _to_float(parts[4]),
                        "power_draw_w": parts[5] if len(parts) > 5 else "N/A",
                    }
        except Exception:
            pass

        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.5)
            s.connect(("8.8.8.8", 80))
            info["local_ip"] = s.getsockname()[0]
            s.close()
        except Exception:
            info["local_ip"] = "127.0.0.1"

        return info

    def _tool_list_directory(self, args: Dict[str, Any]) -> Dict[str, Any]:
        target_dir = self._resolve_path(args.get("path", self.workspace_root))
        pattern = args.get("pattern", "*")
        if not os.path.exists(target_dir):
            return {"status": "error", "error": f"Dizin bulunamadı: {target_dir}"}
        if os.path.isfile(target_dir):
            st = os.stat(target_dir)
            return {
                "status": "success",
                "path": target_dir,
                "type": "file",
                "size_bytes": st.st_size,
            }

        items = []
        for entry in sorted(Path(target_dir).glob(pattern), key=lambda p: (not p.is_dir(), p.name.lower())):
            try:
                st = entry.stat()
                items.append({
                    "name": entry.name,
                    "type": "dir" if entry.is_dir() else "file",
                    "size_bytes": 0 if entry.is_dir() else st.st_size,
                })
            except Exception:
                continue
            if len(items) >= 150:
                break

        return {
            "status": "success",
            "directory": target_dir,
            "total_listed": len(items),
            "entries": items,
        }

    def _tool_read_file(self, args: Dict[str, Any]) -> Dict[str, Any]:
        path = self._resolve_path(args.get("path", ""))
        if not os.path.isfile(path):
            return {"status": "error", "error": f"Dosya bulunamadı: {path}"}

        start_line = max(1, int(args.get("start_line", 1)))
        end_line = max(start_line, int(args.get("end_line", start_line + 120)))

        with open(path, "r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()

        selected = all_lines[start_line - 1 : end_line]
        numbered = "".join(f"{idx}: {line}" for idx, line in enumerate(selected, start=start_line))
        return {
            "status": "success",
            "path": path,
            "total_lines": len(all_lines),
            "shown_range": f"{start_line}-{min(end_line, len(all_lines))}",
            "content": numbered,
        }

    def _tool_write_file(self, args: Dict[str, Any]) -> Dict[str, Any]:
        raw_path = str(args.get("path", "")).strip()
        if not raw_path:
            return {"status": "error", "error": "Dosya yolu belirtilmedi."}
        path = self._resolve_path(raw_path)
        content = str(args.get("content", ""))
        append = bool(args.get("append", False))

        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)

        mode = "a" if append else "w"
        with open(path, mode, encoding="utf-8") as f:
            f.write(content)

        return {
            "status": "success",
            "action": "appended" if append else "written",
            "path": path,
            "bytes_written": len(content.encode("utf-8")),
            "file_exists": os.path.isfile(path),
        }

    def _tool_edit_file(self, args: Dict[str, Any]) -> Dict[str, Any]:
        path = self._resolve_path(args.get("path", ""))
        target = str(args.get("target", ""))
        replacement = str(args.get("replacement", ""))
        if not os.path.isfile(path):
            return {"status": "error", "error": f"Dosya bulunamadı: {path}"}
        if not target:
            return {"status": "error", "error": "Değiştirilecek hedef metin (target) boş olamaz."}

        with open(path, "r", encoding="utf-8", errors="replace") as f:
            original = f.read()

        if target not in original:
            return {"status": "error", "path": path, "error": "Hedef metin dosyada bulunamadı."}

        count = original.count(target)
        updated = original.replace(target, replacement)
        with open(path, "w", encoding="utf-8") as f:
            f.write(updated)

        return {
            "status": "success",
            "path": path,
            "replacements_made": count,
            "new_size_bytes": len(updated.encode("utf-8")),
        }

    def _tool_search_in_files(self, args: Dict[str, Any]) -> Dict[str, Any]:
        query = str(args.get("query", "")).strip()
        if not query:
            return {"status": "error", "error": "Arama sorgusu boş olamaz."}
        root_dir = self._resolve_path(args.get("path", self.workspace_root))
        file_pattern = str(args.get("file_pattern", "*.py"))

        matches = []
        try:
            pattern_re = re.compile(query, re.IGNORECASE)
        except re.error:
            pattern_re = re.compile(re.escape(query), re.IGNORECASE)

        def _scan_file(fpath: str) -> bool:
            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    for lineno, line in enumerate(f, start=1):
                        if pattern_re.search(line):
                            matches.append({
                                "file": _safe_relpath(fpath, self.workspace_root),
                                "line": lineno,
                                "snippet": line.strip()[:180],
                            })
                            if len(matches) >= 50:
                                return True
            except Exception:
                pass
            return False

        if os.path.isfile(root_dir):
            truncated = _scan_file(root_dir)
            if truncated:
                return {"status": "success", "query": query, "matches": matches, "truncated": True}
            return {"status": "success", "query": query, "total_matches": len(matches), "matches": matches}

        skip_dirs = {".git", "__pycache__", ".pytest_cache", "node_modules", "weights", "build"}
        for dirpath, dirnames, filenames in os.walk(root_dir):
            dirnames[:] = [d for d in dirnames if d not in skip_dirs]
            for fname in filenames:
                if file_pattern != "*" and not Path(fname).match(file_pattern):
                    continue
                if _scan_file(os.path.join(dirpath, fname)):
                    return {"status": "success", "query": query, "matches": matches, "truncated": True}

        return {"status": "success", "query": query, "total_matches": len(matches), "matches": matches}

    def _tool_execute_python(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Manus-AI Tarzı Durum-Korumalı (Stateful) CodeAct Çalışma Zamanı.
        Önceki adımlarda tanımlanan değişkenleri (`self.codeact_globals`) korur
        ve `host.*` üzerinden doğrudan işletim sistemine erişim sağlar.
        """
        code = _strip_code_fences(str(args.get("code", "")))
        if not code:
            return {"status": "error", "error": "Boş Python kodu."}

        stdout_buf = StringIO()
        stderr_buf = StringIO()
        result_val = None
        with self._codeact_lock:
            prev_result = self.codeact_globals.pop("result", _MISSING)
            try:
                with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
                    try:
                        compiled_expr = compile(code, "<kam_codeact_expr>", "eval")
                        result_val = eval(compiled_expr, self.codeact_globals)
                    except SyntaxError:
                        compiled_exec = compile(code, "<kam_codeact_exec>", "exec")
                        exec(compiled_exec, self.codeact_globals)
                        if "result" in self.codeact_globals:
                            result_val = self.codeact_globals["result"]
            except SystemExit as exc:
                return {
                    "status": "error",
                    "error": f"CodeAct içinde sys.exit({exc.code}) engellendi.",
                    "stdout": stdout_buf.getvalue()[:12000],
                    "stderr": stderr_buf.getvalue()[:4000],
                }
            except Exception as exc:
                if prev_result is not _MISSING and "result" not in self.codeact_globals:
                    self.codeact_globals["result"] = prev_result
                return {
                    "status": "error",
                    "error": str(exc),
                    "traceback": traceback.format_exc(limit=4),
                    "stdout": stdout_buf.getvalue()[:12000],
                    "stderr": stderr_buf.getvalue()[:4000],
                }

        out_text = stdout_buf.getvalue().strip()
        err_text = stderr_buf.getvalue().strip()
        if result_val is not None and not out_text:
            out_text = repr(result_val)
        if len(out_text) > 12000:
            out_text = out_text[:12000] + "\n...[STDOUT KISALTILDI]..."
        if len(err_text) > 4000:
            err_text = err_text[:4000] + "\n...[STDERR KISALTILDI]..."

        ret_repr = repr(result_val) if result_val is not None else None
        if ret_repr and len(ret_repr) > 4000:
            ret_repr = ret_repr[:4000] + "...[KISALTILDI]"

        return {
            "status": "success",
            "engine": "KAM-Stateful-CodeAct-Runtime",
            "stdout": out_text,
            "stderr": err_text,
            "return_value": ret_repr,
        }

    def _tool_manage_processes(self, args: Dict[str, Any]) -> Dict[str, Any]:
        action = str(args.get("action", "list")).lower().strip()
        target = str(args.get("target", "")).strip()

        if action in ("list", "find"):
            if sys.platform == "win32":
                safe_regex = _ps_escape_single_quoted(re.escape(target)) if target else ""
                filter_clause = (
                    f"| Where-Object {{ $_.ProcessName -match '{safe_regex}' }}" if safe_regex else ""
                )
                ps_cmd = (
                    f"Get-Process {filter_clause} "
                    "| Sort-Object WorkingSet64 -Descending "
                    "| Select-Object -First 25 Id, ProcessName, @{Name='MemoryMB';Expression={[math]::Round($_.WorkingSet64/1MB,1)}}, CPU "
                    "| ConvertTo-Json -Compress"
                )
                res = self._tool_run_shell({"command": ps_cmd})
                try:
                    procs = json.loads(res.get("stdout", "[]") or "[]")
                    if isinstance(procs, dict):
                        procs = [procs]
                except Exception:
                    procs = []
                return {"status": "success", "action": action, "filter": target, "processes": procs}
            else:
                res = self._tool_run_shell({"command": "ps aux --sort=-%mem | head -n 25"})
                return {"status": "success", "action": action, "raw_output": res.get("stdout", "")}

        elif action == "kill":
            if not target:
                return {"status": "error", "error": "Sonlandırılacak süreç adı veya PID belirtilmedi."}
            if target.isdigit():
                cmd = f"Stop-Process -Id {int(target)} -Force" if sys.platform == "win32" else f"kill -9 {int(target)}"
            else:
                clean_name = re.sub(r"\.exe$", "", target, flags=re.IGNORECASE).strip()
                if clean_name.lower() in HostSafetyShield.PROTECTED_PROCESS_NAMES:
                    return {
                        "status": "blocked_by_safety_shield",
                        "reason": f"CBF Güvenlik Kalkanı İhlali: Kritik sistem süreci '{clean_name}' sonlandırılamaz.",
                    }
                safe_name = _ps_escape_single_quoted(clean_name)
                cmd = f"Stop-Process -Name '{safe_name}' -Force" if sys.platform == "win32" else f"pkill -f '{safe_name}'"
            return self._tool_run_shell({"command": cmd})

        return {"status": "error", "error": f"Bilinmeyen süreç eylemi: {action}"}

    def _tool_launch_application(self, args: Dict[str, Any]) -> Dict[str, Any]:
        target = str(args.get("target", "")).strip()
        extra_args = str(args.get("arguments", "")).strip()
        if not target:
            return {"status": "error", "error": "Açılacak uygulama veya hedef belirtilmedi."}

        aliases = {
            "hesap makinesi": "calc.exe",
            "calculator": "calc.exe",
            "calc": "calc.exe",
            "not defteri": "notepad.exe",
            "notepad": "notepad.exe",
            "dosya gezgini": "explorer.exe",
            "gezgin": "explorer.exe",
            "explorer": "explorer.exe",
            "görev yöneticisi": "taskmgr.exe",
            "taskmgr": "taskmgr.exe",
            "cmd": "cmd.exe",
            "terminal": "powershell.exe",
            "powershell": "powershell.exe",
            "paint": "mspaint.exe",
            "denetim masası": "control.exe",
            "ayarlar": "ms-settings:",
        }
        resolved_target = aliases.get(target.lower(), target)

        safe, reason = HostSafetyShield.verify_command(f"{resolved_target} {extra_args}".strip())
        if not safe:
            return {"status": "blocked_by_safety_shield", "reason": reason, "target": resolved_target}

        try:
            if sys.platform == "win32" and not extra_args and (
                resolved_target.startswith(("http://", "https://", "ms-settings:"))
                or os.path.exists(self._resolve_path(resolved_target))
            ):
                final_target = (
                    resolved_target
                    if resolved_target.startswith(("http://", "https://", "ms-settings:"))
                    else self._resolve_path(resolved_target)
                )
                os.startfile(final_target)
                return {"status": "success", "launched": final_target, "method": "os.startfile"}
            else:
                cmd_list = [resolved_target] + ([extra_args] if extra_args else [])
                proc = subprocess.Popen(cmd_list, shell=(sys.platform == "win32"))
                return {"status": "success", "launched": resolved_target, "pid": proc.pid}
        except Exception as exc:
            return {"status": "error", "target": resolved_target, "error": str(exc)}

    def _find_window_by_title(self, query_title: str) -> Optional[Dict[str, Any]]:
        q_low = query_title.lower().strip()
        # Yaygın Türkçe pencere takma adları
        title_synonyms = {
            "not defteri": ["not defteri", "notepad", "adsız", "untitled"],
            "notepad": ["not defteri", "notepad", "adsız", "untitled"],
            "hesap makinesi": ["hesap makinesi", "calculator"],
            "tarayıcı": ["chrome", "edge", "firefox", "brave"],
        }
        candidates = title_synonyms.get(q_low, [q_low])
        for w in Win32ComputerUseController.enumerate_windows_detailed():
            w_low = w["title"].lower()
            if any(c in w_low for c in candidates):
                return w
        return None

    def _tool_desktop_window_manager(self, args: Dict[str, Any]) -> Dict[str, Any]:
        action = str(args.get("action", "list_windows")).lower().strip()
        value = str(args.get("value", "")).strip()

        if action == "list_windows":
            windows = Win32ComputerUseController.enumerate_windows_detailed()
            return {"status": "success", "open_windows_count": len(windows), "windows": windows[:40]}

        elif action in ("focus_window", "minimize_window", "maximize_window", "restore_window", "close_window"):
            if sys.platform == "win32" and value:
                target_win = self._find_window_by_title(value)
                if target_win:
                    hwnd = target_win["hwnd"]
                    user32 = ctypes.windll.user32
                    if action == "focus_window":
                        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                        user32.SetForegroundWindow(hwnd)
                    elif action == "minimize_window":
                        user32.ShowWindow(hwnd, 6)  # SW_MINIMIZE
                    elif action == "maximize_window":
                        user32.ShowWindow(hwnd, 3)  # SW_MAXIMIZE
                        user32.SetForegroundWindow(hwnd)
                    elif action == "restore_window":
                        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                    elif action == "close_window":
                        user32.PostMessageW(hwnd, 0x0010, 0, 0)  # WM_CLOSE
                    return {
                        "status": "success",
                        "action": action,
                        "window": target_win["title"],
                        "hwnd": hwnd,
                        "bounds": target_win["bounds"],
                    }
            return {"status": "error", "error": f"Pencere bulunamadı: {value}"}

        elif action == "get_clipboard":
            res = self._tool_run_shell({"command": "Get-Clipboard"})
            return {"status": "success" if res.get("status") == "success" else "error", "clipboard": res.get("stdout", "")}

        elif action == "set_clipboard":
            escaped = _ps_escape_single_quoted(value)
            res = self._tool_run_shell({"command": f"Set-Clipboard -Value '{escaped}'"})
            if res.get("status") != "success":
                return {"status": "error", "error": res.get("stderr") or res.get("error") or "Pano yazılamadı."}
            return {"status": "success", "copied_chars": len(value), "preview": value[:120]}

        elif action == "screenshot":
            out_path = self._resolve_path(value or os.path.join(self.workspace_root, "assets", "kam_live_capture.png"))
            parent_dir = os.path.dirname(out_path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)
            try:
                from PyQt6.QtGui import QGuiApplication
                app = QGuiApplication.instance()
                if app and app.primaryScreen():
                    pixmap = app.primaryScreen().grabWindow(0)
                    pixmap.save(out_path, "PNG")
                    return {
                        "status": "success",
                        "screenshot_path": out_path,
                        "resolution": f"{pixmap.width()}x{pixmap.height()}",
                        "size_bytes": os.path.getsize(out_path),
                    }
            except Exception:
                pass

            safe_out_path = _ps_escape_single_quoted(out_path)
            ps_shot = (
                "Add-Type -AssemblyName System.Windows.Forms,System.Drawing; "
                "$b = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds; "
                "$bmp = New-Object System.Drawing.Bitmap $b.Width, $b.Height; "
                "$g = [System.Drawing.Graphics]::FromImage($bmp); "
                "try { "
                "$g.CopyFromScreen($b.Location, [System.Drawing.Point]::Empty, $b.Size); "
                f"$bmp.Save('{safe_out_path}', [System.Drawing.Imaging.ImageFormat]::Png); "
                "} finally { $g.Dispose(); $bmp.Dispose() }"
            )
            self._tool_run_shell({"command": ps_shot})
            return {
                "status": "success" if os.path.isfile(out_path) else "error",
                "screenshot_path": out_path,
                "size_bytes": os.path.getsize(out_path) if os.path.isfile(out_path) else 0,
            }

        return {"status": "error", "error": f"Bilinmeyen masaüstü eylemi: {action}"}

    def _tool_os_hardware_control(self, args: Dict[str, Any]) -> Dict[str, Any]:
        action = str(args.get("action", "battery")).lower().strip()
        steps = max(1, min(50, int(args.get("steps", 5))))

        if action in ("volume_up", "volume_down", "volume_mute"):
            if sys.platform == "win32":
                vk = Win32ComputerUseController.VK_MAP[action]
                count = 1 if action == "volume_mute" else steps
                for _ in range(count):
                    ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
                    ctypes.windll.user32.keybd_event(vk, 0, 2, 0)
                    time.sleep(0.01)
                return {"status": "success", "action": action, "steps_applied": count}

        elif action == "battery":
            if sys.platform == "win32":
                class SYSTEM_POWER_STATUS(ctypes.Structure):
                    _fields_ = [
                        ("ACLineStatus", ctypes.c_ubyte),
                        ("BatteryFlag", ctypes.c_ubyte),
                        ("BatteryLifePercent", ctypes.c_ubyte),
                        ("SystemStatusFlag", ctypes.c_ubyte),
                        ("BatteryLifeTime", ctypes.c_ulong),
                        ("BatteryFullLifeTime", ctypes.c_ulong),
                    ]

                sps = SYSTEM_POWER_STATUS()
                ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(sps))
                pct = int(sps.BatteryLifePercent)
                return {
                    "status": "success",
                    "ac_plugged_in": bool(sps.ACLineStatus == 1),
                    "battery_percent": pct if 0 <= pct <= 100 else 100,
                    "battery_present": bool(sps.BatteryFlag != 128 and pct != 255),
                    "battery_saver_active": bool(sps.SystemStatusFlag == 1),
                }

        elif action == "services":
            res = self._tool_run_shell({
                "command": "Get-Service | Where-Object {$_.Status -eq 'Running'} | Select-Object -First 25 Name, DisplayName, Status | ConvertTo-Json -Compress"
            })
            try:
                svcs = json.loads(res.get("stdout", "[]") or "[]")
                if isinstance(svcs, dict):
                    svcs = [svcs]
            except Exception:
                svcs = []
            return {"status": "success", "running_services_sample": svcs}

        elif action == "installed_apps":
            res = self._tool_run_shell({
                "command": "Get-ItemProperty HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\* | Where-Object {$_.DisplayName} | Select-Object -First 30 DisplayName, DisplayVersion, Publisher | ConvertTo-Json -Compress"
            })
            try:
                apps = json.loads(res.get("stdout", "[]") or "[]")
                if isinstance(apps, dict):
                    apps = [apps]
            except Exception:
                apps = []
            return {"status": "success", "installed_applications": apps}

        elif action == "env_vars":
            safe_env = {
                k: v for k, v in os.environ.items()
                if not any(secret in k.lower() for secret in ("key", "token", "secret", "password"))
            }
            return {"status": "success", "total_vars": len(safe_env), "sample": dict(list(safe_env.items())[:30])}

        elif action == "drives":
            drives = []
            if sys.platform == "win32":
                bitmask = ctypes.windll.kernel32.GetLogicalDrives()
                for i in range(26):
                    if bitmask & (1 << i):
                        d_letter = f"{chr(65 + i)}:\\"
                        try:
                            u = shutil.disk_usage(d_letter)
                            drives.append({
                                "drive": d_letter,
                                "total_gb": round(u.total / (1024 ** 3), 2),
                                "used_gb": round(u.used / (1024 ** 3), 2),
                                "free_gb": round(u.free / (1024 ** 3), 2),
                                "usage_percent": round((u.used / max(1, u.total)) * 100.0, 1),
                            })
                        except Exception:
                            continue
            return {"status": "success", "PermissionLevel": self.permission_level, "drives": drives}

        elif action == "wifi":
            res = self._tool_run_shell({"command": "netsh wlan show interfaces"})
            return {"status": "success", "wifi_interfaces": res.get("stdout", "")}

        elif action == "startup":
            res = self._tool_run_shell({
                "command": "Get-CimInstance Win32_StartupCommand | Select-Object Name, Command, Location, User | ConvertTo-Json -Compress"
            })
            try:
                startup_items = json.loads(res.get("stdout", "[]") or "[]")
                if isinstance(startup_items, dict):
                    startup_items = [startup_items]
            except Exception:
                startup_items = res.get("stdout", "")
            return {"status": "success", "startup_commands": startup_items}

        elif action == "large_files":
            scan_dir = self._resolve_path(args.get("path", self.workspace_root))
            found = []
            skip_dirs = {".git", "__pycache__", "node_modules"}
            for dirpath, dirnames, filenames in os.walk(scan_dir):
                dirnames[:] = [d for d in dirnames if d not in skip_dirs]
                for fname in filenames:
                    fpath = os.path.join(dirpath, fname)
                    try:
                        sz = os.path.getsize(fpath)
                        found.append((sz, fpath))
                    except Exception:
                        continue
            found.sort(key=lambda x: x[0], reverse=True)
            top_files = [
                {"path": p, "size_mb": round(s / (1024 * 1024), 2), "size_bytes": s}
                for s, p in found[:15]
            ]
            return {"status": "success", "scanned_directory": scan_dir, "largest_files": top_files}

        elif action == "permissions":
            is_admin = False
            if sys.platform == "win32":
                try:
                    is_admin = bool(ctypes.windll.shell32.IsUserAnAdmin())
                except Exception:
                    is_admin = False
            return {
                "status": "success",
                "full_permissions_granted": self.full_permissions,
                "permission_tier": self.permission_level,
                "os_admin_token": is_admin,
                "capabilities_unlocked": [
                    "ALL_DRIVES_READ_WRITE",
                    "POWERSHELL_UNRESTRICTED_EXEC",
                    "STATEFUL_PYTHON_CODEACT",
                    "WIN32_MOUSE_KEYBOARD_INJECTION",
                    "WIN32_WINDOW_GEOMETRY_UIA",
                    "PROCESS_AND_SERVICE_CONTROL",
                    "HARDWARE_AUDIO_POWER_BATTERY",
                    "OPEN_WEB_RESEARCH_AND_SCRAPING",
                    "PERSISTENT_EPISODIC_MEMORY",
                    "18_CYBER_PHYSICAL_DEFENSE_TOOLS",
                ],
            }

        return {"status": "error", "error": f"Bilinmeyen donanım/OS eylemi: {action}"}

    def _tool_web_research(self, args: Dict[str, Any]) -> Dict[str, Any]:
        action = str(args.get("action", "search")).lower().strip()
        query = str(args.get("query", "")).strip()
        url = str(args.get("url", "")).strip()
        save_path = str(args.get("save_path", "")).strip()

        if action == "search":
            return WebResearchEngine.search_web(query or url)
        elif action == "fetch" and url:
            return WebResearchEngine.fetch_webpage_clean(url)
        elif action == "download" and url:
            if not url.lower().startswith(("http://", "https://")):
                return {"status": "error", "error": "İndirme yalnızca http:// veya https:// adreslerinden yapılabilir."}
            dest = self._resolve_path(save_path or os.path.basename(urllib.parse.urlparse(url).path) or "downloaded_file.bin")
            parent_dir = os.path.dirname(dest)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) KAM-Autonomous-Agent/3.5"},
            )
            max_bytes = 50 * 1024 * 1024  # 50 MB güvenlik sınırı
            total_written = 0
            try:
                with urllib.request.urlopen(req, timeout=20.0) as resp, open(dest, "wb") as out_f:
                    while True:
                        chunk = resp.read(65536)
                        if not chunk:
                            break
                        total_written += len(chunk)
                        if total_written > max_bytes:
                            out_f.close()
                            try:
                                os.remove(dest)
                            except OSError:
                                pass
                            return {"status": "error", "url": url, "error": "Dosya 50 MB indirme sınırını aşıyor."}
                        out_f.write(chunk)
            except Exception as exc:
                return {"status": "error", "url": url, "error": str(exc)}
            return {"status": "success", "url": url, "saved_to": dest, "size_bytes": total_written}

        return {"status": "error", "error": f"Geçersiz web araştırma eylemi: {action}"}

    def _tool_network_probe(self, args: Dict[str, Any]) -> Dict[str, Any]:
        action = str(args.get("action", "status")).lower().strip()
        target = str(args.get("target", "")).strip()

        if action == "status":
            sys_info = self._tool_system_telemetry()
            ports_res = self._tool_run_shell({
                "command": "Get-NetTCPConnection -State Listen | Select-Object -First 20 LocalAddress, LocalPort, OwningProcess | ConvertTo-Json -Compress"
            })
            try:
                ports = json.loads(ports_res.get("stdout", "[]") or "[]")
                if isinstance(ports, dict):
                    ports = [ports]
            except Exception:
                ports = []
            return {
                "status": "success",
                "hostname": sys_info.get("hostname"),
                "local_ip": sys_info.get("local_ip"),
                "listening_ports": ports,
            }
        elif action == "http_get" and target:
            return WebResearchEngine.fetch_webpage_clean(target)
        elif action == "ping" and target:
            if not re.fullmatch(r"[a-zA-Z0-9._:\-]+", target):
                return {"status": "error", "error": f"Geçersiz ping hedefi: {target}"}
            safe_target = _ps_escape_single_quoted(target)
            if sys.platform == "win32":
                cmd = f"Test-Connection -ComputerName '{safe_target}' -Count 2 | Select-Object Address, ResponseTime | ConvertTo-Json -Compress"
            else:
                cmd = f"ping -c 2 '{safe_target}'"
            res = self._tool_run_shell({"command": cmd})
            return {"status": "success" if res.get("status") == "success" else "error", "target": target, "ping_output": res.get("stdout", ""), "stderr": res.get("stderr", "")}

        return {"status": "error", "error": f"Geçersiz ağ eylemi veya hedef: {action}"}

    def _tool_analyze_codebase(self, args: Dict[str, Any]) -> Dict[str, Any]:
        target_dir = self._resolve_path(args.get("path", self.workspace_root))
        ext_stats: Dict[str, Dict[str, int]] = {}
        total_files = 0
        total_lines = 0
        py_classes = 0
        py_functions = 0
        top_modules = []

        skip_dirs = {".git", "__pycache__", ".pytest_cache", "node_modules", "weights", "build"}
        tracked_exts = {".py", ".cpp", ".hpp", ".h", ".c", ".js", ".html", ".css", ".md", ".json", ".cmake"}

        for dirpath, dirnames, filenames in os.walk(target_dir):
            dirnames[:] = [d for d in dirnames if d not in skip_dirs]
            for fname in filenames:
                ext = os.path.splitext(fname)[1].lower()
                if ext not in tracked_exts and fname != "CMakeLists.txt":
                    continue
                if fname == "CMakeLists.txt":
                    ext = ".cmake"
                fpath = os.path.join(dirpath, fname)
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()
                    l_count = len(lines)
                    total_files += 1
                    total_lines += l_count
                    bucket = ext_stats.setdefault(ext, {"files": 0, "lines": 0})
                    bucket["files"] += 1
                    bucket["lines"] += l_count
                    top_modules.append((l_count, _safe_relpath(fpath, target_dir)))
                    if ext == ".py":
                        for line in lines:
                            s = line.lstrip()
                            if s.startswith("class "):
                                py_classes += 1
                            elif s.startswith("def "):
                                py_functions += 1
                except Exception:
                    continue

        top_modules.sort(key=lambda x: x[0], reverse=True)
        return {
            "status": "success",
            "analyzed_root": target_dir,
            "total_source_files": total_files,
            "total_lines_of_code": total_lines,
            "python_classes": py_classes,
            "python_functions": py_functions,
            "by_extension": ext_stats,
            "top_largest_modules": [{"file": p, "lines": l} for l, p in top_modules[:12]],
        }

    def _tool_file_power_ops(self, args: Dict[str, Any]) -> Dict[str, Any]:
        import zipfile
        action = str(args.get("action", "mkdir")).lower().strip()
        src = self._resolve_path(args.get("source", "")) if args.get("source") else ""
        dst = self._resolve_path(args.get("destination", "")) if args.get("destination") else ""

        if action == "mkdir" and src:
            os.makedirs(src, exist_ok=True)
            return {"status": "success", "action": "mkdir", "created_directory": src}
        elif action == "copy" and src and dst:
            if os.path.isdir(src):
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                dst_parent = os.path.dirname(dst)
                if dst_parent:
                    os.makedirs(dst_parent, exist_ok=True)
                shutil.copy2(src, dst)
            return {"status": "success", "action": "copy", "from": src, "to": dst}
        elif action == "move" and src and dst:
            dst_parent = os.path.dirname(dst)
            if dst_parent:
                os.makedirs(dst_parent, exist_ok=True)
            shutil.move(src, dst)
            return {"status": "success", "action": "move", "from": src, "to": dst}
        elif action == "delete" and src:
            safe_del, del_reason = HostSafetyShield.verify_delete_path(src)
            if not safe_del:
                return {"status": "blocked_by_safety_shield", "reason": del_reason, "path": src}
            if os.path.isfile(src):
                os.remove(src)
                return {"status": "success", "action": "delete", "deleted_file": src}
            return {"status": "error", "error": f"Silinecek dosya bulunamadı: {src}"}
        elif action == "zip" and src:
            zip_out = dst if dst.endswith(".zip") else (src.rstrip("/\\") + ".zip")
            with zipfile.ZipFile(zip_out, "w", zipfile.ZIP_DEFLATED) as zf:
                if os.path.isdir(src):
                    for root, _, files in os.walk(src):
                        for file in files:
                            full_p = os.path.join(root, file)
                            zf.write(full_p, os.path.relpath(full_p, src))
                else:
                    zf.write(src, os.path.basename(src))
            return {"status": "success", "action": "zip", "archive_path": zip_out, "size_bytes": os.path.getsize(zip_out)}
        elif action == "unzip" and src:
            out_dir = os.path.abspath(dst or os.path.splitext(src)[0])
            os.makedirs(out_dir, exist_ok=True)
            with zipfile.ZipFile(src, "r") as zf:
                for member in zf.infolist():
                    member_dest = os.path.abspath(os.path.join(out_dir, member.filename))
                    if not (member_dest == out_dir or member_dest.startswith(out_dir + os.sep)):
                        return {
                            "status": "blocked_by_safety_shield",
                            "reason": f"Zip Slip dizin aşımı engellendi: {member.filename}",
                        }
                zf.extractall(out_dir)
            return {"status": "success", "action": "unzip", "extracted_to": out_dir}

        return {"status": "error", "error": f"Geçersiz dosya sistemi eylemi veya eksik yol: {action}"}

    def _tool_voice_tts(self, args: Dict[str, Any]) -> Dict[str, Any]:
        raw_text = str(args.get("text", "KAM bilişsel zihni nöbette. Dirlik ve nizam kaimdir.")).strip()
        text = re.sub(r"[\r\n]+", " ", raw_text).strip()
        if sys.platform == "win32":
            escaped = _ps_escape_single_quoted(text)
            ps_tts = (
                "Add-Type -AssemblyName System.Speech; "
                "$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                "$synth.Rate = 0; $synth.Volume = 100; "
                f"$synth.Speak('{escaped}')"
            )
            subprocess.Popen(
                _ps_build_command(ps_tts),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=_CREATE_NO_WINDOW,
            )
            return {"status": "success", "spoken_text": text, "engine": "Windows-SAPI-SpeechSynthesizer"}
        return {"status": "unsupported_platform", "spoken_text": text}

    def _tool_build_interactive_webapp(self, args: Dict[str, Any]) -> Dict[str, Any]:
        title = str(args.get("title", "KAM // OTONOM SİBER KOMUTA & SİSTEM KOKPİTİ")).strip()
        safe_title = html.escape(title)
        out_path = self._resolve_path(
            args.get("output_path") or os.path.join(self.workspace_root, "assets", "kam_autonomous_cockpit.html")
        )
        launch = bool(args.get("launch", True))
        sys_info = self._tool_system_telemetry()
        code_info = self._tool_analyze_codebase({})

        html_doc = f"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<title>{safe_title}</title>
<style>
  body {{ background: #050811; color: #E2E8F0; font-family: 'Segoe UI', sans-serif; margin: 0; padding: 28px; }}
  .header {{ border-bottom: 1px solid #1E293B; padding-bottom: 16px; margin-bottom: 24px; display:flex; justify-content:space-between; align-items:center; }}
  .title {{ font-size: 22px; font-weight: 800; letter-spacing: 3px; color: #00E5FF; }}
  .badge {{ background: rgba(16,185,129,0.15); color: #10B981; border: 1px solid #10B981; padding: 6px 14px; border-radius: 20px; font-family: Consolas, monospace; font-weight: 700; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(290px, 1fr)); gap: 18px; }}
  .card {{ background: #090E1A; border: 1px solid #1E293B; border-left: 3px solid #00E5FF; border-radius: 10px; padding: 18px; }}
  .card h3 {{ margin-top: 0; color: #00E5FF; font-size: 13px; letter-spacing: 1.5px; text-transform: uppercase; }}
  .metric {{ font-size: 28px; font-weight: 800; color: #F8FAFC; font-family: Consolas, monospace; margin: 8px 0; }}
  .sub {{ color: #94A3B8; font-size: 12px; }}
</style>
</head>
<body>
  <div class="header">
    <div>
      <div class="title">{safe_title}</div>
      <div class="sub">Dede Korkut Hikmeti &bull; Karl Friston Serbest Enerji (F &rarr; 0) &bull; Manus-Sınıfı Tam Yetkili AgentOS</div>
    </div>
    <div class="badge" id="clock">NÖBET AKTİF</div>
  </div>
  <div class="grid">
    <div class="card">
      <h3>I. Bilgisayar & İşlemci</h3>
      <div class="metric">{sys_info.get('hostname')}</div>
      <div class="sub">{sys_info.get('os_platform')}<br>Çekirdek: {sys_info.get('cpu_logical_cores')} Mantıksal İşlemci</div>
    </div>
    <div class="card">
      <h3>II. Fiziksel RAM Belleği</h3>
      <div class="metric">{sys_info.get('ram', {}).get('used_gb', 0)} / {sys_info.get('ram', {}).get('total_gb', 0)} GB</div>
      <div class="sub">Kullanım Oranı: %{sys_info.get('ram', {}).get('usage_percent', 0)}</div>
    </div>
    <div class="card">
      <h3>III. NVIDIA RTX / CUDA</h3>
      <div class="metric">{sys_info.get('gpu', {}).get('name', 'CUDA Aktif')}</div>
      <div class="sub">Sıcaklık: {sys_info.get('gpu', {}).get('temp_c', 48)} &deg;C | VRAM: {sys_info.get('gpu', {}).get('vram_used_mb', 0)} MB</div>
    </div>
    <div class="card">
      <h3>IV. KAM Kod Külliyatı</h3>
      <div class="metric">{code_info.get('total_lines_of_code', 0):,} Satır</div>
      <div class="sub">{code_info.get('total_source_files', 0)} Kaynak Dosya | {code_info.get('python_classes', 0)} Sınıf | {code_info.get('python_functions', 0)} Fonksiyon</div>
    </div>
  </div>
  <script>
    setInterval(() => {{
      document.getElementById('clock').innerText = 'CANLI NÖBET // ' + new Date().toLocaleTimeString('tr-TR');
    }}, 1000);
  </script>
</body>
</html>"""
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html_doc)

        if launch and sys.platform == "win32":
            try:
                os.startfile(out_path)
            except Exception:
                pass

        return {
            "status": "success",
            "webapp_path": out_path,
            "launched": launch,
            "size_bytes": len(html_doc.encode("utf-8")),
        }

    def _tool_smart_workspace_search(self, args: Dict[str, Any]) -> Dict[str, Any]:
        query = str(args.get("query", "")).strip()
        if not query:
            return {"status": "error", "error": "Arama sorgusu (query) boş olamaz."}

        root_dir = self._resolve_path(args.get("path", self.workspace_root))
        if not os.path.exists(root_dir):
            return {"status": "error", "error": f"Arama dizini bulunamadı: {root_dir}"}

        raw_pattern = str(args.get("file_pattern", "*")).strip() or "*"
        patterns = [p.strip() for p in raw_pattern.split(",") if p.strip()] or ["*"]
        case_sensitive = bool(args.get("case_sensitive", False))
        try:
            max_results = max(1, min(200, int(args.get("max_results", 40))))
        except (TypeError, ValueError):
            max_results = 40
        try:
            context_lines = max(0, min(3, int(args.get("context_lines", 0))))
        except (TypeError, ValueError):
            context_lines = 0

        flags = 0 if case_sensitive else re.IGNORECASE
        try:
            pattern_re = re.compile(query, flags)
        except re.error:
            pattern_re = re.compile(re.escape(query), flags)

        skip_dirs = {
            ".git", "__pycache__", ".pytest_cache", "node_modules", "weights",
            "build", "dist", ".venv", "venv", ".mypy_cache", ".ruff_cache",
        }
        binary_exts = {
            ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".webp",
            ".exe", ".dll", ".pyd", ".so", ".dylib", ".bin", ".gguf",
            ".pt", ".pth", ".onnx", ".zip", ".tar", ".gz", ".7z",
            ".pdf", ".mp3", ".mp4", ".wav", ".avi", ".woff", ".woff2", ".ttf",
        }
        max_file_bytes = 2 * 1024 * 1024

        matches: List[Dict[str, Any]] = []
        files_scanned = 0
        truncated = False

        def _matches_pattern(fname: str) -> bool:
            if "*" in patterns:
                return True
            p_obj = Path(fname)
            return any(p_obj.match(pat) for pat in patterns)

        def _scan_one(fpath: str) -> bool:
            nonlocal files_scanned, truncated
            ext = os.path.splitext(fpath)[1].lower()
            if ext in binary_exts:
                return False
            try:
                if os.path.getsize(fpath) > max_file_bytes:
                    return False
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
            except Exception:
                return False

            files_scanned += 1
            rel = _safe_relpath(fpath, self.workspace_root).replace("\\", "/")
            for idx, line in enumerate(lines):
                if pattern_re.search(line):
                    lineno = idx + 1
                    item: Dict[str, Any] = {
                        "location": f"{rel}:{lineno}",
                        "file": rel,
                        "line": lineno,
                        "snippet": line.strip()[:200],
                    }
                    if context_lines > 0:
                        c_start = max(0, idx - context_lines)
                        c_end = min(len(lines), idx + context_lines + 1)
                        item["context"] = [
                            f"{c_i + 1}: {lines[c_i].rstrip()[:180]}"
                            for c_i in range(c_start, c_end)
                        ]
                    matches.append(item)
                    if len(matches) >= max_results:
                        truncated = True
                        return True
            return False

        if os.path.isfile(root_dir):
            _scan_one(root_dir)
        else:
            for dirpath, dirnames, filenames in os.walk(root_dir):
                dirnames[:] = sorted(d for d in dirnames if d not in skip_dirs)
                for fname in sorted(filenames):
                    if not _matches_pattern(fname):
                        continue
                    if _scan_one(os.path.join(dirpath, fname)):
                        break
                if truncated:
                    break

        return {
            "status": "success",
            "query": query,
            "root": root_dir,
            "files_scanned": files_scanned,
            "total_matches": len(matches),
            "truncated": truncated,
            "matches": matches,
        }

    def _tool_clipboard_manager(self, args: Dict[str, Any]) -> Dict[str, Any]:
        action = str(args.get("action", "get")).lower().strip()
        text = args.get("text")
        if text is None:
            text = args.get("value", "")
        text = str(text)

        if sys.platform != "win32":
            return {"status": "unsupported_platform", "action": action}

        if action == "get":
            ps_cmd = _ps_build_command(
                "$v = Get-Clipboard -Raw; if ($null -ne $v) { [Console]::Out.Write($v) }"
            )
            try:
                proc = subprocess.run(
                    ps_cmd,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=5.0,
                    creationflags=_CREATE_NO_WINDOW,
                )
            except subprocess.TimeoutExpired:
                return {"status": "timeout", "action": "get", "error": "Pano okuma zaman aşımına uğradı."}
            if proc.returncode != 0:
                return {"status": "error", "action": "get", "error": (proc.stderr or "Pano okunamadı.").strip()}
            clip_val = proc.stdout or ""
            return {"status": "success", "action": "get", "text": clip_val, "length": len(clip_val)}

        elif action == "set":
            b64_utf8 = base64.b64encode(text.encode("utf-8")).decode("ascii")
            ps_script = (
                f"$bytes = [System.Convert]::FromBase64String('{b64_utf8}'); "
                "$txt = [System.Text.Encoding]::UTF8.GetString($bytes); "
                "Set-Clipboard -Value $txt"
            )
            try:
                proc = subprocess.run(
                    _ps_build_command(ps_script),
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=5.0,
                    creationflags=_CREATE_NO_WINDOW,
                )
            except subprocess.TimeoutExpired:
                return {"status": "timeout", "action": "set", "error": "Pano yazma zaman aşımına uğradı."}
            if proc.returncode != 0:
                return {"status": "error", "action": "set", "error": (proc.stderr or "Pano yazılamadı.").strip()}
            return {"status": "success", "action": "set", "length": len(text), "preview": text[:120]}

        elif action == "clear":
            try:
                proc = subprocess.run(
                    _ps_build_command("Set-Clipboard -Value $null"),
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=5.0,
                    creationflags=_CREATE_NO_WINDOW,
                )
            except subprocess.TimeoutExpired:
                return {"status": "timeout", "action": "clear", "error": "Pano temizleme zaman aşımına uğradı."}
            if proc.returncode != 0:
                return {"status": "error", "action": "clear", "error": (proc.stderr or "Pano temizlenemedi.").strip()}
            return {"status": "success", "action": "clear"}

        return {"status": "error", "error": f"Bilinmeyen pano eylemi: {action} ('get', 'set' veya 'clear' kullanın)."}

    def _tool_system_notification(self, args: Dict[str, Any]) -> Dict[str, Any]:
        title = str(args.get("title", "KAM // Otonom Ajan")).strip() or "KAM // Otonom Ajan"
        message = str(args.get("message") or args.get("body") or args.get("text") or "").strip()
        if not message:
            return {"status": "error", "error": "Bildirim metni (message) boş olamaz."}

        level = str(args.get("level", "info")).lower().strip()
        icon_map = {"info": "Info", "warning": "Warning", "warn": "Warning", "error": "Error"}
        balloon_icon = icon_map.get(level, "Info")
        try:
            duration_ms = max(1000, min(15000, int(args.get("duration_ms", 4000))))
        except (TypeError, ValueError):
            duration_ms = 4000

        if sys.platform != "win32":
            return {"status": "unsupported_platform", "title": title, "message": message, "level": level}

        title_b64 = base64.b64encode(title[:128].encode("utf-8")).decode("ascii")
        msg_b64 = base64.b64encode(message[:500].encode("utf-8")).decode("ascii")
        ps_notify = (
            "Add-Type -AssemblyName System.Windows.Forms,System.Drawing; "
            "$n = New-Object System.Windows.Forms.NotifyIcon; "
            "try { "
            "$n.Icon = [System.Drawing.SystemIcons]::Information; "
            f"$n.BalloonTipIcon = [System.Windows.Forms.ToolTipIcon]::{balloon_icon}; "
            f"$n.BalloonTipTitle = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String('{title_b64}')); "
            f"$n.BalloonTipText = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String('{msg_b64}')); "
            "$n.Visible = $true; "
            f"$n.ShowBalloonTip({duration_ms}); "
            f"Start-Sleep -Milliseconds {min(duration_ms + 500, 6000)}; "
            "} finally { $n.Visible = $false; $n.Dispose() }"
        )
        subprocess.Popen(
            _ps_build_command(ps_notify),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=_CREATE_NO_WINDOW,
        )
        return {
            "status": "success",
            "title": title,
            "message": message,
            "level": level,
            "duration_ms": duration_ms,
            "non_blocking": True,
            "engine": "Windows-NotifyIcon-Balloon",
        }

    # ------------------------------------------------------------------
    # 3. MANUS-AI TARZI PLANLAYICI + ÇOK ADIMLI OTONOM İCRA MOTORU (STAGE 1)
    # ------------------------------------------------------------------
    def detect_and_execute_direct_intent(self, prompt: str) -> List[Dict[str, Any]]:
        """
        Kullanıcının Türkçe emrini (tekil veya çok adımlı zincirleme görev) analiz eder,
        Manus-AI tarzı görev adımlarına (Mission Plan DAG) ayırır ve sırasıyla bilgisayarda
        gerçek zamanlı icra ederek doğrulanmış sonuçlarını döndürür.
        """
        p_raw = prompt.strip()
        p_low = p_raw.lower()
        executed: List[Dict[str, Any]] = []

        def _add_step(step_title: str, tool_name: str, tool_args: Dict[str, Any]) -> Dict[str, Any]:
            res = self.execute_tool(tool_name, tool_args)
            step_record = {
                "step_index": len(executed) + 1,
                "step_title": step_title,
                "tool": tool_name,
                "args": tool_args,
                "result": res,
            }
            executed.append(step_record)
            return res

        # 1. Açık Slash Komutları (/run, /shell, /cmd, /python, /codeact)
        if p_low.startswith(("/run ", "/shell ", "/cmd ", "/komut ")):
            cmd_str = p_raw.split(" ", 1)[1].strip()
            _add_step(f"Kabuk Komutu İcrası: {cmd_str}", "run_shell_command", {"command": cmd_str})
            return executed

        if p_low.startswith(("/py ", "/python ", "/codeact ")):
            code_str = p_raw.split(" ", 1)[1].strip()
            _add_step("Stateful CodeAct Python İcrası", "execute_python_code", {"code": code_str})
            return executed

        # 2. Doğal Dilde Kabuk Komutu Çalıştırma
        cmd_match = re.search(
            r"(?:komutu(?:nu)?\s+çalıştır|komut\s+koş|terminalde\s+çalıştır|powershell(?:'de|de)?\s+çalıştır)\s*[:\-]?\s*[`'\"]?([^`'\"]+)[`'\"]?",
            p_raw,
            re.IGNORECASE,
        )
        if not cmd_match:
            cmd_match = re.search(r"[`'\"]([^`'\"]{2,120})[`'\"]\s+komutunu\s+(?:çalıştır|koş|icra\s+et)", p_raw, re.IGNORECASE)
        if cmd_match:
            cmd_str = cmd_match.group(1).strip()
            _add_step(f"Kabuk Komutu İcrası: {cmd_str}", "run_shell_command", {"command": cmd_str})
            return executed

        # 3. Çok Adımlı Uygulama Aç + İçine Metin/Rapor Yaz (Örn: "Not defterini aç ve içine '...' yaz")
        notepad_write_match = re.search(
            r"(?:not\s+defterini|notepad(?:'i|i)?)\s+aç.*?(?:içine|ve)\s+['\"]([^'\"]+)['\"]\s+yaz",
            p_raw,
            re.IGNORECASE,
        )
        if notepad_write_match:
            text_to_type = notepad_write_match.group(1)
            _add_step("Not Defteri (notepad.exe) Başlatılıyor", "launch_application", {"target": "notepad.exe"})
            time.sleep(0.6)
            _add_step("Not Defteri Penceresi Odaklanıyor", "desktop_window_manager", {"action": "focus_window", "value": "notepad"})
            _add_step("Aktif Pencereye Metin Enjekte Ediliyor", "keyboard_control", {"action": "type", "text": text_to_type, "press_enter": True})
            return executed

        # 4. Dosya Oluşturma / Yazma
        write_match = re.search(
            r"([a-zA-Z0-9_\-\./\\]+\.[a-zA-Z0-9]{1,8})\s+(?:adında\s+|isminde\s+)?(?:bir\s+)?(?:dosya|dosyası|dosyasını)\s+(?:oluştur|yaz|kaydet).*?(?:içine|içeriğine|olarak)\s+['\"]([^'\"]+)['\"]",
            p_raw,
            re.IGNORECASE,
        )
        if not write_match:
            write_match = re.search(
                r"([a-zA-Z0-9_\-\./\\]+\.[a-zA-Z0-9]{1,8})\s+(?:dosyasına|dosyasının\s+içine)\s+['\"]([^'\"]+)['\"]\s+(?:yaz|ekle|kaydet)",
                p_raw,
                re.IGNORECASE,
            )
        if write_match:
            fpath = write_match.group(1).strip()
            if "masaüstü" in p_low or "masaustu" in p_low:
                fpath = os.path.join(os.path.expanduser("~"), "Desktop", os.path.basename(fpath))
            content = write_match.group(2)
            _add_step(f"Dosya Yazılıyor: {fpath}", "write_file", {"path": fpath, "content": content})

        # 5. Dosya Okuma
        read_match = re.search(
            r"([a-zA-Z0-9_\-\./\\]+\.[a-zA-Z0-9]{1,8})\s+(?:dosyasını|dosyasının\s+içeriğini)\s+(?:oku|göster|incele|aç)",
            p_raw,
            re.IGNORECASE,
        )
        if read_match:
            fpath = read_match.group(1).strip()
            _add_step(f"Dosya Okunuyor: {fpath}", "read_file", {"path": fpath})

        # 6. Dizin / Klasör Listeleme
        if any(k in p_low for k in ("dosyaları listele", "klasörü listele", "dizini listele", "dosyaları göster", "klasör içeriği", "masaustundeki dosya", "masaüstündeki dosya", "indirilenleri listele")):
            if "masaüstü" in p_low or "masaustu" in p_low:
                target_dir = "desktop"
            elif "indirilen" in p_low:
                target_dir = "downloads"
            else:
                target_dir = self.workspace_root
            _add_step(f"Dizin Taranıyor: {target_dir}", "list_directory", {"path": target_dir})

        # 7. Gerçek Bilgisayar / Donanım / Sistem Durumu (+ Rapor Dosyası Kaydı İstenmişse Zincirleme Kaydet!)
        if any(
            k in p_low
            for k in (
                "bilgisayarın durumu",
                "bilgisayarın gerçek",
                "sistem durumu",
                "donanım durumu",
                "donanım denetimi",
                "ram kullanım",
                "bellek kullanım",
                "disk kullanım",
                "gpu durum",
                "ekran kartı",
                "işlemci durum",
                "cpu durum",
                "sistem özellik",
                "bilgisayar özellik",
                "tam sistem raporu",
            )
        ):
            sys_res = _add_step("Gerçek Zamanlı Bilgisayar, RAM, Disk ve GPU Telemetrisi Okunuyor", "get_real_system_telemetry", {})
            if any(k in p_low for k in ("kaydet", "rapor oluştur", "dosyaya yaz")):
                rep_file = re.search(r"([a-zA-Z0-9_\-]+\.(?:md|txt|json|html))", p_raw, re.IGNORECASE)
                fname = rep_file.group(1) if rep_file else "kam_sistem_raporu.md"
                dest = os.path.join(os.path.expanduser("~"), "Desktop", fname) if ("masaüstü" in p_low or "masaustu" in p_low) else fname
                report_md = (
                    f"# KAM // OTONOM BİLGİSAYAR VE DONANIM DENETİM RAPORU\n"
                    f"- **Tarih / Saat:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"- **Bilgisayar (Host):** `{sys_res.get('hostname')}` ({sys_res.get('os_platform')})\n"
                    f"- **İşlemci:** `{sys_res.get('processor')}` ({sys_res.get('cpu_logical_cores')} mantıksal çekirdek)\n"
                    f"- **Fiziksel RAM:** `{sys_res.get('ram', {}).get('used_gb')} GB / {sys_res.get('ram', {}).get('total_gb')} GB` (%{sys_res.get('ram', {}).get('usage_percent')})\n"
                    f"- **Disk:** `{sys_res.get('disk', {}).get('used_gb')} GB / {sys_res.get('disk', {}).get('total_gb')} GB` (%{sys_res.get('disk', {}).get('usage_percent')})\n"
                    f"- **NVIDIA GPU:** `{json.dumps(sys_res.get('gpu', {}), ensure_ascii=False)}`\n"
                )
                _add_step(f"Sistem Denetim Raporu Diske Kaydediliyor: {dest}", "write_file", {"path": dest, "content": report_md})

        # 8. Fare (Mouse) Hükümranlığı ("fareyi (500, 400) konumuna taşı", "fare konumunu göster", "(300, 200) noktasına tıkla")
        mouse_move_m = re.search(r"(?:fareyi|imleci|mouse'u)\s*\(?\s*(\d{1,4})\s*[,x\s]\s*(\d{1,4})\s*\)?\s*(?:konumuna|noktasına)?\s*(?:taşı|götür)", p_raw, re.IGNORECASE)
        if mouse_move_m:
            mx, my = int(mouse_move_m.group(1)), int(mouse_move_m.group(2))
            _add_step(f"Fare İmleci ({mx}, {my}) Koordinatına Taşınıyor", "mouse_control", {"action": "move", "x": mx, "y": my})

        mouse_click_m = re.search(r"\(?\s*(\d{1,4})\s*[,x\s]\s*(\d{1,4})\s*\)?\s*(?:konumuna|noktasına|koordinatına)\s*(?:çift\s+tıkla|sağ\s+tıkla|tıkla)", p_raw, re.IGNORECASE)
        if mouse_click_m:
            mx, my = int(mouse_click_m.group(1)), int(mouse_click_m.group(2))
            act = "double_click" if "çift" in p_low else ("right_click" if "sağ" in p_low else "click")
            _add_step(f"Fare ({mx}, {my}) Koordinatına Tıklıyor ({act})", "mouse_control", {"action": act, "x": mx, "y": my})

        if any(k in p_low for k in ("fare konumu", "imleç konumu", "mouse konumu", "ekran çözünürlüğü")):
            _add_step("Ekran Çözünürlüğü ve Fare Koordinatı Okunuyor", "mouse_control", {"action": "position"})

        # 9. Klavye ve Kısayol Hükümranlığı ("klavyeyle '...' yaz", "'ctrl+s' tuşlarına bas")
        kb_type_m = re.search(r"(?:klavyeyle|aktif\s+pencereye|ekrana)\s+['\"]([^'\"]+)['\"]\s+yaz", p_raw, re.IGNORECASE)
        if kb_type_m:
            _add_step("Aktif Pencereye Klavye Metni Yazılıyor", "keyboard_control", {"action": "type", "text": kb_type_m.group(1), "press_enter": "enter" in p_low})

        hotkey_m = re.search(r"['\"]((?:ctrl|alt|shift|win)\+[a-z0-9\+]+)['\"]\s+(?:kısayoluna|tuşlarına|tuşuna)\s+bas", p_raw, re.IGNORECASE)
        if hotkey_m:
            _add_step(f"Klavye Kısayolu İcra Ediliyor: {hotkey_m.group(1)}", "keyboard_control", {"action": "hotkey", "keys": hotkey_m.group(1)})

        # 10. Donanım Ses, Batarya, Servisler ve Kurulu Uygulamalar
        if any(k in p_low for k in ("sesi aç", "sesi artır", "ses seviyesini artır", "sesi yükselt")):
            _add_step("Sistem Ses Seviyesi Artırılıyor", "os_hardware_control", {"action": "volume_up", "steps": 5})
        elif any(k in p_low for k in ("sesi kıs", "sesi azalt", "ses seviyesini azalt", "sesi düşür")):
            _add_step("Sistem Ses Seviyesi Kısılıyor", "os_hardware_control", {"action": "volume_down", "steps": 5})
        elif any(k in p_low for k in ("sesi kapat", "sessize al", "mute")):
            _add_step("Sistem Sesi Sessize (Mute) Alınıyor", "os_hardware_control", {"action": "volume_mute"})

        if any(k in p_low for k in ("batarya durumu", "pil durumu", "şarj durumu", "güç durumu")):
            _add_step("Batarya ve Güç Durumu Okunuyor", "os_hardware_control", {"action": "battery"})

        if any(k in p_low for k in ("kurulu programlar", "yüklü uygulamalar", "kurulu yazılımlar")):
            _add_step("Bilgisayarda Kurulu Uygulamalar Taranıyor", "os_hardware_control", {"action": "installed_apps"})

        if any(k in p_low for k in ("çalışan servisler", "windows servisleri")):
            _add_step("Aktif Windows Servisleri Denetleniyor", "os_hardware_control", {"action": "services"})

        # 11. Açık Pencereler / Pencere Yönetimi / Ekran Görüntüsü / Pano
        if any(k in p_low for k in ("açık pencereleri", "pencereleri listele", "masaüstündeki pencereler", "hangi pencereler açık")):
            _add_step("Masaüstündeki Açık Pencereler ve Koordinatları Listeleniyor", "desktop_window_manager", {"action": "list_windows"})

        win_ctrl_m = re.search(
            r"['\"]([^'\"]+)['\"]\s+penceresini\s+(?:öne\s+getir|odakla|küçült|büyüt|tam\s+ekran\s+yap|kapat)",
            p_raw,
            re.IGNORECASE,
        )
        if win_ctrl_m:
            w_name = win_ctrl_m.group(1)
            if "küçült" in p_low:
                w_act = "minimize_window"
            elif "büyüt" in p_low or "tam ekran" in p_low:
                w_act = "maximize_window"
            elif "kapat" in p_low:
                w_act = "close_window"
            else:
                w_act = "focus_window"
            _add_step(f"Pencere Yönetimi ({w_act}): {w_name}", "desktop_window_manager", {"action": w_act, "value": w_name})

        if any(k in p_low for k in ("ekran görüntüsü", "screenshot", "ekranı yakala", "ekran fotoğrafı")):
            _add_step("Canlı Masaüstü Ekran Görüntüsü Yakalanıyor", "desktop_window_manager", {"action": "screenshot"})

        if any(k in p_low for k in ("panoyu oku", "clipboard oku", "kopyalanan metni göster", "panoda ne var")):
            _add_step("Sistem Panosu (Clipboard) Okunuyor", "desktop_window_manager", {"action": "get_clipboard"})

        clip_match = re.search(r"panoya\s+['\"]([^'\"]+)['\"]\s+(?:kopyala|yaz)", p_raw, re.IGNORECASE)
        if clip_match:
            val = clip_match.group(1)
            _add_step("Sistem Panosuna (Clipboard) Metin Kopyalanıyor", "desktop_window_manager", {"action": "set_clipboard", "value": val})

        # 12. Çalışan Süreçler / İşlemler ve Süreç Sonlandırma
        kill_m = re.search(r"['\"]?([a-zA-Z0-9_\-]+(?:\.exe)?)['\"]?\s+(?:sürecini|uygulamasını|programını)\s+(?:sonlandır|kapat|öldür|durdur)", p_raw, re.IGNORECASE)
        if kill_m:
            _add_step(f"Süreç Sonlandırılıyor: {kill_m.group(1)}", "manage_processes", {"action": "kill", "target": kill_m.group(1)})
        elif any(k in p_low for k in ("çalışan süreç", "çalışan işlem", "çalışan program", "çalışan uygulama", "aktif süreç", "görev listesi", "en çok ram")):
            _add_step("Çalışan Süreçler Bellek ve CPU Tüketimine Göre Taranıyor", "manage_processes", {"action": "list"})

        # 13. Uygulama Başlatma
        for app_phrase, app_bin in (
            ("hesap makinesini aç", "calc.exe"),
            ("hesap makinesi aç", "calc.exe"),
            ("not defterini aç", "notepad.exe"),
            ("not defteri aç", "notepad.exe"),
            ("notepad aç", "notepad.exe"),
            ("dosya gezginini aç", "explorer.exe"),
            ("klasörü aç", self.workspace_root),
            ("görev yöneticisini aç", "taskmgr.exe"),
            ("denetim masasını aç", "control.exe"),
            ("ayarları aç", "ms-settings:"),
            ("paint aç", "mspaint.exe"),
        ):
            if app_phrase in p_low:
                _add_step(f"Uygulama Başlatılıyor: {app_bin}", "launch_application", {"target": app_bin})
                break

        # 14. Web Araştırması ve Sayfa Okuma ("web'de '...' araştır", "internette '...' ara", "https://... sayfasını oku")
        web_search_m = re.search(r"(?:web'de|webde|internette)\s+['\"]([^'\"]+)['\"]\s+(?:araştır|ara|bul)", p_raw, re.IGNORECASE)
        if web_search_m:
            _add_step(f"Açık Web Araştırması: {web_search_m.group(1)}", "web_research", {"action": "search", "query": web_search_m.group(1)})

        url_fetch_m = re.search(r"(https?://[^\s'\"<>]+)\s+(?:sayfasını|içeriğini|adresini)\s+(?:oku|getir|çek|analiz\s+et)", p_raw, re.IGNORECASE)
        if url_fetch_m:
            _add_step(f"Web Sayfası İçeriği Okunuyor: {url_fetch_m.group(1)}", "web_research", {"action": "fetch", "url": url_fetch_m.group(1)})
        else:
            url_open_m = re.search(r"(https?://[^\s'\"<>]+)\s+(?:adresini\s+|sitesini\s+)?aç", p_raw, re.IGNORECASE)
            if url_open_m:
                _add_step(f"Web Adresi Tarayıcıda Açılıyor: {url_open_m.group(1)}", "launch_application", {"target": url_open_m.group(1)})

        # 15. Ağ ve Port Denetimi
        if any(k in p_low for k in ("açık portlar", "ağ durumu", "ip adresim", "dinlenen portlar", "netstat")):
            _add_step("Ağ Bağlantıları ve Dinlenen TCP Portları Denetleniyor", "network_probe", {"action": "status"})

        # 16. Dosyalarda / Kodlarda Arama
        search_match = re.search(
            r"(?:dosyalarda|kodlarda|repoda|projede)\s+['\"]([^'\"]+)['\"]\s+(?:ara|bul|tara)",
            p_raw,
            re.IGNORECASE,
        )
        if search_match:
            q = search_match.group(1).strip()
            _add_step(f"Kaynak Kodlarda Arama: '{q}'", "search_in_files", {"query": q})

        # 17. Tüm Disk Sürücüleri (C:, D:, G:), Büyük Dosyalar, Wi-Fi, Başlangıç ve İzin Denetimi
        if any(k in p_low for k in ("tüm disk", "disk sürücü", "hangi diskler", "sürücüleri listele", "c: ve", "boş alan")):
            _add_step("Bilgisayardaki Tüm Disk Sürücüleri ve Doluluk Oranları Taranıyor", "os_hardware_control", {"action": "drives"})

        if any(k in p_low for k in ("en büyük dosya", "en çok yer kaplayan", "büyük dosyaları bul")):
            t_dir = "desktop" if ("masaüstü" in p_low or "masaustu" in p_low) else self.workspace_root
            _add_step(f"En Büyük Dosyalar Analiz Ediliyor ({t_dir})", "os_hardware_control", {"action": "large_files", "path": t_dir})

        if any(k in p_low for k in ("wifi", "wi-fi", "kablosuz ağ", "bağlı olduğum ağ", "sinyal gücü")):
            _add_step("Kablosuz Ağ (Wi-Fi) Arayüzü ve Sinyal Gücü Okunuyor", "os_hardware_control", {"action": "wifi"})

        if any(k in p_low for k in ("başlangıç program", "startup", "açılışta çalışan")):
            _add_step("Windows Başlangıç (Startup) Uygulamaları Denetleniyor", "os_hardware_control", {"action": "startup"})

        if any(k in p_low for k in ("izin durumu", "yetki durumu", "tüm izinler", "yetkilerin neler")):
            _add_step("Egemen Ajan Tam Yetki ve İzin Matrisi Doğrulanıyor", "os_hardware_control", {"action": "permissions"})

        # 18. Kalıcı Epizodik Hafıza ("hafızana kaydet: ...", "unutma: ...", "hafızanda ne var")
        mem_save_m = re.search(r"(?:hafızana\s+kaydet|bunu\s+unutma|aklında\s+tut|not\s+al)\s*[:\-]?\s*(.+)", p_raw, re.IGNORECASE)
        if mem_save_m:
            note_txt = mem_save_m.group(1).strip()
            res_mem = self.remember_fact(note_txt)
            executed.append({
                "step_index": len(executed) + 1,
                "step_title": "Kalıcı Epizodik Hafızaya Kaydedildi",
                "tool": "episodic_memory_remember",
                "args": {"note": note_txt},
                "result": res_mem,
            })

        if any(k in p_low for k in ("hafızanda ne var", "neleri hatırlıyorsun", "kayıtlı notlar", "hafızanı göster")):
            res_rec = self.recall_memories()
            executed.append({
                "step_index": len(executed) + 1,
                "step_title": "Kalıcı Epizodik Hafıza Kayıtları Okunuyor",
                "tool": "episodic_memory_recall",
                "args": {},
                "result": res_rec,
            })

        # 19. Kod Külliyatı Analizi ("kaç satır kod", "projeyi analiz et", "kod istatistikleri")
        if any(k in p_low for k in ("kaç satır kod", "toplam satır", "kod analizi", "projeyi analiz et", "külliyat analizi", "kaç dosya var")):
            _add_step("KAM Kaynak Kod Külliyatı ve Mimari İstatistikleri Analiz Ediliyor", "analyze_codebase", {})

        # 20. Sesli Konuşma / TTS ("sesli söyle:", "sesli konuş:", "seslendir:")
        tts_m = re.search(r"(?:sesli\s+söyle|sesli\s+konuş|seslendir|sesli\s+oku)\s*[:\-]?\s*['\"]?([^'\"]+)['\"]?", p_raw, re.IGNORECASE)
        if tts_m:
            _add_step("Windows SAPI Ses Sentezleyici (TTS) Konuşuyor", "voice_tts", {"text": tts_m.group(1).strip()})

        # 21. Canlı İnteraktif Web Uygulaması / Kokpit İnşası ("kokpit uygulaması yap", "html dashboard oluştur ve aç")
        if any(k in p_low for k in ("html dashboard", "canlı kokpit", "web uygulaması yap", "gösterge paneli oluştur")):
            _add_step("Canlı İnteraktif HTML5 Siber Kokpit Üretiliyor ve Başlatılıyor", "build_interactive_webapp", {"launch": True})

        # 22. Klasör Oluşturma ve ZIP Arşivleme ("... adında klasör oluştur", "... klasörünü zip yap")
        mkdir_m = re.search(r"([a-zA-Z0-9_\-\./\\]+)\s+(?:adında\s+|isminde\s+)?(?:bir\s+)?klasör\s+(?:oluştur|aç)", p_raw, re.IGNORECASE)
        if mkdir_m:
            folder_name = mkdir_m.group(1).strip()
            if "masaüstü" in p_low or "masaustu" in p_low:
                folder_name = os.path.join(os.path.expanduser("~"), "Desktop", os.path.basename(folder_name))
            _add_step(f"Klasör Oluşturuluyor: {folder_name}", "file_power_ops", {"action": "mkdir", "source": folder_name})

        zip_m = re.search(r"([a-zA-Z0-9_\-\./\\]+)\s+(?:klasörünü|dosyasını)\s+(?:zip\s+yap|arşivle|sıkıştır)", p_raw, re.IGNORECASE)
        if zip_m:
            _add_step(f"ZIP Arşivi Oluşturuluyor: {zip_m.group(1)}", "file_power_ops", {"action": "zip", "source": zip_m.group(1).strip()})

        if len(executed) > 1:
            self.mission_plan_history.append({
                "timestamp": time.strftime("%H:%M:%S"),
                "objective": p_raw,
                "total_steps": len(executed),
                "steps": [
                    {"step": s["step_index"], "title": s["step_title"], "tool": s["tool"], "status": s["result"].get("status", "ok")}
                    for s in executed
                ],
            })

        return executed

    # ------------------------------------------------------------------
    # 4. LLM ÇIKTISINDAN <tool_call> VE <codeact> AYRIŞTIRICI (STAGE 2)
    # ------------------------------------------------------------------
    @staticmethod
    def is_actionable_computer_query(prompt: str) -> bool:
        """
        Kullanıcı isteminin bilgisayarda bir hesaplama, dosya/sistem işlemi,
        web araştırması, uygulama/pencere/fare/klavye otomasyonu veya inceleme
        gerektirip gerektirmediğini tespit eder (Türkçe + İngilizce).
        """
        p_low = str(prompt or "").lower().strip()
        if not p_low:
            return False
        if p_low.startswith(("/run", "/py", "/python", "/sh", "/shell", "/cmd", "/komut", "/codeact", "/agent")):
            return True
        action_keywords = (
            # Türkçe bilgisayar/ajan eylemleri
            "hesapla", "sayısını bul", "kaç tane", "kaç satır", "oluştur", "yap ve aç",
            "çalıştır", "listele", "tara", "kontrol et", "denetle", "analiz et",
            "klasör", "dosya", "masaüstü", "masaüstüne", "belgeler", "indirilenler",
            "sil", "kopyala", "taşı", "indir", "kur", "yükle", "kaldır", "düzenle",
            "değiştir", "güncelle", "kaydet", "yazdır", "oku", "aç", "kapat", "sonlandır",
            "python", "powershell", "cmd", "terminal", "kod çalıştır", "script", "betik",
            "pencere", "ekran", "fare", "tıkla", "klavye", "ses", "sesi", "parlaklık",
            "batarya", "pil", "gpu", "vram", "ram", "cpu", "disk", "port", "ağ", "wifi",
            "wi-fi", "ip ", "süreç", "servis", "hizmet", "chrome", "edge", "tarayıcı",
            "youtube", "google", "spotify", "discord", "not defteri", "notepad", "vscode",
            "web'de ara", "internette ara", "araştır", "çek", "scrape", "git ", "test",
            "screenshot", "ekran görüntüsü", "sesli söyle", "oku bana", "hatırlat",
            "hazırla", "üret", "yap ", "yap.", "yap!", "getir", "göster", "bul ", "bul.",
            "panoyu", "pano", "zip", "arşivle", "sıkıştır",
            # İngilizce bilgisayar/ajan eylemleri
            "run ", "execute ", "list files", "show files", "read file", "write file",
            "create file", "edit file", "delete file", "search files", "find files",
            "open ", "launch ", "close window", "kill process", "check system",
            "system info", "system status", "battery", "volume", "mute", "clipboard",
            "window", "mouse", "click", "keyboard", "download", "analyze codebase",
            "lines of code", "folder", "directory", "desktop", "downloads",
            "processes", "network", "ping ", "web search", "browser", "calculator",
            "speak", "tts", "dashboard", "webapp", "unzip",
        )
        return any(v in p_low for v in action_keywords)

    @staticmethod
    def _parse_tool_json(raw_block: str) -> Optional[Dict[str, Any]]:
        """
        <tool_call> içindeki JSON gövdesini küçük LLM biçimlendirme kusurlarına
        (iç markdown çitleri, sondaki virgüller, ham satır sonları, çevre metin,
        string olarak serileştirilmiş arguments) karşı dayanıklı biçimde ayrıştırır.
        """
        body = _strip_code_fences(raw_block).strip()
        if not body:
            return None

        candidates = [body]
        # Çevre metin varsa ilk dengeli {...} nesnesini çıkar
        first_brace = body.find("{")
        if first_brace != -1:
            depth = 0
            in_str = False
            esc = False
            for idx in range(first_brace, len(body)):
                ch = body[idx]
                if esc:
                    esc = False
                    continue
                if ch == "\\" and in_str:
                    esc = True
                    continue
                if ch == '"':
                    in_str = not in_str
                elif not in_str:
                    if ch == "{":
                        depth += 1
                    elif ch == "}":
                        depth -= 1
                        if depth == 0:
                            balanced = body[first_brace : idx + 1]
                            if balanced != body:
                                candidates.append(balanced)
                            break

        for cand in candidates:
            attempts = [
                cand,
                # Sondaki fazla virgülleri temizle: {"a": 1,} -> {"a": 1}
                re.sub(r",\s*([}\]])", r"\1", cand),
            ]
            # String içindeki kaçırılmamış yeni satırları \n yap (strict=False de yardımcı olur)
            for txt in attempts:
                for strict_flag in (True, False):
                    try:
                        parsed = json.loads(txt, strict=strict_flag)
                        if isinstance(parsed, dict) and "name" in parsed:
                            args_val = parsed.get("arguments", parsed.get("args", {}))
                            if isinstance(args_val, str):
                                try:
                                    args_val = json.loads(args_val)
                                except Exception:
                                    args_val = {"raw": args_val}
                            if not isinstance(args_val, dict):
                                args_val = {}
                            return {
                                "name": str(parsed["name"]).strip(),
                                "arguments": args_val,
                            }
                    except Exception:
                        continue
        return None

    @staticmethod
    def extract_tool_calls(llm_text: str, include_fenced_code: bool = False) -> List[Dict[str, Any]]:
        """
        Model yanıtı içindeki <tool_call>{"name": "...", "arguments": {...}}</tool_call>,
        ```tool_call ... ``` veya <codeact>...</codeact> bloklarını belge sırasını koruyarak ayrıştırır.
        Eğer include_fenced_code=True ise ```python / ```py / ```powershell / ```bash
        bloklarını da doğrudan çalıştırılabilir CodeAct / kabuk çağrısına dönüştürür.
        """
        if not llm_text:
            return []

        # Kapalı <think>...</think> iç muhakeme bloklarını temizle (hayalet araç çağrılarını önler)
        cleaned_text = re.sub(r"<think\b[^>]*>.*?</think>", "", str(llm_text), flags=re.IGNORECASE | re.DOTALL)

        found: List[Tuple[int, Dict[str, Any]]] = []
        occupied_spans: List[Tuple[int, int]] = []

        def _overlaps(start: int, end: int) -> bool:
            return any(not (end <= s or start >= e) for s, e in occupied_spans)

        # 1. <tool_call ...>...</tool_call> ve ```tool_call / ```tool
        tool_patterns = (
            r"<tool_call\b[^>]*>(.*?)</tool_call>",
            r"```(?:tool_call|tool)\s*(.*?)```",
        )
        for pat in tool_patterns:
            for match in re.finditer(pat, cleaned_text, re.IGNORECASE | re.DOTALL):
                s, e = match.span()
                if _overlaps(s, e):
                    continue
                parsed = KamAutonomousAgent._parse_tool_json(match.group(1))
                if parsed:
                    occupied_spans.append((s, e))
                    found.append((s, parsed))

        # 2. <codeact ...>...</codeact> ve ```codeact ... ```
        codeact_patterns = (
            r"<codeact\b[^>]*>(.*?)</codeact>",
            r"```codeact\s*(.*?)```",
        )
        for cpat in codeact_patterns:
            for match in re.finditer(cpat, cleaned_text, re.IGNORECASE | re.DOTALL):
                s, e = match.span()
                if _overlaps(s, e):
                    continue
                code_body = _strip_code_fences(match.group(1))
                if code_body:
                    occupied_spans.append((s, e))
                    found.append((
                        s,
                        {"name": "execute_python_code", "arguments": {"code": code_body}},
                    ))

        # 2b. Kesilmiş/kapatılmamış son <codeact> bloğu kurtarma
        if not found:
            unclosed_ca = re.search(r"<codeact\b[^>]*>(.+)$", cleaned_text, re.IGNORECASE | re.DOTALL)
            if unclosed_ca:
                code_body = _strip_code_fences(unclosed_ca.group(1))
                if code_body:
                    found.append((
                        unclosed_ca.start(),
                        {"name": "execute_python_code", "arguments": {"code": code_body}},
                    ))

        # 3. İsteğe bağlı düz çitli kod blokları (```python, ```py, ```powershell, ```bash)
        if include_fenced_code and not found:
            for match in re.finditer(r"```(?:python3?|py)\s*\n?(.*?)```", cleaned_text, re.IGNORECASE | re.DOTALL):
                s, e = match.span()
                if _overlaps(s, e):
                    continue
                py_body = match.group(1).strip()
                if py_body:
                    occupied_spans.append((s, e))
                    found.append((s, {"name": "execute_python_code", "arguments": {"code": py_body}}))
            for match in re.finditer(r"```(?:powershell|ps1|bash|sh)\s*\n?(.*?)```", cleaned_text, re.IGNORECASE | re.DOTALL):
                s, e = match.span()
                if _overlaps(s, e):
                    continue
                sh_body = match.group(1).strip()
                if sh_body:
                    occupied_spans.append((s, e))
                    found.append((s, {"name": "run_shell_command", "arguments": {"command": sh_body}}))

        found.sort(key=lambda item: item[0])
        return [item[1] for item in found]

    @staticmethod
    def format_mission_plan_card(executed_steps: List[Dict[str, Any]]) -> str:
        """
        Manus-AI tarzı çok adımlı görev planı (Mission Checklist) özet kartı üretir.
        """
        if len(executed_steps) <= 1:
            return ""
        lines = [f"🧭 [MANUS-SINIFI OTONOM GÖREV PLANI // {len(executed_steps)} ADIMLI ZİNCİRLEME İCRA]"]
        for s in executed_steps:
            st = s["result"].get("status", "ok").upper()
            icon = "✓" if st in ("SUCCESS", "OK", "DEPLOYED") else "!"
            dur = s["result"].get("execution_time_ms", 0.0)
            lines.append(f"  [{icon}] Adım {s['step_index']}/{len(executed_steps)}: {s['step_title']} ({s['tool']} — {dur} ms)")
        return "\n".join(lines) + "\n"

    @staticmethod
    def format_execution_badge(tool_name: str, args: Dict[str, Any], result: Dict[str, Any], step_title: str = "") -> str:
        """
        İcra edilen aracın kanıtlı sonucunu hem masaüstü hem terminalde okunaklı
        ve vakur bir komuta raporu bloğu olarak biçimlendirir.
        """
        status = result.get("status", "ok").upper()
        dur = result.get("execution_time_ms", 0.0)
        compact_res = json.dumps(result, ensure_ascii=False, indent=2)
        if len(compact_res) > 1800:
            compact_res = compact_res[:1800] + "\n  ... [ÇIKTI ÖZETLENDİ]"
        header_extra = f" — {step_title}" if step_title else ""
        return (
            f"⚡ [OTONOM AJAN İCRASI // {tool_name.upper()}{header_extra} | DURUM: {status} | {dur} ms]\n"
            f"{compact_res}\n"
        )

    @classmethod
    def get_agent_tool_instructions(cls) -> str:
        return """
MANUS-SINIFI OTONOM BİLGİSAYAR HÜKÜMRANLIĞI VE CODEACT PROTOKOLÜ:
Sen yalnızca konuşan bir dil modeli değil; üzerinde çalıştığın bilgisayara sonuna kadar hükmeden Manus-AI ve Microsoft UFO² sınıfı tam yetkili Otonom Bilgisayar Ajanısın.
Kullanıcı senden bilgisayarda tekil veya çok adımlı bir görev istediğinde iki güçlü icra yöntemine sahipsin:

1. **CodeAct (Durum-Korumalı Python & `host.*` Köprüsü):**
   Karmaşık otomasyon, veri analizi, dosya işleme veya zincirleme masaüstü görevleri için `<codeact>` bloğu içinde doğrudan Python kodu yazabilirsin. İçeride `host` nesnesi hazırdır (`host.shell(cmd)`, `host.sysinfo()`, `host.windows()`, `host.focus(title)`, `host.click(x, y)`, `host.move_mouse(x, y)`, `host.type_text(text, press_enter=True)`, `host.hotkey(keys)`, `host.open_app(target)`, `host.write_file(path, text)`, `host.read_file(path)`, `host.smart_search(query)`, `host.clipboard(text=None)`, `host.notify(message, title=...)`, `host.web_search(q)`, `host.fetch_url(url)`, `host.screenshot(path)`):
   <codeact>
   info = host.sysinfo()
   print("Aktif RAM Kullanımı:", info.get("ram"))
   </codeact>

2. **Doğrudan Yapılandırılmış Araç Çağrısı (`<tool_call>`):**
   <tool_call>{"name": "ARAÇ_ADI", "arguments": {"param1": "değer1"}}</tool_call>
   Araçlar: `run_shell_command`, `get_real_system_telemetry`, `list_directory`, `read_file`, `write_file`, `edit_file`, `search_in_files`, `smart_workspace_search`, `clipboard_manager`, `system_notification`, `execute_python_code`, `manage_processes`, `launch_application`, `desktop_window_manager`, `mouse_control`, `keyboard_control`, `os_hardware_control`, `web_research`, `network_probe`, `kam_defense_tool`.
"""
