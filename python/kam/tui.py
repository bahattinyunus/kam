import time
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

def render_bar(percentage: float, width: int = 24) -> str:
    filled = int(percentage * width)
    empty = width - filled
    if percentage >= 0.80:
        color = "\033[1;31m" # Kırmızı
    elif percentage >= 0.40:
        color = "\033[1;33m" # Sarı
    else:
        color = "\033[1;32m" # Yeşil
    return f"{color}[{'█' * filled}{'░' * empty}]\033[0m {int(percentage * 100)}%"

class KamDashboard:
    def __init__(self):
        self.entropy = 0.03
        self.free_energy = 0.12
        self.active_channel = "UART-2 (Primary)"
        self.npu_temp = 48.0
        self.cpu_load = 14.5
        self.ebpf_events_sec = 2840

    def clear(self):
        os.system("cls" if os.name == "nt" else "clear")

    def display(self, status_msg: str = "Sistem Kararlı & Bilişsel Denge Aktif"):
        self.clear()
        print("\033[1;36m" + "=" * 65 + "\033[0m")
        print("\033[1;35m  🐺 KAM BİLİŞSEL VE KENDİ KENDİNİ İYİLEŞTİREN SİSTEM MOTORU  \033[0m")
        print("\033[1;36m" + "=" * 65 + "\033[0m")
        print(f" Durum: \033[1;32m{status_msg}\033[0m")
        print(f" Aktif Telemetri Hattı : \033[1;34m{self.active_channel}\033[0m")
        print(f" eBPF Çekirdek Olayları : \033[1;33m{self.ebpf_events_sec} kprobe/s\033[0m")
        print("-" * 65)
        print(f" Sistem Entropisi (Kaos) : {render_bar(self.entropy)}")
        print(f" Varyasyonel Serbest E. : {render_bar(min(1.0, self.free_energy / 2.0))} ({self.free_energy:.3f} nat)")
        print(f" NPU Sıcaklığı           : {render_bar(self.npu_temp / 100.0)} ({self.npu_temp:.1f}°C)")
        print(f" CPU Çekirdek Yükü       : {render_bar(self.cpu_load / 100.0)}")
        print("\033[1;36m" + "=" * 65 + "\033[0m")
        print(" Donanım Düğümleri:")
        print("  • [UART-2]       Telemetri Ana Hattı     : " + ("\033[1;32m[ONLINE]\033[0m" if self.entropy < 0.8 else "\033[1;31m[KOPUK - FD DEAD]\033[0m"))
        print("  • [SDR-868]      Yazılım Tanımlı Radyo   : \033[1;32m[STANDBY - HAZIR]\033[0m")
        print("  • [IMU-1]        Ataletsel Ölçüm Birimi  : \033[1;32m[ONLINE]\033[0m")
        print("  • [CAM-FRONT]    Görsel Derinlik / NPU   : \033[1;32m[ONLINE]\033[0m")
        print("-" * 65)
        sys.stdout.flush()

    def simulate_live_dashboard(self):
        self.display("Sistem Başlatıldı. Telemetri Dinleniyor...")
        time.sleep(1.2)

        # Normal dalgalanma
        self.entropy = 0.05
        self.display("Normal Seyir: Uçuş Telemetrisi Akışı Stabil")
        time.sleep(1.0)

        # Kaos Enjeksiyonu
        self.entropy = 0.89
        self.free_energy = 1.84
        self.npu_temp = 72.0
        self.active_channel = "KESİNTİ (UART-2 FILE DESCRIPTOR YANITSIZ)"
        self.display("\033[1;31mKRİTİK KAOS: UART-2 Telemetri Sinyali Kesildi!\033[0m")
        time.sleep(1.5)

        # İyileşme
        self.entropy = 0.15
        self.free_energy = 0.28
        self.npu_temp = 51.0
        self.active_channel = "SDR-868 FHSS (Yedek Hat Devrede)"
        self.display("\033[1;32mİYİLEŞME TAMAMLANDI: sdr_fallback_node.cpp JIT Derlendi ve Bağlandı.\033[0m")
        time.sleep(1.2)
