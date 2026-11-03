#!/usr/bin/env python3
import struct
import os
import sys
import math

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

def generate_weights():
    os.makedirs("models", exist_ok=True)
    out_path = os.path.join("models", "kam_weights_v1.bin")

    magic = b"KAM1" # 4 bytes
    version = 1     # uint32
    input_dim = 16  # uint32
    hidden_dim = 64 # uint32
    num_experts = 8 # uint32

    # Ağırlık üretimi
    w_gate = [math.sin(i * 0.3) * 0.25 for i in range(num_experts * input_dim)]
    w_in = [math.cos(i * 0.15) * 0.3 for i in range(hidden_dim * input_dim)]
    w_hh = [math.sin(i * 0.2) * 0.1 for i in range(hidden_dim * hidden_dim)]
    b_ode = [0.01 for _ in range(hidden_dim)]

    total_floats = len(w_gate) + len(w_in) + len(w_hh) + len(b_ode)

    with open(out_path, "wb") as f:
        f.write(magic)
        f.write(struct.pack("<IIII", version, input_dim, hidden_dim, num_experts))
        for val in w_gate:
            f.write(struct.pack("<f", val))
        for val in w_in:
            f.write(struct.pack("<f", val))
        for val in w_hh:
            f.write(struct.pack("<f", val))
        for val in b_ode:
            f.write(struct.pack("<f", val))

    file_size_kb = os.path.getsize(out_path) / 1024
    print(f"[KAM-AĞIRLIK] {out_path} başarıyla oluşturuldu. Boyut: {file_size_kb:.2f} KB ({total_floats} parametre).")

if __name__ == "__main__":
    generate_weights()
