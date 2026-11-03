#pragma once

#include <string>
#include <vector>
#include <cstdint>
#include <fstream>

namespace kam::llm {

enum class QuantizationType {
    FP32,
    FP16,
    INT8,
    INT4_AWQ,
    Q4_K_M,
    Q8_0,
    UNKNOWN
};

struct ModelMetadata {
    std::string model_name;
    std::string architecture; // "llama", "mistral", "kam-7b"
    uint32_t context_length = 4096;
    uint32_t embedding_dim = 4096;
    uint32_t layer_count = 32;
    uint64_t tensor_count = 291;
    QuantizationType quant_type = QuantizationType::INT8;
    bool is_air_gapped_verified = true;
    uint64_t file_size_bytes = 0;
};

class GgufModelParser {
public:
    static bool parseHeader(const std::string& model_file_path, ModelMetadata& out_meta);
    static std::string quantTypeToString(QuantizationType type);
};

} // namespace kam::llm
