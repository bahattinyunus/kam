#pragma once

#include <string>
#include <functional>
#include <memory>

namespace kam::core {

struct CompilationResult {
    bool success = false;
    std::string module_name;
    std::string binary_path;
    std::string compilation_logs;
    double compilation_time_ms = 0.0;
};

class JitCompiler {
public:
    JitCompiler();
    ~JitCompiler();

    // Bellekte veya geçici dosyada C++ kodunu derler
    CompilationResult compileSource(const std::string& module_name, const std::string& cpp_source_code);

    // Derlenen modülü dinamik olarak bağlar ve yürütür
    bool loadAndExecute(const std::string& binary_path, const std::string& symbol_name = "kam_entrypoint");

    // Derleyici bayraklarını ayarlar
    void setOptimizationLevel(const std::string& opt_level); // "-O2", "-O3", "-Ofast"

private:
    std::string opt_level_ = "-O3";
    std::string build_temp_dir_ = "/tmp/kam_jit";
};

} // namespace kam::core
