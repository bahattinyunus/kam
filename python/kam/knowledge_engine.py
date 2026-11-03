import os
import json
import re
from typing import Optional, Dict, Any, List

class LocalKnowledgeEngine:
    """
    Yerel Açık Kaynak Bilgi Tabanı ve Semantik Çıkarım Motoru
    İnternetsiz (Air-Gapped) Türkçe Soru-Cevap, Terim Doğrulayıcı ve RAG Mekanizması
    """
    def __init__(self, dataset_path: str = None):
        if not dataset_path:
            dataset_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "turkish_knowledge_dataset.json")
        self.dataset_path = dataset_path
        self.knowledge_base: List[Dict[str, Any]] = []
        self.load_dataset()

    def load_dataset(self):
        self.knowledge_base = []
        data_dir = os.path.dirname(self.dataset_path)
        target_files = [
            self.dataset_path,
            os.path.join(data_dir, "kam_lore_dataset.json"),
            os.path.join(data_dir, "kam_master_dataset.json")
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
                    "answer": "Türkiye Cumhuriyeti'nin başkenti Ankara'dır."
                }
            ]

    def normalize(self, text: str) -> str:
        # Türkçe karakter, şapkalı harf ve teknik terim normalizasyonu
        text = text.lower()
        text = text.replace("c++20", "cpp20").replace("c++", "cpp")
        replacements = {
            "ı": "i", "İ": "i", "ş": "s", "ğ": "g", "ü": "u", "ö": "o", "ç": "c",
            "â": "a", "Â": "a", "î": "i", "Î": "i", "û": "u", "Û": "u"
        }
        for k, v in replacements.items():
            text = text.replace(k, v)
        text = re.sub(r"[^\w\s]", " ", text)
        return " ".join(text.split())

    def query(self, user_question: str) -> Optional[str]:
        norm_q = self.normalize(user_question)
        words = set(norm_q.split())

        # Özel Kısayol: Türkiye başkenti
        if ("tr" in words or "turkiye" in words or "turkiyenin" in words) and ("baskent" in words or "baskenti" in words or "neresi" in words or "neresidir" in words):
            return "Türkiye Cumhuriyeti'nin başkenti Ankara'dır. 13 Ekim 1923 tarihinde Türkiye Büyük Millet Meclisi kararıyla başkent ilan edilmiştir."

        best_match = None
        best_score = 0.0

        for entry in self.knowledge_base:
            keywords = [self.normalize(k) for k in entry.get("keywords", [])]
            match_score = 0.0

            for kw in keywords:
                # 1. Çok kelimeli tam öbek eşleşmesi (örn: "karl friston", "serbest enerji", "bellek havuzu")
                if " " in kw and kw in norm_q:
                    match_score += 2.5
                    continue

                # 2. Tam tek kelime eşleşmesi
                if kw in words:
                    match_score += 1.5
                    continue

                # 3. Türkçe eklemeli dil kök/gövde eşleşmesi (agglutinative suffix matching)
                kw_stem = kw[:4] if len(kw) >= 4 else kw
                for w in words:
                    w_stem = w[:4] if len(w) >= 4 else w
                    if len(kw) >= 4 and len(w) >= 4 and (kw_stem == w_stem or kw in w or w in kw):
                        match_score += 0.9
                        break

            if match_score > 0:
                # Soru içindeki anahtar yoğunluğu
                score = match_score / max(1.0, min(len(words), 5.0))
                if score > best_score and match_score >= 1.2:
                    best_score = score
                    best_match = entry

        if best_match and best_score >= 0.20:
            return best_match["answer"]

        return None
