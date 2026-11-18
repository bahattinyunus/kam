// +build ignore
// SPDX-License-Identifier: GPL-2.0
// KAM eBPF Çekirdek Kancası: EDAC / MCE Donanım Bellek Bit-Flip (SEU/MBU) ve ECC Sendrom İzleyicisi

#define BPF_NO_PRESERVE_ACCESS_INDEX
typedef unsigned char __u8;
typedef unsigned short __u16;
typedef unsigned int __u32;
typedef unsigned long long __u64;

#define ECC_ACTION_NONE              0
#define ECC_ACTION_SECDED_AUTO_FIX   1
#define ECC_ACTION_TMR_BANK_SCRUB    2

struct edac_ecc_bitflip_event_t {
    __u64 timestamp_ns;
    __u64 physical_page_addr;
    __u64 corrupted_word64;
    __u8  secded_syndrome;
    __u8  overall_parity_err;
    __u8  remediation_action; // 1: SECDED 1-Bit Repair, 2: TMR 3-Bank Scrub
};

// Linux çekirdeği tracepoint:mce:mce_record ve kprobe:edac_mc_handle_error
// kancalarından gelen donanım SRAM/DRAM/NPU bit tersinmelerini < 6 mikrosaniyede
// sınıflandırarak kullanıcı alanı TMR/SECDED bellek temizleyicisini tetikler.
static inline int kam_classify_edac_ecc_syndrome(__u8 syndrome, __u8 overall_parity_err) {
    if (syndrome == 0 && overall_parity_err == 0) {
        return ECC_ACTION_NONE;
    }
    if (syndrome != 0 && overall_parity_err == 1) {
        return ECC_ACTION_SECDED_AUTO_FIX; // Tekil Bit Tersinmesi (SEU)
    }
    return ECC_ACTION_TMR_BANK_SCRUB;      // Çoklu Bit Tersinmesi (MBU) -> TMR Çoğunluk Oylaması
}
