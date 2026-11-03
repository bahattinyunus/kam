// KAM CUDA Serbest Enerji ve Entropi Çekirdekleri
// NVIDIA Jetson Orin / RTX Serisi GPU'larda milisaniye altı hızlandırma

#if defined(__CUDACC__) || defined(USE_CUDA)
#include <cuda_runtime.h>
#include <device_launch_parameters.h>
#include <math.h>

__global__ void compute_free_energy_cuda_kernel(
    const double* __restrict__ prior,
    const double* __restrict__ obs,
    const double* __restrict__ likelihood,
    double* __restrict__ out_fe,
    int size
) {
    int idx = blockDim.x * blockIdx.x + threadIdx.x;
    if (idx < size) {
        double p = fmax(prior[idx], 1e-12);
        double q = fmax(obs[idx], 1e-12);
        double l = fmax(likelihood[idx], 1e-12);

        // KL complexity - accuracy
        double kl_part = q * log(q / p);
        double acc_part = q * log(l);
        out_fe[idx] = kl_part - acc_part;
    }
}

extern "C" void launch_cuda_entropy_calc(
    const double* h_prior,
    const double* h_obs,
    const double* h_likelihood,
    double* h_out,
    int size
) {
    double *d_prior, *d_obs, *d_likelihood, *d_out;
    size_t bytes = size * sizeof(double);

    cudaMalloc(&d_prior, bytes);
    cudaMalloc(&d_obs, bytes);
    cudaMalloc(&d_likelihood, bytes);
    cudaMalloc(&d_out, bytes);

    cudaMemcpy(d_prior, h_prior, bytes, cudaMemcpyHostToDevice);
    cudaMemcpy(d_obs, h_obs, bytes, cudaMemcpyHostToDevice);
    cudaMemcpy(d_likelihood, h_likelihood, bytes, cudaMemcpyHostToDevice);

    int threads = 256;
    int blocks = (size + threads - 1) / threads;
    compute_free_energy_cuda_kernel<<<blocks, threads>>>(d_prior, d_obs, d_likelihood, d_out, size);

    cudaMemcpy(h_out, d_out, bytes, cudaMemcpyDeviceToHost);

    cudaFree(d_prior);
    cudaFree(d_obs);
    cudaFree(d_likelihood);
    cudaFree(d_out);
}
#endif
