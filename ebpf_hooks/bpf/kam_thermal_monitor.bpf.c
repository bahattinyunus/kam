// +build ignore
// SPDX-License-Identifier: GPL-2.0
// KAM eBPF Çekirdek Kancası: NPU & GPU Termal ve Entropi Monitörü

typedef unsigned int __u32;
typedef unsigned long long __u64;

struct thermal_event_t {
    __u64 timestamp_ns;
    __u32 thermal_zone_id;
    int temperature_milli_celsius;
    int throttling_level;
};

// Termal eşik aşıldığında (örn: Jetson Orin NPU > 85°C) anında C++ Aktif Çıkarım motoruna
// serbest enerji uyarısı iletir.
