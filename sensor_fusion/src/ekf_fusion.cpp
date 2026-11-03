#include "ekf_fusion.hpp"
#include "../../core/include/logger.hpp"
#include <algorithm>

namespace kam::fusion {

ExtendedKalmanFilter::ExtendedKalmanFilter() {
    x_.fill(0.0);

    // Başlangıç kovaryans matrisi
    for (size_t i = 0; i < 6; ++i) {
        for (size_t j = 0; j < 6; ++j) {
            P_[i][j] = (i == j) ? ((i < 3) ? 5.0 : 1.0) : 0.0;
            Q_[i][j] = (i == j) ? ((i < 3) ? 0.05 : 0.2) : 0.0;
        }
    }
}

void ExtendedKalmanFilter::predict(double dt_sec, double ax, double ay, double az) {
    // Kinematik hareket modeli:
    // x(k+1) = x(k) + v(k)*dt + 0.5*a*dt^2
    // v(k+1) = v(k) + a*dt
    x_[0] += x_[3] * dt_sec + 0.5 * ax * dt_sec * dt_sec;
    x_[1] += x_[4] * dt_sec + 0.5 * ay * dt_sec * dt_sec;
    x_[2] += x_[5] * dt_sec + 0.5 * az * dt_sec * dt_sec;

    x_[3] += ax * dt_sec;
    x_[4] += ay * dt_sec;
    x_[5] += az * dt_sec;

    // Kovaryans öngörüsü: P = F * P * F^T + Q
    for (size_t i = 0; i < 3; ++i) {
        P_[i][i] += (P_[i + 3][i + 3] * dt_sec * dt_sec) + Q_[i][i];
        P_[i + 3][i + 3] += Q_[i + 3][i + 3];
    }
}

void ExtendedKalmanFilter::updateGps(double zx, double zy, double zz, double measurement_noise) {
    if (gps_compromised_) {
        // GPS kirlendi veya sahtelendi (Spoofed/Jammed) - Doğrudan yok say!
        return;
    }

    // Yenilik (Innovation / Prediction Error): y = z - H*x
    double yx = zx - x_[0];
    double yy = zy - x_[1];
    double yz = zz - x_[2];

    last_innovation_norm_ = std::sqrt(yx * yx + yy * yy + yz * yz);

    // Eğer anlık tahmin hatası devasa ise (örn: GPS aniden 100m sıçradı -> Spoofing)
    if (last_innovation_norm_ > 35.0) {
        core::Logger::instance().warn(core::Subsystem::NERVOUS_SYS, 
            "EKF YENİLİK ANOMALİSİ: GPS pozisyon sıçraması (" + 
            std::to_string(last_innovation_norm_) + "m) tespit edildi! Olası GPS Spoofing.");
        markGpsCompromised(true);
        return;
    }

    // Kalman kazancı K = P * H^T * (H*P*H^T + R)^-1
    for (size_t i = 0; i < 3; ++i) {
        double r = measurement_noise * measurement_noise;
        double s = P_[i][i] + r;
        double k = P_[i][i] / s;

        double err = (i == 0) ? yx : ((i == 1) ? yy : yz);
        x_[i] += k * err;
        P_[i][i] = (1.0 - k) * P_[i][i];
    }
}

void ExtendedKalmanFilter::updateOpticalFlow(double flow_vx, double flow_vy, double measurement_noise) {
    double yvx = flow_vx - x_[3];
    double yvy = flow_vy - x_[4];

    double r = measurement_noise * measurement_noise;
    for (size_t i = 3; i < 5; ++i) {
        double s = P_[i][i] + r;
        double k = P_[i][i] / s;
        double err = (i == 3) ? yvx : yvy;
        x_[i] += k * err;
        P_[i][i] = (1.0 - k) * P_[i][i];
    }
}

void ExtendedKalmanFilter::markGpsCompromised(bool compromised) {
    gps_compromised_ = compromised;
    if (compromised) {
        core::Logger::instance().warn(core::Subsystem::NERVOUS_SYS, 
            "SENSÖR FÜZYONU: GPS hattı devreden çıkarıldı. Ataletsel Seyrüsefer (Dead Reckoning) devrede.");
    }
}

FusionState ExtendedKalmanFilter::getState() const {
    FusionState s;
    s.state = x_;
    s.position_uncertainty = std::sqrt(P_[0][0] + P_[1][1] + P_[2][2]);
    s.velocity_uncertainty = std::sqrt(P_[3][3] + P_[4][4] + P_[5][5]);
    s.dead_reckoning_active = gps_compromised_;
    s.prediction_error_norm = last_innovation_norm_;
    return s;
}

double ExtendedKalmanFilter::getInnovationNorm() const {
    return last_innovation_norm_;
}

} // namespace kam::fusion
