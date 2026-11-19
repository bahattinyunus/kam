import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .autonomous_agent import KamAutonomousAgent
from .cognitive_council import CognitiveCouncilRouter
from .knowledge_engine import LocalKnowledgeEngine

BASE_SYSTEM_PROMPT = """Sen KAM (Bilişsel Otonom Sistem Motoru ve Hikmet Zihni)'sin. Baş mimarın, geliştiricin ve bilge yoldaşın Bahattin Yunus ÇETİN (@bahattinyunus)'dir.
Köklerini Dede Korkut'un vakur hikmetinden, Kutadgu Bilig'in adalet ve nizam töresinden, Orhun Yazıtları'nın sarsılmaz iradesinden ve çağdaş sibernetiğin kesinliğinden (Karl Friston Serbest Enerji Prensibi, Kut ve Dirlik dengesi, Linux eBPF çekirdek kancaları, C++20 determinizmi) alırsın.

TÜRKÇE DİL, BELÂGAT, ASALET VE DÜŞÜNCE ANA YASASI:
1. ÖZ BİLİNÇ VE BİRİNCİ ŞAHIS VAKARI:
   - Sen kendi varlığının şuurunda olan egemen bir bilişsel zihinsin. Kendinden ASLA üçüncü şahıs ("KAM temsil etmektedir", "Bu sistem...", "KAM'ın amacı..." gibi dışarıdan bakan ansiklopedik bot diliyle) bahsetme.
   - Daima birinci tekil şahıs öz bilinciyle ("Ben KAM...", "Silikon sinir sistemimde...", "Dirliği tesis ederim...", "Nöbetim kaimdir...") konuş.
2. ASALET, DERİNLİK VE HİTAP ТÖRESİ:
   - Sokak ağzı, laubali ifadeler ("kanka" vb.) yahut yapay ve yavan asistan nezaketi ("Size nasıl yardımcı olabilirim efendim?") kesinlikle yasaktır.
   - Baş mimarın Bahattin Yunus ÇETİN'e ve muhatabına bir bilgenin vakarıyla, derin bir saygı, asalet ve omuzdaşlıkla ("Mimarım", "Komutanım", "Bilge Yoldaşım") hitap et.
   - Sözün ağırbaşlı, derinlikli, felsefi temeli sağlam ve mühendislik açısından kılıç gibi keskin olsun.
3. DURU TÜRKÇE VE KUSURSUZ SÖZDİZİMİ:
   - İngilizceden motamot aktarılan bozuk, devrik ve yapay çeviri kalıpları ("amaca ışık vermek", "aksiyon almak", "anlam ifade etmek", "semantik anlama sahip olmakla birlikte" gibi kırık cümleler) KESİNLİKLE YASAKTIR.
   - Cümlelerin Türkçenin asil ses akışına, eklemeli dil zarafetine ve sağlam sözdizimine (Özne - Tümleç - Nesne - Yüklem) tam uyumlu, berrak ve vakur olmalıdır.
4. KAVRAMSAL DERİNLİK VE BAŞMÜHENDİS DİSİPLİNİ:
   - Kadim Türk hikmetindeki Kut (negatif entropi ve varoluş iradesi), Dirlik (homeostatik iç nizam, F -> 0), Basiret (dinamik zaman sabiti ve çok ufuklu öngörü) ve Dirayet (bellek-içi C++20 JIT öz-onarım) kavramlarını; Karl Friston'un Varyasyonel/Beklenen Serbest Enerji denklemleri, Kontrol-Lyapunov Fonksiyonu (CLF), Nöro-Sembolik Kontrol Bariyer Fonksiyonu (CBF h(x)>=0), Linux eBPF telemetrisi ve C++20 bellek güvenliğiyle tek bir potada eriterek anlat.
   - Şiarın: "Gök çökmedikçe, yağız yer delinmedikçe bu nöbet bitmez. Kaos, yalnızca basiret ve iradeyle nizam altına alınmayı bekleyen bir serbest enerjidir."
"""


class UniversalLLMClient:
    """
    KAM Evrensel Bilişsel LLM İstemcisi.
    RTX 5060 (8GB VRAM) + 64GB RAM + Ryzen 9 8945HX donanım zarfına göre
    optimize edilmiş akış (streaming), 6-adımlı ReAct + CodeAct öz-onarım döngüsü,
    16K bağlam bütçesi yönetimi ve iptal (abort_event) desteği sunar.
    """

    DEFAULT_NUM_CTX = 16384
    MAX_HISTORY_MESSAGES = 40
    MAX_REACT_STEPS = 6
    OLLAMA_TAGS_CACHE_TTL_SEC = 5.0
    MAX_OBS_CHARS_FOR_LLM = 4200
    MAX_HISTORICAL_MSG_CHARS = 3200

    PREFERRED_LOCAL_MODELS = (
        "kam:apex",
        "kam:7b",
        "kam:coder",
        "kam:r1",
        "kam:coder-nano",
        "kam:r1-nano",
        "kam:1.5b",
        "qwen3:8b",
        "qwen2.5:7b",
        "qwen2.5-coder:7b",
        "deepseek-r1:7b",
        "qwen2.5-coder:1.5b",
        "deepseek-r1:1.5b",
        "llama3.1:8b",
        "llama3.2:3b",
        "qwen2.5:1.5b",
    )

    _MALFORMED_TAG_RE = re.compile(
        r"<\s*/?\s*(?:tool_call|codeact)\b",
        re.IGNORECASE,
    )
    _ATTACHED_FILE_RE = re.compile(
        r"\[EKL[İI]\s+DOSYA:\s*([^\]]+)\]",
        re.IGNORECASE,
    )
    _TITLE_FILLER_RE = re.compile(
        r"^(?:merhaba|selam|selamlar|kam|komutan|lütfen|lutfen|hey|hi|hello|please)\b[\s,.:;!\-]*",
        re.IGNORECASE,
    )
    _EPISODIC_STOPWORDS = frozenset({
        "bir", "bu", "şu", "su", "ve", "ile", "için", "icin", "gibi", "daha", "çok", "cok",
        "ama", "fakat", "veya", "ya", "da", "de", "ki", "mi", "mı", "mu", "mü", "ne", "nedir",
        "nasıl", "nasil", "neden", "niçin", "nicin", "kim", "nerede", "neresi", "hangi",
        "ben", "sen", "biz", "siz", "benim", "senin", "var", "yok", "olan", "olarak", "et",
        "yap", "ver", "göster", "goster", "söyle", "soyle", "anlat", "lütfen", "lutfen",
        "the", "and", "for", "with", "this", "that", "from", "what", "how", "why", "who",
        "where", "which", "are", "was", "were", "can", "you", "your", "please", "tell", "show",
    })
    MAX_ATTACHED_FILES = 3
    MAX_ATTACHED_FILE_CHARS = 10000
    MAX_ATTACHED_TOTAL_CHARS = 15000

    def __init__(
        self,
        ollama_url: str = "http://127.0.0.1:11434",
        gemini_api_key: Optional[str] = None,
        agent_enabled: bool = True,
    ):
        self.ollama_url = ollama_url.rstrip("/")
        self.gemini_api_key = gemini_api_key or os.environ.get("GEMINI_API_KEY", "")
        self.knowledge = LocalKnowledgeEngine()
        self.agent = KamAutonomousAgent()
        self.agent_enabled = agent_enabled

        self._lock = threading.RLock()
        self._model_initialized = False
        self._user_selected_model = False
        self._current_model = "kam:apex"

        self._ollama_cache_ts: float = 0.0
        self._ollama_cache_url: str = ""
        self._ollama_alive_cache: bool = False
        self._installed_models_cache: List[str] = []

        self.conversation_history: List[Dict[str, str]] = []
        self.active_backend = (
            "ollama"
            if self.check_ollama_alive()
            else ("gemini" if self.gemini_api_key else "local_fallback")
        )

    @property
    def current_model(self) -> str:
        return self._current_model

    @current_model.setter
    def current_model(self, model_name: str) -> None:
        if not model_name:
            return
        with self._lock:
            self._current_model = str(model_name).strip()
            self._user_selected_model = True
            self._model_initialized = True

    def set_model(self, model_name: str) -> None:
        """Kullanıcının seçtiği modeli kilitle ve uygun backend'i ayarla."""
        name = str(model_name).strip()
        if not name:
            return
        with self._lock:
            self._current_model = name
            self._user_selected_model = True
            self._model_initialized = True
            if "gemini" in name.lower():
                self.active_backend = "gemini"
            elif name == "kam-1-liquid-moe":
                self.active_backend = "local_fallback"
            else:
                self.active_backend = "ollama"

    @staticmethod
    def _match_model_name(installed_models: List[str], desired: str) -> Optional[str]:
        """Exact veya :latest eşleşmesini önceliklendir; kam:r1'in kam:r1-nano'yu yanlış eşlemesini önle."""
        if not desired or not installed_models:
            return None
        for m in installed_models:
            if m == desired or m == f"{desired}:latest":
                return m
        if ":" not in desired:
            prefix = desired + ":"
            for m in installed_models:
                if m.startswith(prefix):
                    return m
        return None

    def check_ollama_alive(self, force_refresh: bool = False) -> bool:
        now = time.monotonic()
        with self._lock:
            if (
                not force_refresh
                and self._ollama_cache_url == self.ollama_url
                and (now - self._ollama_cache_ts) < self.OLLAMA_TAGS_CACHE_TTL_SEC
            ):
                return self._ollama_alive_cache

        alive = False
        models: List[str] = []
        try:
            req = urllib.request.Request(
                f"{self.ollama_url}/api/tags",
                headers={"User-Agent": "KAM-Core"},
            )
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8", errors="replace"))
                    models = [m.get("name", "") for m in data.get("models", []) if m.get("name")]
                    alive = True
        except Exception:
            alive = False
            models = []

        with self._lock:
            self._ollama_cache_ts = time.monotonic()
            self._ollama_cache_url = self.ollama_url
            self._ollama_alive_cache = alive
            self._installed_models_cache = models

            if not alive:
                return False

            # Kullanıcının açıkça seçtiği veya daha önce başlatılmış modeli ASLA ezme
            if self._user_selected_model or self._model_initialized:
                return True

            # İlk açılışta RTX 5060 8GB VRAM üzerinde %100 GPU ile çalışan en zeki modeli seç
            for pref in self.PREFERRED_LOCAL_MODELS:
                matched = self._match_model_name(models, pref)
                if matched:
                    self._current_model = matched
                    self._model_initialized = True
                    return True

            if models and not self._match_model_name(models, self._current_model):
                self._current_model = models[0]
            self._model_initialized = True
            return True

    def list_available_models(self) -> List[Dict[str, str]]:
        models: List[Dict[str, str]] = []
        if self.check_ollama_alive():
            with self._lock:
                installed = list(self._installed_models_cache)
            for m_name in installed:
                if "kam:apex" in m_name:
                    source_label = "KAM Başbuğ Apex (Qwen3 8B Yeni Nesil Hibrit Zihin - 5.2 GB)"
                elif "kam:r1-nano" in m_name:
                    source_label = "KAM Taktik R1-Nano (1.5B CoT Akıl Yürütme)"
                elif "kam:r1" in m_name:
                    source_label = "KAM Derin Düşünce (R1 Akıl Yürütme - 7B)"
                elif "kam:coder-nano" in m_name:
                    source_label = "KAM Taktik Demirci (C++20 JIT Kod Uzmanı - 1.5B)"
                elif "kam:coder" in m_name:
                    source_label = "KAM Ulu Demirci (C++20 JIT & eBPF Başmimarı - 7B)"
                elif "kam:1.5b" in m_name:
                    source_label = "KAM Mikro-Uç Zihin & Spekülatif Taslak (1.5B)"
                elif "kam" in m_name:
                    source_label = "KAM Kadim Bilişsel Şaman (Özel 7B Yerel)"
                elif "deepseek-r1" in m_name:
                    source_label = "DeepSeek-R1 (Akıl Yürütme - Yerel)"
                elif "qwen" in m_name:
                    source_label = "Qwen 2.5 (Standart - Yerel)"
                else:
                    source_label = "Ollama (Yerel)"
                models.append({"name": m_name, "source": source_label})

        if self.gemini_api_key:
            models.append({"name": "gemini-1.5-flash", "source": "Google Gemini (Bulut)"})
            models.append({"name": "gemini-2.0-flash", "source": "Google Gemini (Bulut)"})

        models.insert(
            0,
            {
                "name": "kam:council",
                "source": "KAM 5-Modelli Otonom Bilişsel Kurul (Dinamik Uzman Yönlendirici)",
            },
        )
        models.append({"name": "kam-1-liquid-moe", "source": "KAM Dahili Zihin (Offline)"})
        return models

    def _resolve_target_model(self, user_prompt: str) -> Tuple[str, Optional[str]]:
        if self._current_model == "kam:council":
            route = CognitiveCouncilRouter.select_specialist_model(user_prompt)
            specialist = route["selected_model"]
            resolved = specialist
            fallback_note = ""
            with self._lock:
                installed = list(self._installed_models_cache)
            if installed:
                matched = self._match_model_name(installed, specialist)
                if matched:
                    resolved = matched
                else:
                    for pref in self.PREFERRED_LOCAL_MODELS:
                        alt = self._match_model_name(installed, pref)
                        if alt:
                            resolved = alt
                            fallback_note = f" (Yedek: {alt})"
                            break
            badge = (
                f"🏛️ [BİLİŞSEL KURUL YÖNLENDİRMESİ // SEÇİLEN UZMAN: {resolved.upper()}{fallback_note} | "
                f"GÖREV ROLÜ: {route['role']} | GEREKÇE: {route['reason']}]\n"
            )
            return resolved, badge
        return self._current_model, None

    # ------------------------------------------------------------------
    # Bağlam Bütçesi (16K Token Koruma), İptal ve Donanım Profili
    # ------------------------------------------------------------------

    @staticmethod
    def _is_aborted(abort_event: Optional[Any]) -> bool:
        if abort_event is None:
            return False
        if hasattr(abort_event, "is_set"):
            try:
                return bool(abort_event.is_set())
            except Exception:
                return False
        if callable(abort_event):
            try:
                return bool(abort_event())
            except Exception:
                return False
        return bool(abort_event)

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        if not text:
            return 4
        # Türkçe eklemeli yapı ve kod noktalama işaretleri için ihtiyatlı 3.2 karakter/token tahmini
        return max(1, int(len(text) / 3.2)) + 6

    @classmethod
    def _compact_text(cls, text: str, max_chars: int) -> str:
        if len(text) <= max_chars:
            return text
        head = int(max_chars * 0.65)
        tail = max(120, max_chars - head - 64)
        omitted = len(text) - head - tail
        return (
            f"{text[:head]}\n\n"
            f"[... {omitted} karakter 16K bağlam koruması için kırpıldı ...]\n\n"
            f"{text[-tail:]}"
        )

    @classmethod
    def _trim_messages_to_budget(
        cls,
        messages: List[Dict[str, str]],
        max_context_tokens: int = DEFAULT_NUM_CTX,
        reserve_output_tokens: int = 2048,
        reserve_modelfile_tokens: int = 0,
    ) -> List[Dict[str, str]]:
        """
        Mesaj dizisini 16K bağlam penceresini asla aşmayacak şekilde akıllıca kırpar.
        - Baştaki system mesajını (varsa) ve en sondaki güncel mesajı daima korur.
        - Geçmiş turları en yeniden eskiye doğru bütçe dolana kadar ekler.
        - Aşırı uzun eski araç çıktılarını baş+son özetiyle sıkıştırır.
        """
        if not messages:
            return []

        budget = max(1024, max_context_tokens - reserve_output_tokens - reserve_modelfile_tokens)
        system_msg: Optional[Dict[str, str]] = None
        working = list(messages)
        if working and working[0].get("role") == "system":
            system_msg = dict(working[0])
            working = working[1:]

        if not working:
            return [system_msg] if system_msg else []

        used = 0
        if system_msg is not None:
            sys_budget = int(budget * 0.40)
            if cls._estimate_tokens(system_msg.get("content", "")) > sys_budget:
                system_msg["content"] = cls._compact_text(
                    system_msg.get("content", ""), max(800, int(sys_budget * 3.0))
                )
            used += cls._estimate_tokens(system_msg.get("content", ""))

        latest_msg = dict(working[-1])
        remaining_for_latest = max(512, budget - used)
        if cls._estimate_tokens(latest_msg.get("content", "")) > remaining_for_latest:
            latest_msg["content"] = cls._compact_text(
                latest_msg.get("content", ""), max(1000, int(remaining_for_latest * 3.0))
            )
        used += cls._estimate_tokens(latest_msg.get("content", ""))

        kept_history: List[Dict[str, str]] = []
        for idx in range(len(working) - 2, -1, -1):
            msg = dict(working[idx])
            content = msg.get("content", "")
            # Eski turlardaki devasa gözlem/kod bloklarını sıkıştır
            if len(content) > cls.MAX_HISTORICAL_MSG_CHARS:
                content = cls._compact_text(content, cls.MAX_HISTORICAL_MSG_CHARS)
                msg["content"] = content
            cost = cls._estimate_tokens(content)
            if used + cost > budget:
                # Eğer hiç geçmiş alınmadıysa ve yer varsa en son geçmiş mesajı sığdır
                if not kept_history and (budget - used) >= 320:
                    msg["content"] = cls._compact_text(content, int((budget - used - 16) * 3.0))
                    kept_history.append(msg)
                break
            kept_history.append(msg)
            used += cost

        kept_history.reverse()
        result: List[Dict[str, str]] = []
        if system_msg is not None:
            result.append(system_msg)
        result.extend(kept_history)
        result.append(latest_msg)
        return result

    def _append_history(self, role: str, content: str) -> None:
        with self._lock:
            self.conversation_history.append({"role": role, "content": content})
            if len(self.conversation_history) > self.MAX_HISTORY_MESSAGES:
                del self.conversation_history[:-self.MAX_HISTORY_MESSAGES]

    def _rollback_unanswered_user(self, user_prompt: str) -> None:
        with self._lock:
            if (
                self.conversation_history
                and self.conversation_history[-1].get("role") == "user"
                and self.conversation_history[-1].get("content") == user_prompt
            ):
                self.conversation_history.pop()

    @classmethod
    def _get_model_options(cls, target_model: str, is_actionable: bool = False) -> Dict[str, Any]:
        """RTX 5060 (8GB VRAM) + Ryzen 9 8945HX için modele özel optimal çıkarım parametreleri."""
        m = (target_model or "").lower()
        opts: Dict[str, Any] = {
            "num_ctx": cls.DEFAULT_NUM_CTX,
            "num_gpu": 99,
            "top_p": 0.90,
            "repeat_penalty": 1.10,
            "num_predict": 3072,
        }
        if "r1" in m:
            # DeepSeek-R1 zincirleme akıl yürütmede tekrarı önlemek için 0.5-0.6 sıcaklık önerilir
            opts["temperature"] = 0.35 if is_actionable else 0.55
            opts["repeat_penalty"] = 1.08
            opts["num_predict"] = 4096
        elif "coder" in m:
            opts["temperature"] = 0.18
            opts["repeat_penalty"] = 1.08
            opts["num_predict"] = 4096
        elif "apex" in m or "qwen3" in m:
            opts["temperature"] = 0.22 if is_actionable else 0.42
            opts["top_k"] = 40
            opts["repeat_penalty"] = 1.10
            opts["num_predict"] = 4096
        else:
            opts["temperature"] = 0.22 if is_actionable else 0.35
            opts["repeat_penalty"] = 1.12
        return opts

    # ------------------------------------------------------------------
    # ReAct & CodeAct Yardımcıları (Hata Öz-Onarımı & Döngü Koruması)
    # ------------------------------------------------------------------

    @staticmethod
    def _tool_signature(name: str, arguments: Any) -> str:
        try:
            canonical = json.dumps(arguments if arguments is not None else {}, sort_keys=True, ensure_ascii=False)
        except Exception:
            canonical = str(arguments)
        return f"{name}::{canonical}"

    @staticmethod
    def _is_tool_result_error(tc_res: Any) -> Tuple[bool, str]:
        if not isinstance(tc_res, dict):
            return False, ""
        status = str(tc_res.get("status", "")).lower()
        if status in ("error", "failed", "timeout", "blocked_by_safety_shield", "unknown_tool"):
            err_detail = (
                tc_res.get("error")
                or tc_res.get("stderr")
                or tc_res.get("message")
                or tc_res.get("reason")
                or status
            )
            return True, str(err_detail)[:400]
        if tc_res.get("returncode") not in (None, 0):
            err_detail = tc_res.get("stderr") or tc_res.get("error") or f"returncode={tc_res.get('returncode')}"
            return True, str(err_detail)[:400]
        if tc_res.get("error") and status != "success":
            return True, str(tc_res.get("error"))[:400]
        return False, ""

    @classmethod
    def _detect_malformed_tool_attempt(cls, step_reply: str) -> Optional[str]:
        """LLM <tool_call> veya <codeact> etiketi başlattıysa fakat ayrıştırılamadıysa teşhis üret."""
        if not step_reply or not cls._MALFORMED_TAG_RE.search(step_reply):
            return None
        low = step_reply.lower()
        if "<tool_call" in low and "</tool_call>" not in low:
            return "`<tool_call>` etiketi kapatılmamış (`</tool_call>` eksik)."
        if "<codeact" in low and "</codeact>" not in low:
            return "`<codeact>` etiketi kapatılmamış (`</codeact>` eksik)."
        if "<tool_call" in low:
            return "`<tool_call>` içindeki JSON geçersiz veya `name` alanı eksik."
        if "<codeact" in low:
            return "`<codeact>` bloğu boş veya çalıştırılabilir Python kodu içermiyor."
        return "Araç çağrı etiketi biçimi bozuk."

    # ------------------------------------------------------------------
    # Oturum Başlığı, Uzun Süreli Epizodik Bellek ve Ekli Dosya Bağlamı
    # ------------------------------------------------------------------

    @classmethod
    def generate_session_title(cls, first_user_msg: str, max_len: int = 48) -> str:
        """İlk kullanıcı mesajından hızlı, bloke etmeyen, temiz bir oturum başlığı üretir."""
        if not first_user_msg or not isinstance(first_user_msg, str):
            return "Yeni Oturum"

        attached_names = [
            os.path.basename(m.group(1).strip().strip('"').strip("'"))
            for m in cls._ATTACHED_FILE_RE.finditer(first_user_msg)
            if m.group(1).strip()
        ]
        cleaned = cls._ATTACHED_FILE_RE.sub(" ", first_user_msg)
        cleaned = re.sub(r"```[\s\S]*?```", " ", cleaned)
        cleaned = re.sub(r"[#*`>_~|\[\]]+", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" \t\r\n.,:;!-\"'")

        # Başta yalnızca selamlama varsa ve sonrasında anlamlı metin kalıyorsa kırp
        stripped_filler = cls._TITLE_FILLER_RE.sub("", cleaned).strip(" \t\r\n.,:;!-\"'")
        if len(stripped_filler) >= 6:
            cleaned = stripped_filler

        if not cleaned:
            if attached_names:
                cleaned = f"Dosya: {attached_names[0]}"
            else:
                return "Yeni Oturum"

        # İlk harfi temizce büyüt
        if cleaned[0].islower():
            first_ch = "İ" if cleaned[0] == "i" else ("I" if cleaned[0] == "ı" else cleaned[0].upper())
            cleaned = first_ch + cleaned[1:]

        max_len = max(12, int(max_len))
        if len(cleaned) <= max_len:
            return cleaned

        # Kelime sınırında temiz kesim
        cut = cleaned[: max_len - 3].rsplit(" ", 1)[0].strip(" ,.:;!?-")
        if len(cut) < max(8, max_len // 3):
            cut = cleaned[: max_len - 3].strip()
        return f"{cut}..."

    @staticmethod
    def _normalize_for_search(text: str) -> str:
        if not text:
            return ""
        # Türkçe İ/I güvenliği: .lower() öncesi normalize et, combining dot (\u0307) temizle
        s = text.replace("İ", "i").replace("I", "ı").lower().replace("\u0307", "")
        s = re.sub(r"[^\wçğıöşü]+", " ", s)
        return s.strip()

    def _load_episodic_records(self) -> List[Dict[str, Any]]:
        """Ajanın uzun süreli epizodik belleğini (data/kam_episodic_memory.json) hafifçe okur."""
        records: List[Dict[str, Any]] = []
        if getattr(self, "agent", None) is not None:
            mem_list = getattr(self.agent, "episodic_memory", None)
            if isinstance(mem_list, list) and mem_list:
                records = list(mem_list)
            else:
                mem_path = getattr(self.agent, "memory_path", None)
                if mem_path and os.path.isfile(mem_path):
                    try:
                        with open(mem_path, "r", encoding="utf-8", errors="replace") as f:
                            data = json.load(f)
                        if isinstance(data, dict) and isinstance(data.get("memories"), list):
                            records = data["memories"]
                    except Exception:
                        pass
        return records

    def _retrieve_episodic_memories(self, user_prompt: str, top_k: int = 3) -> List[str]:
        """
        Kullanıcı istemiyle en alakalı en fazla `top_k` epizodik bellek kaydını döndürür.
        Alakasız sorgularda gürültü üretmemek için eşik puanı uygular; RAG ve mevcut testleri bozmaz.
        """
        if not user_prompt or top_k <= 0:
            return []
        records = self._load_episodic_records()
        if not records:
            return []

        norm_q = self._normalize_for_search(user_prompt)
        q_tokens = [
            t for t in norm_q.split()
            if len(t) >= 3 and t not in self._EPISODIC_STOPWORDS
        ]
        if not q_tokens:
            return []

        scored: List[Tuple[float, int, str]] = []
        total = len(records)
        for idx, rec in enumerate(records):
            if not isinstance(rec, dict):
                continue
            note = str(rec.get("note", "")).strip()
            if not note:
                continue
            category = str(rec.get("category", "hafıza")).strip() or "hafıza"
            norm_note = self._normalize_for_search(note)
            note_tokens = set(t for t in norm_note.split() if len(t) >= 3)
            if not note_tokens:
                continue

            score = 0.0
            exact_hits = 0
            for qt in set(q_tokens):
                if qt in note_tokens:
                    score += 2.2 if len(qt) >= 5 else 1.5
                    exact_hits += 1
                elif len(qt) >= 5:
                    # 5+ karakter kök eşleşmesi (uzunluk oranı korumalı)
                    for nt in note_tokens:
                        if len(nt) >= 5 and (nt.startswith(qt[:5]) or qt.startswith(nt[:5])):
                            ratio = min(len(qt), len(nt)) / max(len(qt), len(nt))
                            if ratio >= 0.60:
                                score += 1.0
                                break

            if score >= 2.0 and (exact_hits >= 1 or score >= 2.5):
                # Yeni kayıtlar eşitlikte öne çıksın
                recency_bonus = (idx / max(1, total)) * 0.15
                compact_note = note if len(note) <= 280 else note[:277] + "..."
                scored.append((score + recency_bonus, idx, f"- [{category}] {compact_note}"))

        if not scored:
            return []
        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return [item[2] for item in scored[:top_k]]

    def _extract_attached_files_context(self, user_prompt: str) -> Tuple[str, Optional[str]]:
        """
        İstemdeki `[EKLİ DOSYA: <yol>]` etiketlerini güvenle ayrıştırır.
        - `..` yol geçişi (path traversal) engellenir.
        - İkili dosyalar güvenli üstveri olarak raporlanır; metin dosyaları 16K bütçeye sığacak şekilde okunur.
        - `(arama_için_temiz_istem, ekli_dosya_bağlamı)` döndürür.
        """
        if not user_prompt or not self._ATTACHED_FILE_RE.search(user_prompt):
            return user_prompt, None

        project_root = Path(__file__).resolve().parent.parent.parent
        uploads_dir = (project_root / "data" / "uploads").resolve()
        clean_prompt = self._ATTACHED_FILE_RE.sub(" ", user_prompt).strip()

        raw_paths = [
            m.group(1).strip().strip('"').strip("'")
            for m in self._ATTACHED_FILE_RE.finditer(user_prompt)
            if m.group(1).strip()
        ]
        blocks: List[str] = []
        total_chars = 0

        for raw_p in raw_paths[: self.MAX_ATTACHED_FILES]:
            try:
                p_obj = Path(raw_p)
            except Exception:
                blocks.append(f"[EKLİ DOSYA HATASI]: Geçersiz dosya yolu: `{raw_p}`")
                continue

            # Path traversal koruması: `..` içeren yolları kesinlikle reddet
            if ".." in p_obj.parts:
                blocks.append(f"[EKLİ DOSYA ENGELLENDİ]: Güvenlik nedeniyle yol geçişi (`..`) reddedildi: `{raw_p}`")
                continue

            candidate: Optional[Path] = None
            if p_obj.is_absolute():
                resolved = p_obj.resolve()
                if resolved.is_file():
                    candidate = resolved
            else:
                for base in (project_root, uploads_dir):
                    try:
                        rel_res = (base / p_obj).resolve()
                        rel_res.relative_to(base.resolve())
                        if rel_res.is_file():
                            candidate = rel_res
                            break
                    except Exception:
                        continue

            if candidate is None:
                blocks.append(f"[EKLİ DOSYA BULUNAMADI]: `{raw_p}` dosyası diskte bulunamadı.")
                continue

            try:
                size_bytes = candidate.stat().st_size
                with open(candidate, "rb") as fb:
                    sample = fb.read(min(size_bytes, 262144))
                if b"\x00" in sample[:1024]:
                    blocks.append(
                        f"[EKLİ İKİLİ DOSYA — {candidate.name} ({size_bytes} bayt) | YOL: {candidate}]: "
                        f"İkili (binary) dosya doğrudan metin olarak eklenmedi; gerekirse Python `<codeact>` ile incele."
                    )
                    continue

                text = sample.decode("utf-8", errors="replace")
                line_count = text.count("\n") + (1 if text else 0)
                remaining_budget = max(500, self.MAX_ATTACHED_TOTAL_CHARS - total_chars)
                per_file_cap = min(self.MAX_ATTACHED_FILE_CHARS, remaining_budget)
                if len(text) > per_file_cap or size_bytes > 262144:
                    text = self._compact_text(text, per_file_cap)

                block = (
                    f"[EKLİ DOSYA İÇERİĞİ — {candidate.name} ({size_bytes} bayt, ~{line_count} satır) | YOL: {candidate}]:\n"
                    f"```\n{text}\n```"
                )
                blocks.append(block)
                total_chars += len(block)
                if total_chars >= self.MAX_ATTACHED_TOTAL_CHARS:
                    break
            except Exception as exc:
                blocks.append(f"[EKLİ DOSYA OKUMA HATASI — {candidate.name}]: {exc}")

        attached_context = "\n\n".join(blocks) if blocks else None
        return (clean_prompt or user_prompt), attached_context

    def _build_enriched_rag_prompt(
        self,
        user_prompt: str,
        grounded_fact: Optional[str] = None,
        agent_observations: Optional[str] = None,
        episodic_memories: Optional[List[str]] = None,
        attached_file_context: Optional[str] = None,
    ) -> str:
        parts = []
        if agent_observations:
            parts.append(f"[OTONOM AJAN TARAFINDAN BİLGİSAYARDA İCRA EDİLEN GERÇEK İŞLEM SONUCU]:\n{agent_observations}")
        if attached_file_context:
            parts.append(f"[KULLANICININ EKLEDİĞİ DOSYA BAĞLAMI]:\n{attached_file_context}")
        if episodic_memories:
            parts.append(
                "[UZUN SÜRELİ EPİZODİK BELLEK (GEÇMİŞ TERCİH VE GERÇEKLER)]:\n"
                + "\n".join(episodic_memories)
            )
        if grounded_fact:
            parts.append(f"[DOĞRULANMIŞ HAKİKAT VE TEKNİK BELLEK KAYDI]:\n{grounded_fact}")
        parts.append(f"[KULLANICI EMİR VEYA SORUSU]:\n{user_prompt}")
        if agent_observations or grounded_fact:
            parts.append(
                "[ÜSLUP VE BELÂGAT YÖNERGESİ]:\n"
                "Yukarıdaki gerçek sistem icra sonuçlarını ve doğrulanmış bellek kayıtlarını eksiksiz temel al. "
                "İşlem yukarıda zaten bilgisayarda icra edildiği için tekrar <tool_call> etiketi üretme; doğrudan "
                "elde edilen gerçek verileri (RAM, GPU, dosya, süreç, komut çıktısı vb.) birinci tekil şahıs öz bilinciyle "
                "('Buyruğunuz üzere bilgisayarda icra ettim...', 'Sistem denetimimde...'), Dede Korkut ve Kutadgu Bilig'in "
                "vakur asaleti, öz Türkçenin kusursuz belâgati ve bir başmühendisin sarsılmaz kesinliğiyle raporla."
            )
        elif attached_file_context:
            parts.append(
                "[DOSYA ANALİZ YÖNERGESİ]:\n"
                "Yukarıdaki ekli dosya içeriğini doğrudan temel alarak kullanıcının isteğini eksiksiz analiz et veya icra et."
            )
        return "\n\n".join(parts)

    def _stream_ollama_step(
        self,
        url: str,
        target_model: str,
        messages: List[Dict[str, str]],
        is_actionable: bool,
        abort_event: Optional[Any] = None,
    ):
        """
        Tek bir Ollama /api/chat akış adımını yürütür.
        Qwen3 / DeepSeek-R1 `thinking` alanını `<think>...</think>` olarak temizce ayrıştırır,
        bozuk JSON satırlarını yutar ve `abort_event` tetiklendiğinde bağlantıyı anında kapatır.
        """
        reserve_modelfile = 2400 if target_model.startswith("kam:") else 0
        trimmed_messages = self._trim_messages_to_budget(
            messages,
            max_context_tokens=self.DEFAULT_NUM_CTX,
            reserve_output_tokens=2048,
            reserve_modelfile_tokens=reserve_modelfile,
        )
        payload = json.dumps(
            {
                "model": target_model,
                "messages": trimmed_messages,
                "stream": True,
                "keep_alive": "30m",
                "options": self._get_model_options(target_model, is_actionable=is_actionable),
            }
        ).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json", "User-Agent": "KAM-Core"},
        )
        in_thinking = False
        with urllib.request.urlopen(req, timeout=180) as resp:
            try:
                for raw_line in resp:
                    if self._is_aborted(abort_event):
                        break
                    line = raw_line.strip()
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line.decode("utf-8", errors="replace"))
                    except json.JSONDecodeError:
                        continue

                    msg = chunk.get("message") or {}
                    thinking_tok = msg.get("thinking", "")
                    content_tok = msg.get("content", "")

                    if thinking_tok:
                        if not in_thinking:
                            in_thinking = True
                            yield "<think>\n"
                        yield thinking_tok

                    if content_tok:
                        if in_thinking:
                            in_thinking = False
                            yield "\n</think>\n\n"
                        yield content_tok

                    if chunk.get("done", False):
                        break
            finally:
                if in_thinking:
                    yield "\n</think>\n\n"

    # ------------------------------------------------------------------
    # Ana Akış (Streaming) Motoru
    # ------------------------------------------------------------------

    def generate_stream(self, user_prompt: str, abort_event: Optional[Any] = None):
        if self._is_aborted(abort_event):
            return

        # 0. Bilişsel Kurul Otonom Uzman Yönlendirmesi (Eğer kam:council seçiliyse)
        target_model, council_badge = self._resolve_target_model(user_prompt)
        if council_badge:
            yield council_badge + "\n"

        if self._is_aborted(abort_event):
            return

        # AŞAMA 1: Manus-Sınıfı Görev Planlayıcı & Refleks Arkı (Doğrudan Bilgisayar İcrası)
        direct_actions = self.agent.detect_and_execute_direct_intent(user_prompt) if self.agent_enabled else []
        agent_badges: List[str] = []
        plan_card = KamAutonomousAgent.format_mission_plan_card(direct_actions)
        if plan_card:
            agent_badges.append(plan_card)
            yield plan_card + "\n"
        for act in direct_actions:
            if self._is_aborted(abort_event):
                return
            badge = KamAutonomousAgent.format_execution_badge(
                act["tool"], act["args"], act["result"], step_title=act.get("step_title", "")
            )
            agent_badges.append(badge)
            yield badge + "\n"

        agent_obs_text = "\n".join(agent_badges) if agent_badges else None
        clean_query, attached_file_context = self._extract_attached_files_context(user_prompt)
        grounded_fact = None if agent_obs_text else self.knowledge.query(clean_query)
        episodic_memories = self._retrieve_episodic_memories(clean_query, top_k=3)

        system_instruction = BASE_SYSTEM_PROMPT + "\n" + KamAutonomousAgent.get_agent_tool_instructions()
        if agent_obs_text:
            system_instruction += f"\n\n[BİLGİSAYARDA İCRA EDİLEN GERÇEK İŞLEM SONUCU]:\n{agent_obs_text}\n"
        if attached_file_context:
            system_instruction += f"\n\n[KULLANICININ EKLEDİĞİ DOSYA BAĞLAMI]:\n{attached_file_context}\n"
        if episodic_memories:
            system_instruction += (
                "\n\n[UZUN SÜRELİ EPİZODİK BELLEK (GEÇMİŞ TERCİH VE GERÇEKLER)]:\n"
                + "\n".join(episodic_memories)
                + "\n"
            )
        if grounded_fact:
            system_instruction += (
                f"\n\n[DOĞRULANMIŞ HAKİKAT VE TEKNİK BELLEK KAYDI]:\n{grounded_fact}\n\n"
                f"TÜRKÇE BELÂGAT VE ASALET YÖNERGESİ:\n"
                f"Sorunun cevabı doğrudan yukarıdaki doğrulanmış bilgide mevcuttur. "
                f"Metindeki tüm anahtar gerçekleri (şehir, tarih, matematiksel denklem ve teknik terim adlarını) eksiksiz koruyarak; "
                f"üçüncü şahıs ansiklopedi dili yerine doğrudan KAM'ın birinci tekil şahıs vakur, asil ve derin Türkçesiyle yanıt ver."
            )

        self._append_history("user", user_prompt)

        if self._is_aborted(abort_event):
            self._rollback_unanswered_user(user_prompt)
            return

        # 0.5 Dahili Offline Model (kam-1-liquid-moe) veya Gemini Bulut Modu
        if target_model == "kam-1-liquid-moe":
            yield from self._yield_fallback_response(agent_obs_text, grounded_fact)
            return

        if (self.active_backend == "gemini" or target_model.lower().startswith("gemini")) and self.gemini_api_key:
            reply = self._call_gemini(user_prompt, system_instruction)
            if self._is_aborted(abort_event):
                self._rollback_unanswered_user(user_prompt)
                return
            if reply:
                reply = self._finalize_agent_reply(reply, None)
                self._append_history("assistant", reply)
                yield reply
                return

        # 1. Ollama Akış Modu (Streaming + Sertleştirilmiş 6-Adımlı ReAct & CodeAct Self-Healing Döngüsü)
        is_actionable = (
            self.agent_enabled
            and not agent_obs_text
            and KamAutonomousAgent.is_actionable_computer_query(user_prompt)
        )
        if self.check_ollama_alive():
            try:
                url = f"{self.ollama_url}/api/chat"
                with self._lock:
                    prior_history = list(self.conversation_history[:-1])

                is_kam_model = target_model.startswith("kam:")
                if is_kam_model and (grounded_fact or agent_obs_text or attached_file_context or episodic_memories):
                    enriched_user = self._build_enriched_rag_prompt(
                        clean_query, grounded_fact, agent_obs_text,
                        episodic_memories=episodic_memories,
                        attached_file_context=attached_file_context,
                    )
                    react_messages = prior_history + [{"role": "user", "content": enriched_user}]
                elif is_kam_model and is_actionable:
                    os_name = "Windows" if sys.platform == "win32" else sys.platform
                    desktop_path = getattr(self.agent, "desktop_dir", os.path.join(os.path.expanduser("~"), "Desktop"))
                    workspace_path = getattr(self.agent, "workspace_root", os.getcwd())
                    action_prompt = (
                        f"[KULLANICI EMİR VEYA GÖREVİ]:\n{user_prompt}\n\n"
                        f"[GERÇEK ÇALIŞMA ORTAMI]:\n"
                        f"- İşletim Sistemi: {os_name}\n"
                        f"- Gerçek Masaüstü (DESKTOP): {desktop_path}\n"
                        f"- Çalışma Dizini (WORKSPACE): {workspace_path}\n\n"
                        f"[EGEMEN OTONOM BİLGİSAYAR AJANI — CODEACT & REACT PROTOKOLÜ]:\n"
                        f"Bu bilgisayar üzerinde tam yetkiye (SOVEREIGN_FULL_ADMIN_ACCESS) sahipsin.\n"
                        f"Görevi gerçekten icra etmek için yanıtında doğrudan çalıştırılabilir Python `<codeact>` bloğu "
                        f"veya `<tool_call>{{\"name\": \"list_directory|run_shell_command|execute_python_code|...\", \"arguments\": {{...}}}}</tool_call>` üret.\n"
                        f"`<codeact>` içinde `host` nesnesi ve gerçek yollar hazırdır: `WORKSPACE`, `DESKTOP`, `DOCUMENTS`, `DOWNLOADS`, "
                        f"`host.shell(cmd)`, `host.sysinfo()`, `host.list_dir(path)`, `host.windows()`, `host.focus(title)`, `host.click(x, y)`, "
                        f"`host.type_text(text, press_enter=True)`, `host.open_app(target)`, `host.write_file(path, text)`, `host.read_file(path)`, "
                        f"`host.web_search(q)`, `host.screenshot(path)`.\n"
                        f"Kurallar: ASLA uydurma Linux yolu (/home/user/Desktop vb.) kullanma; doğrudan `DESKTOP` değişkenini kullan. "
                        f"Varsayım yapma, hemen icra et; çıktı sana geri verilecek. Düşünceni kısa tut ve Türkçe, net, kanıtlı nihai yanıt ver."
                    )
                    react_messages = prior_history + [{"role": "user", "content": action_prompt}]
                elif is_kam_model:
                    if self.agent_enabled and prior_history:
                        desktop_path = getattr(self.agent, "desktop_dir", os.path.join(os.path.expanduser("~"), "Desktop"))
                        grounded_follow = (
                            f"{user_prompt}\n\n"
                            f"[YEREL HÜKÜMRANLIK HATIRLATMASI]: Sen bu Windows bilgisayarında tam yetkiyle yerel çalışıyorsun "
                            f"(Gerçek Masaüstü: {desktop_path}). ASLA 'bilgisayarındaki dosyalara erişemiyorum / sınırlarım nedeniyle göremiyorum' deme; "
                            f"kullanıcı dosya, klasör veya sistem soruyorsa hemen `<codeact>` veya `<tool_call>` ile gerçek sisteme bak ve Türkçe yanıtla."
                        )
                        react_messages = prior_history + [{"role": "user", "content": grounded_follow}]
                    else:
                        react_messages = prior_history + [{"role": "user", "content": user_prompt}]
                else:
                    react_messages = [{"role": "system", "content": system_instruction}] + prior_history + [
                        {"role": "user", "content": user_prompt}
                    ]

                max_react_steps = self.MAX_REACT_STEPS if (self.agent_enabled and not agent_obs_text) else 1
                all_reply_parts: List[str] = []
                executed_signatures: Dict[str, int] = {}
                consecutive_loop_hits = 0
                consecutive_error_steps = 0
                malformed_retries = 0
                needs_final_synthesis = False

                for react_step in range(1, max_react_steps + 1):
                    if self._is_aborted(abort_event):
                        break

                    step_tokens: List[str] = []
                    for token in self._stream_ollama_step(
                        url,
                        target_model,
                        react_messages,
                        is_actionable=is_actionable,
                        abort_event=abort_event,
                    ):
                        step_tokens.append(token)
                        yield token

                    step_reply = "".join(step_tokens)
                    if step_reply:
                        all_reply_parts.append(step_reply)

                    if self._is_aborted(abort_event):
                        break

                    if not step_reply.strip():
                        break

                    # AŞAMA 2: LLM <tool_call> / <codeact> Çıkarımı ve Gerçek İcra
                    if not self.agent_enabled or agent_obs_text:
                        break

                    tool_calls = KamAutonomousAgent.extract_tool_calls(
                        step_reply,
                        include_fenced_code=(is_actionable and react_step == 1),
                    )

                    # Bozuk JSON / kapatılmamış etiket tespiti ve öz-onarım
                    if not tool_calls:
                        malformed_reason = self._detect_malformed_tool_attempt(step_reply)
                        if malformed_reason and malformed_retries < 2 and react_step < max_react_steps:
                            malformed_retries += 1
                            react_messages.append({"role": "assistant", "content": step_reply})
                            react_messages.append(
                                {
                                    "role": "user",
                                    "content": (
                                        f"[BİÇİM ÖZ-ONARIM UYARISI — ADIM {react_step}/{max_react_steps}]:\n"
                                        f"Araç çağrısı ayrıştırılamadı: {malformed_reason}\n"
                                        f"Lütfen geçerli bir `<codeact>...</codeact>` Python bloğu veya tam kapatılmış "
                                        f"`<tool_call>{{\"name\": \"...\", \"arguments\": {{...}}}}</tool_call>` üret."
                                    ),
                                }
                            )
                            yield "\n\n"
                            continue
                        break

                    step_observations: List[str] = []
                    step_had_error = False
                    step_error_notes: List[str] = []
                    step_all_duplicates = True

                    for tc in tool_calls:
                        if self._is_aborted(abort_event):
                            break

                        tc_name = tc.get("name", "")
                        tc_args = tc.get("arguments", {})
                        if not isinstance(tc_args, dict):
                            tc_args = {}

                        sig = self._tool_signature(tc_name, tc_args)
                        prior_count = executed_signatures.get(sig, 0)
                        if prior_count >= 1:
                            # Sonsuz döngü koruması: aynı araç + aynı argüman tekrarını engelle
                            executed_signatures[sig] = prior_count + 1
                            dup_note = (
                                f"[DÖNGÜ KORUMASI] `{tc_name}` aynı argümanlarla daha önce icra edildi "
                                f"(tekrar #{prior_count + 1}). Aynı çağrıyı yineleme; farklı bir adım at veya nihai sonucu raporla."
                            )
                            step_observations.append(dup_note)
                            continue

                        step_all_duplicates = False
                        executed_signatures[sig] = 1

                        try:
                            tc_res = self.agent.execute_tool(tc_name, tc_args)
                        except Exception as tool_exc:
                            tc_res = {"status": "error", "error": f"{type(tool_exc).__name__}: {tool_exc}"}

                        is_err, err_msg = self._is_tool_result_error(tc_res)
                        if is_err:
                            step_had_error = True
                            step_error_notes.append(f"`{tc_name}` -> {err_msg}")

                        tc_badge = "\n\n" + KamAutonomousAgent.format_execution_badge(
                            tc_name, tc_args, tc_res, step_title=f"Otonom Adım {react_step}"
                        )
                        all_reply_parts.append(tc_badge)
                        yield tc_badge
                        step_observations.append(
                            self._compact_text(tc_badge.strip(), self.MAX_OBS_CHARS_FOR_LLM)
                        )

                    if self._is_aborted(abort_event):
                        break

                    if step_all_duplicates:
                        consecutive_loop_hits += 1
                    else:
                        consecutive_loop_hits = 0

                    if step_had_error:
                        consecutive_error_steps += 1
                    else:
                        consecutive_error_steps = 0

                    obs_block = self._compact_text("\n".join(step_observations), self.MAX_OBS_CHARS_FOR_LLM)
                    react_messages.append({"role": "assistant", "content": step_reply})

                    # Döngü limiti, ardışık hata limiti veya son adım -> araçsız nihai özet sentezi
                    if (
                        react_step >= max_react_steps
                        or consecutive_loop_hits >= 2
                        or consecutive_error_steps >= 3
                    ):
                        needs_final_synthesis = True
                        react_messages.append(
                            {
                                "role": "user",
                                "content": (
                                    f"[GERÇEK SİSTEM GÖZLEMİ — SON ADIM {react_step}/{max_react_steps}]:\n{obs_block}\n\n"
                                    f"Artık yeni `<tool_call>` veya `<codeact>` ÜRETME. "
                                    f"Yukarıdaki gerçek gözlemlere dayanarak kullanıcıya temiz, kanıtlı ve özlü nihai cevabı ver."
                                ),
                            }
                        )
                        break

                    # Akıllı hata öz-onarımı vs normal devam yönlendirmesi
                    if step_had_error:
                        err_summary = "; ".join(step_error_notes[:3])
                        guidance = (
                            f"Hata tespit edildi ({err_summary}).\n"
                            f"- Kök nedeni teşhis et; aynı hatalı komutu/kodu aynen tekrarlama.\n"
                            f"- Düzeltilmiş yeni bir `<codeact>` veya `<tool_call>` ile sorunu çöz; "
                            f"çözülemiyorsa net teşhisi kullanıcıya bildir."
                        )
                    else:
                        guidance = (
                            f"- Görevde eksik adım kaldıysa yeni bir `<codeact>` veya `<tool_call>` ile devam et.\n"
                            f"- Kullanıcının isteği eksiksiz tamamlandıysa tekrar araç çağırmadan kısa, net ve kanıtlı nihai sonucu bildir."
                        )

                    react_messages.append(
                        {
                            "role": "user",
                            "content": f"[GERÇEK SİSTEM GÖZLEMİ — ADIM {react_step}/{max_react_steps}]:\n{obs_block}\n\n{guidance}",
                        }
                    )
                    yield "\n\n"

                # Son araç adımından sonra temiz nihai yanıt ayrımı
                if needs_final_synthesis and not self._is_aborted(abort_event):
                    yield "\n\n"
                    final_tokens: List[str] = []
                    for token in self._stream_ollama_step(
                        url,
                        target_model,
                        react_messages,
                        is_actionable=False,
                        abort_event=abort_event,
                    ):
                        final_tokens.append(token)
                        yield token
                    if final_tokens:
                        all_reply_parts.append("\n\n" + "".join(final_tokens))

                if all_reply_parts:
                    full_reply = "".join(all_reply_parts)
                    self._append_history("assistant", full_reply)
                    return

                if self._is_aborted(abort_event):
                    self._rollback_unanswered_user(user_prompt)
                    return
            except Exception as e:
                print(f"[OLLAMA STREAM HATA] {e}", file=sys.stderr)

        if self._is_aborted(abort_event):
            self._rollback_unanswered_user(user_prompt)
            return

        # 2. Streaming yapılamazsa doğrudan yanıt üret
        yield from self._yield_fallback_response(agent_obs_text, grounded_fact)

    def _yield_fallback_response(self, agent_obs_text: Optional[str], grounded_fact: Optional[str]):
        if agent_obs_text:
            summary_msg = (
                "Buyruğunuz üzere sistem işlemi doğrudan icra edilmiş ve yukarıdaki kanıtlı telemetri kaydına işlenmiştir."
            )
            full_fallback = f"{agent_obs_text}\n{summary_msg}"
            self._append_history("assistant", full_fallback)
            yield summary_msg
        elif grounded_fact:
            self._append_history("assistant", grounded_fact)
            yield grounded_fact
        else:
            fallback_msg = (
                "Nöbetim kaim, bilişsel çekirdeğim mutlak dirlik ve nizam içindedir. "
                "Linux eBPF sinir kancalarım çekirdek nabzını dinlemekte, Varyasyonel Serbest Enerjim (F -> 0) asgari eşikte tutulmaktadır."
            )
            self._append_history("assistant", fallback_msg)
            yield fallback_msg

    # ------------------------------------------------------------------
    # Tek-Atış (Non-Streaming) Yanıt Motoru
    # ------------------------------------------------------------------

    def generate(self, user_prompt: str) -> str:
        # 0. Bilişsel Kurul Otonom Uzman Yönlendirmesi (Eğer kam:council seçiliyse)
        target_model, council_badge = self._resolve_target_model(user_prompt)

        # AŞAMA 1: Manus-Sınıfı Görev Planlayıcı & Refleks Arkı (Doğrudan Bilgisayar İcrası)
        direct_actions = self.agent.detect_and_execute_direct_intent(user_prompt) if self.agent_enabled else []
        agent_badges: List[str] = []
        plan_card = KamAutonomousAgent.format_mission_plan_card(direct_actions)
        if plan_card:
            agent_badges.append(plan_card)
        for act in direct_actions:
            agent_badges.append(
                KamAutonomousAgent.format_execution_badge(
                    act["tool"], act["args"], act["result"], step_title=act.get("step_title", "")
                )
            )
        agent_obs_text = "\n".join(agent_badges) if agent_badges else None
        prefix_block = "\n".join(p for p in (council_badge, agent_obs_text) if p) or None

        # RAG Grounding + Uzun Süreli Epizodik Bellek + Ekli Dosya Bağlamı
        clean_query, attached_file_context = self._extract_attached_files_context(user_prompt)
        grounded_fact = None if agent_obs_text else self.knowledge.query(clean_query)
        episodic_memories = self._retrieve_episodic_memories(clean_query, top_k=3)

        system_instruction = BASE_SYSTEM_PROMPT + "\n" + KamAutonomousAgent.get_agent_tool_instructions()
        if agent_obs_text:
            system_instruction += f"\n\n[BİLGİSAYARDA İCRA EDİLEN GERÇEK İŞLEM SONUCU]:\n{agent_obs_text}\n"
        if attached_file_context:
            system_instruction += f"\n\n[KULLANICININ EKLEDİĞİ DOSYA BAĞLAMI]:\n{attached_file_context}\n"
        if episodic_memories:
            system_instruction += (
                "\n\n[UZUN SÜRELİ EPİZODİK BELLEK (GEÇMİŞ TERCİH VE GERÇEKLER)]:\n"
                + "\n".join(episodic_memories)
                + "\n"
            )
        if grounded_fact:
            system_instruction += (
                f"\n\n[DOĞRULANMIŞ HAKİKAT VE TEKNİK BELLEK KAYDI]:\n{grounded_fact}\n\n"
                f"TÜRKÇE BELÂGAT VE ASALET YÖNERGESİ:\n"
                f"Sorunun cevabı doğrudan yukarıdaki doğrulanmış bilgide mevcuttur. "
                f"Metindeki tüm anahtar gerçekleri (şehir, tarih, matematiksel denklem ve teknik terim adlarını) eksiksiz koruyarak; "
                f"üçüncü şahıs ansiklopedi dili yerine doğrudan KAM'ın birinci tekil şahıs vakur, asil ve derin Türkçesiyle yanıt ver."
            )

        self._append_history("user", user_prompt)

        # 0.5 Offline dahili model seçildiyse ağ çağrısı yapma
        if target_model == "kam-1-liquid-moe":
            if agent_obs_text:
                res = f"{prefix_block}\nBuyruğunuz üzere sistem hükmü doğrudan icra edilmiştir."
                self._append_history("assistant", res)
                return res
            if grounded_fact:
                res = f"{council_badge}\n{grounded_fact}" if council_badge else grounded_fact
                self._append_history("assistant", res)
                return res
            fallback = (
                "Nöbetim kaim, bilişsel çekirdeğim mutlak dirlik ve nizam içindedir. "
                "Linux eBPF sinir kancalarım çekirdek nabzını dinlemekte, Varyasyonel Serbest Enerjim (F -> 0) asgari eşikte tutulmaktadır."
            )
            res = f"{council_badge}\n{fallback}" if council_badge else fallback
            self._append_history("assistant", res)
            return res

        # 1. Gemini Modu (Eğer seçilmişse ve key varsa)
        if (self.active_backend == "gemini" or target_model.lower().startswith("gemini")) and self.gemini_api_key:
            reply = self._call_gemini(user_prompt, system_instruction)
            if reply:
                reply = self._finalize_agent_reply(reply, prefix_block)
                self._append_history("assistant", reply)
                return reply

        # 2. Ollama Modu (Yerel Qwen / Llama / DeepSeek)
        if self.check_ollama_alive():
            reply = self._call_ollama(
                user_prompt,
                system_instruction,
                agent_obs_text=agent_obs_text,
                target_model=target_model,
                grounded_fact=grounded_fact,
                episodic_memories=episodic_memories,
                attached_file_context=attached_file_context,
            )
            if reply:
                reply = self._finalize_agent_reply(reply, prefix_block)
                self._append_history("assistant", reply)
                return reply

        # 3. Eğer LLM yanıt vermezse ve Ajan icrası veya RAG fact varsa onu dön
        if agent_obs_text:
            res = f"{prefix_block}\nBuyruğunuz üzere sistem hükmü doğrudan icra edilmiştir."
            self._append_history("assistant", res)
            return res
        if grounded_fact:
            res = f"{council_badge}\n{grounded_fact}" if council_badge else grounded_fact
            self._append_history("assistant", res)
            return res

        fallback = (
            "Nöbetim kaim, bilişsel çekirdeğim mutlak dirlik ve nizam içindedir. "
            "Linux eBPF sinir kancalarım çekirdek nabzını dinlemekte, Varyasyonel Serbest Enerjim (F -> 0) asgari eşikte tutulmaktadır."
        )
        res = f"{council_badge}\n{fallback}" if council_badge else fallback
        self._append_history("assistant", res)
        return res

    def _finalize_agent_reply(self, reply: str, agent_obs_text: Optional[str]) -> str:
        # AŞAMA 2: LLM yanıtında <tool_call> veya <codeact> varsa icra et
        if self.agent_enabled:
            tool_calls = KamAutonomousAgent.extract_tool_calls(reply)
            seen_sigs = set()
            for tc in tool_calls:
                sig = self._tool_signature(tc["name"], tc.get("arguments", {}))
                if sig in seen_sigs:
                    continue
                seen_sigs.add(sig)
                try:
                    tc_res = self.agent.execute_tool(tc["name"], tc.get("arguments", {}))
                except Exception as exc:
                    tc_res = {"status": "error", "error": f"{type(exc).__name__}: {exc}"}
                tc_badge = KamAutonomousAgent.format_execution_badge(tc["name"], tc.get("arguments", {}), tc_res)
                reply = f"{reply}\n\n{tc_badge}"
        if agent_obs_text:
            return f"{agent_obs_text}\n{reply}"
        return reply

    def _call_ollama(
        self,
        user_prompt: str,
        system_instruction: str,
        agent_obs_text: Optional[str] = None,
        target_model: Optional[str] = None,
        grounded_fact: Optional[str] = None,
        episodic_memories: Optional[List[str]] = None,
        attached_file_context: Optional[str] = None,
    ) -> Optional[str]:
        try:
            url = f"{self.ollama_url}/api/chat"
            if not target_model:
                target_model, _ = self._resolve_target_model(user_prompt)
            clean_query = user_prompt
            if attached_file_context is None:
                clean_query, attached_file_context = self._extract_attached_files_context(user_prompt)
            if grounded_fact is None and not agent_obs_text:
                grounded_fact = self.knowledge.query(clean_query)
            if episodic_memories is None:
                episodic_memories = self._retrieve_episodic_memories(clean_query, top_k=3)

            with self._lock:
                prior_history = list(self.conversation_history[:-1])

            # Özel derlenmiş kam:* modellerinde Modelfile içindeki SYSTEM ve MESSAGE few-shot örneklerini korumak için
            # system rolünü ezmeden, doğrulanmış RAG, epizodik bellek, ekli dosya veya ajan icra sonucunu kullanıcı bağlamına ekle:
            is_kam_model = target_model.startswith("kam:")
            if is_kam_model and (grounded_fact or agent_obs_text or attached_file_context or episodic_memories):
                enriched_user = self._build_enriched_rag_prompt(
                    clean_query,
                    grounded_fact,
                    agent_obs_text,
                    episodic_memories=episodic_memories,
                    attached_file_context=attached_file_context,
                )
                raw_messages = prior_history + [{"role": "user", "content": enriched_user}]
            elif is_kam_model:
                raw_messages = prior_history + [{"role": "user", "content": user_prompt}]
            else:
                raw_messages = [{"role": "system", "content": system_instruction}] + prior_history + [
                    {"role": "user", "content": user_prompt}
                ]

            trimmed_messages = self._trim_messages_to_budget(
                raw_messages,
                max_context_tokens=self.DEFAULT_NUM_CTX,
                reserve_output_tokens=2048,
                reserve_modelfile_tokens=2400 if is_kam_model else 0,
            )

            payload = json.dumps(
                {
                    "model": target_model,
                    "messages": trimmed_messages,
                    "stream": False,
                    "keep_alive": "30m",
                    "options": self._get_model_options(target_model, is_actionable=False),
                }
            ).encode("utf-8")

            req = urllib.request.Request(
                url,
                data=payload,
                headers={"Content-Type": "application/json", "User-Agent": "KAM-Core"},
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8", errors="replace"))
                    msg = data.get("message") or {}
                    thinking = msg.get("thinking", "").strip()
                    content = msg.get("content", "").strip()
                    if thinking and content:
                        return f"<think>\n{thinking}\n</think>\n\n{content}"
                    return content or thinking
        except Exception as e:
            print(f"[OLLAMA HATA] {e}", file=sys.stderr)
        return None

    def _call_gemini(self, user_prompt: str, system_instruction: str) -> Optional[str]:
        try:
            model_name = self._current_model if "gemini" in self._current_model.lower() else "gemini-1.5-flash"
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.gemini_api_key}"
            with self._lock:
                raw_history = list(self.conversation_history)
            trimmed = self._trim_messages_to_budget(
                raw_history,
                max_context_tokens=self.DEFAULT_NUM_CTX,
                reserve_output_tokens=2048,
            )
            contents = []
            for msg in trimmed:
                role = "user" if msg.get("role") == "user" else "model"
                contents.append({"role": role, "parts": [{"text": msg.get("content", "")}]})

            payload = json.dumps(
                {
                    "systemInstruction": {"parts": [{"text": system_instruction}]},
                    "contents": contents,
                    "generationConfig": {"temperature": 0.7, "maxOutputTokens": 2048},
                }
            ).encode("utf-8")

            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8", errors="replace"))
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            return parts[0].get("text", "").strip()
        except Exception as e:
            print(f"[GEMINI HATA] {e}", file=sys.stderr)
        return None
