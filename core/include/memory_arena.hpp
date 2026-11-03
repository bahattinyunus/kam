#pragma once

#include <cstddef>
#include <cstdint>
#include <vector>
#include <new>
#include <stdexcept>
#include <algorithm>

namespace kam::core {

// RealTimeMemoryArena:
// Gerçek zamanlı uç donanımlarda dinamik malloc/free bellek parçalanmasını engellemek için
// önceden tahsis edilmiş (pre-allocated) sabit boyutlu bellek havuzu.
// O(1) deterministik tahsisat garantisi verir.

class RealTimeMemoryArena {
public:
    explicit RealTimeMemoryArena(size_t total_bytes = 4 * 1024 * 1024) // Varsayılan 4MB
        : capacity_(total_bytes), offset_(0) {
        buffer_ = new uint8_t[capacity_];
    }

    ~RealTimeMemoryArena() {
        delete[] buffer_;
    }

    // Kopyalama engellendi
    RealTimeMemoryArena(const RealTimeMemoryArena&) = delete;
    RealTimeMemoryArena& operator=(const RealTimeMemoryArena&) = delete;

    // Belirli boyutta bellek bloğu tahsis et (O(1))
    void* allocate(size_t bytes, size_t alignment = alignof(std::max_align_t)) {
        size_t current_addr = reinterpret_cast<size_t>(buffer_ + offset_);
        size_t padding = (alignment - (current_addr % alignment)) % alignment;

        if (offset_ + padding + bytes > capacity_) {
            return nullptr; // Arena kapasitesi aşıldı
        }

        offset_ += padding;
        void* ptr = buffer_ + offset_;
        offset_ += bytes;
        return ptr;
    }

    // T tipinde nesne oluştur
    template <typename T, typename... Args>
    T* create(Args&&... args) {
        void* mem = allocate(sizeof(T), alignof(T));
        if (!mem) return nullptr;
        return new (mem) T(std::forward<Args>(args)...);
    }

    // Arenayı sıfırla (bellek tahliye edilmez, işaretçi başa döner - O(1))
    void reset() {
        offset_ = 0;
    }

    size_t getUsedBytes() const { return offset_; }
    size_t getCapacity() const { return capacity_; }
    double getUtilizationRatio() const {
        return static_cast<double>(offset_) / static_cast<double>(capacity_);
    }

private:
    uint8_t* buffer_;
    size_t capacity_;
    size_t offset_;
};

} // namespace kam::core
