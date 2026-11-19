import math
import os
import json
import re
from typing import Optional, Dict, Any, List, Set


class LocalKnowledgeEngine:
    """
    Yerel Açık Kaynak Bilgi Tabanı ve BM25/TF-IDF Ağırlıklı Semantik Çıkarım Motoru
    İnternetsiz (Air-Gapped) Türkçe Soru-Cevap, Terim Doğrulayıcı ve RAG Mekanizması
    """

    _TR_MAP = str.maketrans({
        "İ": "i", "I": "i", "ı": "i",
        "Ş": "s", "ş": "s",
        "Ğ": "g", "ğ": "g",
        "Ü": "u", "ü": "u",
        "Ö": "o", "ö": "o",
        "Ç": "c", "ç": "c",
        "Â": "a", "â": "a",
        "Î": "i", "î": "i",
        "Û": "u", "û": "u",
    })

    # Okapi BM25 hiperparametreleri
    _BM25_K1: float = 1.5
    _BM25_B: float = 0.75

    # Tek başına eşleşme üretmemesi gereken genel soru/bağlaç sözcükleri
    _GENERIC_WORDS: Set[str] = {
        "nedir", "kimdir", "neresi", "neresidir", "nasil", "neden", "nicin",
        "hangi", "ne", "midir", "mudur", "hakkinda", "acikla", "anlat",
        "nelerdir", "ise", "yarar", "ve", "ile", "icin", "bir", "bu", "su",
        "sen", "senin", "ben", "nin", "nun", "un", "in", "de", "da", "te", "ta",
        "mi", "mu", "misin", "musun", "var", "yok", "kac", "kactir", "en",
    }

    # Definitional / açıklayıcı soru sinyalleri
    _DEFINITIONAL_WORDS: Set[str] = {
        "nedir", "kimdir", "neresi", "neresidir", "nasil", "neden", "nicin",
        "nelerdir", "acikla", "anlat", "hakkinda", "anlami", "manasi",
        "ozellikleri", "yenilikleri", "farki", "kurallari", "prensibi",
        "teoremi", "formulu", "mantigi", "felsefesi", "yarar",
    }

    # Tek başına bir bilgi kaydını tetiklememesi gereken geniş/gündelik tekil anahtar kelimeler
    # (İkinci bir anahtar kelime veya çok kelimeli öbek ile desteklenmelidir)
    _BROAD_SINGLE_KEYWORDS: Set[str] = {
        "saat", "zaman", "linux", "sehir", "motor", "yerel", "guvenlik",
        "savas", "kriz", "ariza", "kopma", "duzen", "felsefe", "bulut",
        "cloud", "nufus", "standart", "mantik", "bilinc", "benlik", "lider",
        "filo", "rota", "3d", "sinir", "ruh", "mimar", "alp", "kalabalik",
        "tasarruf", "cekirdek", "kernel", "radar", "siber", "otomotiv",
        "telsiz", "surpriz", "hipotez", "dogrulama", "vakar", "nizam",
        "basiret", "hikmet", "anlami", "manasi", "tarzin", "uslubun",
        "adin", "kimsin", "kimlik", "bozkir", "turkce", "cografya",
        "surekli", "frekans", "clock", "neural", "liquid", "sparse",
        "mesh", "swarm", "suru", "uav", "siha", "rtx", "jetson", "termal",
        "baskent", "turkiye", "kam", "enerji", "serbest", "karl", "kanca",
        "kurucu", "cumhurbaskani", "enformasyon", "entropi", "bilgi",
        "teorisi", "kalkani", "izdusum", "emiter", "orkestrasyon", "silikon",
        "yontem", "toz", "belagat", "kaynasma", "ozne", "yuklem", "tumlec",
        "top2", "imu", "ode", "tau", "lnn", "cpp", "tr", "yarar", "ne",
    }

    # Bilgisayar kullanımı, gerçek zamanlı sorgu veya kod yazma emirlerini yakalayan koruma kalıpları
    _ACTION_OR_REALTIME_PATTERNS = (
        re.compile(r"\b(?:saat kac|what time|bugun hava|hava durumu|weather|trafik durumu|motor yagi)\b"),
        re.compile(r"\b(?:ekran goruntusu|masaustu\w*|klasor\w*|dosya\w*|disk alani\w*|yerel disk|guvenlik duvari\w*|tarayici\w*|chrome|firefox|notepad|powershell|terminal|ram kullanimi|cpu kullanimi)\b"),
        re.compile(r"\b(?:olustur\w*|listele\w*|kaydet\w*|tikla\w*|kopyala\w*|tasi\w*|sil\w*|kapat\w*|baslat\w*|calistir\w*|kontrol et\w*|denetle\w*|onerir\w*|oneri\w*)\b"),
        re.compile(r"\b(?:open|create|delete|remove|run|execute|launch|install|download|screenshot|click|type|write a|write me|fix this|refactor|show me my|list files|check disk)\b"),
    )
    _IMPERATIVE_CODE_OR_OPEN_RE = re.compile(r"\b(?:yaz|ac|yap|kur|indir|goster)\b")

    def __init__(self, dataset_path: str = None):
        if not dataset_path:
            dataset_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "turkish_knowledge_dataset.json")
        self.dataset_path = dataset_path
        self.knowledge_base: List[Dict[str, Any]] = []
        self._indexed_entries: List[Dict[str, Any]] = []
        self._idf: Dict[str, float] = {}
        self._avg_doc_len: float = 1.0
        self.load_dataset()

    def load_dataset(self):
        self.knowledge_base = []
        data_dir = os.path.dirname(self.dataset_path)
        target_files = [
            self.dataset_path,
            os.path.join(data_dir, "kam_lore_dataset.json"),
            os.path.join(data_dir, "kam_master_dataset.json"),
            os.path.join(data_dir, "kam_turkish_intelligence_corpus.json"),
        ]

        for path in target_files:
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        self.knowledge_base.extend(data.get("entries", []))
                except Exception:
                    pass

        if not self.knowledge_base:
            # Fallback yerleşik bilgiler
            self.knowledge_base = [
                {
                    "keywords": ["türkiye", "başkent", "ankara", "tr", "turkiye"],
                    "question": "Türkiye'nin başkenti neresidir?",
                    "answer": "Türkiye Cumhuriyeti'nin başkenti Ankara'dır.",
                }
            ]

        self._rebuild_index()

    def _rebuild_index(self):
        self._indexed_entries = []
        doc_freq: Dict[str, int] = {}
        total_len = 0

        for entry in self.knowledge_base:
            norm_keywords = [self.normalize(k) for k in entry.get("keywords", []) if isinstance(k, str)]
            norm_keywords = [k for k in norm_keywords if k]
            norm_question = self.normalize(entry.get("question", ""))
            q_words = {w for w in norm_question.split() if w not in self._GENERIC_WORDS and len(w) >= 3}

            # BM25/TF-IDF belge terim frekansları (anahtar kelimeler 2x alan ağırlıklı)
            tf: Dict[str, float] = {}
            for kw in norm_keywords:
                for tok in kw.split():
                    if tok not in self._GENERIC_WORDS:
                        tf[tok] = tf.get(tok, 0.0) + 2.0
            for qw in q_words:
                tf[qw] = tf.get(qw, 0.0) + 1.0

            doc_len = max(1, int(sum(tf.values())))
            total_len += doc_len
            for tok in tf:
                doc_freq[tok] = doc_freq.get(tok, 0) + 1

            self._indexed_entries.append({
                "entry": entry,
                "keywords": norm_keywords,
                "question_words": q_words,
                "tf": tf,
                "doc_len": doc_len,
            })

        n_docs = max(1, len(self._indexed_entries))
        self._avg_doc_len = max(1.0, total_len / float(n_docs))
        # Okapi BM25 IDF: nadir alan terimleri (df=1) sık geçen terimlerden çok daha yüksek ağırlık alır
        self._idf = {
            tok: math.log(1.0 + (n_docs - df + 0.5) / (df + 0.5))
            for tok, df in doc_freq.items()
        }

    def get_term_idf(self, term: str) -> float:
        """Normalize edilmiş bir terimin BM25 IDF ağırlığını döndürür."""
        norm = self.normalize(term)
        if not norm:
            return 0.0
        n_docs = max(1, len(self._indexed_entries))
        default_idf = math.log(1.0 + (n_docs + 0.5) / 1.5)
        if " " in norm:
            toks = [t for t in norm.split() if t not in self._GENERIC_WORDS]
            if not toks:
                return 0.0
            return sum(self._idf.get(t, default_idf) for t in toks) / float(len(toks))
        return self._idf.get(norm, default_idf)

    def _bm25_term_weight(self, tok: str, tf_map: Dict[str, float], doc_len: int) -> float:
        tf = tf_map.get(tok, 1.0)
        idf = self.get_term_idf(tok)
        norm_dl = 1.0 - self._BM25_B + self._BM25_B * (doc_len / self._avg_doc_len)
        return idf * ((tf * (self._BM25_K1 + 1.0)) / (tf + self._BM25_K1 * norm_dl))

    def normalize(self, text: str) -> str:
        if not text or not isinstance(text, str):
            return ""
        # Türkçe karakter (özellikle İ -> i, I -> i) normalizasyonu .lower() ÖNCESİNDE yapılır
        # Böylece Python'un "İ".lower() -> "i\u0307" birleşik nokta hatası oluşmaz.
        text = text.translate(self._TR_MAP).lower().replace("\u0307", "")
        text = text.replace("c++20", "cpp20").replace("c++", "cpp")
        text = re.sub(r"[^\w\s]", " ", text)
        return " ".join(text.split())

    @classmethod
    def _is_safe_stem_match(cls, kw: str, word: str) -> bool:
        """
        Türkçe eklemeli dil gövde/ek eşleşmesi:
        - En az 5 karakterli gövdelerde çalışır (kısa 4-harf çakışmalarını engeller).
        - Uzunluk oranı koruması (örn. 'bilgi' vs 'bilgisayar' -> 0.50 < 0.62 -> RED).
        - Sadece ileri yönlü ek eşleşmesi (word, kw ile başlamalı veya ünsüz yumuşaması).
        """
        if len(kw) < 5 or len(word) < 5:
            return False
        if len(word) < len(kw):
            return False
        diff = len(word) - len(kw)
        if diff > 4:
            return False
        if (len(kw) / len(word)) < 0.62:
            return False
        if word.startswith(kw):
            return True
        # Türkçe ünsüz yumuşaması (örn. mantik -> mantigi, kitap -> kitabi, sozluk -> sozlugu)
        if kw[-1] in ("k", "p", "t", "c") and word.startswith(kw[:-1]):
            return True
        return False

    def _is_non_knowledge_action(self, norm_q: str, words: Set[str]) -> bool:
        """Bilgisayar-kullanımı, gerçek zamanlı saat/hava veya kod yazma emirlerini RAG'dan ayırır."""
        for pat in self._ACTION_OR_REALTIME_PATTERNS:
            if pat.search(norm_q):
                return True
        if self._IMPERATIVE_CODE_OR_OPEN_RE.search(norm_q) and not (words & self._DEFINITIONAL_WORDS):
            return True
        return False

    def score_entries(self, user_question: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Verilen soru için bilgi tabanındaki kayıtları BM25/TF-IDF ağırlıklı olarak puanlar.
        Nadir alan terimleri sık geçen genel sözcüklere göre çok daha yüksek skor alır.
        """
        norm_q = self.normalize(user_question)
        if not norm_q:
            return []

        words = set(norm_q.split())
        if self._is_non_knowledge_action(norm_q, words):
            return []

        content_words = {w for w in words if w not in self._GENERIC_WORDS}
        if not content_words:
            return []

        ranked: List[Dict[str, Any]] = []
        denom = max(1.0, min(float(len(content_words)), 6.0))

        for item in self._indexed_entries:
            entry = item["entry"]
            keywords = item["keywords"]
            q_words = item["question_words"]
            tf_map = item["tf"]
            doc_len = item["doc_len"]

            bm25_score = 0.0
            keyword_bm25 = 0.0
            phrase_hits = 0
            specific_hits = 0
            broad_hits = 0
            matched_tokens: Set[str] = set()

            for kw in keywords:
                if kw in self._GENERIC_WORDS:
                    if kw in words:
                        bm25_score += 0.10
                    continue

                # 1. Çok kelimeli tam öbek eşleşmesi (BM25 öbek IDF bonusu)
                if " " in kw:
                    if re.search(rf"\b{re.escape(kw)}\b", norm_q):
                        phrase_toks = [t for t in kw.split() if t not in self._GENERIC_WORDS]
                        phrase_bm25 = sum(self._bm25_term_weight(t, tf_map, doc_len) for t in phrase_toks)
                        w_val = max(3.0, phrase_bm25 * 1.15)
                        bm25_score += w_val
                        keyword_bm25 += w_val
                        phrase_hits += 1
                        matched_tokens.update(phrase_toks)
                    continue

                is_broad = kw in self._BROAD_SINGLE_KEYWORDS

                # 2. Tam tek kelime eşleşmesi (nadir alan terimleri yüksek BM25/IDF alır)
                if kw in words:
                    term_w = self._bm25_term_weight(kw, tf_map, doc_len)
                    if is_broad:
                        w_val = term_w * 0.55
                        broad_hits += 1
                    else:
                        w_val = term_w * 1.15
                        specific_hits += 1
                    bm25_score += w_val
                    keyword_bm25 += w_val
                    matched_tokens.add(kw)
                    continue

                # 3. Güvenli Türkçe eklemeli gövde/ek eşleşmesi
                for w in content_words:
                    if self._is_safe_stem_match(kw, w):
                        term_w = self._bm25_term_weight(kw, tf_map, doc_len)
                        if is_broad:
                            w_val = term_w * 0.40
                            broad_hits += 1
                        else:
                            w_val = term_w * 0.80
                            specific_hits += 1
                        bm25_score += w_val
                        keyword_bm25 += w_val
                        matched_tokens.add(kw)
                        break

            distinct_hits = phrase_hits + specific_hits + broad_hits
            if distinct_hits == 0:
                continue

            # Tekil geniş/gündelik sözcük eşleşmesini kesin olarak reddet (örn. yalnız "saat", "linux", "yerel", "motor")
            qualified = (
                phrase_hits >= 1
                or (specific_hits >= 1 and (distinct_hits >= 2 or keyword_bm25 >= 2.8))
                or broad_hits >= 2
            )
            if not qualified:
                continue

            # Soru metniyle BM25 içerik örtüşmesi bonusu (eşitlik bozma ve hassasiyet artışı)
            if q_words:
                q_bonus = 0.0
                for qw in q_words:
                    if qw in matched_tokens:
                        continue
                    if qw in content_words or any(self._is_safe_stem_match(qw, cw) for cw in content_words):
                        q_bonus += self._bm25_term_weight(qw, tf_map, doc_len) * 0.25
                bm25_score += min(2.0, q_bonus)

            norm_score = bm25_score / denom
            if bm25_score >= 2.4 and norm_score >= 0.55:
                ranked.append({
                    "entry": entry,
                    "score": round(norm_score, 4),
                    "raw_bm25": round(bm25_score, 4),
                    "phrase_hits": phrase_hits,
                    "specific_hits": specific_hits,
                    "broad_hits": broad_hits,
                })

        ranked.sort(key=lambda r: (r["score"], r["raw_bm25"]), reverse=True)
        return ranked[:max(1, top_k)]

    def query(self, user_question: str) -> Optional[str]:
        norm_q = self.normalize(user_question)
        if not norm_q:
            return None

        words = set(norm_q.split())

        # Özel Kısayol: Türkiye başkenti ("tr nin başkentii neresi" vb. yazım hatalarına dayanıklı)
        has_tr = bool(words & {"tr", "turkiye", "turkiyenin"})
        has_baskent = any(w.startswith("baskent") for w in words) or bool(words & {"neresi", "neresidir"})
        if has_tr and has_baskent and not (words & {"kurucu", "kurucusu", "kalabalik", "istanbul", "ataturk"}):
            return (
                "Türkiye Cumhuriyeti'nin başkenti Ankara'dır. 13 Ekim 1923 tarihinde Türkiye Büyük Millet Meclisi "
                "(TBMM) kararıyla başkent ilan edilmiştir. Milli Mücadele'nin karargahı olan Ankara, coğrafi olarak "
                "Anadolu'nun tam merkezinde bulunması ve stratejik güvenliği nedeniyle Gazi Mustafa Kemal Atatürk "
                "önderliğinde başkent seçilmiştir."
            )

        ranked = self.score_entries(user_question, top_k=1)
        if ranked:
            return ranked[0]["entry"]["answer"]

        return None
