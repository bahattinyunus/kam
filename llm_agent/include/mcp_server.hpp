#pragma once

#include <string>
#include <vector>
#include <functional>
#include <unordered_map>
#include "../../core/include/system_state.hpp"
#include "../../core/include/jit_compiler.hpp"

namespace kam::llm {

struct McpTool {
    std::string name;
    std::string description_tr;
    std::string schema_json;
};

class McpServer {
public:
    McpServer(core::SystemState& state, core::JitCompiler& compiler);
    ~McpServer();

    // Gelen JSON-RPC 2.0 mesajını işle ve yanıt JSON üret
    std::string handleJsonRpcRequest(const std::string& request_json);

    // Tanımlı araç listesini JSON olarak döndür
    std::string listToolsJson() const;

    // Tek bir aracı yürüt
    std::string callTool(const std::string& tool_name, const std::string& arguments_json);

private:
    core::SystemState& state_;
    core::JitCompiler& compiler_;
    std::vector<McpTool> tools_;

    void initializeTools();
};

} // namespace kam::llm
