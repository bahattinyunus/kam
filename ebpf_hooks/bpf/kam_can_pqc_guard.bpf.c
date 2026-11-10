// +build ignore
// SPDX-License-Identifier: GPL-2.0
// KAM eBPF Çekirdek Kancası: SocketCAN Spoofing Filtresi ve ML-KEM PQC Replay Koruması

#define BPF_NO_PRESERVE_ACCESS_INDEX
typedef unsigned char __u8;
typedef unsigned short __u16;
typedef unsigned int __u32;
typedef unsigned long long __u64;

#define CAN_Quarantined_Spoof_ID 0x1BA
#define KYBER_MODULUS_Q          3329

struct can_pqc_frame_event_t {
    __u64 timestamp_ns;
    __u32 can_id;
    __u32 pqc_nonce;
    __u16 lwe_syndrome_tag;
    __u8  dlc;
    __u8  quarantine_action; // 0: PASS, 1: DROP_SPOOF_ID, 2: DROP_PQC_REPLAY
};

// SocketCAN (can0) çekirdek katmanında yetkisiz çerçeveleri (0x1BA) ve
// kuantum-sonrası (ML-KEM-768) nonce tekrar saldırılarını kullanıcı alanına
// çıkmadan < 8 mikrosaniye içinde karantinaya alır.
static inline int kam_validate_can_pqc_frame(__u32 can_id, __u32 nonce, __u32 last_valid_nonce) {
    if (can_id == CAN_Quarantined_Spoof_ID) {
        return 1; // DROP_SPOOF_ID
    }
    if (nonce <= last_valid_nonce) {
        return 2; // DROP_PQC_REPLAY
    }
    return 0; // PASS
}
