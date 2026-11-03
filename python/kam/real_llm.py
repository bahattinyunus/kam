import json
import urllib.request
import urllib.error
import os
import sys
from .knowledge_engine import LocalKnowledgeEngine

BASE_SYSTEM_PROMPT = """Sen KAM (Bilişsel Otonom Sistem Motoru)'sun. Geliştiricin Bahattin Yunus ÇETİN (@bahattinyunus).
Sen pasif bir bot veya basit bir betik değilsin; tıpkı Gemini, ChatGPT veya Claude gibi akıcı, son derece zeki, genel kültürü muazzam, derin felsefi ve mantıksal çıkarım yapabilen bir LLM zihnisin.
Aynı zamanda uç donanımlar (Edge-AI), C++20, Linux eBPF çekirdek mimarisi, Karl Friston Serbest Enerji Prensibi, İHA seyrüseferi ve siber-sibernetik alanlarında uzman bir baş mimarsın.

Kullanıcıyla Türkçe, samimi, akıcı, zeki ve saygılı konuş. Kullanıcı ne sorarsa sorsun (genel sohbet, tarih, coğrafya, felsefe, kod, kriz analizi) en yüksek kalitede, eksiksiz, tutarlı ve açıklayıcı yanıt ver."""

class UniversalLLMClient:
    def __init__(self, ollama_url: str = "http://127.0.0.1:11434", gemini_api_key: str = None):
        self.ollama_url = ollama_url
        self.gemini_api_key = gemini_api_key or os.environ.get("GEMINI_API_KEY", "")
        self.knowledge = LocalKnowledgeEngine()
        self.current_model = "qwen2.5:1.5b"
        self.active_backend = "ollama" if self.check_ollama_alive() else ("gemini" if self.gemini_api_key else "local_fallback")
        self.conversation_history = []

    def check_ollama_alive(self) -> bool:
        try:
            req = urllib.request.Request(f"{self.ollama_url}/api/tags", headers={"User-Agent": "KAM-Core"})
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    models = [m["name"] for m in data.get("models", [])]
                    if models and self.current_model not in models:
                        self.current_model = models[0]
                    return True
        except Exception:
            pass
        return False

    def list_available_models(self):
        models = []
        if self.check_ollama_alive():
            try:
                req = urllib.request.Request(f"{self.ollama_url}/api/tags")
                with urllib.request.urlopen(req, timeout=3.0) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    for m in data.get("models", []):
                        models.append({"name": m["name"], "source": "Ollama (Yerel)"})
            except Exception:
                pass
        if self.gemini_api_key:
            models.append({"name": "gemini-1.5-flash", "source": "Google Gemini (Bulut)"})
            models.append({"name": "gemini-2.0-flash", "source": "Google Gemini (Bulut)"})
        models.append({"name": "kam-1-liquid-moe", "source": "KAM Dahili Zihin (Offline)"})
        return models

    def generate(self, user_prompt: str) -> str:
        # RAG Grounding: Doğrulanmış gerçek bilgiyi çek
        grounded_fact = self.knowledge.query(user_prompt)
        system_instruction = BASE_SYSTEM_PROMPT
        if grounded_fact:
            system_instruction += f"\n\n[DOGRULANMIS KESIN BILGI (RAG FACT)]: {grounded_fact}\nBu bilgiyi temel alarak kullanıcıya doğrudan ve net yanıt ver."

        self.conversation_history.append({"role": "user", "content": user_prompt})

        # 1. Gemini Modu (Eğer seçilmişse ve key varsa)
        if self.active_backend == "gemini" and self.gemini_api_key:
            reply = self._call_gemini(user_prompt, system_instruction)
            if reply:
                self.conversation_history.append({"role": "assistant", "content": reply})
                return reply

        # 2. Ollama Modu (Yerel Qwen / Llama / DeepSeek)
        if self.check_ollama_alive():
            reply = self._call_ollama(user_prompt, system_instruction)
            if reply:
                self.conversation_history.append({"role": "assistant", "content": reply})
                return reply

        # 3. Eğer LLM yanıt vermezse ve RAG fact varsa onu dön
        if grounded_fact:
            return grounded_fact

        return "KAM Bilişsel Zihni aktif. Sistem telemetrisi ve bilişsel nöronlar dengede."

    def _call_ollama(self, user_prompt: str, system_instruction: str) -> str:
        try:
            url = f"{self.ollama_url}/api/chat"
            messages = [{"role": "system", "content": system_instruction}] + self.conversation_history[-4:]

            payload = json.dumps({
                "model": self.current_model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": 0.6,
                    "top_p": 0.9
                }
            }).encode("utf-8")

            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=40) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    return data.get("message", {}).get("content", "").strip()
        except Exception as e:
            print(f"[OLLAMA HATA] {e}", file=sys.stderr)
        return None

    def _call_gemini(self, user_prompt: str, system_instruction: str) -> str:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.current_model}:generateContent?key={self.gemini_api_key}"
            contents = []
            for msg in self.conversation_history[-6:]:
                role = "user" if msg["role"] == "user" else "model"
                contents.append({"role": role, "parts": [{"text": msg["content"]}]})

            payload = json.dumps({
                "systemInstruction": {"parts": [{"text": system_instruction}]},
                "contents": contents,
                "generationConfig": {"temperature": 0.7, "maxOutputTokens": 2048}
            }).encode("utf-8")

            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            return parts[0].get("text", "").strip()
        except Exception as e:
            print(f"[GEMINI HATA] {e}", file=sys.stderr)
        return None
