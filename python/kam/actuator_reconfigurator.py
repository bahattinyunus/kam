import math
from typing import List, Dict, Any


class ActuatorFaultReconfigurator:
    """
    Kinetik Hasar ve Eyleyici (Actuator/Servo/Motor) Arızası Altında Ağırlıklı
    Sözde-Ters (Weighted Moore-Penrose Pseudo-Inverse) Kontrol Tahsisi Motoru.

    Fiziksel kanatçık sıkışması (Jammed Elevon/Aileron) veya motor/servo kaybı
    durumunda; istenen sanal moment vektörünü v = [Roll (L), Pitch (M), Yaw (N)]^T
    sağlam kalan yedekli kontrol yüzeylerine (sol/sağ elevon, sol/sağ V-kuyruk
    dümeni, diferansiyel itki vektörlemesi) milisaniyede yeniden dağıtır:

        v_compensated = v_desired - B[:, j] * u_stuck_j
        u_healthy = W * B_eff^T * (B_eff * W * B_eff^T + lambda * I)^(-1) * v_compensated
    """

    ACTUATOR_NAMES = [
        "LEFT_ELEVON",
        "RIGHT_ELEVON",
        "LEFT_RUDDERVATOR",
        "RIGHT_RUDDERVATOR",
        "THRUST_VECTOR_YAW_PITCH",
        "DIFF_PROPULSION_TRIM",
    ]

    # 3x6 Kontrol Etkinlik Matrisi B (Satırlar: [Roll L, Pitch M, Yaw N], Sütunlar: 6 Eyleyici)
    B_NOMINAL: List[List[float]] = [
        [ 0.85, -0.85,  0.30, -0.30,  0.05,  0.45],  # Roll (Yatış) momenti etkinliği
        [ 0.65,  0.65,  0.55,  0.55,  0.80,  0.10],  # Pitch (Yunuslama) momenti etkinliği
        [-0.15,  0.15,  0.75, -0.75,  0.85,  0.60],  # Yaw (Sapma) momenti etkinliği
    ]

    @staticmethod
    def _invert_3x3(m: List[List[float]]) -> List[List[float]]:
        a, b, c = m[0][0], m[0][1], m[0][2]
        d, e, f = m[1][0], m[1][1], m[1][2]
        g, h, i = m[2][0], m[2][1], m[2][2]

        A = e * i - f * h
        B = -(d * i - f * g)
        C = d * h - e * g
        D = -(b * i - c * h)
        E = a * i - c * g
        F = -(a * h - b * g)
        G = b * f - c * e
        H = -(a * f - c * d)
        I_cof = a * e - b * d

        det = a * A + b * B + c * C
        if abs(det) < 1e-9:
            det = 1e-9 if det >= 0 else -1e-9

        inv_det = 1.0 / det
        return [
            [A * inv_det, D * inv_det, G * inv_det],
            [B * inv_det, E * inv_det, H * inv_det],
            [C * inv_det, F * inv_det, I_cof * inv_det],
        ]

    @classmethod
    def reconfigure_control_allocation(
        cls,
        desired_moments_lmn: List[float] = None,
        health_weights: List[float] = None,
        stuck_deflections_rad: Dict[int, float] = None,
        damping_lambda: float = 1e-4,
    ) -> Dict[str, Any]:
        """
        Arızalı veya sıkışmış eyleyicileri telafi eden yeni kontrol dağılımını hesaplar.
        - desired_moments_lmn: [Roll, Pitch, Yaw] hedef moment vektörü
        - health_weights: 6 eyleyici için [0.0 (kayıp/sıkışmış) .. 1.0 (tam sağlam)] sağlık ağırlıkları
        - stuck_deflections_rad: {eyleyici_indeksi: sıkıştığı_açı_radyan} (parasitik momenti telafi eder)
        """
        if desired_moments_lmn is None:
            desired_moments_lmn = [0.45, 0.60, -0.25]
        if health_weights is None:
            # Varsayılan kriz: Sol Elevon (indis 0) +0.22 rad açıda kilitlendi (w_0 = 0.0)
            health_weights = [0.0, 1.0, 1.0, 1.0, 1.0, 1.0]
        if stuck_deflections_rad is None:
            stuck_deflections_rad = {0: 0.22}

        w = [max(0.0, min(1.0, float(hw))) for hw in health_weights]
        for stuck_idx in stuck_deflections_rad:
            if 0 <= stuck_idx < 6:
                w[stuck_idx] = 0.0

        # 1. Sıkışmış kanatçığın ürettiği bozucu (parasitik) momenti hesapla ve hedeften çıkar
        parasitic_lmn = [0.0, 0.0, 0.0]
        for idx, stuck_val in stuck_deflections_rad.items():
            if 0 <= idx < 6:
                for row in range(3):
                    parasitic_lmn[row] += cls.B_NOMINAL[row][idx] * float(stuck_val)

        v_comp = [desired_moments_lmn[r] - parasitic_lmn[r] for r in range(3)]

        # 2. M = B * W * B^T + lambda * I (3x3 matris)
        m_mat = [[0.0, 0.0, 0.0] for _ in range(3)]
        for r in range(3):
            for c in range(3):
                s = 0.0
                for k in range(6):
                    s += cls.B_NOMINAL[r][k] * w[k] * cls.B_NOMINAL[c][k]
                if r == c:
                    s += damping_lambda
                m_mat[r][c] = s

        m_inv = cls._invert_3x3(m_mat)

        # 3. z = M^(-1) * v_comp (3x1 vektör)
        z = [sum(m_inv[r][c] * v_comp[c] for c in range(3)) for r in range(3)]

        # 4. u_healthy = W * B^T * z (6x1 eyleyici komutu)
        u_cmd = [0.0] * 6
        for k in range(6):
            if k in stuck_deflections_rad:
                u_cmd[k] = float(stuck_deflections_rad[k])
            else:
                bt_z = sum(cls.B_NOMINAL[r][k] * z[r] for r in range(3))
                u_cmd[k] = w[k] * bt_z

        # 5. Elde edilen gerçek momenti doğrula: v_achieved = B * u_cmd
        v_achieved = [
            sum(cls.B_NOMINAL[r][k] * u_cmd[k] for k in range(6)) for r in range(3)
        ]
        tracking_error_norm = math.sqrt(
            sum((desired_moments_lmn[r] - v_achieved[r]) ** 2 for r in range(3))
        )

        allocations = []
        for k in range(6):
            status = "JAMMED_ISOLATED" if k in stuck_deflections_rad else ("ACTIVE_COMPENSATING" if w[k] > 0.0 else "DISABLED")
            allocations.append({
                "actuator": cls.ACTUATOR_NAMES[k],
                "health_weight": round(w[k], 2),
                "command_rad": round(u_cmd[k], 4),
                "status": status,
            })

        return {
            "allocator": "KAM-Weighted-PseudoInverse-Control-Reconfigurator",
            "desired_moments_lmn": [round(x, 4) for x in desired_moments_lmn],
            "parasitic_jam_moments_lmn": [round(x, 4) for x in parasitic_lmn],
            "achieved_moments_lmn": [round(x, 4) for x in v_achieved],
            "moment_tracking_error_l2": round(tracking_error_norm, 6),
            "control_authority_preserved": tracking_error_norm < 0.01,
            "actuator_allocations": allocations,
            "recommended_cpp_patch": "actuator_mixer_reconfig.cpp",
        }
