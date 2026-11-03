#pragma once

#include <string>
#include <vector>
#include <memory>

namespace kam::llm {

struct InferenceConfig {
    std::string model_path = "models/kam-cognitive-7b-int8.engine";
    int max_tokens = 512;
    float temperature = 0.2f; // Deterministik, hatasız kod ve teşhis için düşük sıcaklık
    bool use_fp8 = false;
    bool use_int8 = true;
};

class TensorRtInference {
public:
    TensorRtInference(const InferenceConfig& config = {});
    ~TensorRtInference();

    bool loadEngine();
    
    // Saf Türkçe karar ve analiz üret
    std::string generateResponse(const std::string& prompt);

    bool isLoaded() const;

private:
    InferenceConfig config_;
    bool loaded_ = false;
};

} // namespace kam::llm
