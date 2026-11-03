cmake_minimum_required(VERSION 3.20)
project(kam VERSION 1.0.0 LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Derleme Seçenekleri
option(USE_CUDA "CUDA ivmelendirmesini etkinleştir" OFF)
option(USE_TENSORRT "TensorRT yerel çıkarım motorunu bağla" OFF)
option(USE_EBPF "Gerçek Linux eBPF kancalarını etkinleştir" OFF)
option(BUILD_EXAMPLES "Örnek simülasyonları derle" ON)
option(BUILD_TESTS "Testleri derle" ON)

if(USE_CUDA)
    enable_language(CUDA)
    add_compile_definitions(USE_CUDA=1)
endif()

if(USE_TENSORRT)
    add_compile_definitions(USE_TENSORRT=1)
endif()

if(USE_EBPF)
    add_compile_definitions(USE_EBPF=1)
endif()

# Dahil Edilecek Dizinler
include_directories(
    ${CMAKE_CURRENT_SOURCE_DIR}/core/include
    ${CMAKE_CURRENT_SOURCE_DIR}/ebpf_hooks/include
    ${CMAKE_CURRENT_SOURCE_DIR}/active_inference/include
    ${CMAKE_CURRENT_SOURCE_DIR}/llm_agent/include
)

# 1. Core Kütüphanesi
set(CORE_SOURCES
    core/src/logger.cpp
    core/src/system_state.cpp
    core/src/jit_compiler.cpp
    core/src/kam_core.cpp
)

# 2. eBPF Kancaları Kütüphanesi
set(EBPF_SOURCES
    ebpf_hooks/src/ebpf_telemetry.cpp
)

# 3. Aktif Çıkarım (Active Inference) Kütüphanesi
set(ACTIVE_INFERENCE_SOURCES
    active_inference/src/free_energy_math.cpp
    active_inference/src/active_inference.cpp
)
if(USE_CUDA)
    list(APPEND ACTIVE_INFERENCE_SOURCES active_inference/cuda/entropy_kernels.cu)
endif()

# 4. LLM Ajanı & MCP Kütüphanesi
set(LLM_AGENT_SOURCES
    llm_agent/src/tensorrt_inference.cpp
    llm_agent/src/code_generator.cpp
    llm_agent/src/autonomous_agent.cpp
    llm_agent/src/mcp_server.cpp
)

# Ana KAM Kütüphanesi
add_library(kam_static STATIC
    ${CORE_SOURCES}
    ${EBPF_SOURCES}
    ${ACTIVE_INFERENCE_SOURCES}
    ${LLM_AGENT_SOURCES}
)

if(UNIX AND NOT APPLE)
    target_link_libraries(kam_static dl pthread)
endif()

# Örnek Uygulamalar
if(BUILD_EXAMPLES)
    add_executable(kam_uav_scenario examples/uav_telemetry_failure_scenario.cpp)
    target_link_libraries(kam_uav_scenario kam_static)

    add_executable(kam_edge_recovery examples/edge_mission_recovery.cpp)
    target_link_libraries(kam_edge_recovery kam_static)
endif()

# Kurulum Kuralları
install(TARGETS kam_static DESTINATION lib)
install(DIRECTORY core/include/ DESTINATION include/kam/core)
install(DIRECTORY ebpf_hooks/include/ DESTINATION include/kam/ebpf)
install(DIRECTORY active_inference/include/ DESTINATION include/kam/active_inference)
install(DIRECTORY llm_agent/include/ DESTINATION include/kam/llm)
