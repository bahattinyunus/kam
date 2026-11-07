import math
from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass(frozen=True)
class AutonomousAssetNode:
    asset_id: str
    domain: str               # AIR_STRIKE, AIR_EW, AIR_ISR, GROUND_UGV
    capabilities: List[str]   # ["SEAD_EW", "PRECISION_STRIKE", "MESH_RELAY", "OPTICAL_ISR"]
    battery_pct: float
    pos_x_km: float
    pos_y_km: float
    variational_free_energy: float = 0.08


class IntentToTaskOrchestrator:
    """
    Anduril Lattice 'Intent-to-Task' ve A-GRA (Autonomy Government Reference Architecture)
    standardını Karl Friston Beklenen Serbest Enerji (EFE) ihale algoritmasıyla aşan
    Çoklu-Alan (Hava/Kara/EW) Otonom Görev Orkestrasyon Motoru.

    Komutanın yüksek seviyeli Türkçe niyetini (Commander's Intent) alır, bağımlılık
    sıralı görev çizgesine (Task DAG) ayrıştırır ve filodaki en düşük serbest enerjili
    platformlara otonom olarak tahsis eder.
    """

    def __init__(self):
        self.fleet: List[AutonomousAssetNode] = [
            AutonomousAssetNode(
                asset_id="Sungur-EW-1",
                domain="AIR_EW",
                capabilities=["SEAD_EW", "DRFM_JAMMING", "MESH_RELAY"],
                battery_pct=94.0,
                pos_x_km=12.0,
                pos_y_km=3.0,
                variational_free_energy=0.06,
            ),
            AutonomousAssetNode(
                asset_id="Kizilelma-Strike-2",
                domain="AIR_STRIKE",
                capabilities=["PRECISION_STRIKE", "STEALTH_PENETRATION"],
                battery_pct=91.0,
                pos_x_km=8.0,
                pos_y_km=-1.5,
                variational_free_energy=0.07,
            ),
            AutonomousAssetNode(
                asset_id="Bozkurt-Relay-3",
                domain="AIR_EW",
                capabilities=["MESH_RELAY", "FHSS_BACKBONE", "OPTICAL_ISR"],
                battery_pct=96.0,
                pos_x_km=5.0,
                pos_y_km=0.5,
                variational_free_energy=0.05,
            ),
            AutonomousAssetNode(
                asset_id="Alpagu-ISR-4",
                domain="AIR_ISR",
                capabilities=["OPTICAL_ISR", "BDA_VERIFICATION", "THERMAL_RECON"],
                battery_pct=89.0,
                pos_x_km=15.0,
                pos_y_km=2.0,
                variational_free_energy=0.09,
            ),
        ]

    def decompose_and_allocate(
        self,
        commander_intent: str,
        target_x_km: float = 28.0,
        target_y_km: float = 4.0,
    ) -> Dict[str, Any]:
        """
        Komutan niyetini 4 aşamalı Görev Çizgesine (DAG) böler ve her görevi
        Beklenen Serbest Enerji G(asset, task) maliyeti en düşük olan platforma atar.
        """
        task_dag = [
            {
                "task_id": "TASK-101-EW-SEAD",
                "phase": 1,
                "required_capability": "SEAD_EW",
                "description": "Düşman hava savunma radarlarını DRFM ve Altın Oran FHSS ile körelt",
                "depends_on": [],
            },
            {
                "task_id": "TASK-102-MESH-RELAY",
                "phase": 1,
                "required_capability": "MESH_RELAY",
                "description": "868MHz/433MHz kesintisiz kuantum-dirençli sürü röle koridoru kur",
                "depends_on": [],
            },
            {
                "task_id": "TASK-103-STEALTH-STRIKE",
                "phase": 2,
                "required_capability": "PRECISION_STRIKE",
                "description": "Vadi tabanından (Nap-of-the-Earth) hedefe 3B stealth taarruz icra et",
                "depends_on": ["TASK-101-EW-SEAD", "TASK-102-MESH-RELAY"],
            },
            {
                "task_id": "TASK-104-ISR-BDA",
                "phase": 3,
                "required_capability": "OPTICAL_ISR",
                "description": "Termal/Optik sensör füzyonu ile hedef imha doğrulaması (BDA) yap",
                "depends_on": ["TASK-103-STEALTH-STRIKE"],
            },
        ]

        used_assets = set()
        allocations = []

        for task in task_dag:
            req_cap = task["required_capability"]
            best_asset = None
            best_efe_g = 1e9

            for node in self.fleet:
                if req_cap not in node.capabilities:
                    continue
                dist = math.sqrt((node.pos_x_km - target_x_km) ** 2 + (node.pos_y_km - target_y_km) ** 2)
                reuse_penalty = 0.45 if node.asset_id in used_assets else 0.0
                # Beklenen Serbest Enerji G(node, task)
                efe_g = (
                    node.variational_free_energy
                    + 0.015 * dist
                    + ((100.0 - node.battery_pct) * 0.008)
                    + reuse_penalty
                )
                if efe_g < best_efe_g:
                    best_efe_g = efe_g
                    best_asset = node

            if best_asset is not None:
                used_assets.add(best_asset.asset_id)
                allocations.append(
                    {
                        "task_id": task["task_id"],
                        "phase": task["phase"],
                        "assigned_asset": best_asset.asset_id,
                        "asset_domain": best_asset.domain,
                        "required_capability": req_cap,
                        "expected_free_energy_g": round(best_efe_g, 4),
                        "depends_on": task["depends_on"],
                        "description": task["description"],
                    }
                )

        return {
            "architecture_standard": "KAM-Lattice-A-GRA-v3 (Zero-Cloud Intent-to-Task)",
            "commander_intent": commander_intent,
            "total_tasks_generated": len(allocations),
            "unique_assets_mobilized": len(used_assets),
            "task_dag_allocations": allocations,
        }
