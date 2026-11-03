from dataclasses import dataclass
from typing import List, Optional

@dataclass
class CanMessage:
    can_id: int
    payload: bytes
    is_extended: bool = False

class HardwareBusSimulator:
    """
    CAN-Bus, UART ve SDR veriyolu simülatörü.
    """
    def __init__(self):
        self.can_id_whitelist = {0x100, 0x101, 0x200, 0x205}
        self.filtered_spoofed_packets = 0
        self.active_channel = "UART-2"

    def is_can_packet_valid(self, msg: CanMessage) -> bool:
        if msg.can_id not in self.can_id_whitelist:
            self.filtered_spoofed_packets += 1
            return False
        return True

    def switch_to_sdr_frequency(self, freq_mhz: float = 868.3):
        self.active_channel = f"SDR-{freq_mhz}MHz"
        return self.active_channel
