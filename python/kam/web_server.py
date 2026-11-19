import os
import re
import sys
import copy
import json
import time
import uuid
import inspect
import threading
import subprocess
import webbrowser
from datetime import datetime, timezone
from urllib.parse import urlsplit, parse_qs
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

try:
    import psutil
except ImportError:
    psutil = None

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from .engine import KamEngine
from .models.liquid_moe import KamLiquidFoundationModel
from .code_mutator import CodeMutator
from .knowledge_engine import LocalKnowledgeEngine
from .real_llm import UniversalLLMClient
from .edge_optimizer import EdgeHardwareBudget, EdgeModelOptimizer, TernaryBitNetQuantizer, SpeculativeDecoder
from .tactical_planner import TacticalRoutePlanner3D
from .ew_cognitive_radar import PulseDescriptorWord, CognitiveEwEmitterClassifier
from .intent_c2_orchestrator import IntentToTaskOrchestrator
from .neuro_symbolic_shield import FlightControlCommand, NeuroSymbolicSafetyShield
from .lyapunov_controller import LyapunovCognitiveController
from .byzantine_pqc_swarm import SwarmNodeBelief, ByzantinePqcSwarmGuard
from .terrain_matching_trn import TerrainRelativeNavigator
from .actuator_reconfigurator import ActuatorFaultReconfigurator
from .covert_fso_comm import FsoLinkParameters, CovertFsoLaserTransceiver
from .radiation_ecc_scrubber import RadiationHardenedMemoryScrubber
from .differential_game_evasion import MissileEngagementState, DifferentialGameMissileEvasion
from .autonomous_agent import Win32ComputerUseController


MAX_POST_BODY_BYTES = 10 * 1024 * 1024  # 10 MB safety limit
MAX_UPLOAD_BYTES = 2 * 1024 * 1024  # 2 MB file upload limit
CLIENT_DISCONNECT_ERRORS = (BrokenPipeError, ConnectionResetError, ConnectionAbortedError)

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_DATA_DIR = os.path.join(_REPO_ROOT, "data")
_DEFAULT_SESSIONS_FILE = os.path.join(_DATA_DIR, "kam_sessions.json")
_DEFAULT_UPLOADS_DIR = os.path.join(_DATA_DIR, "uploads")
_SESSION_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_WINDOWS_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}

BUILTIN_WORKFLOWS = {
    "system_health_audit": {
        "id": "system_health_audit",
        "name": "Sistem Sağlık Denetimi",
        "description": "CPU, RAM, GPU, disk ve aktif süreç telemetrisini otonom olarak denetler.",
        "steps": ["get_real_system_telemetry", "manage_processes"],
    },
    "repo_code_audit": {
        "id": "repo_code_audit",
        "name": "Proje & Kod Tabanı Denetimi",
        "description": "Çalışma dizini yapısını ve Python çekirdek modüllerini analiz eder.",
        "steps": ["list_directory", "analyze_codebase"],
    },
    "network_security_scan": {
        "id": "network_security_scan",
        "name": "Ağ & Güvenlik Taraması",
        "description": "Yerel ağ arayüzlerini, açık portları ve loopback bağlantı sağlığını tarar.",
        "steps": ["network_probe (status)", "network_probe (ping 127.0.0.1)"],
    },
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sanitize_upload_filename(raw_name: str):
    """Strictly validate and sanitize an upload filename; returns (safe_name, error_msg)."""
    if not isinstance(raw_name, str) or not raw_name.strip():
        return None, "'filename' must be a non-empty string"

    cleaned_raw = raw_name.strip()
    if any(tok in cleaned_raw for tok in ("..", "/", "\\", "\x00", ":")):
        return None, "Invalid filename: path traversal or separator characters are forbidden"

    base = os.path.basename(cleaned_raw).lstrip(".")
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", base).strip("._ ")
    if not safe or len(safe) > 120:
        return None, "Invalid filename after sanitization"

    stem = safe.split(".", 1)[0].upper()
    if stem in _WINDOWS_RESERVED_NAMES:
        return None, "Reserved OS device name is not allowed"

    return safe, None


class _SessionStore:
    """Thread-safe persistent multi-session chat store backed by data/kam_sessions.json."""

    def __init__(self, path: str = _DEFAULT_SESSIONS_FILE):
        self._path = path
        self._lock = threading.RLock()
        self._active_id = None
        self._sessions = {}
        self._load()

    def _load(self):
        with self._lock:
            if not os.path.exists(self._path):
                self._ensure_active_session_locked()
                return
            try:
                with open(self._path, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                if isinstance(data, dict) and isinstance(data.get("sessions"), dict):
                    self._sessions = data["sessions"]
                    self._active_id = data.get("active_id")
            except Exception:
                self._sessions = {}
                self._active_id = None
            self._ensure_active_session_locked()

    def _save_locked(self):
        parent = os.path.dirname(self._path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        payload = {
            "active_id": self._active_id,
            "sessions": self._sessions,
        }
        tmp_path = f"{self._path}.{threading.get_ident()}.tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, ensure_ascii=False, indent=2)
            os.replace(tmp_path, self._path)
        except Exception:
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except OSError:
                pass

    def _ensure_active_session_locked(self):
        if self._active_id and self._active_id in self._sessions:
            return self._sessions[self._active_id]
        if self._sessions:
            latest = max(
                self._sessions.values(),
                key=lambda s: s.get("updated_at", ""),
            )
            self._active_id = latest["id"]
            return latest
        return self._create_session_locked(title="Yeni Oturum", save=False)

    def _create_session_locked(self, title: str = "Yeni Oturum", save: bool = True) -> dict:
        sid = f"sess_{uuid.uuid4().hex[:10]}"
        now = _utc_now_iso()
        session = {
            "id": sid,
            "title": (title or "Yeni Oturum").strip()[:80] or "Yeni Oturum",
            "created_at": now,
            "updated_at": now,
            "messages": [],
        }
        self._sessions[sid] = session
        self._active_id = sid
        if save:
            self._save_locked()
        return session

    @staticmethod
    def _derive_title(messages: list, llm_client=None) -> str:
        first_user = ""
        for msg in messages:
            if isinstance(msg, dict) and str(msg.get("role", "")).lower() == "user":
                first_user = str(msg.get("content", "")).strip()
                if first_user:
                    break
        if not first_user:
            return "Yeni Oturum"

        # Prefer UniversalLLMClient.generate_session_title when available
        if llm_client is not None and hasattr(llm_client, "generate_session_title"):
            try:
                gen_title = llm_client.generate_session_title(first_user)
                if isinstance(gen_title, str) and gen_title.strip():
                    return gen_title.strip()[:80]
            except Exception:
                pass

        cleaned = re.sub(r"\[EKLİ DOSYA:[^\]]*\]", "", first_user).strip()
        cleaned = re.sub(r"\s+", " ", cleaned) or first_user
        return (cleaned[:48] + "…") if len(cleaned) > 48 else cleaned

    def _summary_item(self, s: dict) -> dict:
        msgs = s.get("messages") or []
        return {
            "id": s["id"],
            "title": s.get("title", "Yeni Oturum"),
            "created_at": s.get("created_at", ""),
            "updated_at": s.get("updated_at", ""),
            "message_count": len(msgs),
        }

    def list_sessions(self) -> dict:
        with self._lock:
            self._ensure_active_session_locked()
            items = [self._summary_item(s) for s in self._sessions.values()]
            items.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
            return {
                "active_id": self._active_id,
                "sessions": items,
            }

    def create_session(self, title: str = None, llm_client=None) -> dict:
        with self._lock:
            sess = self._create_session_locked(title=title or "Yeni Oturum", save=True)
            if llm_client is not None and hasattr(llm_client, "conversation_history"):
                llm_client.conversation_history.clear()
            return {
                **self._summary_item(sess),
                "messages": [],
            }

    def get_session(self, session_id: str):
        with self._lock:
            sess = self._sessions.get(session_id)
            if sess is None:
                return None
            return {
                **self._summary_item(sess),
                "messages": copy.deepcopy(sess.get("messages") or []),
            }

    def activate_session(self, session_id: str, llm_client=None):
        with self._lock:
            sess = self._sessions.get(session_id)
            if sess is None:
                return None
            self._active_id = session_id
            msgs = copy.deepcopy(sess.get("messages") or [])
            if llm_client is not None and hasattr(llm_client, "conversation_history"):
                llm_client.conversation_history[:] = msgs
            self._save_locked()
            return {
                **self._summary_item(sess),
                "messages": msgs,
            }

    def delete_session(self, session_id: str, llm_client=None):
        with self._lock:
            if session_id not in self._sessions:
                return None
            del self._sessions[session_id]
            if self._active_id == session_id:
                self._active_id = None
                new_active = self._ensure_active_session_locked()
                if llm_client is not None and hasattr(llm_client, "conversation_history"):
                    llm_client.conversation_history[:] = copy.deepcopy(new_active.get("messages") or [])
            self._save_locked()
            return {
                "status": "ok",
                "deleted_id": session_id,
                "active_id": self._active_id,
            }

    def sync_active_session(self, llm_client=None):
        if llm_client is None or not hasattr(llm_client, "conversation_history"):
            return
        with self._lock:
            sess = self._ensure_active_session_locked()
            msgs = copy.deepcopy(list(llm_client.conversation_history))
            sess["messages"] = msgs
            sess["updated_at"] = _utc_now_iso()
            if (not sess.get("title") or sess.get("title") == "Yeni Oturum") and msgs:
                sess["title"] = self._derive_title(msgs, llm_client=llm_client)
            self._save_locked()


class _HostStatsCache:
    """Lightweight non-blocking host telemetry cache for 1.8s UI polling."""

    def __init__(self, cpu_ram_ttl: float = 1.5, gpu_ttl: float = 5.0):
        self._lock = threading.Lock()
        self._cpu_ram_ttl = cpu_ram_ttl
        self._gpu_ttl = gpu_ttl
        self._start_monotonic = time.monotonic()

        self._last_cpu_ram_ts = 0.0
        self._cpu_ram_snapshot = {
            "cpu_percent": None,
            "ram_percent": None,
            "ram_used_gb": None,
            "ram_total_gb": None,
        }

        self._last_gpu_ts = 0.0
        self._gpu_refreshing = False
        self._gpu_unavailable = False
        self._gpu_snapshot = {
            "gpu_name": None,
            "gpu_util_percent": None,
            "gpu_vram_used_mb": None,
            "gpu_vram_total_mb": None,
            "gpu_temp_c": None,
        }

        # Prime psutil's non-blocking cpu_percent counter once
        if psutil is not None:
            try:
                psutil.cpu_percent(interval=None)
            except Exception:
                pass

    def _refresh_gpu_worker(self):
        try:
            kwargs = {
                "capture_output": True,
                "text": True,
                "timeout": 2.0,
                "check": False,
            }
            if hasattr(subprocess, "CREATE_NO_WINDOW"):
                kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

            proc = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu",
                    "--format=csv,noheader,nounits",
                ],
                **kwargs,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                first_line = proc.stdout.strip().splitlines()[0]
                parts = [p.strip() for p in first_line.split(",")]
                if len(parts) >= 5:
                    def _safe_float(val):
                        try:
                            return round(float(val), 1)
                        except (ValueError, TypeError):
                            return None

                    gpu_data = {
                        "gpu_name": parts[0] or None,
                        "gpu_util_percent": _safe_float(parts[1]),
                        "gpu_vram_used_mb": _safe_float(parts[2]),
                        "gpu_vram_total_mb": _safe_float(parts[3]),
                        "gpu_temp_c": _safe_float(parts[4]),
                    }
                    with self._lock:
                        self._gpu_snapshot = gpu_data
                        self._last_gpu_ts = time.monotonic()
        except FileNotFoundError:
            with self._lock:
                self._gpu_unavailable = True
        except Exception:
            with self._lock:
                self._last_gpu_ts = time.monotonic()
        finally:
            with self._lock:
                self._gpu_refreshing = False

    def get_snapshot(self) -> dict:
        now = time.monotonic()
        trigger_gpu = False

        with self._lock:
            if psutil is not None and (now - self._last_cpu_ram_ts) >= self._cpu_ram_ttl:
                try:
                    cpu_pct = round(float(psutil.cpu_percent(interval=None)), 1)
                    vm = psutil.virtual_memory()
                    self._cpu_ram_snapshot = {
                        "cpu_percent": cpu_pct,
                        "ram_percent": round(float(vm.percent), 1),
                        "ram_used_gb": round(vm.used / (1024 ** 3), 2),
                        "ram_total_gb": round(vm.total / (1024 ** 3), 2),
                    }
                except Exception:
                    pass
                self._last_cpu_ram_ts = now

            if (
                not self._gpu_unavailable
                and not self._gpu_refreshing
                and (now - self._last_gpu_ts) >= self._gpu_ttl
            ):
                self._gpu_refreshing = True
                trigger_gpu = True

            snapshot = {
                **self._cpu_ram_snapshot,
                **self._gpu_snapshot,
                "uptime_sec": int(now - self._start_monotonic),
            }

        if trigger_gpu:
            t = threading.Thread(target=self._refresh_gpu_worker, daemon=True)
            t.start()

        return snapshot


class KamWebHandler(SimpleHTTPRequestHandler):
    engine = None
    model = None
    llm_client = None
    session_store = None
    uploads_dir = _DEFAULT_UPLOADS_DIR
    _init_lock = threading.Lock()
    _host_stats = _HostStatsCache()

    def __init__(self, *args, **kwargs):
        with KamWebHandler._init_lock:
            if KamWebHandler.engine is None:
                KamWebHandler.engine = KamEngine()
            if KamWebHandler.model is None:
                KamWebHandler.model = KamLiquidFoundationModel()
            if KamWebHandler.llm_client is None:
                KamWebHandler.llm_client = UniversalLLMClient()
            if KamWebHandler.session_store is None:
                KamWebHandler.session_store = _SessionStore(_DEFAULT_SESSIONS_FILE)
        web_dir = os.path.join(os.path.dirname(__file__), "..", "..", "web")
        super().__init__(*args, directory=web_dir, **kwargs)

    def _send_json(self, payload: dict, status: int = 200):
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(raw)
        except (*CLIENT_DISCONNECT_ERRORS, OSError):
            pass

    def _send_text(
        self,
        text: str,
        content_type: str = "text/plain; charset=utf-8",
        status: int = 200,
        extra_headers: dict = None,
    ):
        raw = text.encode("utf-8")
        try:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            if extra_headers:
                for k, v in extra_headers.items():
                    self.send_header(k, v)
            self.end_headers()
            self.wfile.write(raw)
        except (*CLIENT_DISCONNECT_ERRORS, OSError):
            pass

    def _read_json_body(self):
        raw_cl = self.headers.get("Content-Length", "0")
        try:
            content_length = int(raw_cl)
        except (ValueError, TypeError):
            return None, 400, "Invalid Content-Length header"

        if content_length < 0:
            return None, 400, "Negative Content-Length header"
        if content_length > MAX_POST_BODY_BYTES:
            return None, 413, f"Payload exceeds {MAX_POST_BODY_BYTES} bytes limit"

        if content_length == 0:
            return {}, None, None

        try:
            raw_bytes = self.rfile.read(content_length)
            post_data = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return None, 400, "Request body must be valid UTF-8"
        except (*CLIENT_DISCONNECT_ERRORS, OSError):
            return None, 400, "Connection closed while reading request body"

        if not post_data.strip():
            return {}, None, None

        try:
            parsed = json.loads(post_data)
        except json.JSONDecodeError as exc:
            return None, 400, f"Malformed JSON body: {exc.msg}"

        if not isinstance(parsed, dict):
            return None, 400, "JSON body must be an object"

        return parsed, None, None

    @staticmethod
    def _format_chat_markdown(history: list, current_model: str, active_backend: str) -> str:
        exported_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        lines = [
            "# KAM Konuşma Kaydı",
            "",
            f"- **Dışa Aktarım Zamanı:** {exported_at}",
            f"- **Aktif Model:** `{current_model}`",
            f"- **Motor:** `{active_backend}`",
            f"- **Mesaj Sayısı:** {len(history)}",
            "",
            "---",
            "",
        ]
        if not history:
            lines.append("_Henüz kayıtlı konuşma bulunmamaktadır._")
            lines.append("")
            return "\n".join(lines)

        for idx, msg in enumerate(history, start=1):
            if not isinstance(msg, dict):
                continue
            role = str(msg.get("role", "unknown")).strip().lower()
            content = str(msg.get("content", "")).strip()
            if role == "user":
                heading = f"## {idx}. Kullanıcı"
            elif role == "assistant":
                heading = f"## {idx}. KAM"
            else:
                heading = f"## {idx}. {role.capitalize()}"
            lines.append(heading)
            lines.append("")
            lines.append(content)
            lines.append("")
            lines.append("---")
            lines.append("")

        return "\n".join(lines)

    def do_GET(self):
        parsed_url = urlsplit(self.path)
        route = parsed_url.path
        query = parse_qs(parsed_url.query)

        if route == "/api/telemetry":
            entropy = KamWebHandler.engine.inference.entropy
            free_energy = 0.08 if entropy < 0.2 else (1.84 if entropy > 0.8 else 0.28)
            try:
                sc = Win32ComputerUseController.get_screen_and_cursor()
            except Exception:
                sc = {}
            tools_cnt = (
                len(KamWebHandler.llm_client.agent.list_agent_tools())
                if hasattr(KamWebHandler.llm_client, "agent")
                else 39
            )
            host_stats = KamWebHandler._host_stats.get_snapshot()
            data = {
                "active_telemetry": KamWebHandler.engine.active_telemetry,
                "entropy": entropy,
                "free_energy": free_energy,
                "npu_temp": 48.2 if entropy < 0.2 else (74.5 if entropy > 0.8 else 51.0),
                "ebpf_events_per_sec": 3420 if entropy < 0.2 else (8940 if entropy > 0.8 else 4610),
                "jit_latency_ms": 41.2,
                "chaos_detected": entropy >= 0.80,
                "active_model": KamWebHandler.llm_client.current_model,
                "backend": KamWebHandler.llm_client.active_backend,
                "lyapunov_v": round(0.5 * (entropy ** 2) + 0.15 * free_energy, 4),
                "lyapunov_stable": entropy < 0.80,
                "agent_tools_count": tools_cnt,
                "cursor_x": sc.get("cursor_x", 0),
                "cursor_y": sc.get("cursor_y", 0),
                "screen_width": sc.get("screen_width", 1920),
                "screen_height": sc.get("screen_height", 1080),
                "host_stats": host_stats,
                "cpu_percent": host_stats.get("cpu_percent"),
                "ram_percent": host_stats.get("ram_percent"),
                "ram_used_gb": host_stats.get("ram_used_gb"),
                "ram_total_gb": host_stats.get("ram_total_gb"),
                "gpu_temp_c": host_stats.get("gpu_temp_c"),
                "gpu_util_percent": host_stats.get("gpu_util_percent"),
                "gpu_vram_used_mb": host_stats.get("gpu_vram_used_mb"),
                "gpu_vram_total_mb": host_stats.get("gpu_vram_total_mb"),
            }
            self._send_json(data)
            return

        elif route == "/api/models":
            try:
                models = KamWebHandler.llm_client.list_available_models()
                if not isinstance(models, list):
                    models = []
            except Exception:
                models = [{"name": "kam-1-liquid-moe", "source": "KAM Dahili Zihin (Offline)"}]
            self._send_json({
                "models": models,
                "current_model": KamWebHandler.llm_client.current_model,
                "active_backend": KamWebHandler.llm_client.active_backend,
            })
            return

        elif route == "/api/export_chat":
            history = list(getattr(KamWebHandler.llm_client, "conversation_history", []) or [])
            md_text = self._format_chat_markdown(
                history,
                KamWebHandler.llm_client.current_model,
                KamWebHandler.llm_client.active_backend,
            )
            if query.get("format", [""])[0].lower() == "json":
                self._send_json({
                    "markdown": md_text,
                    "message_count": len(history),
                    "current_model": KamWebHandler.llm_client.current_model,
                    "active_backend": KamWebHandler.llm_client.active_backend,
                })
            else:
                self._send_text(
                    md_text,
                    content_type="text/markdown; charset=utf-8",
                    extra_headers={
                        "Content-Disposition": 'attachment; filename="kam_chat_export.md"'
                    },
                )
            return

        elif route == "/api/edge_plan":
            plan_data = {
                "tier1_micro_uav": EdgeModelOptimizer.plan_optimal_deployment(
                    EdgeHardwareBudget(ram_mb=1536, tdp_watts=8.0, npu_temp_c=55.0)
                ).__dict__,
                "tier2_tactical_siha": EdgeModelOptimizer.plan_optimal_deployment(
                    EdgeHardwareBudget(ram_mb=4096, tdp_watts=18.0, npu_temp_c=62.0)
                ).__dict__,
                "tier3_command_rtx5060": EdgeModelOptimizer.plan_optimal_deployment(
                    EdgeHardwareBudget(ram_mb=8192, tdp_watts=35.0, npu_temp_c=68.0)
                ).__dict__,
                "bitnet_b158": TernaryBitNetQuantizer.quantize_tensor([0.45, -0.41, 0.01, 0.52, -0.49]),
                "speculative_decoding": SpeculativeDecoder().verify_draft_step(
                    ["extern", '"C"', "int", "kam_entrypoint", "()"],
                    [0.92, 0.88, 0.95, 0.90, 0.94],
                    [0.94, 0.91, 0.96, 0.92, 0.95],
                ),
            }
            self._send_json(plan_data)
            return

        elif route == "/api/fleet_manifest":
            fleet_data = {
                "fleet_name": "KAM Sovereign Defense AI Fleet (Hugging Face Hub)",
                "total_models": 8,
                "fleet_size_gb": "20.83 GB GGUF + 848-Param BitNet b1.58",
                "huggingface_author": "bahattinyunus",
                "models": [
                    {
                        "key": "kam:apex",
                        "repo_id": "bahattinyunus/kam-apex-8b-gguf",
                        "url": "https://huggingface.co/bahattinyunus/kam-apex-8b-gguf",
                        "base_model": "Qwen3-8B",
                        "size": "5.20 GB",
                        "role": "Başbuğ Kam — Hibrit Düşünen Komuta Zihni, C2 & EW Orkestrasyonu",
                        "offline_gguf": "kam_apex_qwen3_8b.gguf"
                    },
                    {
                        "key": "kam:7b",
                        "repo_id": "bahattinyunus/kam-7b-gguf",
                        "url": "https://huggingface.co/bahattinyunus/kam-7b-gguf",
                        "base_model": "Qwen2.5-7B",
                        "size": "4.68 GB",
                        "role": "Ulu Kam — 16K Bağlam Duru Türkçe & Karl Friston Aktif Çıkarım",
                        "offline_gguf": "kam_7b_qwen_foundation.gguf"
                    },
                    {
                        "key": "kam:r1",
                        "repo_id": "bahattinyunus/kam-r1-gguf",
                        "url": "https://huggingface.co/bahattinyunus/kam-r1-gguf",
                        "base_model": "DeepSeek-R1-7B",
                        "size": "4.68 GB",
                        "role": "Baş Bilge — <think> CoT Akıl Yürütme, CLF/CBF Sibernetik İspat",
                        "offline_gguf": "kam_r1_deepseek_7b.gguf"
                    },
                    {
                        "key": "kam:coder",
                        "repo_id": "bahattinyunus/kam-coder-7b-gguf",
                        "url": "https://huggingface.co/bahattinyunus/kam-coder-7b-gguf",
                        "base_model": "Qwen2.5-Coder-7B",
                        "size": "4.68 GB",
                        "role": "Ulu Demirci — C++20 JIT, Linux eBPF & CUDA Başmimarı",
                        "offline_gguf": "kam_coder_7b_qwen.gguf"
                    },
                    {
                        "key": "kam:coder-nano",
                        "repo_id": "bahattinyunus/kam-coder-nano-1.5b-gguf",
                        "url": "https://huggingface.co/bahattinyunus/kam-coder-nano-1.5b-gguf",
                        "base_model": "Qwen2.5-Coder-1.5B",
                        "size": "986 MB",
                        "role": "Taktik Demirci — Uç C++20 JIT & AST Güvenli Kurtarma Kod Üreteci",
                        "offline_gguf": "qwen2.5-coder-1.5b-q4_k_m.gguf"
                    },
                    {
                        "key": "kam:r1-nano",
                        "repo_id": "bahattinyunus/kam-r1-nano-1.5b-gguf",
                        "url": "https://huggingface.co/bahattinyunus/kam-r1-nano-1.5b-gguf",
                        "base_model": "DeepSeek-R1-1.5B",
                        "size": "1.10 GB",
                        "role": "Taktik Bilge — Kısıtlı Donanım (>85°C, 1.5GB RAM) CoT Zihni",
                        "offline_gguf": "deepseek-r1-1.5b-q4_k_m.gguf"
                    },
                    {
                        "key": "kam:1.5b",
                        "repo_id": "bahattinyunus/kam-1.5b-edge-gguf",
                        "url": "https://huggingface.co/bahattinyunus/kam-1.5b-edge-gguf",
                        "base_model": "Qwen2.5-1.5B",
                        "size": "986 MB",
                        "role": "Uç Gözcü — Mikro-Uç Zihin & 3.53x Öz-Spekülatif Taslak Motoru",
                        "offline_gguf": "qwen_1.5b_lightweight_fallback.gguf"
                    },
                    {
                        "key": "kam:edge-moe-b158",
                        "repo_id": "bahattinyunus/kam-edge-moe-b158",
                        "url": "https://huggingface.co/bahattinyunus/kam-edge-moe-b158",
                        "base_model": "Tri-Hybrid RK4 Liquid-SSM MoE",
                        "size": "848 Ternary Params",
                        "role": "BitNet b1.58 {-1,0,+1} Kriz Politikası + EW Sınıflandırma + CBF Marjı",
                        "offline_gguf": "kam_edge_apex_checkpoint.json"
                    }
                ]
            }
            self._send_json(fleet_data)
            return

        elif route == "/api/lyapunov_status":
            clf = LyapunovCognitiveController()
            e = KamWebHandler.engine.inference.entropy
            state_vec = [e, e * 0.5, 0.01, 0.01, 0.0, 0.0]
            fe = 0.08 if e < 0.2 else (1.84 if e > 0.8 else 0.28)
            res = clf.evaluate_stability_step(state_vec, free_energy=fe)
            temp = 48.2 if e < 0.2 else (76.4 if e > 0.8 else 52.0)
            tta = clf.forecast_time_to_anomaly([temp - 6.0, temp - 3.0, temp - 1.0, temp], critical_threshold=85.0, sample_dt_sec=1.0)
            out = {
                "entropy": e,
                "stability": res.__dict__,
                "time_to_anomaly": tta,
            }
            self._send_json(out)
            return

        elif route == "/api/agent_tools":
            tools = KamWebHandler.llm_client.agent.list_agent_tools()
            self._send_json({
                "agent": "KAM Egemen Otonom Bilgisayar ve Sistem Ajanı",
                "total_tools": len(tools),
                "tools": tools,
            })
            return

        elif route == "/api/sessions":
            self._send_json(KamWebHandler.session_store.list_sessions())
            return

        elif route.startswith("/api/sessions/"):
            session_id = route[len("/api/sessions/"):].strip("/")
            if not _SESSION_ID_RE.match(session_id):
                self._send_json({"error": "Invalid session id"}, status=400)
                return
            sess = KamWebHandler.session_store.get_session(session_id)
            if sess is None:
                self._send_json({"error": "Session not found"}, status=404)
                return
            self._send_json(sess)
            return

        elif route == "/api/workflows":
            self._send_json({
                "workflows": list(BUILTIN_WORKFLOWS.values()),
            })
            return

        super().do_GET()

    def do_DELETE(self):
        route = urlsplit(self.path).path
        if route.startswith("/api/sessions/"):
            session_id = route[len("/api/sessions/"):].strip("/")
            if not _SESSION_ID_RE.match(session_id):
                self._send_json({"error": "Invalid session id"}, status=400)
                return
            res = KamWebHandler.session_store.delete_session(
                session_id, llm_client=KamWebHandler.llm_client
            )
            if res is None:
                self._send_json({"error": "Session not found"}, status=404)
                return
            self._send_json(res)
            return

        self._send_json({"error": "Not Found"}, status=404)

    def _run_builtin_workflow(self, workflow_id: str) -> dict:
        meta = BUILTIN_WORKFLOWS[workflow_id]
        agent = KamWebHandler.llm_client.agent
        t0 = time.perf_counter()
        steps_out = []

        def _exec_step(tool_name: str, args: dict):
            try:
                res = agent.execute_tool(tool_name, args)
                status = res.get("status", "success") if isinstance(res, dict) else "success"
            except Exception as exc:
                res = {"status": "error", "error": str(exc)}
                status = "error"
            steps_out.append({"tool": tool_name, "arguments": args, "status": status, "result": res})
            return res

        if workflow_id == "system_health_audit":
            _exec_step("get_real_system_telemetry", {})
            _exec_step("manage_processes", {"action": "list", "limit": 8})
            host_snap = KamWebHandler._host_stats.get_snapshot()
            summary = (
                f"### {meta['name']}\n"
                f"- **CPU:** {host_snap.get('cpu_percent')}% | "
                f"**RAM:** {host_snap.get('ram_used_gb')}/{host_snap.get('ram_total_gb')} GB "
                f"({host_snap.get('ram_percent')}%)\n"
                f"- **GPU:** {host_snap.get('gpu_name') or 'N/A'} "
                f"({host_snap.get('gpu_temp_c') or 'N/A'}°C)\n"
                f"- **Tamamlanan Adım:** {len(steps_out)}"
            )
        elif workflow_id == "repo_code_audit":
            _exec_step("list_directory", {"path": "."})
            _exec_step("analyze_codebase", {"path": "python/kam"})
            summary = (
                f"### {meta['name']}\n"
                f"- Çalışma dizini ve `python/kam` çekirdek modülleri tarandı.\n"
                f"- **Tamamlanan Adım:** {len(steps_out)}"
            )
        else:  # network_security_scan
            _exec_step("network_probe", {"action": "status"})
            _exec_step("network_probe", {"action": "ping", "target": "127.0.0.1"})
            summary = (
                f"### {meta['name']}\n"
                f"- Yerel ağ arayüzleri, dinleme portları ve loopback (127.0.0.1) erişilebilirliği denetlendi.\n"
                f"- **Tamamlanan Adım:** {len(steps_out)}"
            )

        return {
            "status": "ok",
            "workflow": workflow_id,
            "name": meta["name"],
            "description": meta["description"],
            "duration_ms": round((time.perf_counter() - t0) * 1000.0, 2),
            "steps": steps_out,
            "summary": summary,
        }

    def do_POST(self):
        route = urlsplit(self.path).path
        body, err_status, err_msg = self._read_json_body()
        if err_status is not None:
            self._send_json({"error": err_msg}, status=err_status)
            return

        if route == "/api/chat":
            raw_msg = body.get("message", "")
            if not isinstance(raw_msg, str):
                self._send_json({"error": "'message' must be a string"}, status=400)
                return
            message = raw_msg.strip()
            reply, code = self.process_chat(message)
            KamWebHandler.session_store.sync_active_session(KamWebHandler.llm_client)
            self._send_json({"reply": reply, "code": code})
            return

        elif route == "/api/chat/stream":
            raw_msg = body.get("message", "")
            if not isinstance(raw_msg, str):
                self._send_json({"error": "'message' must be a string"}, status=400)
                return
            message = raw_msg.strip()
            if not message:
                self._send_json({"error": "'message' must be a non-empty string"}, status=400)
                return

            try:
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream; charset=utf-8")
                self.send_header("Cache-Control", "no-cache, no-transform")
                self.send_header("X-Accel-Buffering", "no")
                self.send_header("Connection", "close")
                self.close_connection = True
                self.end_headers()
            except (*CLIENT_DISCONNECT_ERRORS, OSError):
                return

            abort_event = threading.Event()
            gen = None
            disconnected = False

            try:
                stream_fn = KamWebHandler.llm_client.generate_stream
                try:
                    sig = inspect.signature(stream_fn)
                    if "abort_event" in sig.parameters:
                        gen = stream_fn(message, abort_event=abort_event)
                    else:
                        gen = stream_fn(message)
                except (TypeError, ValueError):
                    gen = stream_fn(message)

                for token in gen:
                    if abort_event.is_set():
                        break
                    data = json.dumps({"token": token}, ensure_ascii=False)
                    try:
                        self.wfile.write(f"data: {data}\n\n".encode("utf-8"))
                        self.wfile.flush()
                    except (*CLIENT_DISCONNECT_ERRORS, OSError):
                        disconnected = True
                        abort_event.set()
                        break

                if not disconnected and not abort_event.is_set():
                    try:
                        self.wfile.write(b'data: {"done": true}\n\n')
                        self.wfile.flush()
                    except (*CLIENT_DISCONNECT_ERRORS, OSError):
                        disconnected = True
            except (*CLIENT_DISCONNECT_ERRORS, OSError):
                disconnected = True
                abort_event.set()
            except Exception as exc:
                if not disconnected:
                    err_payload = json.dumps({"error": str(exc), "done": True}, ensure_ascii=False)
                    try:
                        self.wfile.write(f"data: {err_payload}\n\n".encode("utf-8"))
                        self.wfile.flush()
                    except (*CLIENT_DISCONNECT_ERRORS, OSError):
                        pass
            finally:
                abort_event.set()
                if gen is not None and hasattr(gen, "close"):
                    try:
                        gen.close()
                    except BaseException:
                        pass
                try:
                    KamWebHandler.session_store.sync_active_session(KamWebHandler.llm_client)
                except Exception:
                    pass
            return

        elif route == "/api/clear_chat":
            if KamWebHandler.llm_client:
                KamWebHandler.llm_client.conversation_history.clear()
            KamWebHandler.session_store.sync_active_session(KamWebHandler.llm_client)
            self._send_json({"status": "ok"})
            return

        elif route == "/api/sessions":
            title = body.get("title")
            if title is not None and not isinstance(title, str):
                self._send_json({"error": "'title' must be a string"}, status=400)
                return
            sess = KamWebHandler.session_store.create_session(
                title=title, llm_client=KamWebHandler.llm_client
            )
            self._send_json({
                "status": "ok",
                "active_id": sess["id"],
                "session": sess,
                **sess,
            })
            return

        elif route.startswith("/api/sessions/") and route.endswith("/activate"):
            session_id = route[len("/api/sessions/"):-len("/activate")].strip("/")
            if not _SESSION_ID_RE.match(session_id):
                self._send_json({"error": "Invalid session id"}, status=400)
                return
            sess = KamWebHandler.session_store.activate_session(
                session_id, llm_client=KamWebHandler.llm_client
            )
            if sess is None:
                self._send_json({"error": "Session not found"}, status=404)
                return
            self._send_json({
                "status": "ok",
                "active_id": sess["id"],
                "session": sess,
                **sess,
            })
            return

        elif route == "/api/upload":
            raw_filename = body.get("filename")
            content = body.get("content")
            safe_name, name_err = _sanitize_upload_filename(raw_filename)
            if name_err is not None:
                self._send_json({"error": name_err}, status=400)
                return
            if not isinstance(content, str):
                self._send_json({"error": "'content' must be a string"}, status=400)
                return

            encoded = content.encode("utf-8")
            if len(encoded) > MAX_UPLOAD_BYTES:
                self._send_json(
                    {"error": f"File content exceeds {MAX_UPLOAD_BYTES} bytes (2 MB) limit"},
                    status=413,
                )
                return

            uploads_dir = os.path.realpath(KamWebHandler.uploads_dir)
            os.makedirs(uploads_dir, exist_ok=True)
            dest_path = os.path.realpath(os.path.join(uploads_dir, safe_name))
            if not dest_path.startswith(uploads_dir + os.sep):
                self._send_json({"error": "Invalid upload destination path"}, status=400)
                return

            try:
                with open(dest_path, "wb") as fh:
                    fh.write(encoded)
            except OSError as exc:
                self._send_json({"error": f"Failed to save uploaded file: {exc}"}, status=500)
                return

            rel_path = f"data/uploads/{safe_name}"
            self._send_json({
                "status": "ok",
                "filename": safe_name,
                "path": rel_path,
                "size_bytes": len(encoded),
                "preview": content[:300],
            })
            return

        elif route == "/api/workflows":
            wf_id = body.get("workflow") or body.get("workflow_id") or body.get("id")
            if not isinstance(wf_id, str) or not wf_id.strip():
                self._send_json({"error": "'workflow' must be a non-empty string"}, status=400)
                return
            wf_id = wf_id.strip()
            if wf_id not in BUILTIN_WORKFLOWS:
                self._send_json(
                    {"error": f"Unknown workflow '{wf_id}'", "available": list(BUILTIN_WORKFLOWS.keys())},
                    status=404,
                )
                return
            result = self._run_builtin_workflow(wf_id)
            self._send_json(result)
            return

        elif route == "/api/config":
            # API Key veya Model Değiştirme (strict validation)
            has_gemini = "gemini_key" in body
            has_model = "model" in body
            clear_gemini = body.get("clear_gemini_key") is True
            if not has_gemini and not has_model and not clear_gemini:
                self._send_json(
                    {"error": "At least one of 'model' or 'gemini_key' must be provided"},
                    status=400,
                )
                return

            gemini_key = body.get("gemini_key")
            selected_model = body.get("model")

            if has_gemini and gemini_key is not None and not isinstance(gemini_key, str):
                self._send_json({"error": "'gemini_key' must be a string"}, status=400)
                return

            if has_model and selected_model is not None:
                if not isinstance(selected_model, str):
                    self._send_json({"error": "'model' must be a string"}, status=400)
                    return
                selected_model = selected_model.strip()
                if not selected_model or len(selected_model) > 128 or any(ch in selected_model for ch in ("\r", "\n", "\x00")):
                    self._send_json({"error": "'model' must be a valid non-empty model identifier"}, status=400)
                    return

            if clear_gemini:
                KamWebHandler.llm_client.gemini_api_key = ""
                KamWebHandler.llm_client.active_backend = (
                    "ollama" if KamWebHandler.llm_client.check_ollama_alive() else "local_fallback"
                )
            elif has_gemini and gemini_key is not None:
                cleaned_key = gemini_key.strip()
                # Do not silently wipe an existing key if client sends blank "" on save
                if cleaned_key:
                    KamWebHandler.llm_client.gemini_api_key = cleaned_key
                    KamWebHandler.llm_client.active_backend = "gemini"
                    KamWebHandler.llm_client.current_model = "gemini-1.5-flash"

            if selected_model:
                KamWebHandler.llm_client.current_model = selected_model
                KamWebHandler.llm_client._model_initialized = True
                if "gemini" in selected_model.lower():
                    KamWebHandler.llm_client.active_backend = "gemini"
                elif selected_model == "kam-1-liquid-moe":
                    KamWebHandler.llm_client.active_backend = "local_fallback"
                else:
                    KamWebHandler.llm_client.active_backend = "ollama"

            self._send_json({
                "status": "ok",
                "active_backend": KamWebHandler.llm_client.active_backend,
                "current_model": KamWebHandler.llm_client.current_model,
            })
            return

        elif route == "/api/crisis":
            c_type = body.get("crisis_type", "")
            if not isinstance(c_type, str):
                self._send_json({"error": "'crisis_type' must be a string"}, status=400)
                return
            reply, code = self.process_crisis(c_type)
            self._send_json({"message": reply, "code": code})
            return

        elif route == "/api/tactical_route":
            try:
                tx = float(body.get("target_x_km", 50.0))
                ty = float(body.get("target_y_km", 0.0))
                segs = int(body.get("num_segments", 10))
            except (ValueError, TypeError) as exc:
                self._send_json({"error": f"Invalid numeric parameter: {exc}"}, status=400)
                return
            planner = TacticalRoutePlanner3D()
            route_data = planner.plan_stealth_trajectory(target_xyz=(tx, ty, 580.0), num_segments=segs)
            self._send_json(route_data)
            return

        elif route == "/api/ew_radar":
            try:
                pdw = PulseDescriptorWord(
                    rf_ghz=float(body.get("rf_ghz", 9.2)),
                    pri_us=float(body.get("pri_us", 420.0)),
                    pw_us=float(body.get("pw_us", 1.8)),
                    aoa_deg=float(body.get("aoa_deg", 32.0)),
                    chirp_bw_mhz=float(body.get("chirp_bw_mhz", 45.0)),
                    agility_score=float(body.get("agility_score", 0.1)),
                )
            except (ValueError, TypeError) as exc:
                self._send_json({"error": f"Invalid numeric parameter: {exc}"}, status=400)
                return
            classifier = CognitiveEwEmitterClassifier()
            res = classifier.classify_pdw_burst(pdw)
            code = CodeMutator.generate_ew_drfm_fallback()
            self._send_json({"classification": res, "countermeasure_code": code})
            return

        elif route == "/api/c2_intent":
            try:
                intent = str(body.get("commander_intent", "Sektör-4 S-400 bataryasını körelt ve vadi taarruzu icra et"))
                tx = float(body.get("target_x_km", 50.0))
                ty = float(body.get("target_y_km", 0.0))
            except (ValueError, TypeError) as exc:
                self._send_json({"error": f"Invalid parameter: {exc}"}, status=400)
                return
            orchestrator = IntentToTaskOrchestrator()
            plan = orchestrator.decompose_and_allocate(intent, target_x_km=tx, target_y_km=ty)
            code = CodeMutator.generate_c2_dag_fallback()
            self._send_json({"c2_plan": plan, "executor_code": code})
            return

        elif route == "/api/safety_shield":
            try:
                cmd = FlightControlCommand(
                    target_altitude_agl_m=float(body.get("target_altitude_agl_m", 12.0)),
                    airspeed_mps=float(body.get("airspeed_mps", 15.0)),
                    bank_angle_deg=float(body.get("bank_angle_deg", 68.0)),
                    battery_pct=float(body.get("battery_pct", 14.0)),
                )
            except (ValueError, TypeError) as exc:
                self._send_json({"error": f"Invalid numeric parameter: {exc}"}, status=400)
                return
            shield_res = NeuroSymbolicSafetyShield.verify_and_project(cmd)
            code = CodeMutator.generate_cbf_safety_shield_fallback()
            self._send_json({"shield_result": shield_res, "cbf_code": code})
            return

        elif route == "/api/lyapunov_status":
            clf = LyapunovCognitiveController()
            e = KamWebHandler.engine.inference.entropy
            try:
                state_vec = body.get("state_vector", [e, e * 0.5, 0.01, 0.01, 0.0, 0.0])
                fe = float(body.get("free_energy", 0.08 if e < 0.2 else (1.84 if e > 0.8 else 0.28)))
                temp = float(body.get("temperature", 48.2 if e < 0.2 else (76.4 if e > 0.8 else 52.0)))
            except (ValueError, TypeError) as exc:
                self._send_json({"error": f"Invalid numeric parameter: {exc}"}, status=400)
                return
            res = clf.evaluate_stability_step(state_vec, free_energy=fe)
            tta = clf.forecast_time_to_anomaly([temp - 6.0, temp - 3.0, temp - 1.0, temp], critical_threshold=85.0, sample_dt_sec=1.0)
            self._send_json({"entropy": e, "stability": res.__dict__, "time_to_anomaly": tta})
            return

        elif route == "/api/bft_swarm":
            inject_traitor = bool(body.get("inject_byzantine_traitor", True))
            beliefs = [
                SwarmNodeBelief("Alpha-1", [0.82, 0.10, 0.05, 0.03], pqc_nonce=101),
                SwarmNodeBelief("Bravo-2", [0.80, 0.11, 0.06, 0.03], pqc_nonce=102),
                SwarmNodeBelief(
                    "Charlie-3",
                    [0.02, 0.04, 0.12, 0.82] if inject_traitor else [0.81, 0.10, 0.06, 0.03],
                    pqc_nonce=103,
                ),
                SwarmNodeBelief("Delta-4", [0.81, 0.09, 0.06, 0.04], pqc_nonce=104),
            ]
            bft_res = ByzantinePqcSwarmGuard.filter_byzantine_and_fuse(beliefs)
            code = CodeMutator.generate_byzantine_pqc_fallback()
            self._send_json({"bft_result": bft_res, "pqc_code": code})
            return

        elif route == "/api/trn_localize":
            try:
                tx = float(body.get("true_x_km", 24.5))
                ty = float(body.get("true_y_km", -3.2))
                dx = float(body.get("drifted_ins_x_km", 25.25))
                dy = float(body.get("drifted_ins_y_km", -2.70))
            except (ValueError, TypeError) as exc:
                self._send_json({"error": f"Invalid numeric parameter: {exc}"}, status=400)
                return
            trn_res = TerrainRelativeNavigator.match_terrain_profile(
                true_x_km=tx, true_y_km=ty, drifted_ins_x_km=dx, drifted_ins_y_km=dy
            )
            code = CodeMutator.generate_trn_terrain_lock_fallback()
            self._send_json({"trn_result": trn_res, "trn_code": code})
            return

        elif route == "/api/actuator_reconfig":
            try:
                jam_idx = int(body.get("jammed_actuator_index", 0))
                jam_ang = float(body.get("jammed_angle_rad", 0.22))
            except (ValueError, TypeError) as exc:
                self._send_json({"error": f"Invalid numeric parameter: {exc}"}, status=400)
                return
            act_res = ActuatorFaultReconfigurator.reconfigure_control_allocation(
                stuck_deflections_rad={jam_idx: jam_ang}
            )
            code = CodeMutator.generate_actuator_reconfig_fallback()
            self._send_json({"actuator_result": act_res, "mixer_code": code})
            return

        elif route == "/api/fso_link":
            try:
                params = FsoLinkParameters(
                    distance_km=float(body.get("distance_km", 4.5)),
                    visibility_km=float(body.get("visibility_km", 12.0)),
                    pointing_jitter_urad=float(body.get("pointing_jitter_urad", 35.0)),
                )
            except (ValueError, TypeError) as exc:
                self._send_json({"error": f"Invalid numeric parameter: {exc}"}, status=400)
                return
            fso_res = CovertFsoLaserTransceiver.evaluate_covert_fso_link(params)
            code = CodeMutator.generate_fso_laser_mesh_fallback()
            self._send_json({"fso_result": fso_res, "fso_code": code})
            return

        elif route == "/api/ecc_scrub":
            try:
                seu_bit = int(body.get("injected_seu_bit", 19))
                tmr_corrupt = bool(body.get("inject_tmr_bank_corruption", True))
            except (ValueError, TypeError) as exc:
                self._send_json({"error": f"Invalid parameter: {exc}"}, status=400)
                return
            ecc_res = RadiationHardenedMemoryScrubber.scrub_bitnet_weights_with_tmr(
                injected_seu_bit=seu_bit,
                inject_tmr_bank_corruption=tmr_corrupt,
            )
            code = CodeMutator.generate_radiation_tmr_scrubber_fallback()
            self._send_json({"ecc_result": ecc_res, "ecc_code": code})
            return

        elif route == "/api/hji_evasion":
            try:
                state = MissileEngagementState(
                    missile_range_m=float(body.get("missile_range_m", 2850.0)),
                    closing_velocity_mps=float(body.get("closing_velocity_mps", 980.0)),
                    evader_max_g=float(body.get("evader_max_g", 9.0)),
                )
            except (ValueError, TypeError) as exc:
                self._send_json({"error": f"Invalid numeric parameter: {exc}"}, status=400)
                return
            hji_res = DifferentialGameMissileEvasion.solve_hji_evasion_maneuver(state)
            code = CodeMutator.generate_hji_missile_evasion_fallback()
            self._send_json({"hji_result": hji_res, "hji_code": code})
            return

        elif route == "/api/agent_execute":
            tool_name = body.get("tool", "get_real_system_telemetry")
            tool_args = body.get("arguments", {})
            if not isinstance(tool_name, str) or not tool_name.strip():
                self._send_json({"error": "'tool' must be a non-empty string"}, status=400)
                return
            if not isinstance(tool_args, dict):
                self._send_json({"error": "'arguments' must be a JSON object"}, status=400)
                return
            res = KamWebHandler.llm_client.agent.execute_tool(tool_name.strip(), tool_args)
            self._send_json({"tool": tool_name.strip(), "result": res})
            return

        elif route == "/api/reset":
            KamWebHandler.engine.active_telemetry = "UART-2 (Primary)"
            KamWebHandler.engine.inference.reset_equilibrium(0.03)
            self._send_json({"status": "ok"})
            return

        self._send_json({"error": "Not Found"}, status=404)

    def process_chat(self, prompt: str):
        p_lower = prompt.lower()

        # Sadece açık donanım arızası ve telemetri kopması varsa donanım durumunu güncelle
        code_snippet = None
        if "uart" in p_lower and ("kop" in p_lower or "onar" in p_lower or "kesil" in p_lower):
            KamWebHandler.engine.active_telemetry = "SDR 868MHz (Yedek Hat Aktif)"
            KamWebHandler.engine.inference.reset_equilibrium(0.15)
            code_snippet = CodeMutator.generate_sdr_fallback()
        elif "termal" in p_lower and ("92" in p_lower or "asimi" in p_lower):
            code_snippet = CodeMutator.generate_thermal_fallback()

        # Doğrudan Gerçek LLM Motoruna Sor (Qwen2.5 / DeepSeek / Gemini)
        llm_reply = KamWebHandler.llm_client.generate(prompt)

        return llm_reply, code_snippet

    def process_crisis(self, c_type: str):
        if c_type == "uav_uart_cut":
            KamWebHandler.engine.inference.trigger_anomaly()
            KamWebHandler.engine.active_telemetry = "SDR-868MHz (FHSS Fallback)"
            return (
                "Kırılan Bağ Tespit Edildi: UART-2 telemetri hattı koptu, varyasyonel entropi %89 seviyesine yükseldi. "
                "Bilişsel KAM otonom onarım protokolünü devreye aldı: SDR 868MHz frekans atlamalı kurtarma köprüsü bellekte JIT derlendi ve görev hattı kesintisiz devralındı.",
                CodeMutator.generate_sdr_fallback()
            )
        elif c_type == "ew_jamming":
            KamWebHandler.engine.active_telemetry = "SDR-433MHz (Anti-Jamming Hopping)"
            return (
                "Elektronik Harp Karıştırması: Spektrumda -95 dBm geniş bant gürültü tespit edildi. "
                "FHSS bilişsel radyo topolojisi 433 MHz temiz frekans bandına sıçradı, gürültü tabanı aşılarak dirlik korundu.",
                CodeMutator.generate_ew_fhss_fallback()
            )
        elif c_type == "thermal_spike":
            return (
                "Termal Eşik Aşımı: NPU sıcaklığı 92.4°C seviyesine ulaştı. "
                "Linux eBPF termal kancası devreye girdi: Model dinamik INT4-AWQ kuantizasyon moduna çekildi, güç tüketimi 45W -> 14.5W seviyesine indirildi.",
                CodeMutator.generate_thermal_fallback()
            )
        elif c_type == "can_spoof":
            return (
                "Veriyolu Anomalisi: CAN-0 hattına yetkisiz çerçeve (ID 0x1BA) enjeksiyonu tespit edildi. "
                "Bellek-içi eBPF güvenlik filtresi (can_firewall_filter.cpp) derlenerek sahte paketler mikrosaniyede karantinaya alındı.",
                CodeMutator.generate_can_firewall_fallback()
            )
        elif c_type == "gnss_spoof":
            KamWebHandler.engine.active_telemetry = "IMU + Optik Akış (GNSS İzole)"
            return (
                "GNSS/GPS Spoofing Tespit Edildi: Mahalanobis yenilik kapısı (d_M > 16.0) aşıldı. "
                "Sahte uydu koordinatları reddedilerek gnss_optical_flow_ekf.cpp bellekte JIT derlendi; 200 Hz Optik Akış + Barometre EKF ölü-hesaplama moduna geçildi.",
                CodeMutator.generate_gnss_spoof_fallback()
            )
        elif c_type == "swarm_loss":
            KamWebHandler.engine.active_telemetry = "SDR-868.9MHz (Bravo-2 Lider)"
            return (
                "Sürü Lideri Kaybı: Alpha-1 düğümüyle bağlantı koptu. Dağıtık Markov Battaniyesi serbest enerji konsensüsü "
                "en düşük F=0.14 nats değerine sahip Bravo-2 birimini yeni lider seçti; swarm_raft_leader_handover.cpp sıcak-yama olarak bağlandı.",
                CodeMutator.generate_swarm_handover_fallback()
            )
        elif c_type == "ew_radar_threat":
            KamWebHandler.engine.inference.trigger_anomaly()
            KamWebHandler.engine.active_telemetry = "DRFM Aldatıcı Karıştırıcı (17.4GHz)"
            return (
                "Bilişsel Radar Tehdidi Tespit Edildi: 17.4 GHz LPI çevik darbe dizisi algılandı. "
                "Çevrimiçi darbe kelimesi (PDW) sınıflandırıcısı tehdidi öğrendi; ew_drfm_responder.cpp JIT derlenerek 8 adet tutarlı sahte hedef üretildi ve spektruma basıldı.",
                CodeMutator.generate_ew_drfm_fallback()
            )
        elif c_type == "cbf_envelope_breach":
            KamWebHandler.engine.inference.trigger_anomaly()
            KamWebHandler.engine.active_telemetry = "CBF Kalkanı (RTL Devrede)"
            return (
                "Uçuş Güvenlik Zarfı İhlali: DARPA ANSR & CBF Nöro-Sembolik Kalkanı h(x) < 0 bariyer ihlali saptadı. "
                "İrtifa < 30m, stall sürati < 22 m/s ve batarya <%18 ihlalleri engellenerek cbf_safety_shield.cpp ile komuta güvenli sınıra izdüşürüldü ve Eve Dönüş (RTL) devreye alındı.",
                CodeMutator.generate_cbf_safety_shield_fallback()
            )
        elif c_type == "intent_c2_mission":
            KamWebHandler.engine.active_telemetry = "C2 Çoklu Alan Ağı (DAG Aktif)"
            return (
                "Komutan Niyeti Göreve Bölündü: 'S-400 radarını körelt ve vadi taarruzu icra et' emri DAG grafiğine çevrildi. "
                "c2_task_executor.cpp üzerinden Sungur-EW-1, Kizilelma-Strike-2, Bayraktar-TB3 ve ANKA unsurlarına bağımlılık sırasıyla otonom tahsis yapıldı.",
                CodeMutator.generate_c2_dag_fallback()
            )
        elif c_type == "byzantine_swarm_attack":
            KamWebHandler.engine.inference.trigger_anomaly()
            KamWebHandler.engine.active_telemetry = "BFT-PQC-Mesh (ML-KEM-768)"
            return (
                "Bizans Sürü İhaneti Tespit Edildi: Charlie-3 düğümünden sahte Markov Battaniyesi inancı (D_JS = 0.474 > 0.18) yayıldı. "
                "byzantine_pqc_guard.cpp bellekte JIT derlendi; hain düğüm oylamadan izole edildi ve ML-KEM-768 (Kyber q=3329) kuantum-dirençli oturum anahtarları yenilendi.",
                CodeMutator.generate_byzantine_pqc_fallback()
            )
        elif c_type == "trn_terrain_lock":
            KamWebHandler.engine.active_telemetry = "TRN-TERCOM (0W Pasif Kilit)"
            return (
                "Uzun Menzil INS Kayması Düzeltildi: 901.4 metrelik ölü-hesaplama (dead-reckoning) kayması, "
                "trn_tercom_navigator.cpp ile 0W RF yayımıyla (stealth) Sayısal Yükselti Modeli (DEM) üzerinde eşleştirilerek %99.47 oranında sönümlendi.",
                CodeMutator.generate_trn_terrain_lock_fallback()
            )
        elif c_type == "kinetic_actuator_jam":
            KamWebHandler.engine.inference.trigger_anomaly()
            KamWebHandler.engine.active_telemetry = "PseudoInverse-Mixer (Yedekli)"
            return (
                "Kinetik Kanatçık Hasarı: Sol Elevon (LEFT_ELEVON) +0.22 rad açıda mekanik olarak sıkıştı. "
                "actuator_mixer_reconfig.cpp bellekte JIT derlenerek Ağırlıklı Sözde-Ters (Weighted Moore-Penrose Pseudo-Inverse) matrisiyle momentler sağlam V-kuyruk ve itki vektörlemesine dağıtıldı.",
                CodeMutator.generate_actuator_reconfig_fallback()
            )
        elif c_type == "emcon_fso_switch":
            KamWebHandler.engine.active_telemetry = "1550nm FSO Lazer (0W RF)"
            return (
                "EMCON-Sıfır Radyo Sessizliği: Düşman SIGINT/ELINT yön bulucu (DF) dizisi saptandı, tüm RF vericileri 0.0W seviyesine kapatıldı. "
                "fso_laser_mesh_link.cpp bellekte JIT derlenerek 1550nm SWIR MEMS lazer köprüsü üzerinden %0 yakalanma olasılığıyla (POI=0) 685 Mbps sürü bağı kuruldu.",
                CodeMutator.generate_fso_laser_mesh_fallback()
            )
        elif c_type == "radiation_seu_bitflip":
            KamWebHandler.engine.inference.trigger_anomaly()
            KamWebHandler.engine.active_telemetry = "SECDED-TMR-Scrubber (ECC)"
            return (
                "Kozmik Işın / EMP Bellek Bit-Flip (SEU/MBU) Tespit Edildi: Linux eBPF EDAC kancası Bit-19 tersinmesi ve Bank-B ağırlık bozulması yakaladı. "
                "radiation_tmr_scrubber.cpp bellekte JIT derlenerek Hamming(72,64) SECDED ve 3-Bank TMR çoğunluk oylamasıyla BitNet b1.58 ağırlıkları %100 bit-kesinliğinde onarıldı.",
                CodeMutator.generate_radiation_tmr_scrubber_fallback()
            )
        elif c_type == "sam_missile_lock":
            KamWebHandler.engine.inference.trigger_anomaly()
            KamWebHandler.engine.active_telemetry = "HJI-9G-Evasion + DRFM-CrossEye"
            return (
                "Hipersonik SAM Füze Kilidi Algılandı: Terminal safhada (R=2850m, V_c=980 m/s) oransal seyrüsefer (PN) güdümlü füze yaklaşıyor! "
                "hji_evasion_maneuver.cpp bellekte JIT derlenerek Hamilton-Jacobi-Isaacs (HJI) eyer noktası 9.0G dikgen fıçı tonosu ve DRFM Cross-Eye açı aldatmasıyla ıskalama mesafesi 18m ölümcül yarıçapın dışına (>75m) çıkarıldı.",
                CodeMutator.generate_hji_missile_evasion_fallback()
            )
        return "Bilinmeyen kriz tipi", None

def run_gui(host: str = "127.0.0.1", port: int = 8080, open_browser: bool = True):
    KamWebHandler.engine = KamEngine()
    KamWebHandler.model = KamLiquidFoundationModel()
    KamWebHandler.llm_client = UniversalLLMClient()

    server = ThreadingHTTPServer((host, port), KamWebHandler)
    url = f"http://{host}:{port}"

    print("=" * 68)
    print("  KAM BILISSEL VE OTONOM SISTEM KOMUTA MERKEZI (WEB GUI v2.5)")
    print("=" * 68)
    print(f"  * Yerel Arayuz Adresi : {url}")
    print(f"  * Aktif LLM Motoru    : {KamWebHandler.llm_client.current_model} ({KamWebHandler.llm_client.active_backend})")
    print("  * Tum telemetri ve kriz simulasyonlari web arayuzunde aktiftir.")
    print("=" * 68 + "\n")

    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[KAM] Web sunucusu güvenle kapatıldı.")
        server.server_close()
