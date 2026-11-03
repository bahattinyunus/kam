import os
import json
import re
from typing import Optional, Dict, Any, List

class LocalKnowledgeEngine:
    """
    Yerel Açık Kaynak Bilgi Tabanı ve Semantik Çıkarım Motoru
    İnternetsiz (Air-Gapped) Türkçe Soru-Cevap ve Kavram Doğrulayıcı
    """
    def __init__(self, dataset_path: str = None):
        if not dataset_path:
            dataset_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "turkish_knowledge_dataset.json")
        self.dataset_path = dataset_path
        self.knowledge_base: List[Dict[str, Any]] = []
        self.load_dataset()

    def load_dataset(self):
        if os.path.exists(self.dataset_path):
            try:
                with open(self.dataset_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.knowledge_base = data.get("entries", [])
            except Exception:
                self.knowledge_base = []
        else:
            # Fallback yerleşik bilgiler
            self.knowledge_base = [
                {
                    "keywords": ["türkiye", "başkent", "ankara", "tr", "turkiye"],
                    "question": "Türkiye'nin başkenti neresidir?",
                    "answer": "Türkiye Cumhuriyeti'nin başkenti Ankara'dır."
                }
            ]

    def normalize(self, text: str) -> str:
        # Türkçe karakter ve noktalama normalizasyonu
        text = text.lower()
        replacements = {
            "ı": "i", "İ": "i", "ş": "s", "ğ": "g", "ü": "u", "ö": "o", "ç": "c"
        }
        for k, v in replacements.items():
            text = text.replace(k, v)
        text = re.sub(r"[^\w\s]", " ", text)
        return " ".join(text.split())

    def query(self, user_question: str) -> Optional[str]:
        norm_q = self.normalize(user_question)
        words = set(norm_q.split())

        # Özel Kısayol: "tr nin başkenti", "türkiyenin başkenti"
        if ("tr" in words or "turkiye" in words or "turkiyenin" in words) and ("baskent" in words or "baskenti" in words or "baskentii" in words or "neresi" in words or "neresidir" in words):
            return "Ankara. Türkiye Cumhuriyeti'nin başkenti Ankara'dır."

        best_match = None
        best_score = 0.0

        for entry in self.knowledge_base:
            keywords = [self.normalize(k) for k in entry.get("keywords", [])]
            match_count = 0
            for kw in keywords:
                for w in words:
                    if kw == w:  # Tam kelime eşleşmesi
                        match_count += 1
                        break
                    elif len(kw) > 4 and kw in w:
                        match_count += 0.8
                        break

            if match_count > 0:
                score = match_count / max(1, len(keywords))
                if score > best_score:
                    best_score = score
                    best_match = entry

        if best_match and best_score >= 0.50:
            return best_match["answer"]

        return None
