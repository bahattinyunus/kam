import math
from dataclasses import dataclass
from typing import List


@dataclass
class EKFState:
    x: float
    y: float
    z: float
    vx: float
    vy: float
    vz: float
    gps_active: bool
    dead_reckoning: bool
    mahalanobis_distance: float = 0.0
    position_uncertainty_m: float = 1.0


class SensorFusionEKF:
    """
    6-DOF Genişletilmiş Kalman Filtresi (EKF), Kovaryans Matrisi Yayılımı,
    Mahalanobis Yenilik (Innovation) Spoofing Kapısı ve Optik Akış Ölü-Hesaplama Motoru.
    """

    def __init__(self):
        self.x = 0.0
        self.y = 0.0
        self.z = 100.0
        self.vx = 15.0
        self.vy = 0.0
        self.vz = 0.0
        # Durum kovaryans köşegeni P = diag(px, py, pz, pvx, pvy, pvz)
        self.cov_p: List[float] = [2.5, 2.5, 3.0, 0.5, 0.5, 0.5]
        self.process_noise_q: List[float] = [0.15, 0.15, 0.20, 0.08, 0.08, 0.08]
        self.gps_noise_r: List[float] = [3.2, 3.2, 4.5]
        self.gps_active = True
        self.dead_reckoning = False
        self.last_mahalanobis_distance = 0.0
        self.spoofing_events_detected = 0

    def predict(self, dt: float = 0.1, ax: float = 0.0, ay: float = 0.0, az: float = 0.0):
        # Durum geçişi: x_{k|k-1} = F * x_{k-1} + B * u_k
        self.x += self.vx * dt + 0.5 * ax * dt * dt
        self.y += self.vy * dt + 0.5 * ay * dt * dt
        self.z += self.vz * dt + 0.5 * az * dt * dt
        self.vx += ax * dt
        self.vy += ay * dt
        self.vz += az * dt

        # Kovaryans yayılımı: P_{k|k-1} = F * P * F^T + Q
        self.cov_p[0] += (self.cov_p[3] * dt * dt) + self.process_noise_q[0]
        self.cov_p[1] += (self.cov_p[4] * dt * dt) + self.process_noise_q[1]
        self.cov_p[2] += (self.cov_p[5] * dt * dt) + self.process_noise_q[2]
        self.cov_p[3] += self.process_noise_q[3]
        self.cov_p[4] += self.process_noise_q[4]
        self.cov_p[5] += self.process_noise_q[5]

    def compute_mahalanobis_distance(self, zx: float, zy: float, zz: float) -> float:
        """
        Yenilik (innovation) y = z - H*x ve yenilik kovaryansı S = H*P*H^T + R üzerinden
        Mahalanobis mesafesi: d_M = sqrt(y^T * S^{-1} * y)
        """
        dy_x = zx - self.x
        dy_y = zy - self.y
        dy_z = zz - self.z
        s_x = max(self.cov_p[0] + self.gps_noise_r[0], 1e-6)
        s_y = max(self.cov_p[1] + self.gps_noise_r[1], 1e-6)
        s_z = max(self.cov_p[2] + self.gps_noise_r[2], 1e-6)
        d_m = math.sqrt((dy_x * dy_x) / s_x + (dy_y * dy_y) / s_y + (dy_z * dy_z) / s_z)
        self.last_mahalanobis_distance = round(d_m, 4)
        return self.last_mahalanobis_distance

    def update_gps(self, zx: float, zy: float, zz: float) -> bool:
        if not self.gps_active:
            return False

        # Öklid yenilik ve Mahalanobis Chi-Square kapısı kontrolü
        innovation_euclidean = math.sqrt((zx - self.x) ** 2 + (zy - self.y) ** 2 + (zz - self.z) ** 2)
        d_m = self.compute_mahalanobis_distance(zx, zy, zz)

        if innovation_euclidean > 40.0 or d_m > 16.0:
            # GPS Spoofing tespit edildi!
            self.gps_active = False
            self.dead_reckoning = True
            self.spoofing_events_detected += 1
            return False

        # Dinamik Kalman Kazancı: K = P * H^T * S^{-1}
        kx = self.cov_p[0] / (self.cov_p[0] + self.gps_noise_r[0])
        ky = self.cov_p[1] / (self.cov_p[1] + self.gps_noise_r[1])
        kz = self.cov_p[2] / (self.cov_p[2] + self.gps_noise_r[2])

        self.x += kx * (zx - self.x)
        self.y += ky * (zy - self.y)
        self.z += kz * (zz - self.z)

        # Kovaryans güncellemesi: P = (I - K*H) * P
        self.cov_p[0] *= 1.0 - kx
        self.cov_p[1] *= 1.0 - ky
        self.cov_p[2] *= 1.0 - kz
        return True

    def update_optical_flow(self, vx_flow: float, vy_flow: float, baro_alt_z: float, dt: float = 0.1) -> EKFState:
        """
        GNSS karartması veya spoofing durumunda (Dead-Reckoning aktifken)
        kamera optik akış hızı ve barometrik irtifa ile seyrüsefer güncellemesi yapar.
        """
        r_flow = 0.25
        r_baro = 0.80
        kvx = self.cov_p[3] / (self.cov_p[3] + r_flow)
        kvy = self.cov_p[4] / (self.cov_p[4] + r_flow)
        kz = self.cov_p[2] / (self.cov_p[2] + r_baro)

        self.vx += kvx * (vx_flow - self.vx)
        self.vy += kvy * (vy_flow - self.vy)
        self.z += kz * (baro_alt_z - self.z)
        self.x += self.vx * dt
        self.y += self.vy * dt

        self.cov_p[3] *= 1.0 - kvx
        self.cov_p[4] *= 1.0 - kvy
        self.cov_p[2] *= 1.0 - kz
        return self.get_state()

    def get_state(self) -> EKFState:
        pos_unc = math.sqrt(self.cov_p[0] + self.cov_p[1] + self.cov_p[2])
        return EKFState(
            self.x,
            self.y,
            self.z,
            self.vx,
            self.vy,
            self.vz,
            self.gps_active,
            self.dead_reckoning,
            mahalanobis_distance=self.last_mahalanobis_distance,
            position_uncertainty_m=round(pos_unc, 4),
        )

