#pragma once

#include <vector>
#include <array>
#include <cmath>
#include <string>

namespace kam::fusion {

struct SensorReading {
    double timestamp_s;
    double ax, ay, az; // IMU İvmeölçer (m/s^2)
    double gx, gy, gz; // IMU Jiroskop (rad/s)
    double gps_x, gps_y, gps_z; // GNSS Pozisyonu (m)
    bool gps_valid;
    double optic_flow_vx, optic_flow_vy; // Görsel Akış Hızı
    bool optic_flow_valid;
};

struct FusionState {
    std::array<double, 6> state; // [x, y, z, vx, vy, vz]
    double position_uncertainty; // m
    double velocity_uncertainty; // m/s
    bool dead_reckoning_active;
    double prediction_error_norm;
};

class ExtendedKalmanFilter {
public:
    ExtendedKalmanFilter();

    // Zaman adımı ile durum öngörüsü (Prediction step)
    void predict(double dt_sec, double ax, double ay, double az);

    // GNSS pozisyon ölçümü güncellemesi (Update step)
    void updateGps(double zx, double zy, double zz, double measurement_noise = 2.0);

    // Optik akış hız güncellemesi
    void updateOpticalFlow(double flow_vx, double flow_vy, double measurement_noise = 0.5);

    // Sensör kaybı / GPS Jamming algılandığında Dead Reckoning moduna geç
    void markGpsCompromised(bool compromised);

    // Mevcut füzyon durumunu al
    FusionState getState() const;

    // Tahmin hatası yenilik (innovation) vektörünü al (Serbest enerjiye beslenir)
    double getInnovationNorm() const;

private:
    std::array<double, 6> x_; // State vector
    std::array<std::array<double, 6>, 6> P_; // Kovaryans matrisi
    std::array<std::array<double, 6>, 6> Q_; // Süreç gürültü matrisi
    bool gps_compromised_ = false;
    double last_innovation_norm_ = 0.0;
};

} // namespace kam::fusion
