#include "tensor_engine.hpp"
#include <numeric>
#include <algorithm>

namespace kam::nn {

Tensor1D TensorEngine::linear(const Tensor2D& W, const Tensor1D& x, const Tensor1D& b) {
    Tensor1D y;
    y.data.resize(W.rows, 0.0f);

    for (size_t r = 0; r < W.rows; ++r) {
        float sum = (r < b.size()) ? b[r] : 0.0f;
        for (size_t c = 0; c < W.cols; ++c) {
            sum += W.at(r, c) * x[c];
        }
        y[r] = sum;
    }
    return y;
}

Tensor1D TensorEngine::silu(const Tensor1D& x) {
    Tensor1D y;
    y.data.resize(x.size());
    for (size_t i = 0; i < x.size(); ++i) {
        float sig = 1.0f / (1.0f + std::exp(-x[i]));
        y[i] = x[i] * sig;
    }
    return y;
}

Tensor1D TensorEngine::gelu(const Tensor1D& x) {
    Tensor1D y;
    y.data.resize(x.size());
    const float kSqrt2OverPi = 0.7978845608f;
    for (size_t i = 0; i < x.size(); ++i) {
        float v = x[i];
        y[i] = 0.5f * v * (1.0f + std::tanh(kSqrt2OverPi * (v + 0.044715f * v * v * v)));
    }
    return y;
}

Tensor1D TensorEngine::softmax(const Tensor1D& x) {
    Tensor1D y;
    y.data.resize(x.size());
    float max_val = *std::max_element(x.data.begin(), x.data.end());

    float sum_exp = 0.0f;
    for (size_t i = 0; i < x.size(); ++i) {
        y[i] = std::exp(x[i] - max_val);
        sum_exp += y[i];
    }
    for (size_t i = 0; i < x.size(); ++i) {
        y[i] /= (sum_exp + 1e-12f);
    }
    return y;
}

Tensor1D TensorEngine::layerNorm(const Tensor1D& x, float eps) {
    Tensor1D y;
    y.data.resize(x.size());

    float mean = std::accumulate(x.data.begin(), x.data.end(), 0.0f) / x.size();
    float var = 0.0f;
    for (float v : x.data) {
        var += (v - mean) * (v - mean);
    }
    var /= x.size();
    float inv_std = 1.0f / std::sqrt(var + eps);

    for (size_t i = 0; i < x.size(); ++i) {
        y[i] = (x[i] - mean) * inv_std;
    }
    return y;
}

Tensor1D TensorEngine::solveRk4(
    const Tensor1D& x0,
    float dt,
    std::function<Tensor1D(const Tensor1D&, float)> ode_func
) {
    size_t dim = x0.size();
    Tensor1D k1 = ode_func(x0, 0.0f);

    Tensor1D x_mid1;
    x_mid1.data.resize(dim);
    for (size_t i = 0; i < dim; ++i) x_mid1[i] = x0[i] + 0.5f * dt * k1[i];
    Tensor1D k2 = ode_func(x_mid1, 0.5f * dt);

    Tensor1D x_mid2;
    x_mid2.data.resize(dim);
    for (size_t i = 0; i < dim; ++i) x_mid2[i] = x0[i] + 0.5f * dt * k2[i];
    Tensor1D k3 = ode_func(x_mid2, 0.5f * dt);

    Tensor1D x_end;
    x_end.data.resize(dim);
    for (size_t i = 0; i < dim; ++i) x_end[i] = x0[i] + dt * k3[i];
    Tensor1D k4 = ode_func(x_end, dt);

    Tensor1D x_next;
    x_next.data.resize(dim);
    for (size_t i = 0; i < dim; ++i) {
        x_next[i] = x0[i] + (dt / 6.0f) * (k1[i] + 2.0f * k2[i] + 2.0f * k3[i] + k4[i]);
    }
    return x_next;
}

} // namespace kam::nn
