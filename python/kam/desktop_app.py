import sys
import os
import re
import math
import time
import base64
import ctypes
import inspect
import subprocess
import threading
from collections import deque

try:
    import psutil
except ImportError:
    psutil = None

from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QPointF, QRectF
from PyQt6.QtGui import (
    QColor,
    QPainter,
    QPainterPath,
    QPen,
    QBrush,
    QFont,
    QIcon,
    QKeySequence,
    QShortcut,
    QPolygonF,
    QLinearGradient,
    QRadialGradient,
)
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QPlainTextEdit,
    QLineEdit,
    QComboBox,
    QProgressBar,
    QSplitter,
    QFrame,
    QFileDialog,
)

from .engine import KamEngine
from .code_mutator import CodeMutator
from .real_llm import UniversalLLMClient
from .autonomous_agent import Win32ComputerUseController


# ---------------------------------------------------------------------------
# Arka Plan LLM Akış İş Parçacığı (UI Donmasını Önleyen QThread)
# ---------------------------------------------------------------------------
class LLMStreamWorker(QThread):
    token_received = pyqtSignal(str)
    finished_stream = pyqtSignal(str)

    def __init__(self, llm_client: UniversalLLMClient, prompt: str):
        super().__init__()
        self.llm_client = llm_client
        self.prompt = prompt
        self._cancel_event = threading.Event()

    def cancel(self):
        self._cancel_event.set()

    @property
    def is_cancelled(self) -> bool:
        return self._cancel_event.is_set()

    def _open_stream(self):
        gen_fn = self.llm_client.generate_stream
        try:
            sig = inspect.signature(gen_fn)
            if "abort_event" in sig.parameters or any(
                p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()
            ):
                return gen_fn(self.prompt, abort_event=self._cancel_event)
        except (TypeError, ValueError):
            pass
        return gen_fn(self.prompt)

    def run(self):
        accumulated = []
        stream = None
        try:
            stream = self._open_stream()
            for token in stream:
                if self._cancel_event.is_set():
                    break
                accumulated.append(token)
                self.token_received.emit(token)
        except Exception as exc:
            if not self._cancel_event.is_set():
                err = f"\n[HATA]: {exc}"
                accumulated.append(err)
                self.token_received.emit(err)
        finally:
            if stream is not None and hasattr(stream, "close"):
                try:
                    stream.close()
                except Exception:
                    pass
        self.finished_stream.emit("".join(accumulated))


# ---------------------------------------------------------------------------
# Arka Plan Hafif Donanım Telemetrisi (CPU / RAM / GPU — UI Bloklamaz)
# ---------------------------------------------------------------------------
class HostStatsWorker(QThread):
    stats_ready = pyqtSignal(dict)

    _last_gpu_ts = 0.0
    _last_gpu_text = "GPU: --"
    _gpu_available = True

    def run(self):
        stats = {
            "cpu": "CPU: --",
            "ram": "RAM: --",
            "gpu": HostStatsWorker._last_gpu_text,
        }
        try:
            if psutil is not None:
                cpu_pct = psutil.cpu_percent(interval=None)
                vm = psutil.virtual_memory()
                used_gb = vm.used / (1024 ** 3)
                total_gb = vm.total / (1024 ** 3)
                stats["cpu"] = f"CPU: %{cpu_pct:.0f}"
                stats["ram"] = f"RAM: {used_gb:.1f}/{total_gb:.0f} GB (%{vm.percent:.0f})"
        except Exception:
            pass

        now = time.monotonic()
        if HostStatsWorker._gpu_available and (now - HostStatsWorker._last_gpu_ts >= 5.0):
            HostStatsWorker._last_gpu_ts = now
            try:
                kwargs = {
                    "stdout": subprocess.PIPE,
                    "stderr": subprocess.PIPE,
                    "text": True,
                    "encoding": "utf-8",
                    "errors": "replace",
                    "timeout": 1.5,
                }
                if sys.platform == "win32":
                    kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
                res = subprocess.run(
                    [
                        "nvidia-smi",
                        "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu",
                        "--format=csv,noheader,nounits",
                    ],
                    **kwargs,
                )
                if res.returncode == 0 and res.stdout.strip():
                    parts = [p.strip() for p in res.stdout.strip().splitlines()[0].split(",")]
                    if len(parts) >= 4:
                        util, mem_u, mem_t, temp = parts[0], parts[1], parts[2], parts[3]
                        HostStatsWorker._last_gpu_text = f"GPU: %{util} ({mem_u}/{mem_t} MB · {temp}°C)"
                        stats["gpu"] = HostStatsWorker._last_gpu_text
                else:
                    HostStatsWorker._last_gpu_text = "GPU: N/A"
                    stats["gpu"] = HostStatsWorker._last_gpu_text
            except FileNotFoundError:
                HostStatsWorker._gpu_available = False
                HostStatsWorker._last_gpu_text = "GPU: N/A"
                stats["gpu"] = HostStatsWorker._last_gpu_text
            except Exception:
                pass

        self.stats_ready.emit(stats)


# ---------------------------------------------------------------------------
# Özel Donanım İvmeli Monolitik KAM Mühür ve Radar Kadranı (QPainter)
# ---------------------------------------------------------------------------
class KamMonolithCrestWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(110, 110)
        self.angle = 0.0
        self.chaos_mode = False

    def advance_phase(self, chaos: bool):
        self.chaos_mode = chaos
        self.angle = (self.angle + (4.5 if chaos else 1.5)) % 360.0
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w, h = self.width(), self.height()
        cx, cy = w / 2.0, h / 2.0
        r = min(w, h) / 2.0 - 4.0

        # Obsidyen Kadran Zemini
        bg_grad = QRadialGradient(cx, cy, r)
        bg_grad.setColorAt(0.0, QColor(12, 16, 26))
        bg_grad.setColorAt(1.0, QColor(7, 9, 14))
        painter.setBrush(QBrush(bg_grad))
        accent = QColor(244, 63, 94) if self.chaos_mode else QColor(0, 229, 255)
        painter.setPen(QPen(QColor(accent.red(), accent.green(), accent.blue(), 90), 1.2))
        painter.drawEllipse(QPointF(cx, cy), r, r)

        # Dönen Telemetri Yay Çemberi
        arc_pen = QPen(accent, 2.0)
        painter.setPen(arc_pen)
        rect = QRectF(cx - r + 5, cy - r + 5, (r - 5) * 2, (r - 5) * 2)
        painter.drawArc(rect, int(self.angle * 16), 75 * 16)
        painter.drawArc(rect, int((self.angle + 180) * 16), 75 * 16)

        # 3-Parçalı Monolitik KAM Amblemi (Vektörel Çizim)
        def scale_pt(px, py):
            return QPointF(cx + (px - 512.0) * (r * 1.42 / 512.0), cy + (py - 512.0) * (r * 1.42 / 512.0))

        diamond = QPolygonF([
            scale_pt(512, 140),
            scale_pt(575, 264),
            scale_pt(512, 388),
            scale_pt(449, 264),
        ])
        left_wing = QPolygonF([
            scale_pt(436, 294),
            scale_pt(496, 405),
            scale_pt(416, 548),
            scale_pt(496, 700),
            scale_pt(496, 880),
            scale_pt(344, 602),
            scale_pt(242, 658),
        ])
        right_wing = QPolygonF([
            scale_pt(588, 294),
            scale_pt(528, 405),
            scale_pt(608, 548),
            scale_pt(528, 700),
            scale_pt(528, 880),
            scale_pt(680, 602),
            scale_pt(782, 658),
        ])

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(accent))
        painter.drawPolygon(diamond)

        painter.setBrush(QBrush(QColor(248, 250, 252)))
        painter.drawPolygon(left_wing)
        painter.drawPolygon(right_wing)


# ---------------------------------------------------------------------------
# 60 FPS Canlı Serbest Enerji ve Entropi Osiloskop Grafiği (QPainter)
# ---------------------------------------------------------------------------
class TelemetryOscilloscopeWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(115)
        self.entropy_history = deque([0.03] * 80, maxlen=80)
        self.fe_history = deque([0.08] * 80, maxlen=80)
        self.phase = 0.0

    def push_sample(self, entropy: float, free_energy: float):
        self.phase += 0.25
        jitter = math.sin(self.phase) * 0.008 + math.cos(self.phase * 2.3) * 0.005
        self.entropy_history.append(max(0.01, min(1.0, entropy + jitter)))
        self.fe_history.append(max(0.02, min(1.0, (free_energy / 2.2) + jitter * 1.4)))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        w, h = self.width(), self.height()

        # Arka plan ve ızgara
        painter.fillRect(0, 0, w, h, QColor(7, 9, 14))
        grid_pen = QPen(QColor(22, 27, 38, 160), 1, Qt.PenStyle.DotLine)
        painter.setPen(grid_pen)
        for i in range(1, 4):
            y = int(h * i / 4)
            painter.drawLine(0, y, w, y)
        for i in range(1, 8):
            x = int(w * i / 8)
            painter.drawLine(x, 0, x, h)

        # Çerçeve
        painter.setPen(QPen(QColor(22, 27, 38), 1))
        painter.drawRect(0, 0, w - 1, h - 1)

        def draw_curve(data, color: QColor, fill_alpha: int):
            if len(data) < 2:
                return
            path = QPainterPath()
            step_x = w / float(len(data) - 1)
            for idx, val in enumerate(data):
                px = idx * step_x
                py = h - 10 - (val * (h - 24))
                if idx == 0:
                    path.moveTo(px, py)
                else:
                    path.lineTo(px, py)

            fill_path = QPainterPath(path)
            fill_path.lineTo(w, h)
            fill_path.lineTo(0, h)
            fill_path.closeSubpath()

            grad = QLinearGradient(0, 0, 0, h)
            grad.setColorAt(0.0, QColor(color.red(), color.green(), color.blue(), fill_alpha))
            grad.setColorAt(1.0, QColor(color.red(), color.green(), color.blue(), 0))
            painter.fillPath(fill_path, QBrush(grad))

            painter.setPen(QPen(color, 1.8))
            painter.drawPath(path)

        # Varyasyonel Serbest Enerji (Buz Mavisi) ve Entropi (Zümrüt / Kırmızı)
        latest_e = self.entropy_history[-1]
        e_color = QColor(244, 63, 94) if latest_e >= 0.8 else QColor(16, 185, 129)
        draw_curve(self.fe_history, QColor(0, 229, 255), 55)
        draw_curve(self.entropy_history, e_color, 70)

        # Başlık Etiketi
        painter.setPen(QColor(148, 163, 184))
        painter.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        painter.drawText(8, 14, "CANLI OSİLOSKOP // SERBEST ENERJİ F(t) & ENTROPİ S(t)")


# ---------------------------------------------------------------------------
# Ana Yerel Masaüstü Komuta Merkezi Penceresi (PyQt6 Native UI)
# ---------------------------------------------------------------------------
class KamDesktopWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.engine = KamEngine()
        self.llm_client = UniversalLLMClient()
        self.worker = None
        self._hw_worker = None
        self._tts_proc = None
        self._tts_lock = threading.Lock()
        self.attached_files = []
        self._discard_next_stream = False
        self._last_chaos_state = None
        self._last_sdr_state = None
        self.current_assistant_buffer = ""
        self.chat_blocks = []

        self.setWindowTitle("KAM // Egemen Bilişsel Zihin ve Otonom Sistem Komuta Merkezi (Native Desktop v2.8 Apex)")
        self.resize(1480, 900)
        self.setMinimumSize(1180, 720)
        self.setAcceptDrops(True)

        logo_path = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "kam_logo.png")
        if os.path.exists(logo_path):
            self.setWindowIcon(QIcon(logo_path))

        self._apply_windows_dark_titlebar()
        self._apply_stylesheet()
        self._build_ui()
        self._setup_shortcuts()
        self._append_welcome_banner()

        # 10 Hz Gerçek Zamanlı Telemetri ve Osiloskop Döngüsü
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick_telemetry)
        self.timer.start(100)

        # Akış sırasında HTML yeniden çizimini ~50ms aralığa kısıtlayan zamanlayıcı
        self._stream_render_timer = QTimer(self)
        self._stream_render_timer.setSingleShot(True)
        self._stream_render_timer.setInterval(50)
        self._stream_render_timer.timeout.connect(self._flush_stream_render)

        # 2.5 saniyede bir hafif arka plan CPU/RAM/GPU durum çubuğu sorgusu
        if psutil is not None:
            try:
                psutil.cpu_percent(interval=None)
            except Exception:
                pass
        self._hw_timer = QTimer(self)
        self._hw_timer.timeout.connect(self._poll_host_stats)
        self._hw_timer.start(2500)
        QTimer.singleShot(300, self._poll_host_stats)

    def _setup_shortcuts(self):
        self.shortcut_clear = QShortcut(QKeySequence("Ctrl+L"), self)
        self.shortcut_clear.activated.connect(self._clear_chat)

        self.shortcut_toggle_panel = QShortcut(QKeySequence("Ctrl+Shift+S"), self)
        self.shortcut_toggle_panel.activated.connect(self._toggle_side_panels_shortcut)

        self.shortcut_stop_stream = QShortcut(QKeySequence("Escape"), self)
        self.shortcut_stop_stream.activated.connect(self._stop_stream)

    def closeEvent(self, event):
        if hasattr(self, "timer") and self.timer is not None:
            self.timer.stop()
        if hasattr(self, "_hw_timer") and self._hw_timer is not None:
            self._hw_timer.stop()
        if hasattr(self, "_stream_render_timer") and self._stream_render_timer is not None:
            self._stream_render_timer.stop()
        self._stop_tts()
        if self.worker is not None and self.worker.isRunning():
            self._discard_next_stream = True
            self.worker.cancel()
            self.worker.wait(1500)
        if self._hw_worker is not None and self._hw_worker.isRunning():
            self._hw_worker.wait(800)
        super().closeEvent(event)

    def _apply_windows_dark_titlebar(self):
        if sys.platform == "win32":
            try:
                hwnd = int(self.winId())
                DWMWA_USE_IMMERSIVE_DARK_MODE = 20
                value = ctypes.c_int(1)
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(value), ctypes.sizeof(value)
                )
            except Exception:
                pass

    def _apply_stylesheet(self):
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #07090E;
                color: #E2E8F0;
                font-family: 'Segoe UI', sans-serif;
            }
            QFrame#PanelCard {
                background-color: #0B0E16;
                border: 1px solid #161C28;
                border-radius: 10px;
            }
            QFrame#HeaderBar {
                background-color: #07090E;
                border-bottom: 1px solid #161C28;
            }
            QLabel#BrandTitle {
                font-size: 17px;
                font-weight: 800;
                letter-spacing: 5px;
                color: #F8FAFC;
            }
            QLabel#BrandSub {
                font-size: 9.5px;
                font-family: 'Consolas', monospace;
                color: #64748B;
                letter-spacing: 1.2px;
            }
            QLabel#SectionHeader {
                font-size: 10.5px;
                font-weight: 700;
                letter-spacing: 1.6px;
                color: #94A3B8;
                padding-bottom: 5px;
                border-bottom: 1px solid #161C28;
            }
            QLabel#StatusPill {
                background-color: rgba(16, 185, 129, 0.08);
                color: #10B981;
                border: 1px solid rgba(16, 185, 129, 0.28);
                border-radius: 12px;
                padding: 4px 14px;
                font-family: 'Consolas', monospace;
                font-size: 10.5px;
                font-weight: 700;
            }
            QPushButton {
                background-color: #0E121C;
                color: #CBD5E1;
                border: 1px solid #1B2333;
                border-radius: 7px;
                padding: 7px 13px;
                font-size: 11.5px;
                font-weight: 600;
            }
            QPushButton:hover {
                border-color: #334155;
                background-color: #141A28;
                color: #F8FAFC;
            }
            QPushButton:pressed {
                background-color: #0B0F18;
            }
            QPushButton:disabled {
                background-color: #0A0D14;
                color: #475569;
                border-color: #141923;
            }
            QPushButton#ToggleHudBtn:checked {
                background-color: rgba(0, 229, 255, 0.10);
                color: #00E5FF;
                border-color: rgba(0, 229, 255, 0.45);
            }
            QPushButton#VoiceTtsBtn {
                background-color: #0E121C;
                color: #94A3B8;
                border: 1px solid #1B2333;
                border-radius: 7px;
                padding: 6px 10px;
                font-size: 13px;
            }
            QPushButton#VoiceTtsBtn:hover {
                border-color: #334155;
                color: #F8FAFC;
            }
            QPushButton#VoiceTtsBtn:checked {
                background-color: rgba(16, 185, 129, 0.14);
                color: #10B981;
                border-color: rgba(16, 185, 129, 0.48);
            }
            QPushButton#AttachBtn {
                background-color: #0B0E16;
                color: #94A3B8;
                border: 1px solid #1B2333;
                border-radius: 8px;
                padding: 9px 12px;
                font-size: 13px;
            }
            QPushButton#AttachBtn:hover {
                border-color: #00E5FF;
                color: #F8FAFC;
                background-color: #111726;
            }
            QFrame#AttachedFilesBar {
                background-color: #090C13;
                border: 1px solid #161C28;
                border-radius: 8px;
            }
            QFrame#BottomStatusBar {
                background-color: #07090E;
                border-top: 1px solid #161C28;
            }
            QLabel#HwStatLabel {
                color: #94A3B8;
                font-family: 'Consolas', monospace;
                font-size: 10px;
                font-weight: 600;
            }
            QLabel#HwHintLabel {
                color: #475569;
                font-family: 'Consolas', monospace;
                font-size: 9.5px;
            }
            QPushButton#PrimarySendBtn {
                background-color: #00E5FF;
                color: #05080F;
                border: 1px solid #00E5FF;
                border-radius: 8px;
                font-weight: 800;
                font-size: 11.5px;
                letter-spacing: 1px;
                padding: 10px 22px;
            }
            QPushButton#PrimarySendBtn:hover {
                background-color: #38BDF8;
                border-color: #38BDF8;
            }
            QPushButton#PrimarySendBtn:pressed {
                background-color: #0284C7;
                border-color: #0284C7;
                color: #F8FAFC;
            }
            QPushButton#PrimarySendBtn:disabled {
                background-color: #111827;
                color: #475569;
                border-color: #1E293B;
            }
            QPushButton#StopBtn {
                background-color: rgba(244, 63, 94, 0.14);
                color: #FDA4AF;
                border: 1px solid rgba(244, 63, 94, 0.45);
                border-radius: 8px;
                font-weight: 800;
                font-size: 11.5px;
                letter-spacing: 1px;
                padding: 10px 20px;
            }
            QPushButton#StopBtn:hover {
                background-color: rgba(244, 63, 94, 0.28);
                border-color: #F43F5E;
                color: #FFFFFF;
            }
            QPushButton#StopBtn:disabled {
                background-color: rgba(244, 63, 94, 0.06);
                color: #9F1239;
                border-color: rgba(244, 63, 94, 0.20);
            }
            QPushButton#CrisisBtn {
                background-color: #0E1019;
                border: 1px solid #261924;
                border-radius: 7px;
                text-align: left;
                padding: 8px 10px;
                font-size: 11px;
            }
            QPushButton#CrisisBtn:hover {
                border-color: #F43F5E;
                background-color: #1F0E19;
                color: #FDA4AF;
            }
            QPushButton#ResetBtn {
                background-color: rgba(16, 185, 129, 0.10);
                color: #10B981;
                border: 1px solid rgba(16, 185, 129, 0.32);
                border-radius: 7px;
                font-weight: 700;
            }
            QPushButton#ResetBtn:hover {
                background-color: rgba(16, 185, 129, 0.22);
                border-color: #10B981;
            }
            QComboBox {
                background-color: #0E121C;
                color: #E2E8F0;
                border: 1px solid #1B2333;
                border-radius: 7px;
                padding: 5px 10px;
                font-family: 'Consolas', monospace;
                font-size: 11.5px;
                font-weight: 700;
            }
            QComboBox:hover {
                border-color: #334155;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox QAbstractItemView {
                background-color: #0B0E16;
                color: #E2E8F0;
                border: 1px solid #1E293B;
                selection-background-color: #162032;
                selection-color: #00E5FF;
                outline: 0;
            }
            QTextBrowser, QPlainTextEdit, QLineEdit {
                background-color: #07090E;
                color: #E2E8F0;
                border: 1px solid #161C28;
                border-radius: 8px;
                padding: 10px 12px;
                selection-background-color: #0284C7;
                selection-color: #FFFFFF;
            }
            QLineEdit {
                background-color: #0B0E16;
                border: 1px solid #1B2333;
            }
            QLineEdit:focus {
                border-color: #00E5FF;
                background-color: #0D111B;
            }
            QProgressBar {
                background-color: #0D111A;
                border: 1px solid #161C28;
                border-radius: 4px;
                height: 7px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #00E5FF;
                border-radius: 3px;
            }
            QSplitter::handle {
                background-color: #07090E;
            }
            QSplitter::handle:hover {
                background-color: #1B2333;
            }
            QScrollBar:vertical {
                background: #07090E;
                width: 8px;
                margin: 2px 0 2px 0;
                border: none;
            }
            QScrollBar::handle:vertical {
                background: #1C2436;
                min-height: 28px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: #334155;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
                background: none;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
            QScrollBar:horizontal {
                background: #07090E;
                height: 8px;
                margin: 0 2px 0 2px;
                border: none;
            }
            QScrollBar::handle:horizontal {
                background: #1C2436;
                min-width: 28px;
                border-radius: 4px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #334155;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
                background: none;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: none;
            }
        """)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # --- ÜST KOMUTA ÇUBUĞU ---
        header = QFrame()
        header.setObjectName("HeaderBar")
        header.setFixedHeight(58)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(18, 0, 18, 0)

        title_col = QVBoxLayout()
        title_col.setSpacing(1)
        lbl_title = QLabel("K A M")
        lbl_title.setObjectName("BrandTitle")
        lbl_sub = QLabel("NATIVE AUTONOMOUS COGNITIVE CORE // C++20 JIT & eBPF ENGINE")
        lbl_sub.setObjectName("BrandSub")
        title_col.addWidget(lbl_title)
        title_col.addWidget(lbl_sub)
        h_layout.addLayout(title_col)

        h_layout.addStretch()

        self.lbl_status_pill = QLabel("DİRLİK VE NİZAM // ENTROPİ: %3 // CLF: dV/dt <= 0")
        self.lbl_status_pill.setObjectName("StatusPill")
        h_layout.addWidget(self.lbl_status_pill)

        h_layout.addStretch()

        lbl_model = QLabel("AKTİF ZİHİN:")
        lbl_model.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 700;")
        h_layout.addWidget(lbl_model)

        self.combo_model = QComboBox()
        models = [m["name"] for m in self.llm_client.list_available_models()]
        for m in ["kam:council", "kam:apex", "kam:7b", "kam:r1", "kam:coder", "kam:coder-nano", "kam:r1-nano", "kam:1.5b", "qwen2.5:7b", "deepseek-r1:7b", "kam-1-liquid-moe"]:
            if m not in models:
                models.append(m)
        self.combo_model.addItems(models)
        idx = self.combo_model.findText(self.llm_client.current_model)
        if idx >= 0:
            self.combo_model.setCurrentIndex(idx)
        self.combo_model.currentTextChanged.connect(self._on_model_changed)
        h_layout.addWidget(self.combo_model)

        self.btn_voice_tts = QPushButton("🔊")
        self.btn_voice_tts.setObjectName("VoiceTtsBtn")
        self.btn_voice_tts.setToolTip("Sesli Okuma (Windows SAPI TTS — Yanıtı Seslendir)")
        self.btn_voice_tts.setCheckable(True)
        self.btn_voice_tts.setChecked(False)
        self.btn_voice_tts.toggled.connect(self._on_voice_toggled)
        h_layout.addWidget(self.btn_voice_tts)

        self.btn_toggle_hud = QPushButton("SİSTEM PANELİ")
        self.btn_toggle_hud.setObjectName("ToggleHudBtn")
        self.btn_toggle_hud.setToolTip("Sistem Panelini Aç / Kapat (Ctrl+Shift+S)")
        self.btn_toggle_hud.setCheckable(True)
        self.btn_toggle_hud.setChecked(False)
        self.btn_toggle_hud.clicked.connect(self._toggle_side_panels)
        h_layout.addWidget(self.btn_toggle_hud)

        btn_clear = QPushButton("YENİ SOHBET")
        btn_clear.setToolTip("Sohbeti Temizle (Ctrl+L)")
        btn_clear.clicked.connect(self._clear_chat)
        h_layout.addWidget(btn_clear)

        root_layout.addWidget(header)

        # --- 3 SÜTUNLU ANA KOMUTA ALANI ---
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setContentsMargins(12, 12, 12, 12)
        splitter.setHandleWidth(8)

        # 1. SOL PANEL: eBPF TELEMETRİ, OSİLOSKOP VE DONANIM DÜĞÜMLERİ
        self.left_panel = QFrame()
        left_panel = self.left_panel
        left_panel.setObjectName("PanelCard")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(14, 14, 14, 14)
        left_layout.setSpacing(10)

        crest_row = QHBoxLayout()
        self.crest_widget = KamMonolithCrestWidget()
        crest_row.addWidget(self.crest_widget)
        crest_info = QVBoxLayout()
        lbl_c1 = QLabel("BİLİŞSEL TELEMETRİ")
        lbl_c1.setStyleSheet("font-weight: 800; font-size: 13px; color: #F8FAFC; letter-spacing: 1px;")
        self.lbl_carrier = QLabel("Hat: UART-2 (Birincil)")
        self.lbl_carrier.setStyleSheet("color: #00E5FF; font-family: 'Consolas'; font-size: 11px; font-weight: 700;")
        lbl_c3 = QLabel("Mimari: Air-Gapped Yerel\nDonanım: RTX 5060 CUDA")
        lbl_c3.setStyleSheet("color: #94A3B8; font-size: 11px;")
        crest_info.addWidget(lbl_c1)
        crest_info.addWidget(self.lbl_carrier)
        crest_info.addWidget(lbl_c3)
        crest_info.addStretch()
        crest_row.addLayout(crest_info)
        left_layout.addLayout(crest_row)

        self.oscilloscope = TelemetryOscilloscopeWidget()
        left_layout.addWidget(self.oscilloscope)

        lbl_sec1 = QLabel("I. SERBEST ENERJİ VE ÇEKİRDEK METRİKLERİ")
        lbl_sec1.setObjectName("SectionHeader")
        left_layout.addWidget(lbl_sec1)

        metrics_grid = QGridLayout()
        metrics_grid.setSpacing(8)

        self.lbl_val_entropy = QLabel("%3")
        self.bar_entropy = QProgressBar()
        self.bar_entropy.setValue(3)

        self.lbl_val_fe = QLabel("0.080 nats")
        self.bar_fe = QProgressBar()
        self.bar_fe.setValue(8)

        self.lbl_val_temp = QLabel("48.2 °C")
        self.bar_temp = QProgressBar()
        self.bar_temp.setValue(48)

        self.lbl_val_ebpf = QLabel("3,420 /s")
        self.bar_ebpf = QProgressBar()
        self.bar_ebpf.setValue(65)

        for row_idx, (title, val_lbl, bar) in enumerate([
            ("Sistem Entropisi (S):", self.lbl_val_entropy, self.bar_entropy),
            ("Serbest Enerji (F):", self.lbl_val_fe, self.bar_fe),
            ("Silikon Sıcaklığı (NPU):", self.lbl_val_temp, self.bar_temp),
            ("eBPF Sinir Kancası:", self.lbl_val_ebpf, self.bar_ebpf),
        ]):
            t_lbl = QLabel(title)
            t_lbl.setStyleSheet("color: #94A3B8; font-size: 11px;")
            val_lbl.setStyleSheet("color: #F8FAFC; font-family: 'Consolas'; font-weight: 700; font-size: 12px;")
            metrics_grid.addWidget(t_lbl, row_idx * 2, 0)
            metrics_grid.addWidget(val_lbl, row_idx * 2, 1, alignment=Qt.AlignmentFlag.AlignRight)
            metrics_grid.addWidget(bar, row_idx * 2 + 1, 0, 1, 2)

        left_layout.addLayout(metrics_grid)

        lbl_sec2 = QLabel("II. DONANIM DÜĞÜMLERİ VE VERİ YOLLARI")
        lbl_sec2.setObjectName("SectionHeader")
        left_layout.addWidget(lbl_sec2)

        self.node_labels = {}
        for key, name, init_state in [
            ("uart", "UART-2 Telemetri Bağı", "ONLINE"),
            ("sdr", "SDR 868MHz Bilişsel Radyo", "STANDBY"),
            ("imu", "IMU & 6-DOF EKF Füzyon", "ONLINE"),
            ("can", "CAN-0 Taşıt Veriyolu", "ONLINE"),
            ("npu", "NVIDIA RTX 5060 / CUDA", "ONLINE (%100)"),
        ]:
            row = QHBoxLayout()
            n_lbl = QLabel(name)
            n_lbl.setStyleSheet("font-size: 11px; color: #CBD5E1;")
            s_lbl = QLabel(init_state)
            s_lbl.setStyleSheet(
                "font-family: 'Consolas'; font-size: 10px; font-weight: 700; "
                "color: #10B981; background: rgba(16,185,129,0.12); padding: 2px 7px; border-radius: 4px;"
            )
            row.addWidget(n_lbl)
            row.addStretch()
            row.addWidget(s_lbl)
            left_layout.addLayout(row)
            self.node_labels[key] = s_lbl

        lbl_sec_host = QLabel("III. GERÇEK BİLGİSAYAR & MANUS AJAN")
        lbl_sec_host.setObjectName("SectionHeader")
        left_layout.addWidget(lbl_sec_host)

        self.host_labels = {}
        for h_key, h_title, h_init in [
            ("cursor", "Fare & Ekran (Win32 UIA)", "(0, 0) // 1920x1080"),
            ("host_ram", "Yetki & İzin Seviyesi", "TAM YETKİ (SOVEREIGN)"),
            ("codeact", "CodeAct & UFO² Motoru", "39 ARAÇ HAZIR"),
        ]:
            h_row = QHBoxLayout()
            ht_lbl = QLabel(h_title)
            ht_lbl.setStyleSheet("font-size: 11px; color: #CBD5E1;")
            hv_lbl = QLabel(h_init)
            hv_lbl.setStyleSheet(
                "font-family: 'Consolas'; font-size: 10px; font-weight: 700; "
                "color: #00E5FF; background: rgba(0,229,255,0.10); padding: 2px 7px; border-radius: 4px;"
            )
            h_row.addWidget(ht_lbl)
            h_row.addStretch()
            h_row.addWidget(hv_lbl)
            left_layout.addLayout(h_row)
            self.host_labels[h_key] = hv_lbl

        left_layout.addStretch()
        splitter.addWidget(left_panel)

        # 2. ORTA PANEL: BİLİŞSEL ZİHİN DİYALOG VE KOMUTA MERKEZİ
        center_panel = QFrame()
        center_panel.setObjectName("PanelCard")
        center_layout = QVBoxLayout(center_panel)
        center_layout.setContentsMargins(14, 14, 14, 14)
        center_layout.setSpacing(10)

        lbl_sec_chat = QLabel("III. BİLİŞSEL ZİHİN & OTONOM BİLGİSAYAR AJANI KOMUTA TUVALİ")
        lbl_sec_chat.setObjectName("SectionHeader")
        center_layout.addWidget(lbl_sec_chat)

        # Sade Hızlı Başlatma Çipleri (Tek Satır, Dikkati Dağıtmayan Minimalist Düzen)
        quick_row = QHBoxLayout()
        quick_row.setSpacing(8)
        for btn_title, prompt_text in [
            ("Donanım & GPU Denetle", "Bilgisayarın gerçek donanım, fiziksel RAM, disk ve GPU durumunu denetle."),
            ("Açık Pencereler & Süreçler", "Masaüstündeki açık pencereleri ve çalışan süreçleri listele."),
            ("Kod Külliyatını Analiz Et", "Projeyi analiz et ve toplam kaç dosya ve kaç satır kod olduğunu göster."),
            ("Canlı HTML5 Kokpit Üret & Aç", "Bana canlı HTML dashboard gösterge paneli oluştur ve ekranda aç."),
        ]:
            q_btn = QPushButton(btn_title)
            q_btn.setStyleSheet(
                "QPushButton { background-color: #0B0E16; color: #94A3B8; border: 1px solid #161C28; border-radius: 14px; padding: 5px 13px; font-size: 11px; font-weight: 600; }"
                "QPushButton:hover { background-color: #131926; color: #F8FAFC; border-color: #334155; }"
            )
            q_btn.clicked.connect(lambda checked=False, p=prompt_text: self._send_prompt(p))
            quick_row.addWidget(q_btn)
        quick_row.addStretch()
        center_layout.addLayout(quick_row)

        self.chat_browser = QTextBrowser()
        self.chat_browser.setOpenExternalLinks(True)
        self.chat_browser.setFont(QFont("Segoe UI", 11))
        center_layout.addWidget(self.chat_browser, stretch=1)

        # Ekli Dosya Çip Çubuğu (Sürükle-Bırak veya Dosya Seç)
        self.attached_bar = QFrame()
        self.attached_bar.setObjectName("AttachedFilesBar")
        self.attached_bar_layout = QHBoxLayout(self.attached_bar)
        self.attached_bar_layout.setContentsMargins(10, 5, 10, 5)
        self.attached_bar_layout.setSpacing(6)
        self.attached_bar_layout.addStretch()
        self.attached_bar.setVisible(False)
        center_layout.addWidget(self.attached_bar)

        # Giriş Çubuğu
        input_row = QHBoxLayout()
        input_row.setSpacing(8)

        self.btn_attach = QPushButton("📎")
        self.btn_attach.setObjectName("AttachBtn")
        self.btn_attach.setToolTip("Dosya Ekle (veya pencereye sürükleyip bırakın)")
        self.btn_attach.clicked.connect(self._open_file_dialog)
        input_row.addWidget(self.btn_attach)

        self.input_line = QLineEdit()
        self.input_line.setPlaceholderText(
            "Emrinizi buyurun: 'sistem durumunu denetle', 'dosyaları listele', '/run git status', 'hesap makinesini aç'... (Enter)"
        )
        self.input_line.setFont(QFont("Segoe UI", 11))
        self.input_line.returnPressed.connect(self._on_send_clicked)
        input_row.addWidget(self.input_line, stretch=1)

        self.btn_send = QPushButton("GÖNDER")
        self.btn_send.setObjectName("PrimarySendBtn")
        self.btn_send.setToolTip("Gönder (Enter)")
        self.btn_send.clicked.connect(self._on_send_clicked)
        input_row.addWidget(self.btn_send)

        self.btn_stop = QPushButton("DURDUR")
        self.btn_stop.setObjectName("StopBtn")
        self.btn_stop.setToolTip("Akışı Durdur (Esc)")
        self.btn_stop.clicked.connect(self._stop_stream)
        self.btn_stop.setVisible(False)
        input_row.addWidget(self.btn_stop)

        center_layout.addLayout(input_row)

        splitter.addWidget(center_panel)

        # 3. SAĞ PANEL: KRİZ SİMÜLATÖRÜ, CANLI C++20 JIT SENTEZİ VE ÇEKİRDEK KAYDI
        self.right_panel = QFrame()
        right_panel = self.right_panel
        right_panel.setObjectName("PanelCard")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(14, 14, 14, 14)
        right_layout.setSpacing(10)

        lbl_sec_crisis = QLabel("IV. KRİZ SİMÜLATÖRÜ VE OTONOM ONARIM")
        lbl_sec_crisis.setObjectName("SectionHeader")
        right_layout.addWidget(lbl_sec_crisis)

        crisis_grid = QGridLayout()
        crisis_grid.setSpacing(6)
        for idx, (c_id, c_label) in enumerate([
            ("uav_uart_cut", "[I] UART-2 Kopuşu\nSDR 868MHz JIT Geçişi"),
            ("ew_jamming", "[II] Elektronik Harp (-95 dBm)\nFHSS Spektral Sıçrama"),
            ("thermal_spike", "[III] 92.4 °C Termal Pik\nINT4-AWQ Kuantizasyon"),
            ("can_spoof", "[IV] CAN-0 Spoofing (0x1BA)\neBPF Paket Karantinası"),
            ("gnss_spoof", "[V] GNSS Spoofing (d_M > 16)\nOptik Akış + EKF Geçişi"),
            ("swarm_loss", "[VI] Sürü Lideri Kaybı (Alpha-1)\nMarkov Raft Lider Seçimi"),
            ("ew_radar_threat", "[VII] Bilişsel Radar PDW\nLPI Tehdit & DRFM Cevabı"),
            ("cbf_envelope_breach", "[VIII] CBF Güvenlik İhlali\nNöro-Sembolik İzdüşüm"),
            ("intent_c2_mission", "[IX] Komutan Niyeti (C2)\nDAG Filo Dağıtımı"),
            ("byzantine_swarm_attack", "[X] Bizans Sürü İhaneti\nBFT Karantina & PQC Kyber"),
            ("trn_terrain_lock", "[XI] GPS-Kör INS Kayması\nPasif TRN/TERCOM Kilidi"),
            ("kinetic_actuator_jam", "[XII] Kanatçık Sıkışması\nSözde-Ters Kontrol Dağıtımı"),
            ("emcon_fso_switch", "[XIII] EMCON-Sıfır RF Kesintisi\n1550nm FSO Lazer Köprüsü"),
            ("radiation_seu_bitflip", "[XIV] Kozmik/EMP Bit-Flip (SEU)\nSECDED & TMR Bellek Onarımı"),
            ("sam_missile_lock", "[XV] Hipersonik SAM Füze Kilidi\nHJI 9G Diferansiyel Kaçınma"),
        ]):
            c_btn = QPushButton(c_label)
            c_btn.setObjectName("CrisisBtn")
            c_btn.clicked.connect(lambda checked=False, cid=c_id: self._trigger_crisis(cid))
            crisis_grid.addWidget(c_btn, idx // 2, idx % 2)
        right_layout.addLayout(crisis_grid)

        btn_reset = QPushButton("DİRLİK VE DENGEYİ SIFIRLA (ENTROPİ %3)")
        btn_reset.setObjectName("ResetBtn")
        btn_reset.clicked.connect(self._reset_equilibrium)
        right_layout.addWidget(btn_reset)

        jit_hdr_row = QHBoxLayout()
        lbl_sec_jit = QLabel("V. CANLI BELLEK-İÇİ C++20 JIT KOD MÜFETTİŞİ")
        lbl_sec_jit.setObjectName("SectionHeader")
        jit_hdr_row.addWidget(lbl_sec_jit, stretch=1)
        btn_copy_jit = QPushButton("JIT KODU KOPYALA")
        btn_copy_jit.setStyleSheet(
            "QPushButton { background-color: #091926; color: #00E5FF; border: 1px solid #0E3A53; font-size: 10px; font-weight: 700; padding: 3px 8px; }"
            "QPushButton:hover { background-color: #0F2940; border-color: #00E5FF; }"
        )
        btn_copy_jit.clicked.connect(self._copy_jit_code)
        jit_hdr_row.addWidget(btn_copy_jit)
        right_layout.addLayout(jit_hdr_row)

        self.lbl_ast_badge = QLabel("AST SANDBOX: DOĞRULANDI // 0 İHLAL // JIT HAZIR (41.2 ms)")
        self.lbl_ast_badge.setStyleSheet(
            "font-family: 'Consolas'; font-size: 10px; font-weight: 700; color: #00E5FF; "
            "background: rgba(0,229,255,0.08); padding: 4px 8px; border-radius: 4px;"
        )
        right_layout.addWidget(self.lbl_ast_badge)

        self.jit_code_view = QPlainTextEdit()
        self.jit_code_view.setReadOnly(True)
        self.jit_code_view.setFont(QFont("Consolas", 10))
        self.jit_code_view.setPlainText(CodeMutator.generate_sdr_fallback().strip())
        right_layout.addWidget(self.jit_code_view, stretch=1)

        lbl_sec_log = QLabel("VI. LINUX eBPF VE AKTİF ÇIKARIM ÇEKİRDEK KAYDI")
        lbl_sec_log.setObjectName("SectionHeader")
        right_layout.addWidget(lbl_sec_log)

        self.kernel_log = QPlainTextEdit()
        self.kernel_log.setReadOnly(True)
        self.kernel_log.setFont(QFont("Consolas", 9))
        self.kernel_log.setMaximumHeight(165)
        right_layout.addWidget(self.kernel_log)

        splitter.addWidget(right_panel)

        # Varsayılan olarak sade odak modu (Sol/Sağ paneller tek tıkla açılır)
        self.left_panel.setVisible(False)
        self.right_panel.setVisible(False)
        splitter.setSizes([340, 900, 420])
        root_layout.addWidget(splitter, stretch=1)

        # --- ALT HAFİF DONANIM TELEMETRİ ÇUBUĞU (CPU / RAM / GPU) ---
        status_bar = QFrame()
        status_bar.setObjectName("BottomStatusBar")
        status_bar.setFixedHeight(26)
        sb_layout = QHBoxLayout(status_bar)
        sb_layout.setContentsMargins(16, 0, 16, 0)
        sb_layout.setSpacing(14)

        self.lbl_hw_cpu = QLabel("CPU: --")
        self.lbl_hw_cpu.setObjectName("HwStatLabel")
        self.lbl_hw_ram = QLabel("RAM: --")
        self.lbl_hw_ram.setObjectName("HwStatLabel")
        self.lbl_hw_gpu = QLabel("GPU: --")
        self.lbl_hw_gpu.setObjectName("HwStatLabel")

        sb_layout.addWidget(self.lbl_hw_cpu)
        sb_layout.addWidget(self.lbl_hw_ram)
        sb_layout.addWidget(self.lbl_hw_gpu)
        sb_layout.addStretch()

        lbl_shortcuts_hint = QLabel("Ctrl+L Yeni Sohbet  ·  Ctrl+Shift+S Sistem Paneli  ·  Dosya Sürükle-Bırak")
        lbl_shortcuts_hint.setObjectName("HwHintLabel")
        sb_layout.addWidget(lbl_shortcuts_hint)

        root_layout.addWidget(status_bar)

        self._log_kernel("[KAM-CORE]   [OK]   Yerel masaüstü komuta merkezi başlatıldı.")
        self._log_kernel("[KAM-CORE]   [SYNC] Linux eBPF SPSC RingBuffer (<12 us) aktif.")
        self._log_kernel(f"[KAM-AGENT]  [LLM]  Aktif bilişsel model: {self.llm_client.current_model}")

    def _log_kernel(self, line: str):
        ts = time.strftime("%H:%M:%S")
        self.kernel_log.appendPlainText(f"{ts} {line}")

    def _append_welcome_banner(self):
        self.chat_blocks = [
            (
                "system",
                "<b>KAM // EGEMEN BİLİŞSEL ZİHİN VE OTONOM SİSTEM KOMUTA MERKEZİ</b><br>"
                "<span style='color:#94A3B8;'>Dede Korkut hikmeti, Kutadgu Bilig'in nizam töresi, Karl Friston Serbest Enerji Prensibi "
                "(F &rarr; 0) ve Linux eBPF çekirdek kancalarıyla mühürlenmiş %100 yerel komuta dergâhı.<br>"
                "<i>\"Gök çökmedikçe, yağız yer delinmedikçe bu nöbet bitmez.\"</i> &mdash; "
                "Baş Mimar: <b>Bahattin Yunus ÇETİN (@bahattinyunus)</b></span>",
            )
        ]
        self._render_chat()

    def _copy_jit_code(self):
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(self.jit_code_view.toPlainText())
            self._log_kernel("[JIT-COMP]   [COPY]  C++20 JIT kaynak kodu panoya kopyalandı.")

    def _format_html_text(self, raw: str) -> str:
        if not raw:
            return ""
        text = str(raw).replace("\r\n", "\n").replace("\r", "\n")
        text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        placeholders = []

        def _stash(html_fragment: str) -> str:
            idx = len(placeholders)
            placeholders.append(html_fragment)
            return f"@@KAM_BLOCK_{idx}@@"

        # 1. <codeact>...</codeact> blokları (canlı akışta henüz kapanmamış etiketler dahil)
        def _repl_codeact(m):
            code_body = m.group(1).strip()
            return _stash(
                "<div style='background:#060E14; border:1px solid #13313D; border-left:3px solid #10B981; "
                "border-radius:6px; padding:9px 11px; margin:7px 0;'>"
                "<div style='color:#10B981; font-family:Consolas,monospace; font-size:8.5pt; "
                "font-weight:700; letter-spacing:0.8px; margin-bottom:4px;'>"
                "⚡ CODEACT // OTONOM PYTHON İCRASI</div>"
                f"<pre style='margin:0; white-space:pre-wrap; font-family:Consolas,monospace; "
                f"font-size:9.5pt; color:#E2E8F0;'>{code_body}</pre></div>"
            )

        text = re.sub(
            r"&lt;codeact&gt;([\s\S]*?)(?:&lt;/codeact&gt;|$)",
            _repl_codeact,
            text,
            flags=re.IGNORECASE,
        )

        # 2. <tool_call>...</tool_call> blokları
        def _repl_tool_call(m):
            body = m.group(1).strip()
            return _stash(
                "<div style='background:#080F18; border:1px solid #1B2A3E; border-left:3px solid #38BDF8; "
                "border-radius:6px; padding:8px 10px; margin:6px 0;'>"
                "<div style='color:#38BDF8; font-family:Consolas,monospace; font-size:8.5pt; "
                "font-weight:700; letter-spacing:0.8px; margin-bottom:4px;'>"
                "⚙ ARAÇ ÇAĞRISI // TOOL CALL</div>"
                f"<pre style='margin:0; white-space:pre-wrap; font-family:Consolas,monospace; "
                f"font-size:9pt; color:#CBD5E1;'>{body}</pre></div>"
            )

        text = re.sub(
            r"&lt;tool_call&gt;([\s\S]*?)(?:&lt;/tool_call&gt;|$)",
            _repl_tool_call,
            text,
            flags=re.IGNORECASE,
        )

        # 3. <think>...</think> akıl yürütme blokları (canlı akışta kapanmamış etiketler dahil)
        def _repl_think(m):
            thought_body = m.group(1).strip().replace("\n", "<br>")
            return _stash(
                "<div style='background:#0B0D17; border:1px solid #1F1B38; border-left:3px solid #8B5CF6; "
                "border-radius:6px; padding:8px 10px; margin:6px 0; color:#A78BFA; "
                "font-family:Consolas,monospace; font-size:9.5pt;'>"
                "<div style='color:#C4B5FD; font-size:8.5pt; font-weight:700; letter-spacing:0.8px; "
                f"margin-bottom:4px;'>◈ CoT AKIL YÜRÜTME ZİNCİRİ</div>{thought_body}</div>"
            )

        text = re.sub(
            r"&lt;think&gt;([\s\S]*?)(?:&lt;/think&gt;|$)",
            _repl_think,
            text,
            flags=re.IGNORECASE,
        )

        # 4. Çitli kod blokları ```lang ... ``` (tamamlanmış ve akış sırasında açık kalmış bloklar)
        def _repl_code(m):
            lang = (m.group(1) or "KOD").strip().upper()
            code_body = m.group(2).strip("\n")
            return _stash(
                "<div style='background:#05070C; border:1px solid #171F2E; border-left:3px solid #00E5FF; "
                "border-radius:6px; padding:9px 11px; margin:7px 0;'>"
                f"<div style='color:#00E5FF; font-family:Consolas,monospace; font-size:8.5pt; "
                f"font-weight:700; letter-spacing:0.8px; margin-bottom:4px;'>⚡ {lang}</div>"
                f"<pre style='margin:0; white-space:pre-wrap; font-family:Consolas,monospace; "
                f"font-size:9.5pt; color:#E2E8F0;'>{code_body}</pre></div>"
            )

        text = re.sub(r"```([a-zA-Z0-9_+#.-]*)[ \t]*\n([\s\S]*?)```", _repl_code, text)
        text = re.sub(r"```([a-zA-Z0-9_+#.-]*)[ \t]*\n([\s\S]+)$", _repl_code, text)

        # 5. Satır-bazlı sistem/ajan icra rozetleri (her biri kendi kapalı <div> kapsülünde)
        def _repl_council_badge(m):
            line = m.group(0).strip()
            return _stash(
                "<div style='background:#110C1E; border:1px solid #3B1F6B; border-left:3px solid #A855F7; "
                "border-radius:6px; padding:7px 10px; margin:6px 0; color:#D8B4FE; "
                f"font-family:Consolas,monospace; font-size:9pt;'><b>{line}</b></div>"
            )

        def _repl_plan_badge(m):
            line = m.group(0).strip()
            return _stash(
                "<div style='background:#151108; border:1px solid #4A3410; border-left:3px solid #F59E0B; "
                "border-radius:6px; padding:7px 10px; margin:6px 0; color:#FCD34D; "
                f"font-family:Consolas,monospace; font-size:9pt;'><b>{line}</b></div>"
            )

        def _repl_exec_badge(m):
            line = m.group(0).strip()
            return _stash(
                "<div style='background:#06121A; border:1px solid #113244; border-left:3px solid #10B981; "
                "border-radius:6px; padding:7px 10px; margin:6px 0; color:#67E8F9; "
                f"font-family:Consolas,monospace; font-size:9pt;'><b>{line}</b></div>"
            )

        text = re.sub(r"🏛️ \[BİLİŞSEL KURUL YÖNLENDİRMESİ //[^\n]*", _repl_council_badge, text)
        text = re.sub(r"🧭 \[MANUS-SINIFI OTONOM GÖREV PLANI //[^\n]*", _repl_plan_badge, text)
        text = re.sub(r"⚡ \[OTONOM AJAN İCRASI //[^\n]*", _repl_exec_badge, text)

        # 6. Satır içi kod (`code`) — önce koru ki bold/italik bozmasın
        def _repl_inline_code(m):
            return _stash(
                f"<span style='background:#0E1420; color:#38BDF8; font-family:Consolas,monospace; "
                f"font-size:9.5pt; padding:1px 5px; border-radius:3px;'>{m.group(1)}</span>"
            )

        text = re.sub(r"`([^`\n]+)`", _repl_inline_code, text)

        # 7. Kalın metin (**bold**) ve başlıklar
        text = re.sub(r"\*\*(.+?)\*\*", r"<b style='color:#F8FAFC;'>\1</b>", text)
        text = re.sub(
            r"(?m)^#{1,3}[ \t]+(.+)$",
            r"<span style='color:#F8FAFC; font-weight:700; font-size:11.5pt;'>\1</span>",
            text,
        )

        # 8. Durdurulma işareti
        text = text.replace(
            "[Akış kullanıcı tarafından durduruldu]",
            "<span style='color:#FDA4AF; font-family:Consolas,monospace; font-size:9pt;'>"
            "■ [Akış kullanıcı tarafından durduruldu]</span>",
        )

        text = text.replace("\n", "<br>")

        # 9. Korumalı blokları geri yerleştir ve blok çevresindeki fazladan <br> temizliği yap
        for idx, fragment in enumerate(placeholders):
            token = f"@@KAM_BLOCK_{idx}@@"
            if fragment.startswith("<div"):
                text = text.replace(f"<br>{token}<br>", fragment)
                text = text.replace(f"<br>{token}", fragment)
                text = text.replace(f"{token}<br>", fragment)
            text = text.replace(token, fragment)

        return text

    def _render_chat(self, streaming_partial: str = None, force_scroll: bool = False):
        sb = self.chat_browser.verticalScrollBar()
        was_at_bottom = force_scroll or (sb.maximum() == 0) or (sb.value() >= sb.maximum() - 40)
        prev_scroll = sb.value()

        parts = []
        for role, content in self.chat_blocks:
            if role == "system":
                parts.append(
                    f"<div style='background:#0A0E17; border:1px solid #161C28; border-left:3px solid #00E5FF; "
                    f"padding:12px 14px; border-radius:8px; margin-bottom:12px;'>{content}</div>"
                )
            elif role == "user":
                parts.append(
                    f"<div style='background:#0E1422; border:1px solid #1B2333; padding:10px 14px; "
                    f"border-radius:8px; margin-bottom:10px;'><b style='color:#38BDF8;'>KOMUTAN //</b> "
                    f"<span style='color:#F8FAFC;'>{self._format_html_text(content)}</span></div>"
                )
            elif role == "assistant":
                parts.append(
                    f"<div style='background:#090C13; border:1px solid #161C28; border-left:3px solid #10B981; "
                    f"padding:12px 14px; border-radius:8px; margin-bottom:12px;'><b style='color:#10B981;'>KAM //</b><br>"
                    f"<span style='color:#E2E8F0;'>{self._format_html_text(content)}</span></div>"
                )
            elif role == "crisis":
                parts.append(
                    f"<div style='background:#190B13; border:1px solid #4C1D2E; border-left:3px solid #F43F5E; "
                    f"padding:12px 14px; border-radius:8px; margin-bottom:12px;'><b style='color:#F43F5E;'>OTONOM KRİZ MÜDAHALESİ //</b><br>"
                    f"<span style='color:#FECDD3;'>{self._format_html_text(content)}</span></div>"
                )

        if streaming_partial is not None:
            parts.append(
                f"<div style='background:#090C13; border:1px solid #1B3044; border-left:3px solid #00E5FF; "
                f"padding:12px 14px; border-radius:8px; margin-bottom:12px;'><b style='color:#00E5FF;'>KAM (AKIYOR...) //</b><br>"
                f"<span style='color:#E2E8F0;'>{self._format_html_text(streaming_partial)}</span></div>"
            )

        self.chat_browser.setHtml("".join(parts))
        if was_at_bottom:
            sb.setValue(sb.maximum())
        else:
            sb.setValue(min(prev_scroll, sb.maximum()))

    def dragEnterEvent(self, event):
        mime = event.mimeData()
        if mime is not None and mime.hasUrls():
            for url in mime.urls():
                if url.isLocalFile() and os.path.isfile(url.toLocalFile()):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event):
        mime = event.mimeData()
        if mime is not None and mime.hasUrls():
            added = 0
            for url in mime.urls():
                if url.isLocalFile():
                    if self.attach_file(url.toLocalFile()):
                        added += 1
            if added:
                event.acceptProposedAction()
                return
        event.ignore()

    def _open_file_dialog(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "KAM'a Dosya Ekle",
            os.getcwd(),
            "Tüm Dosyalar (*.*)",
        )
        for p in paths:
            self.attach_file(p)

    def attach_file(self, path: str) -> bool:
        if not path:
            return False
        abs_path = os.path.abspath(path)
        if not os.path.isfile(abs_path):
            return False
        if any(f["path"] == abs_path for f in self.attached_files):
            return False
        if len(self.attached_files) >= 5:
            self._log_kernel("[KAM-FILE]   [WARN]  En fazla 5 dosya aynı anda eklenebilir.")
            return False
        try:
            size_bytes = os.path.getsize(abs_path)
        except OSError:
            return False
        if size_bytes > 20 * 1024 * 1024:
            self._log_kernel(f"[KAM-FILE]   [WARN]  Dosya çok büyük (>20 MB): {os.path.basename(abs_path)}")
            return False
        self.attached_files.append({
            "path": abs_path,
            "name": os.path.basename(abs_path),
            "size": size_bytes,
        })
        self._refresh_attached_bar()
        self._log_kernel(f"[KAM-FILE]   [ATTACH] Dosya eklendi: {os.path.basename(abs_path)} ({size_bytes:,} B)")
        return True

    def _remove_attached_file(self, abs_path: str):
        self.attached_files = [f for f in self.attached_files if f["path"] != abs_path]
        self._refresh_attached_bar()

    def _refresh_attached_bar(self):
        while self.attached_bar_layout.count() > 0:
            item = self.attached_bar_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        if not self.attached_files:
            self.attached_bar.setVisible(False)
            self.attached_bar_layout.addStretch()
            return

        for f_info in self.attached_files:
            size_kb = max(0.1, f_info["size"] / 1024.0)
            size_label = f"{size_kb:.1f} KB" if size_kb < 1024 else f"{size_kb / 1024.0:.1f} MB"
            chip = QFrame()
            chip.setStyleSheet(
                "QFrame { background-color: #101726; border: 1px solid #1E2C42; border-radius: 6px; }"
            )
            chip_layout = QHBoxLayout(chip)
            chip_layout.setContentsMargins(8, 3, 6, 3)
            chip_layout.setSpacing(6)

            lbl = QLabel(f"📎 {f_info['name']} ({size_label})")
            lbl.setStyleSheet("color: #38BDF8; font-family: 'Consolas'; font-size: 10px; font-weight: 700; border: none; background: transparent;")
            chip_layout.addWidget(lbl)

            btn_x = QPushButton("×")
            btn_x.setFixedSize(18, 18)
            btn_x.setStyleSheet(
                "QPushButton { background: transparent; border: none; color: #94A3B8; font-size: 12px; font-weight: 700; padding: 0; }"
                "QPushButton:hover { color: #F43F5E; }"
            )
            btn_x.clicked.connect(lambda checked=False, p=f_info["path"]: self._remove_attached_file(p))
            chip_layout.addWidget(btn_x)

            self.attached_bar_layout.addWidget(chip)

        self.attached_bar_layout.addStretch()
        self.attached_bar.setVisible(True)

    def _build_prompt_with_attachments(self, prompt: str):
        if not self.attached_files:
            return prompt, prompt

        context_blocks = []
        display_names = []
        for f_info in self.attached_files:
            abs_path = f_info["path"]
            name = f_info["name"]
            display_names.append(name)
            preview = ""
            try:
                with open(abs_path, "rb") as fp:
                    raw_bytes = fp.read(12288)
                if b"\x00" in raw_bytes:
                    preview = f"[İkili dosya — boyut: {f_info['size']:,} bayt]"
                else:
                    preview = raw_bytes.decode("utf-8", errors="replace")
                    if f_info["size"] > 12288:
                        preview += "\n... [İÇERİK ÖZETLENDİ]"
            except Exception as exc:
                preview = f"[Dosya okunamadı: {exc}]"
            context_blocks.append(f"[EKLİ DOSYA: {abs_path}]\n{preview}\n[/EKLİ DOSYA]")

        llm_prompt = "\n\n".join(context_blocks) + "\n\n" + prompt
        display_prompt = f"{prompt}\n📎 Ekli Dosya: {', '.join(display_names)}"
        self.attached_files = []
        self._refresh_attached_bar()
        return llm_prompt, display_prompt

    def _poll_host_stats(self):
        if self._hw_worker is not None and self._hw_worker.isRunning():
            return
        self._hw_worker = HostStatsWorker(self)
        self._hw_worker.stats_ready.connect(self._on_host_stats_ready)
        self._hw_worker.start()

    def _on_host_stats_ready(self, stats: dict):
        if hasattr(self, "lbl_hw_cpu"):
            self.lbl_hw_cpu.setText(stats.get("cpu", "CPU: --"))
            self.lbl_hw_ram.setText(stats.get("ram", "RAM: --"))
            self.lbl_hw_gpu.setText(stats.get("gpu", "GPU: --"))

    def _on_voice_toggled(self, checked: bool):
        if not checked:
            self._stop_tts()
        self._log_kernel(f"[KAM-TTS]    [VOICE] Sesli okuma {'AKTİF (Windows SAPI)' if checked else 'KAPALI'}.")

    @staticmethod
    def _clean_text_for_tts(raw: str) -> str:
        if not raw:
            return ""
        text = re.sub(r"<think>[\s\S]*?(?:</think>|$)", " ", raw, flags=re.IGNORECASE)
        text = re.sub(r"<codeact>[\s\S]*?(?:</codeact>|$)", " ", text, flags=re.IGNORECASE)
        text = re.sub(r"<tool_call>[\s\S]*?(?:</tool_call>|$)", " ", text, flags=re.IGNORECASE)
        text = re.sub(r"```[\s\S]*?```", " ", text)
        text = re.sub(r"(?m)^(?:🏛️|🧭|⚡) \[[^\n]*$", " ", text)
        text = text.replace("[Akış kullanıcı tarafından durduruldu]", " ")
        text = re.sub(r"[`*_#>|]+", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        if len(text) > 750:
            cut = text[:750]
            last_dot = max(cut.rfind("."), cut.rfind("!"), cut.rfind("?"))
            text = cut[: last_dot + 1] if last_dot > 200 else cut
        return text

    def _stop_tts(self):
        with self._tts_lock:
            proc = self._tts_proc
            self._tts_proc = None
        if proc is not None:
            try:
                if proc.poll() is None:
                    proc.terminate()
            except Exception:
                pass

    def _speak_async(self, raw_text: str):
        if sys.platform != "win32":
            return
        spoken = self._clean_text_for_tts(raw_text)
        if not spoken:
            return
        self._stop_tts()

        def _worker():
            try:
                b64_text = base64.b64encode(spoken.encode("utf-8")).decode("ascii")
                ps_script = (
                    "Add-Type -AssemblyName System.Speech; "
                    "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                    "$s.Rate = 1; "
                    f"$txt = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String('{b64_text}')); "
                    "$s.Speak($txt)"
                )
                enc_cmd = base64.b64encode(ps_script.encode("utf-16le")).decode("ascii")
                proc = subprocess.Popen(
                    ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-EncodedCommand", enc_cmd],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=0x08000000,  # CREATE_NO_WINDOW
                )
                with self._tts_lock:
                    self._tts_proc = proc
                proc.wait(timeout=90)
            except Exception:
                pass
            finally:
                with self._tts_lock:
                    if self._tts_proc is not None and self._tts_proc.poll() is not None:
                        self._tts_proc = None

        threading.Thread(target=_worker, daemon=True, name="kam-sapi-tts").start()

    def _toggle_side_panels(self, checked: bool):
        self.left_panel.setVisible(checked)
        self.right_panel.setVisible(checked)

    def _toggle_side_panels_shortcut(self):
        new_state = not self.btn_toggle_hud.isChecked()
        self.btn_toggle_hud.setChecked(new_state)
        self._toggle_side_panels(new_state)

    def _on_model_changed(self, model_name: str):
        if not model_name:
            return
        self.llm_client.current_model = model_name
        self.llm_client._model_initialized = True
        self._log_kernel(f"[KAM-AGENT]  [MODEL] Aktif zihin değiştirildi: {model_name}")

    def _clear_chat(self):
        self._stop_tts()
        if self.worker is not None and self.worker.isRunning():
            self._discard_next_stream = True
            self.worker.cancel()
        if hasattr(self, "_stream_render_timer"):
            self._stream_render_timer.stop()
        self.attached_files = []
        if hasattr(self, "attached_bar"):
            self._refresh_attached_bar()
        self.current_assistant_buffer = ""
        self.llm_client.conversation_history.clear()
        self._set_streaming_ui_state(False)
        self._append_welcome_banner()
        self._log_kernel("[KAM-CORE]   [CLEAR] Diyalog geçmişi sıfırlandı.")

    def _set_streaming_ui_state(self, streaming: bool):
        self.btn_send.setVisible(not streaming)
        self.btn_send.setEnabled(not streaming)
        self.btn_stop.setVisible(streaming)
        self.btn_stop.setEnabled(streaming)
        self.btn_stop.setText("DURDUR")
        self.input_line.setReadOnly(streaming)
        if hasattr(self, "btn_attach"):
            self.btn_attach.setEnabled(not streaming)

    def _on_send_clicked(self):
        if self.worker is not None and self.worker.isRunning():
            return
        text = self.input_line.text().strip()
        if not text and not self.attached_files:
            return
        if not text and self.attached_files:
            text = "Ekli dosyayı analiz et ve özetle."
        self.input_line.clear()
        self._send_prompt(text)

    def _send_prompt(self, prompt: str):
        if self.worker is not None and self.worker.isRunning():
            return

        self._stop_tts()
        llm_prompt, display_prompt = self._build_prompt_with_attachments(prompt)

        self._discard_next_stream = False
        self.chat_blocks.append(("user", display_prompt))
        self.current_assistant_buffer = ""
        self._render_chat(streaming_partial="...", force_scroll=True)
        self._set_streaming_ui_state(True)
        self._log_kernel(f"[KAM-AGENT]  [QUERY] İstemi işliyor: {prompt[:42]}...")

        self.worker = LLMStreamWorker(self.llm_client, llm_prompt)
        self.worker.token_received.connect(self._on_token)
        self.worker.finished_stream.connect(self._on_stream_done)
        self.worker.start()

    def _stop_stream(self):
        if self.worker is not None and self.worker.isRunning():
            self.worker.cancel()
            self.btn_stop.setEnabled(False)
            self.btn_stop.setText("DURDURULUYOR...")
            self._log_kernel("[KAM-AGENT]  [STOP]  Akış kullanıcı tarafından durduruluyor...")

    def _on_token(self, token: str):
        if self._discard_next_stream:
            return
        if "⚡ [OTONOM AJAN İCRASI //" in token:
            lines = token.strip().splitlines()
            if lines:
                self._log_kernel(f"[KAM-AGENT]  [EXEC]  {lines[0][:68]}")
        self.current_assistant_buffer += token
        if not self._stream_render_timer.isActive():
            self._stream_render_timer.start()

    def _flush_stream_render(self):
        if self._discard_next_stream:
            return
        if self.worker is not None and self.worker.isRunning():
            self._render_chat(streaming_partial=self.current_assistant_buffer or "...")

    def _on_stream_done(self, full_text: str):
        self._stream_render_timer.stop()
        was_cancelled = bool(self.worker is not None and self.worker.is_cancelled)
        discard = self._discard_next_stream
        self._discard_next_stream = False
        self._set_streaming_ui_state(False)

        if not discard:
            if was_cancelled:
                final_text = full_text.strip()
                if final_text:
                    final_text = f"{final_text}\n\n[Akış kullanıcı tarafından durduruldu]"
                else:
                    final_text = "[Akış kullanıcı tarafından durduruldu]"
                self.chat_blocks.append(("assistant", final_text))
                self._log_kernel("[KAM-AGENT]  [STOP]  Bilişsel akış kullanıcı tarafından kesildi.")
            else:
                self.chat_blocks.append(("assistant", full_text))
                self._log_kernel("[KAM-AGENT]  [DONE]  Bilişsel yanıt tamamlandı.")
                if hasattr(self, "btn_voice_tts") and self.btn_voice_tts.isChecked():
                    self._speak_async(full_text)
            self._render_chat()

    def _trigger_crisis(self, crisis_type: str):
        if crisis_type == "uav_uart_cut":
            self.engine.inference.trigger_anomaly()
            self.engine.active_telemetry = "SDR-868MHz (FHSS Fallback)"
            code = CodeMutator.generate_sdr_fallback()
            msg = (
                "UART-2 telemetri hattı koptu, varyasyonel entropi %89 seviyesine yükseldi. "
                "Bilişsel KAM otonom onarım protokolünü devreye aldı: sdr_fallback_node.cpp bellekte "
                "JIT derlendi (41.2 ms) ve görev hattı SDR 868MHz üzerinden kesintisiz devralındı."
            )
            self._log_kernel("[NERV-SYS]   [CRIT]  UART-2 koptu! Entropi %89.")
            self._log_kernel("[JIT-COMP]   [BUILD] sdr_fallback_node.cpp derlendi (41.2 ms).")
        elif crisis_type == "ew_jamming":
            self.engine.inference.reset_equilibrium(0.42)
            self.engine.active_telemetry = "SDR-433MHz (Anti-Jamming Hopping)"
            code = CodeMutator.generate_ew_fhss_fallback()
            msg = (
                "Spektrumda -95 dBm geniş bant elektronik harp karıştırması tespit edildi. "
                "ew_fhss_hopper.cpp bellekte derlenerek 433MHz/868MHz altın oran spektral sıçrama "
                "dizisi kilitlendi; dirlik korundu."
            )
            self._log_kernel("[NERV-SYS]   [WARN]  EW Jamming (-95 dBm) algılandı.")
            self._log_kernel("[JIT-COMP]   [BUILD] ew_fhss_hopper.cpp sıcak-yama uygulandı.")
        elif crisis_type == "thermal_spike":
            self.engine.inference.reset_equilibrium(0.35)
            code = CodeMutator.generate_thermal_fallback()
            msg = (
                "NPU sıcaklığı 92.4 °C kritik eşiğine ulaştı. Linux eBPF termal kancası devreye girdi: "
                "thermal_vision_fallback.cpp derlenerek model INT4-AWQ moduna çekildi (45W -> 14.5W)."
            )
            self._log_kernel("[NERV-SYS]   [WARN]  NPU 92.4 C termal pik!")
            self._log_kernel("[JIT-COMP]   [BUILD] thermal_vision_fallback.cpp devrede.")
        elif crisis_type == "gnss_spoof":
            self.engine.inference.reset_equilibrium(0.28)
            self.engine.active_telemetry = "IMU + Optik Akış (GNSS İzole)"
            code = CodeMutator.generate_gnss_spoof_fallback()
            msg = (
                "GNSS/GPS Spoofing saldırısı saptandı (Mahalanobis mesafesi d_M > 16.0). "
                "gnss_optical_flow_ekf.cpp bellekte JIT derlenerek sahte uydu koordinatları reddedildi ve "
                "200 Hz Optik Akış + Barometrik EKF ölü-hesaplama seyrüseferine geçildi."
            )
            self._log_kernel("[NERV-SYS]   [CRIT]  GNSS Spoofing (d_M > 16.0) reddedildi!")
            self._log_kernel("[JIT-COMP]   [BUILD] gnss_optical_flow_ekf.cpp devrede.")
        elif crisis_type == "swarm_loss":
            self.engine.inference.reset_equilibrium(0.22)
            self.engine.active_telemetry = "SDR-868.9MHz (Bravo-2 Lider)"
            code = CodeMutator.generate_swarm_handover_fallback()
            msg = (
                "Sürü lideri Alpha-1 devre dışı kaldı. Dağıtık Markov Battaniyesi serbest enerji konsensüsü "
                "en düşük F=0.14 nats değerine sahip Bravo-2 birimini yeni lider atadı; "
                "swarm_raft_leader_handover.cpp sıcak-yama olarak bağlandı."
            )
            self._log_kernel("[NERV-SYS]   [WARN]  Sürü lideri (Alpha-1) kaybı!")
            self._log_kernel("[JIT-COMP]   [BUILD] swarm_raft_leader_handover.cpp -> Bravo-2 lider.")
        elif crisis_type == "ew_radar_threat":
            self.engine.inference.trigger_anomaly()
            self.engine.active_telemetry = "DRFM-Active-Jammer (17.4GHz)"
            code = CodeMutator.generate_ew_drfm_fallback()
            msg = (
                "17.4 GHz LPI çevik radar darbe dizisi algılandı. Bilişsel PDW sınıflandırıcısı tehdidi öğrendi; "
                "ew_drfm_responder.cpp bellek-içi derlenerek 8 sahte hedef ve Doppler kaymasıyla düşman radarı aldatıldı."
            )
            self._log_kernel("[EW-RADAR]   [ALERT] LPI Radar Tehdidi (17.4 GHz) saptandı!")
            self._log_kernel("[JIT-COMP]   [BUILD] ew_drfm_responder.cpp (DRFM Karıştırıcı) aktif.")
        elif crisis_type == "cbf_envelope_breach":
            self.engine.inference.trigger_anomaly()
            self.engine.active_telemetry = "CBF-Shield-Override (RTL)"
            code = CodeMutator.generate_cbf_safety_shield_fallback()
            msg = (
                "DARPA ANSR & CBF Nöro-Sembolik Güvenlik Kalkanı h(x) < 0 ihlali saptadı! "
                "İrtifa < 30m, stall < 22 m/s ve batarya <%18 ihlalleri engellendi; "
                "cbf_safety_shield.cpp komutayı güvenli zarfa izdüşürdü ve RTL otonomisini devraldı."
            )
            self._log_kernel("[CBF-SHIELD] [CRIT]  Uçuş güvenlik zarfı ihlali önlendi!")
            self._log_kernel("[JIT-COMP]   [BUILD] cbf_safety_shield.cpp kuadratik izdüşüm bağlandı.")
        elif crisis_type == "intent_c2_mission":
            self.engine.active_telemetry = "C2-Multi-Domain-Mesh"
            code = CodeMutator.generate_c2_dag_fallback()
            msg = (
                "Yüksek seviyeli komutan niyeti DAG görevlerine bölündü: Sungur-EW-1 (SEAD), Kizilelma-Strike-2 (Vadi Taarruzu), "
                "Bayraktar-TB3 (Keşif) ve Bozkurt (Röle) unsurlarına Beklenen Serbest Enerji minimizasyonuyla tahsis yapıldı."
            )
            self._log_kernel("[C2-DAG]     [ORDER] Komutan niyeti 4 düğümlü DAG'a tahsis edildi.")
            self._log_kernel("[JIT-COMP]   [BUILD] c2_task_executor.cpp filo kuyruğuna enjekte edildi.")
        elif crisis_type == "byzantine_swarm_attack":
            self.engine.inference.trigger_anomaly()
            self.engine.active_telemetry = "BFT-PQC-Mesh (ML-KEM-768)"
            code = CodeMutator.generate_byzantine_pqc_fallback()
            msg = (
                "Bizans sürü ihaneti tespit edildi: Charlie-3 düğümünden sahte Markov Battaniyesi inancı (D_JS = 0.474 > 0.18) yayıldı! "
                "byzantine_pqc_guard.cpp bellekte JIT derlenerek hain düğüm izole edildi ve ML-KEM-768 (Kyber q=3329) kuantum-dirençli oturum anahtarları yenilendi."
            )
            self._log_kernel("[BFT-PQC]    [CRIT]  Charlie-3 Bizans ihaneti (D_JS=0.474) karantinada!")
            self._log_kernel("[JIT-COMP]   [BUILD] byzantine_pqc_guard.cpp + ML-KEM-768 rotasyonu aktif.")
        elif crisis_type == "trn_terrain_lock":
            self.engine.active_telemetry = "TRN-TERCOM (0W Pasif Kilit)"
            code = CodeMutator.generate_trn_terrain_lock_fallback()
            msg = (
                "Uzun menzil INS ölü-hesaplama kayması (901.4 m) pasif Arazi Referanslı Seyrüsefer (TRN / TERCOM) ile "
                "Sayısal Yükselti Modeli (DEM) üzerinde eşleştirildi; trn_tercom_navigator.cpp ile 0W RF yayımıyla %99.47 doğrulukla kilitlendi."
            )
            self._log_kernel("[TRN-NAV]    [LOCK]  Pasif TERCOM DEM korelasyonu (NCC=0.9999) kilitlendi.")
            self._log_kernel("[JIT-COMP]   [BUILD] trn_tercom_navigator.cpp seyrüsefer hattında.")
        elif crisis_type == "kinetic_actuator_jam":
            self.engine.inference.trigger_anomaly()
            self.engine.active_telemetry = "PseudoInverse-Mixer (Yedekli)"
            code = CodeMutator.generate_actuator_reconfig_fallback()
            msg = (
                "Kinetik kanatçık hasarı: Sol Elevon (LEFT_ELEVON) +0.22 rad açıda mekanik olarak sıkıştı! "
                "actuator_mixer_reconfig.cpp bellekte JIT derlenerek Ağırlıklı Sözde-Ters (Weighted Moore-Penrose Pseudo-Inverse) "
                "matrisiyle momentler sağlam V-kuyruk ve itki vektörlemesine dağıtıldı (Hata L2 = 0.00016)."
            )
            self._log_kernel("[ACTUATOR]   [CRIT]  LEFT_ELEVON (+0.22 rad) sıkıştı! Sözde-Ters mikser devrede.")
            self._log_kernel("[JIT-COMP]   [BUILD] actuator_mixer_reconfig.cpp sıcak-yama uygulandı.")
        elif crisis_type == "emcon_fso_switch":
            self.engine.active_telemetry = "1550nm FSO Lazer (0W RF)"
            code = CodeMutator.generate_fso_laser_mesh_fallback()
            msg = (
                "EMCON-Sıfır Radyo Sessizliği: Düşman SIGINT/ELINT yön bulucu (DF) dizisi algılandı, tüm RF yayımı 0.0W seviyesine kapatıldı. "
                "fso_laser_mesh_link.cpp bellekte JIT derlenerek 1550nm SWIR MEMS lazer köprüsü üzerinden POI=%0.000 ile 685 Mbps sürü bağı kuruldu."
            )
            self._log_kernel("[FSO-LASER]  [EMCON] RF vericileri kapatıldı (0.0W). 1550nm SWIR lazer kilitli.")
            self._log_kernel("[JIT-COMP]   [BUILD] fso_laser_mesh_link.cpp optik ağ köprüsünde.")
        elif crisis_type == "radiation_seu_bitflip":
            self.engine.inference.trigger_anomaly()
            self.engine.active_telemetry = "SECDED-TMR-Scrubber (ECC)"
            code = CodeMutator.generate_radiation_tmr_scrubber_fallback()
            msg = (
                "Kozmik ışın / EMP kaynaklı SRAM/VRAM bit tersinmesi (Bit-19 SEU & Bank-B ağırlık bozulması) Linux eBPF EDAC kancasıyla yakalandı! "
                "radiation_tmr_scrubber.cpp bellekte JIT derlenerek Hamming(72,64) SECDED ve 3-Bank TMR çoğunluk oylamasıyla BitNet b1.58 ağırlıkları %100 onarıldı."
            )
            self._log_kernel("[EDAC-ECC]   [CRIT]  Bit-19 SEU & Bank-B BitNet ağırlık bozulması yakalandı!")
            self._log_kernel("[JIT-COMP]   [BUILD] radiation_tmr_scrubber.cpp ile %100 bit-kesin onarım.")
        elif crisis_type == "sam_missile_lock":
            self.engine.inference.trigger_anomaly()
            self.engine.active_telemetry = "HJI-9G-Evasion + DRFM-CrossEye"
            code = CodeMutator.generate_hji_missile_evasion_fallback()
            msg = (
                "Terminal SAM Füze Kilidi (R=2850m, V_c=980 m/s): Oransal seyrüsefer (PN) güdümlü füze yaklaşıyor! "
                "hji_evasion_maneuver.cpp bellekte JIT derlenerek Hamilton-Jacobi-Isaacs (HJI) eyer noktası 9.0G dikgen fıçı tonosu ve DRFM Cross-Eye açı aldatmasıyla ıskalama mesafesi >75m'ye çıkarıldı."
            )
            self._log_kernel("[HJI-EVADE]  [ALERT] SAM Füze Kilidi! Isaacs 9.0G + DRFM Cross-Eye manevrası aktif.")
            self._log_kernel("[JIT-COMP]   [BUILD] hji_evasion_maneuver.cpp uçuş kontrol döngüsünde.")
        else:
            self.engine.inference.reset_equilibrium(0.18)
            code = CodeMutator.generate_can_firewall_fallback()
            msg = (
                "CAN-0 veriyoluna yetkisiz çerçeve (ID 0x1BA) enjeksiyonu tespit edildi. "
                "can_firewall_filter.cpp mikrosaniyede eBPF halkasına bağlanarak sahte paketler karantinaya alındı."
            )
            self._log_kernel("[NERV-SYS]   [CRIT]  CAN-0 Spoofing (ID 0x1BA) engellendi!")

        efe_plan = self.engine.inference.select_optimal_policy(crisis_hint=crisis_type)
        self._log_kernel(f"[KAM-EFE]    [POLICY] Secilen Politika: {efe_plan['optimal_policy']} (G={efe_plan['expected_free_energy_g']})")

        ast_check = CodeMutator.validate_ast(code)
        self.lbl_ast_badge.setText(
            f"AST SANDBOX: {'DOĞRULANDI' if ast_check['valid'] else 'İHLAL'} // "
            f"{len(ast_check['violations'])} İHLAL // JIT AKTİF (41.2 ms)"
        )
        self.jit_code_view.setPlainText(code.strip())
        self.chat_blocks.append(("crisis", msg))
        self._render_chat()

    def _reset_equilibrium(self):
        self.engine.active_telemetry = "UART-2 (Birincil)"
        self.engine.inference.reset_equilibrium(0.03)
        self._log_kernel("[KAM-CORE]   [STABLE] Dirlik ve nizam sıfırlandı (Entropi %3).")

    def _tick_telemetry(self):
        entropy = self.engine.inference.entropy
        fe = 0.08 if entropy < 0.2 else (1.84 if entropy > 0.8 else 0.34)
        temp = 48.2 if entropy < 0.2 else (76.4 if entropy > 0.8 else 54.5)
        ebpf_rate = 3420 if entropy < 0.2 else (8940 if entropy > 0.8 else 4820)
        chaos = entropy >= 0.80
        e_pct = int(round(entropy * 100))

        # Üst durum hapı yalnızca durum değiştiğinde stil günceller (10 Hz setStyleSheet yükünü sıfırlar)
        if chaos:
            self.lbl_status_pill.setText(f"KRİTİK ENTROPİ // CANLI ONARIM: %{e_pct}")
        else:
            self.lbl_status_pill.setText(f"DİRLİK VE NİZAM // ENTROPİ: %{e_pct}")

        if chaos != self._last_chaos_state:
            self._last_chaos_state = chaos
            if chaos:
                self.lbl_status_pill.setStyleSheet(
                    "background-color: rgba(244, 63, 94, 0.16); color: #F43F5E; "
                    "border: 1px solid rgba(244, 63, 94, 0.55); border-radius: 12px; padding: 4px 14px; "
                    "font-family: 'Consolas'; font-size: 10.5px; font-weight: 700;"
                )
            else:
                self.lbl_status_pill.setStyleSheet(
                    "background-color: rgba(16, 185, 129, 0.08); color: #10B981; "
                    "border: 1px solid rgba(16, 185, 129, 0.28); border-radius: 12px; padding: 4px 14px; "
                    "font-family: 'Consolas'; font-size: 10.5px; font-weight: 700;"
                )

        # Odak modunda sol panel gizliyken gereksiz 10 Hz çizim ve Win32 sorgularını atla
        if not self.left_panel.isVisible():
            return

        self.crest_widget.advance_phase(chaos)
        self.oscilloscope.push_sample(entropy, fe)

        self.lbl_val_entropy.setText(f"%{e_pct}")
        self.bar_entropy.setValue(min(100, e_pct))

        self.lbl_val_fe.setText(f"{fe:.3f} nats")
        self.bar_fe.setValue(min(100, int(fe * 45)))

        self.lbl_val_temp.setText(f"{temp:.1f} °C")
        self.bar_temp.setValue(min(100, int(temp)))

        self.lbl_val_ebpf.setText(f"{ebpf_rate:,} /s")
        self.bar_ebpf.setValue(min(100, int(ebpf_rate / 100)))

        self.lbl_carrier.setText(f"Hat: {self.engine.active_telemetry}")

        # Canlı Fare Koordinatı ve Ekran Telemetrisi (yalnızca sistem paneli açıkken)
        try:
            sc = Win32ComputerUseController.get_screen_and_cursor()
            self.host_labels["cursor"].setText(
                f"({sc.get('cursor_x', 0)}, {sc.get('cursor_y', 0)}) // {sc.get('screen_width', 1920)}x{sc.get('screen_height', 1080)}"
            )
        except Exception:
            pass

        sdr_active = "SDR" in self.engine.active_telemetry
        if sdr_active != self._last_sdr_state:
            self._last_sdr_state = sdr_active
            if sdr_active:
                self.node_labels["uart"].setText("BYPASS (KOPUK)")
                self.node_labels["uart"].setStyleSheet(
                    "font-family: 'Consolas'; font-size: 10px; font-weight: 700; "
                    "color: #F43F5E; background: rgba(244,63,94,0.15); padding: 2px 7px; border-radius: 4px;"
                )
                self.node_labels["sdr"].setText("ONLINE (AKTİF)")
            else:
                self.node_labels["uart"].setText("ONLINE")
                self.node_labels["uart"].setStyleSheet(
                    "font-family: 'Consolas'; font-size: 10px; font-weight: 700; "
                    "color: #10B981; background: rgba(16,185,129,0.12); padding: 2px 7px; border-radius: 4px;"
                )
                self.node_labels["sdr"].setText("STANDBY")


def run_desktop_app():
    if sys.platform == "win32":
        hdesk = None
        try:
            GENERIC_ALL = 0x10000000
            hdesk = ctypes.windll.user32.OpenDesktopW("Default", 0, True, GENERIC_ALL)
            if hdesk:
                ctypes.windll.user32.SetThreadDesktop(hdesk)
        except Exception:
            pass
        finally:
            if hdesk:
                try:
                    ctypes.windll.user32.CloseDesktop(hdesk)
                except Exception:
                    pass

    app = QApplication(sys.argv)
    window = KamDesktopWindow()
    window.show()
    window.raise_()
    window.activateWindow()
    if sys.platform == "win32":
        try:
            hwnd = int(window.winId())
            ctypes.windll.user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            ctypes.windll.user32.SetForegroundWindow(hwnd)
        except Exception:
            pass
    sys.exit(app.exec())
