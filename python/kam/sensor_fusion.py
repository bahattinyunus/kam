import math
from dataclasses import dataclass
from typing import Tuple

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

class SensorFusionEKF:
    """
    Genişletilmiş Kalman Filtresi (EKF) ve GPS Spoofing Dedektörü
    """
    def __init__(self):
        self.x = 0.0
        self.y = 0.0
        self.z = 100.0
        self.vx = 15.0
        self.vy = 0.0
        self.vz = 0.0
        self.gps_active = True
        self.dead_reckoning = False

    def predict(self, dt: float = 0.1, ax: float = 0.0, ay: float = 0.0, az: float = 0.0):
        self.x += self.vx * dt + 0.5 * ax * dt * dt
        self.y += self.vy * dt + 0.5 * ay * dt * dt
        self.z += self.vz * dt + 0.5 * az * dt * dt
        self.vx += ax * dt
        self.vy += ay * dt
        self.vz += az * dt

    def update_gps(self, zx: float, zy: float, zz: float) -> bool:
        if not self.gps_active:
            return False

        # İnovasyon (Tahmin hatası) kontrolü
        innovation = math.sqrt((zx - self.x)**2 + (zy - self.y)**2 + (zz - self.z)**2)
        if innovation > 40.0:
            # GPS Spoofing tespit edildi!
            self.gps_active = False
            self.dead_reckoning = True
            return False

        # Basitleştirilmiş Kalman güncellemesi
        k = 0.7
        self.x += k * (zx - self.x)
        self.y += k * (zy - self.y)
        self.z += k * (zz - self.z)
        return True

    def get_state(self) -> EKFState:
        return EKFState(self.x, self.y, self.z, self.vx, self.vy, self.vz, self.gps_active, self.dead_reckoning)
