import math
from dataclasses import dataclass
from typing import List, Dict, Any, Tuple


@dataclass(frozen=True)
class RadarThreatDome:
    threat_id: str
    center_x_km: float
    center_y_km: float
    base_alt_m: float
    effective_range_km: float
    radar_power_factor: float = 1.0


class TacticalRoutePlanner3D:
    """
    KAM 3-Boyutlu Taktik SİHA / İHA Radar Sönümleme ve Aktif Çıkarım Rota Planlayıcısı.
    Düşman hava savunma radarlarının (SAM) 1/R^4 radar menzil denklemi ve arazi maskelemesi
    (Nap-of-the-Earth / Terrain Masking) altında Beklenen Serbest Enerjiyi G(pi)
    minimize eden 3-boyutlu (x, y, z) stealth uçuş koridorunu hesaplar.
    """

    def __init__(self, rcs_m2: float = 0.015):
        # Stealth SİHA Radar Kesit Alanı (RCS - m^2)
        self.rcs_m2 = rcs_m2
        self.threats: List[RadarThreatDome] = [
            RadarThreatDome("SAM-S400-BAT1", center_x_km=18.0, center_y_km=4.0, base_alt_m=420.0, effective_range_km=14.0),
            RadarThreatDome("EW-XBAND-RAD2", center_x_km=32.0, center_y_km=-3.5, base_alt_m=380.0, effective_range_km=12.0),
        ]

    @staticmethod
    def terrain_elevation_m(x_km: float, y_km: float) -> float:
        """
        Sentetik dağlık/vadilik topografya yüksekliği z_terrain(x, y) (metre).
        """
        ridge = 320.0 * math.sin(x_km * 0.18) * math.cos(y_km * 0.22)
        valley = 140.0 * math.cos(x_km * 0.35 + y_km * 0.15)
        return max(80.0, 450.0 + ridge + valley)

    def compute_radar_exposure(self, x_km: float, y_km: float, alt_m: float) -> float:
        """
        1/R^4 Radar Menzil Denklemi ve Arazi Ufuk Maskelemesi (Terrain Horizon Masking)
        ile anlık radar tespit olasılığını [0.0 - 1.0] hesaplar.
        """
        terrain_z = self.terrain_elevation_m(x_km, y_km)
        agl_m = max(15.0, alt_m - terrain_z)
        # Vadi tabanında alçak irtifa (AGL < 120m) arazi maskeleme katsayısı sağlar
        terrain_masking = min(1.0, (agl_m / 180.0) ** 1.6)

        total_risk = 0.0
        for t in self.threats:
            dx = x_km - t.center_x_km
            dy = y_km - t.center_y_km
            dz_km = (alt_m - t.base_alt_m) / 1000.0
            dist_km = math.sqrt(dx * dx + dy * dy + dz_km * dz_km + 0.25)

            # Radar denklemi: Sinyal gücü ~ (RCS * P) / R^4
            norm_r = dist_km / max(t.effective_range_km, 1.0)
            r4_term = 1.0 / (1.0 + (norm_r ** 4))
            risk_i = r4_term * terrain_masking * (0.5 + 15.0 * self.rcs_m2) * t.radar_power_factor
            total_risk = 1.0 - (1.0 - total_risk) * (1.0 - min(0.98, risk_i))

        return round(min(1.0, max(0.0, total_risk)), 4)

    def plan_stealth_trajectory(
        self,
        start_xyz: Tuple[float, float, float] = (0.0, 0.0, 620.0),
        target_xyz: Tuple[float, float, float] = (50.0, 0.0, 580.0),
        num_segments: int = 12,
    ) -> Dict[str, Any]:
        """
        Başlangıç ve hedef noktası arasında her adımda aday yanal/dikey manevraların
        Beklenen Serbest Enerjisini G(u) = w_1 * Radar_Risk + w_2 * Hedef_Sapma + w_3 * Enerji
        hesaplayarak en güvenli 3B vadi süzülüş (Nap-of-the-Earth) rotasını üretir.
        """
        cx, cy, cz = start_xyz
        tx, ty, tz = target_xyz
        waypoints: List[Dict[str, float]] = [
            {
                "step": 0,
                "x_km": round(cx, 2),
                "y_km": round(cy, 2),
                "alt_m": round(cz, 1),
                "terrain_m": round(self.terrain_elevation_m(cx, cy), 1),
                "radar_risk": self.compute_radar_exposure(cx, cy, cz),
            }
        ]

        lateral_offsets = [-3.5, -1.8, -0.6, 0.0, 0.6, 1.8, 3.5]
        agl_choices = [55.0, 85.0, 130.0, 210.0]

        total_dist_km = 0.0
        for step in range(1, num_segments + 1):
            alpha = step / float(num_segments)
            next_x = start_xyz[0] + alpha * (tx - start_xyz[0])

            if step == num_segments:
                best_y = ty
                best_z = max(tz, self.terrain_elevation_m(next_x, ty) + 60.0)
                best_risk = self.compute_radar_exposure(next_x, best_y, best_z)
            else:
                best_g = 1e9
                best_y = cy
                best_z = cz
                best_risk = 0.0

                for dy in lateral_offsets:
                    cand_y = cy + dy
                    t_elev = self.terrain_elevation_m(next_x, cand_y)
                    for agl in agl_choices:
                        cand_z = t_elev + agl
                        risk = self.compute_radar_exposure(next_x, cand_y, cand_z)
                        goal_dev = abs(cand_y - ty) * 0.035
                        climb_cost = abs(cand_z - cz) * 0.0008
                        # Beklenen Serbest Enerji G(u)
                        g_score = (3.8 * risk) + goal_dev + climb_cost
                        if g_score < best_g:
                            best_g = g_score
                            best_y = cand_y
                            best_z = cand_z
                            best_risk = risk

            seg_d = math.sqrt((next_x - cx) ** 2 + (best_y - cy) ** 2 + ((best_z - cz) / 1000.0) ** 2)
            total_dist_km += seg_d
            cx, cy, cz = next_x, best_y, best_z

            waypoints.append(
                {
                    "step": step,
                    "x_km": round(cx, 2),
                    "y_km": round(cy, 2),
                    "alt_m": round(cz, 1),
                    "terrain_m": round(self.terrain_elevation_m(cx, cy), 1),
                    "radar_risk": best_risk,
                }
            )

        max_risk = max(w["radar_risk"] for w in waypoints)
        mean_agl = sum(w["alt_m"] - w["terrain_m"] for w in waypoints) / float(len(waypoints))
        survival_prob = round((1.0 - max_risk * 0.45) * 100.0, 2)

        return {
            "planner": "KAM-3D-EFE-Stealth-Navigator",
            "waypoints": waypoints,
            "total_distance_km": round(total_dist_km, 2),
            "max_radar_exposure_risk": round(max_risk, 4),
            "mean_agl_altitude_m": round(mean_agl, 1),
            "mission_survival_probability_pct": survival_prob,
        }
