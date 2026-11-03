from dataclasses import dataclass
from typing import List, Dict

@dataclass
class SwarmDrone:
    drone_id: str
    is_leader: bool
    is_alive: bool
    battery_pct: float
    current_freq_mhz: float

class SwarmMeshController:
    """
    Sürü İHA ağı ve Lider Kaybında Otonom Konsensüs Algoritması
    """
    def __init__(self):
        self.drones = {
            "Alpha-1": SwarmDrone("Alpha-1", is_leader=True, is_alive=True, battery_pct=92.0, current_freq_mhz=868.1),
            "Bravo-2": SwarmDrone("Bravo-2", is_leader=False, is_alive=True, battery_pct=95.0, current_freq_mhz=868.1),
            "Charlie-3": SwarmDrone("Charlie-3", is_leader=False, is_alive=True, battery_pct=88.0, current_freq_mhz=868.1),
            "Delta-4": SwarmDrone("Delta-4", is_leader=False, is_alive=True, battery_pct=91.0, current_freq_mhz=868.1)
        }
        self.active_leader = "Alpha-1"

    def simulate_leader_loss(self) -> str:
        self.drones["Alpha-1"].is_alive = False
        self.drones["Alpha-1"].is_leader = False

        # KAM Konsensüs: En yüksek batarya ve sinyal kalitesine sahip İHA lider seçilir
        alive_drones = [d for d in self.drones.values() if d.is_alive]
        new_leader = max(alive_drones, key=lambda d: d.battery_pct)
        new_leader.is_leader = True
        self.active_leader = new_leader.drone_id

        # Tüm sürüyü yeni güvenli frekansa geçir (868.9 MHz)
        for d in alive_drones:
            d.current_freq_mhz = 868.9

        return self.active_leader
