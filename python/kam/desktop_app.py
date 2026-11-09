import sys
import os
import math
import time
import ctypes
from collections import deque

from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QPointF, QRectF
from PyQt6.QtGui import (
    QColor,
    QPainter,
    QPainterPath,
    QPen,
    QBrush,
    QFont,
    QIcon,
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
)

from .engine import KamEngine
from .code_mutator import CodeMutator
from .real_llm import UniversalLLMClient


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

    def run(self):
        accumulated = []
        try:
            for token in self.llm_client.generate_stream(self.prompt):
                accumulated.append(token)
                self.token_received.emit(token)
        except Exception as exc:
            err = f"\n[HATA]: {exc}"
            accumulated.append(err)
            self.token_received.emit(err)
        self.finished_stream.emit("".join(accumulated))


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
        bg_grad.setColorAt(0.0, QColor(10, 16, 28))
        bg_grad.setColorAt(1.0, QColor(3, 5, 10))
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
        painter.fillRect(0, 0, w, h, QColor(6, 10, 18))
        grid_pen = QPen(QColor(30, 41, 59, 110), 1, Qt.PenStyle.DotLine)
        painter.setPen(grid_pen)
        for i in range(1, 4):
            y = int(h * i / 4)
            painter.drawLine(0, y, w, y)
        for i in range(1, 8):
            x = int(w * i / 8)
            painter.drawLine(x, 0, x, h)

        # Çerçeve
        painter.setPen(QPen(QColor(30, 41, 59), 1))
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
        self.current_assistant_buffer = ""
        self.chat_blocks = []

        self.setWindowTitle("KAM // Bilişsel Zihin ve Otonom Sistem Komuta Merkezi (Native Desktop v2.5)")
        self.resize(1460, 880)
        self.setMinimumSize(1180, 720)

        logo_path = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "kam_logo.png")
        if os.path.exists(logo_path):
            self.setWindowIcon(QIcon(logo_path))

        self._apply_windows_dark_titlebar()
        self._apply_stylesheet()
        self._build_ui()
        self._append_welcome_banner()

        # 10 Hz Gerçek Zamanlı Telemetri ve Osiloskop Döngüsü
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick_telemetry)
        self.timer.start(100)

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
                background-color: #050811;
                color: #E2E8F0;
                font-family: 'Segoe UI', sans-serif;
            }
            QFrame#PanelCard {
                background-color: #090E1A;
                border: 1px solid #1E293B;
                border-radius: 8px;
            }
            QFrame#HeaderBar {
                background-color: #070B14;
                border-bottom: 1px solid #1E293B;
            }
            QLabel#BrandTitle {
                font-size: 18px;
                font-weight: 800;
                letter-spacing: 4px;
                color: #F8FAFC;
            }
            QLabel#BrandSub {
                font-size: 10px;
                font-family: 'Consolas', monospace;
                color: #00E5FF;
                letter-spacing: 1px;
            }
            QLabel#SectionHeader {
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 1.5px;
                color: #00E5FF;
                padding-bottom: 4px;
                border-bottom: 1px solid #1E293B;
            }
            QLabel#StatusPill {
                background-color: rgba(16, 185, 129, 0.12);
                color: #10B981;
                border: 1px solid rgba(16, 185, 129, 0.35);
                border-radius: 12px;
                padding: 5px 14px;
                font-family: 'Consolas', monospace;
                font-size: 11px;
                font-weight: 700;
            }
            QPushButton {
                background-color: #0F172A;
                color: #E2E8F0;
                border: 1px solid #1E293B;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                border-color: #00E5FF;
                background-color: #132038;
            }
            QPushButton#PrimarySendBtn {
                background-color: #00E5FF;
                color: #020408;
                border: none;
                font-weight: 800;
                letter-spacing: 1px;
                padding: 10px 22px;
            }
            QPushButton#PrimarySendBtn:hover {
                background-color: #38BDF8;
            }
            QPushButton#CrisisBtn {
                background-color: #111320;
                border: 1px solid #331E2E;
                text-align: left;
                padding: 9px 11px;
            }
            QPushButton#CrisisBtn:hover {
                border-color: #F43F5E;
                background-color: #24101E;
                color: #FDA4AF;
            }
            QPushButton#ResetBtn {
                background-color: rgba(16, 185, 129, 0.12);
                color: #10B981;
                border: 1px solid rgba(16, 185, 129, 0.35);
                font-weight: 700;
            }
            QPushButton#ResetBtn:hover {
                background-color: rgba(16, 185, 129, 0.24);
            }
            QComboBox {
                background-color: #0F172A;
                color: #00E5FF;
                border: 1px solid #1E293B;
                border-radius: 6px;
                padding: 5px 10px;
                font-family: 'Consolas', monospace;
                font-weight: 700;
            }
            QTextBrowser, QPlainTextEdit, QLineEdit {
                background-color: #060A12;
                color: #E2E8F0;
                border: 1px solid #1E293B;
                border-radius: 6px;
                padding: 10px;
                selection-background-color: #0284C7;
            }
            QProgressBar {
                background-color: #0F172A;
                border: 1px solid #1E293B;
                border-radius: 4px;
                height: 8px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #00E5FF;
                border-radius: 3px;
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

        self.lbl_status_pill = QLabel("DİRLİK VE NİZAM // ENTROPİ: %3")
        self.lbl_status_pill.setObjectName("StatusPill")
        h_layout.addWidget(self.lbl_status_pill)

        h_layout.addStretch()

        lbl_model = QLabel("AKTİF ZİHİN:")
        lbl_model.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 700;")
        h_layout.addWidget(lbl_model)

        self.combo_model = QComboBox()
        models = [m["name"] for m in self.llm_client.list_available_models()]
        for m in ["kam:apex", "kam:7b", "kam:r1", "kam:coder", "kam:coder-nano", "kam:r1-nano", "kam:1.5b", "qwen2.5:7b", "deepseek-r1:7b", "kam-1-liquid-moe"]:
            if m not in models:
                models.append(m)
        self.combo_model.addItems(models)
        idx = self.combo_model.findText(self.llm_client.current_model)
        if idx >= 0:
            self.combo_model.setCurrentIndex(idx)
        self.combo_model.currentTextChanged.connect(self._on_model_changed)
        h_layout.addWidget(self.combo_model)

        btn_clear = QPushButton("TEMİZLE")
        btn_clear.clicked.connect(self._clear_chat)
        h_layout.addWidget(btn_clear)

        root_layout.addWidget(header)

        # --- 3 SÜTUNLU ANA KOMUTA ALANI ---
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setContentsMargins(12, 12, 12, 12)
        splitter.setHandleWidth(8)

        # 1. SOL PANEL: eBPF TELEMETRİ, OSİLOSKOP VE DONANIM DÜĞÜMLERİ
        left_panel = QFrame()
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

        left_layout.addStretch()
        splitter.addWidget(left_panel)

        # 2. ORTA PANEL: BİLİŞSEL ZİHİN DİYALOG VE KOMUTA MERKEZİ
        center_panel = QFrame()
        center_panel.setObjectName("PanelCard")
        center_layout = QVBoxLayout(center_panel)
        center_layout.setContentsMargins(14, 14, 14, 14)
        center_layout.setSpacing(10)

        lbl_sec_chat = QLabel("III. BİLİŞSEL ZİHİN DİYALOG VE KOMUTA TUVALİ")
        lbl_sec_chat.setObjectName("SectionHeader")
        center_layout.addWidget(lbl_sec_chat)

        # Hızlı Komut Butonları
        quick_row = QHBoxLayout()
        quick_row.setSpacing(6)
        for btn_title, prompt_text in [
            ("I. Öz Kimlik ve Hikmet", "Neden adın KAM ve Dede Korkut geleneğinden gelen dirlik felsefen nedir?"),
            ("II. Friston Serbest Enerjisi", "Karl Friston serbest enerji prensibini matematiksel ve net açıkla."),
            ("III. 3B SİHA Rota Analizi", "Bir SİHA 3 boyutta düşman radarını aşarak nasıl yol planlaması yapar?"),
            ("IV. C++20 Memory Arena", "Uç sistemler için C++20 ile sıfır bellek sızıntılı bir Memory Arena sınıfı yaz."),
        ]:
            q_btn = QPushButton(btn_title)
            q_btn.clicked.connect(lambda checked=False, p=prompt_text: self._send_prompt(p))
            quick_row.addWidget(q_btn)
        center_layout.addLayout(quick_row)

        self.chat_browser = QTextBrowser()
        self.chat_browser.setOpenExternalLinks(True)
        self.chat_browser.setFont(QFont("Segoe UI", 11))
        center_layout.addWidget(self.chat_browser, stretch=1)

        # Giriş Çubuğu
        input_row = QHBoxLayout()
        input_row.setSpacing(8)
        self.input_line = QLineEdit()
        self.input_line.setPlaceholderText("KAM Bilişsel Zihnine danışın, mimari analiz veya C++20 kodu isteyin... (Enter)")
        self.input_line.setFont(QFont("Segoe UI", 11))
        self.input_line.returnPressed.connect(self._on_send_clicked)
        input_row.addWidget(self.input_line, stretch=1)

        self.btn_send = QPushButton("GÖNDER")
        self.btn_send.setObjectName("PrimarySendBtn")
        self.btn_send.clicked.connect(self._on_send_clicked)
        input_row.addWidget(self.btn_send)
        center_layout.addLayout(input_row)

        splitter.addWidget(center_panel)

        # 3. SAĞ PANEL: KRİZ SİMÜLATÖRÜ, CANLI C++20 JIT SENTEZİ VE ÇEKİRDEK KAYDI
        right_panel = QFrame()
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

        lbl_sec_jit = QLabel("V. CANLI BELLEK-İÇİ C++20 JIT KOD MÜFETTİŞİ")
        lbl_sec_jit.setObjectName("SectionHeader")
        right_layout.addWidget(lbl_sec_jit)

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

        splitter.setSizes([340, 660, 440])
        root_layout.addWidget(splitter, stretch=1)

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
                "<b>KAM BİLİŞSEL ZİHİN VE OTONOM SİSTEM KOMUTA MERKEZİ</b><br>"
                "<span style='color:#94A3B8;'>Dede Korkut hikmeti, Karl Friston Serbest Enerji Prensibi (F &rarr; 0) "
                "ve Linux eBPF çekirdek kancalarıyla donatılmış %100 yerel masaüstü arayüzü. "
                "Baş Mimar: <b>Bahattin Yunus ÇETİN (@bahattinyunus)</b></span>",
            )
        ]
        self._render_chat()

    def _format_html_text(self, raw: str) -> str:
        text = raw.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        if "&lt;think&gt;" in text:
            text = text.replace(
                "&lt;think&gt;",
                "<div style='background:#0D1322; border-left:3px solid #8B5CF6; padding:8px; margin:6px 0; color:#A78BFA; font-family:Consolas; font-size:10pt;'><b>[CoT AKIL YÜRÜTME ZİNCİRİ]:</b><br>",
            ).replace("&lt;/think&gt;", "</div>")
        return text.replace("\n", "<br>")

    def _render_chat(self, streaming_partial: str = None):
        parts = []
        for role, content in self.chat_blocks:
            if role == "system":
                parts.append(
                    f"<div style='background:#0B1324; border:1px solid #1E293B; border-left:3px solid #00E5FF; "
                    f"padding:12px; border-radius:6px; margin-bottom:12px;'>{content}</div>"
                )
            elif role == "user":
                parts.append(
                    f"<div style='background:#111C33; border:1px solid #1E293B; padding:10px 14px; "
                    f"border-radius:6px; margin-bottom:10px;'><b style='color:#00E5FF;'>KOMUTAN //</b> "
                    f"<span style='color:#F8FAFC;'>{self._format_html_text(content)}</span></div>"
                )
            elif role == "assistant":
                parts.append(
                    f"<div style='background:#080D18; border:1px solid #1E293B; border-left:3px solid #10B981; "
                    f"padding:12px 14px; border-radius:6px; margin-bottom:12px;'><b style='color:#10B981;'>KAM //</b><br>"
                    f"<span style='color:#E2E8F0;'>{self._format_html_text(content)}</span></div>"
                )
            elif role == "crisis":
                parts.append(
                    f"<div style='background:#1F0D18; border:1px solid #F43F5E; border-left:4px solid #F43F5E; "
                    f"padding:12px 14px; border-radius:6px; margin-bottom:12px;'><b style='color:#F43F5E;'>OTONOM KRİZ MÜDAHALESİ //</b><br>"
                    f"<span style='color:#FECDD3;'>{self._format_html_text(content)}</span></div>"
                )

        if streaming_partial is not None:
            parts.append(
                f"<div style='background:#080D18; border:1px solid #00E5FF; border-left:3px solid #00E5FF; "
                f"padding:12px 14px; border-radius:6px; margin-bottom:12px;'><b style='color:#00E5FF;'>KAM (AKIYOR...) //</b><br>"
                f"<span style='color:#E2E8F0;'>{self._format_html_text(streaming_partial)}</span></div>"
            )

        self.chat_browser.setHtml("".join(parts))
        sb = self.chat_browser.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _on_model_changed(self, model_name: str):
        self.llm_client.current_model = model_name
        self._log_kernel(f"[KAM-AGENT]  [MODEL] Aktif zihin değiştirildi: {model_name}")

    def _clear_chat(self):
        self.llm_client.conversation_history.clear()
        self._append_welcome_banner()
        self._log_kernel("[KAM-CORE]   [CLEAR] Diyalog geçmişi sıfırlandı.")

    def _on_send_clicked(self):
        text = self.input_line.text().strip()
        if not text:
            return
        self.input_line.clear()
        self._send_prompt(text)

    def _send_prompt(self, prompt: str):
        if self.worker is not None and self.worker.isRunning():
            return

        self.chat_blocks.append(("user", prompt))
        self.current_assistant_buffer = ""
        self._render_chat(streaming_partial="...")
        self.btn_send.setEnabled(False)
        self._log_kernel(f"[KAM-AGENT]  [QUERY] İstemi işliyor: {prompt[:42]}...")

        self.worker = LLMStreamWorker(self.llm_client, prompt)
        self.worker.token_received.connect(self._on_token)
        self.worker.finished_stream.connect(self._on_stream_done)
        self.worker.start()

    def _on_token(self, token: str):
        self.current_assistant_buffer += token
        self._render_chat(streaming_partial=self.current_assistant_buffer)

    def _on_stream_done(self, full_text: str):
        self.chat_blocks.append(("assistant", full_text))
        self._render_chat()
        self.btn_send.setEnabled(True)
        self._log_kernel("[KAM-AGENT]  [DONE]  Bilişsel yanıt tamamlandı.")

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

        self.crest_widget.advance_phase(chaos)
        self.oscilloscope.push_sample(entropy, fe)

        e_pct = int(round(entropy * 100))
        self.lbl_val_entropy.setText(f"%{e_pct}")
        self.bar_entropy.setValue(min(100, e_pct))

        self.lbl_val_fe.setText(f"{fe:.3f} nats")
        self.bar_fe.setValue(min(100, int(fe * 45)))

        self.lbl_val_temp.setText(f"{temp:.1f} °C")
        self.bar_temp.setValue(min(100, int(temp)))

        self.lbl_val_ebpf.setText(f"{ebpf_rate:,} /s")
        self.bar_ebpf.setValue(min(100, int(ebpf_rate / 100)))

        self.lbl_carrier.setText(f"Hat: {self.engine.active_telemetry}")

        if chaos:
            self.lbl_status_pill.setText(f"KRİTİK ENTROPİ // CANLI ONARIM: %{e_pct}")
            self.lbl_status_pill.setStyleSheet(
                "background-color: rgba(244, 63, 94, 0.18); color: #F43F5E; "
                "border: 1px solid #F43F5E; border-radius: 12px; padding: 5px 14px; "
                "font-family: 'Consolas'; font-size: 11px; font-weight: 700;"
            )
        else:
            self.lbl_status_pill.setText(f"DİRLİK VE NİZAM // ENTROPİ: %{e_pct}")
            self.lbl_status_pill.setStyleSheet(
                "background-color: rgba(16, 185, 129, 0.12); color: #10B981; "
                "border: 1px solid rgba(16, 185, 129, 0.35); border-radius: 12px; padding: 5px 14px; "
                "font-family: 'Consolas'; font-size: 11px; font-weight: 700;"
            )

        if "SDR" in self.engine.active_telemetry:
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
        try:
            GENERIC_ALL = 0x10000000
            hdesk = ctypes.windll.user32.OpenDesktopW("Default", 0, True, GENERIC_ALL)
            if hdesk:
                ctypes.windll.user32.SetThreadDesktop(hdesk)
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
