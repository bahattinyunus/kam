#pragma once

#include <vector>
#include <atomic>
#include <cstddef>
#include <optional>
#include <new>

namespace kam::ebpf {

// Lock-Free Single-Producer Single-Consumer (SPSC) Ring Buffer
// Gömülü sistemlerde ve kernel eBPF telemetri akışında mikrosaniye altı sıfır kilit performansı sağlar.
template <typename T, size_t Capacity = 1024>
class LockFreeRingBuffer {
    static_assert((Capacity & (Capacity - 1)) == 0, "Capacity must be a power of 2");

public:
    LockFreeRingBuffer() : head_(0), tail_(0) {
        buffer_.resize(Capacity);
    }

    bool push(const T& item) {
        const size_t current_tail = tail_.load(std::memory_order_relaxed);
        const size_t current_head = head_.load(std::memory_order_acquire);

        if ((current_tail - current_head) >= Capacity) {
            return false; // Kuyruk dolu
        }

        buffer_[current_tail & (Capacity - 1)] = item;
        tail_.store(current_tail + 1, std::memory_order_release);
        return true;
    }

    std::optional<T> pop() {
        const size_t current_head = head_.load(std::memory_order_relaxed);
        const size_t current_tail = tail_.load(std::memory_order_acquire);

        if (current_head == current_tail) {
            return std::nullopt; // Kuyruk boş
        }

        T item = buffer_[current_head & (Capacity - 1)];
        head_.store(current_head + 1, std::memory_order_release);
        return item;
    }

    bool isEmpty() const {
        return head_.load(std::memory_order_relaxed) == tail_.load(std::memory_order_relaxed);
    }

    size_t size() const {
        const size_t h = head_.load(std::memory_order_relaxed);
        const size_t t = tail_.load(std::memory_order_relaxed);
        return (t >= h) ? (t - h) : 0;
    }

private:
    std::vector<T> buffer_;
    alignas(64) std::atomic<size_t> head_;
    alignas(64) std::atomic<size_t> tail_;
};

} // namespace kam::ebpf
