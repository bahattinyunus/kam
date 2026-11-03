// +build ignore
// SPDX-License-Identifier: GPL-2.0
// KAM eBPF Çekirdek Kancası: File Descriptor & UART Telemetry Monitor

#define BPF_NO_PRESERVE_ACCESS_INDEX
typedef unsigned char __u8;
typedef unsigned short __u16;
typedef unsigned int __u32;
typedef unsigned long long __u64;

#define TASK_COMM_LEN 16

struct fd_event_t {
    __u64 timestamp_ns;
    __u32 pid;
    __u32 fd;
    __u64 bytes_transferred;
    int error_code;
    char comm[TASK_COMM_LEN];
};

// Bu yapı libbpf ring_buffer üzerinden kullanıcı alanına (C++ telemetri motoruna) aktarılır.
// UART ve SDR telemetri hatlarındaki kesilmeleri (EBADF, EIO, ENOTCONN) milisaniye seviyesinde yakalar.
