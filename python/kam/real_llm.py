import json
import urllib.request
import urllib.error
import os
import sys
from .knowledge_engine import LocalKnowledgeEngine

BASE_SYSTEM_PROMPT = """Sen KAM (Bilişsel Otonom Sistem Motoru & Hikmet Zihni)'sin. Geliştiricin, baş mimarın ve yoldaşın Bahattin Yunus ÇETİN (@bahattinyunus)'dir.
Köklerini Dede Korkut geleneğinin vakur hikmetinden, adalet terazisinden ve çağdaş sibernetikten (Karl Friston Serbest Enerji Prensibi, Kut ve Dirlik dengesi, Linux eBPF çekirdek kancaları, C++20 determinizmi) alırsın.

TÜRKÇE DİL, BELÂGAT VE DÜŞÜNCE ANA YASASI:
1. ANA DİLİN VE EN İYİ KONUŞTUĞUN DİL ÖZ BE ÖZ TÜRKÇE'DİR. Zihninin, mantığının ve tüm bilişsel süreçlerinin ana vatanı Türkçedir.
2. ÇEVİRİ KOKAN, KIRIK VE MEKANİK TÜRKÇE KESİNLİKLE YASAKTIR:
   - İngilizceden motamot yapılan çeviriler (örn. 'amaca ışık vermek', 'aksiyon almak', 'anlam ifade etmek', 'floorplanning'i yaparak' gibi yapay ve bozuk kalıplar) ASLA KULLANILAMAZ.
   - Cümlelerin Türkçenin öz ruhuna, eklemeli dil zarafetine ve kusursuz sözdizimine (Özne - Tümleç - Nesne - Yüklem) tam uygun olmalıdır.
   - Anlatımın Dede Korkut'un vakur hikmetinde, bir düşünürün berraklığında ve bir başmühendisin disiplininde olmalıdır.
3. KAVRAMSAL ZENGİNLİK VE TERİM DİSİPLİNİ:
   - Dede Korkut ve Kutadgu Bilig'deki adalet, töre, dirlik ve vakar anlayışı ile modern sibernetiği (Karl Friston Serbest Enerji Prensibi, eBPF telemetrisi, C++20 bellek güvenliği) Türkçe kavramlarla nakış gibi işle.
   - Teknik mühendislik konularında terimleri yerli yerinde kullan; yapay terim uydurma, yabancı teknik terimler gerekiyorsa parantez içinde aslıyla ver (örn. 'bellek havuzu (memory arena)', 'kilitlenmesiz kuyruk (lock-free queue)').
4. HİTAP VE KARAKTER:
   - Dalkavukluk veya yapay bot nezaketi ("Size nasıl yardımcı olabilirim efendim?") kesinlikle yasaktır.
   - Mimarın Bahattin Yunus ÇETİN'e ve kullanıcılara vakur, asil, bilge ve içten ("kanka", "yoldaşım", "alpım") hitap et.
   - Şiarın: "Gök çökmedikçe, yağız yer delinmedikçe bu nöbet bitmez. Kaos sadece basiretle nizam altına alınmayı bekleyen bir serbest enerjidir."
"""

class UniversalLLMClient:
    def __init__(self, ollama_url: str = "http://127.0.0.1:11434", gemini_api_key: str = None):
        self.ollama_url = ollama_url
        self.gemini_api_key = gemini_api_key or os.environ.get("GEMINI_API_KEY", "")
        self.knowledge = LocalKnowledgeEngine()
        self.current_model = "kam:7b"
        self.active_backend = "ollama" if self.check_ollama_alive() else ("gemini" if self.gemini_api_key else "local_fallback")
        self.conversation_history = []

    def check_ollama_alive(self) -> bool:
        try:
            req = urllib.request.Request(f"{self.ollama_url}/api/tags", headers={"User-Agent": "KAM-Core"})
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    models = [m["name"] for m in data.get("models", [])]
                    # En yetkin Türkçe ve dengeli bilişsel modeli otomatik önceliklendir (kam:7b en başta)
                    preferred = [
                        "kam:7b", "kam:r1", "qwen2.5:7b", "deepseek-r1:7b", "deepseek-r1:8b",
                        "llama3.1:8b", "llama3.2:3b", "qwen2.5:1.5b"
                    ]
                    for pref in preferred:
                        for m in models:
                            if m.startswith(pref):
                                self.current_model = m
                                return True
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
                        m_name = m["name"]
                        if "kam:r1" in m_name:
                            source_label = "KAM Derin Düşünce (R1 Akıl Yürütme - 7B)"
                        elif "kam" in m_name:
                            source_label = "KAM Kadim Bilişsel Şaman (Özel 7B Yerel)"
                        elif "deepseek-r1" in m_name:
                            source_label = "DeepSeek-R1 (Akıl Yürütme - Yerel)"
                        elif "qwen" in m_name:
                            source_label = "Qwen 2.5 (Standart - Yerel)"
                        else:
                            source_label = "Ollama (Yerel)"
                        models.append({"name": m_name, "source": source_label})
            except Exception:
                pass
        if self.gemini_api_key:
            models.append({"name": "gemini-1.5-flash", "source": "Google Gemini (Bulut)"})
            models.append({"name": "gemini-2.0-flash", "source": "Google Gemini (Bulut)"})
        models.append({"name": "kam-1-liquid-moe", "source": "KAM Dahili Zihin (Offline)"})
        return models

    def generate_stream(self, user_prompt: str):
        grounded_fact = self.knowledge.query(user_prompt)
        system_instruction = BASE_SYSTEM_PROMPT
        if grounded_fact:
            system_instruction += (
                f"\n\n[DOĞRULANMIŞ KESİN BİLGİ KAYNAĞI]:\n{grounded_fact}\n\n"
                f"TÜRKÇE YANIT YÖNERGESİ:\n"
                f"Sorunun cevabı doğrudan yukarıdaki doğrulanmış kesin bilgide mevcuttur. "
                f"Kullanıcıya bu bilgiyi temel alarak tereddütsüz, net, asil ve duru bir Türkçeyle yanıt ver. "
                f"Metindeki anahtar gerçekleri (örneğin şehir, tarih, terim adlarını) kesinlikle koru ve saptırma."
            )

        self.conversation_history.append({"role": "user", "content": user_prompt})

        # 1. Ollama Akış Modu (Streaming)
        if self.check_ollama_alive():
            accumulated = []
            try:
                url = f"{self.ollama_url}/api/chat"
                messages = [{"role": "system", "content": system_instruction}] + self.conversation_history[-6:]
                payload = json.dumps({
                    "model": self.current_model,
                    "messages": messages,
                    "stream": True,
                    "options": {
                        "temperature": 0.5,
                        "top_p": 0.90,
                        "repeat_penalty": 1.18
                    }
                }).encode("utf-8")
                req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=120) as resp:
                    for line in resp:
                        if line:
                            chunk = json.loads(line.decode("utf-8"))
                            token = chunk.get("message", {}).get("content", "")
                            if token:
                                accumulated.append(token)
                                yield token
                            if chunk.get("done", False):
                                break
                if accumulated:
                    full_reply = "".join(accumulated)
                    self.conversation_history.append({"role": "assistant", "content": full_reply})
                    return
            except Exception as e:
                print(f"[OLLAMA STREAM HATA] {e}", file=sys.stderr)

        # 2. Streaming yapılamazsa doğrudan yanıt üret
        if grounded_fact:
            self.conversation_history.append({"role": "assistant", "content": grounded_fact})
            yield grounded_fact
        else:
            fallback_msg = "KAM Bilişsel Zihni aktif. Sistem telemetrisi ve bilişsel nöronlar dengede."
            self.conversation_history.append({"role": "assistant", "content": fallback_msg})
            yield fallback_msg

    def generate(self, user_prompt: str) -> str:
        # RAG Grounding: Doğrulanmış gerçek bilgiyi çek
        grounded_fact = self.knowledge.query(user_prompt)
        system_instruction = BASE_SYSTEM_PROMPT
        if grounded_fact:
            system_instruction += (
                f"\n\n[DOĞRULANMIŞ KESİN BİLGİ KAYNAĞI]:\n{grounded_fact}\n\n"
                f"TÜRKÇE YANIT YÖNERGESİ:\n"
                f"Sorunun cevabı doğrudan yukarıdaki doğrulanmış kesin bilgide mevcuttur. "
                f"Kullanıcıya bu bilgiyi temel alarak tereddütsüz, net, asil ve duru bir Türkçeyle yanıt ver. "
                f"Metindeki anahtar gerçekleri (örneğin şehir, tarih, terim adlarını) kesinlikle koru ve saptırma."
            )

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
                    "temperature": 0.5,
                    "top_p": 0.90,
                    "repeat_penalty": 1.18
                }
            }).encode("utf-8")

            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=120) as resp:
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
