#pragma once

#include <string>
#include <functional>
#include <memory>
#include <vector>

namespace kam::core {

struct CompilationResult {
    bool success = false;
    std::string module_name;
    std::string binary_path;
    std::string compilation_logs;
    double compilation_time_ms = 0.0;
    bool syntax_verified = false;
};

class JitCompiler {
public:
    JitCompiler();
    ~JitCompiler();

    // C++ kodunun sözdizimini (syntax) ve AST bütünlüğünü doğrula
    bool verifyCodeSyntax(const std::string& cpp_source_code, std::string& out_error);

    // Bellekte veya geçici dosyada C++ kodunu derler
    CompilationResult compileSource(const std::string& module_name, const std::string& cpp_source_code);

    // Derlenen modülü dinamik olarak bağlar ve yürütür
    bool loadAndExecute(const std::string& binary_path, const std::string& symbol_name = "kam_entrypoint");

    // Güvenli Geri Alma (Safe Rollback Guard): Canary testi çalıştırır, hata olursa önceki binary'ye döner
    bool loadWithRollbackGuard(const std::string& new_binary_path, const std::string& fallback_binary_path);

    // Derleyici optimizasyon seviyesini ayarla
    void setOptimizationLevel(const std::string& opt_level);

    // Aktif çalışan modül yolunu al
    std::string getActiveBinary() const;

private:
    std::string opt_level_ = "-O3";
    std::string build_temp_dir_ = "./kam_jit_temp";
    std::string active_binary_ = "";
    std::vector<std::string> loaded_modules_history_;
};

} // namespace kam::core
