import math
from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class SwarmDrone:
    drone_id: str
    is_leader: bool
    is_alive: bool
    battery_pct: float
    current_freq_mhz: float
    link_snr_db: float = 24.0

    @property
    def variational_free_energy(self) -> float:
        """
        Dağıtık Markov Battaniyesi düğüm serbest enerjisi F_i:
        Batarya seviyesi yüksek ve SNR güçlü olan birimin entropisi/serbest enerjisi en düşüktür.
        """
        if not self.is_alive:
            return 999.0
        battery_deficit = max(0.0, (100.0 - self.battery_pct) / 100.0)
        snr_penalty = max(0.0, (30.0 - self.link_snr_db) / 40.0)
        return round(0.05 + 1.8 * battery_deficit + 0.9 * snr_penalty, 4)


class SwarmMeshController:
    """
    Dağıtık Markov Battaniyesi Sürü İHA Ağı, Kolektif Serbest Enerji Minimizasyonu (Raft/eBPF)
    ve Altın Oran (Golden-Ratio) FHSS Spektral Sıçrama Motoru.
    """

    GOLDEN_RATIO_CONJUGATE = 0.6180339887498949

    def __init__(self):
        self.drones = {
            "Alpha-1": SwarmDrone("Alpha-1", is_leader=True, is_alive=True, battery_pct=92.0, current_freq_mhz=868.1, link_snr_db=25.0),
            "Bravo-2": SwarmDrone("Bravo-2", is_leader=False, is_alive=True, battery_pct=95.0, current_freq_mhz=868.1, link_snr_db=27.5),
            "Charlie-3": SwarmDrone("Charlie-3", is_leader=False, is_alive=True, battery_pct=88.0, current_freq_mhz=868.1, link_snr_db=22.0),
            "Delta-4": SwarmDrone("Delta-4", is_leader=False, is_alive=True, battery_pct=91.0, current_freq_mhz=868.1, link_snr_db=24.5),
        }
        self.active_leader = "Alpha-1"
        self.consensus_term = 1

    def generate_fhss_hop_sequence(
        self,
        num_hops: int = 8,
        base_freq_mhz: float = 868.0,
        bandwidth_mhz: float = 2.0,
        seed_phase: float = 0.1337,
    ) -> List[float]:
        """
        Elektronik harp karıştırmasına (-95 dBm) karşı Altın Oran (Low-Discrepancy Weyl Sequence)
        tabanlı deterministik frekans sıçrama dizisi üretir.
        """
        hops: List[float] = []
        phase = seed_phase
        for _ in range(max(1, num_hops)):
            phase = (phase + self.GOLDEN_RATIO_CONJUGATE) % 1.0
            freq = base_freq_mhz + phase * bandwidth_mhz
            hops.append(round(freq, 3))
        return hops

    def simulate_leader_loss(self) -> str:
        self.drones["Alpha-1"].is_alive = False
        self.drones["Alpha-1"].is_leader = False
        self.consensus_term += 1

        # KAM Kolektif Serbest Enerji Konsensüsü: En düşük F_i (ve en yüksek batarya/SNR) değerine sahip birim lider seçilir
        alive_drones = [d for d in self.drones.values() if d.is_alive]
        new_leader = min(alive_drones, key=lambda d: d.variational_free_energy)
        new_leader.is_leader = True
        self.active_leader = new_leader.drone_id

        # Tüm sürüyü yeni güvenli frekansa geçir (868.9 MHz)
        for d in alive_drones:
            d.current_freq_mhz = 868.9

        return self.active_leader

    def get_swarm_telemetry(self) -> Dict[str, Any]:
        alive = [d for d in self.drones.values() if d.is_alive]
        collective_fe = sum(d.variational_free_energy for d in alive) / float(max(1, len(alive)))
        return {
            "active_leader": self.active_leader,
            "consensus_term": self.consensus_term,
            "alive_units": len(alive),
            "collective_free_energy": round(collective_fe, 4),
            "fhss_next_hops_mhz": self.generate_fhss_hop_sequence(num_hops=4),
        }

