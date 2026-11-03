#pragma once

#include <vector>
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <string>
#include <functional>

namespace kam::nn {

// Hafif, sıfır bağımlılıklı Gerçek Zamanlı Tensör Yapısı
struct Tensor1D {
    std::vector<float> data;
    size_t size() const { return data.size(); }
    float& operator[](size_t i) { return data[i]; }
    const float& operator[](size_t i) const { return data[i]; }
};

struct Tensor2D {
    size_t rows;
    size_t cols;
    std::vector<float> data;

    Tensor2D(size_t r = 0, size_t c = 0, float val = 0.0f)
        : rows(r), cols(c), data(r * c, val) {}

    float& at(size_t r, size_t c) { return data[r * cols + c]; }
    const float& at(size_t r, size_t c) const { return data[r * cols + c]; }
};

class TensorEngine {
public:
    // Matris-Vektör Çarpımı: y = W * x + b
    static Tensor1D linear(const Tensor2D& W, const Tensor1D& x, const Tensor1D& b);

    // Aktivasyon Fonksiyonları
    static Tensor1D silu(const Tensor1D& x);
    static Tensor1D gelu(const Tensor1D& x);
    static Tensor1D softmax(const Tensor1D& x);
    static Tensor1D layerNorm(const Tensor1D& x, float eps = 1e-5f);

    // Runge-Kutta 4. Derece (RK4) Neural ODE Çözücüsü:
    // dx/dt = f(x, t) denklemini [t, t+dt] aralığında sürekli zamanda çözer
    static Tensor1D solveRk4(
        const Tensor1D& x0,
        float dt,
        std::function<Tensor1D(const Tensor1D&, float)> ode_func
    );
};

} // namespace kam::nn
