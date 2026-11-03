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
    ${CMAKE_CURRENT_SOURCE_DIR}/ros2_bridge/include
    ${CMAKE_CURRENT_SOURCE_DIR}/hardware/include
    ${CMAKE_CURRENT_SOURCE_DIR}/sensor_fusion/include
    ${CMAKE_CURRENT_SOURCE_DIR}/ew_mesh/include
)

# 1. Core Kütüphanesi & Tensör Motoru
set(CORE_SOURCES
    core/src/logger.cpp
    core/src/system_state.cpp
    core/src/jit_compiler.cpp
    core/src/kam_core.cpp
    core/src/watchdog.cpp
    core/src/memory_arena.cpp
    core/src/telemetry_exporter.cpp
    core/src/tensor_engine.cpp
    core/src/liquid_network.cpp
)

# 2. eBPF Kancaları Kütüphanesi
set(EBPF_SOURCES
    ebpf_hooks/src/ebpf_telemetry.cpp
)

# 3. Aktif Çıkarım (Active Inference) Kütüphanesi
set(ACTIVE_INFERENCE_SOURCES
    active_inference/src/free_energy_math.cpp
    active_inference/src/generative_model.cpp
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
    llm_agent/src/gguf_parser.cpp
)

# 5. ROS2 Bilişsel Köprü
set(ROS2_BRIDGE_SOURCES
    ros2_bridge/src/kam_ros2_node.cpp
)

# 6. Donanım Veriyolu Sürücüleri
set(HARDWARE_SOURCES
    hardware/src/hardware_bus.cpp
)

# 7. Sensör Füzyonu & Elektronik Harp Mesh
set(FUSION_SOURCES
    sensor_fusion/src/ekf_fusion.cpp
    ew_mesh/src/fhss_transceiver.cpp
)

# Ana KAM Statik Kütüphanesi
add_library(kam_static STATIC
    ${CORE_SOURCES}
    ${EBPF_SOURCES}
    ${ACTIVE_INFERENCE_SOURCES}
    ${LLM_AGENT_SOURCES}
    ${ROS2_BRIDGE_SOURCES}
    ${HARDWARE_SOURCES}
    ${FUSION_SOURCES}
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

    add_executable(kam_jamming_attack examples/uav_jamming_attack.cpp)
    target_link_libraries(kam_jamming_attack kam_static)

    add_executable(kam_deep_space_bitflip examples/deep_space_radiation_bitflip.cpp)
    target_link_libraries(kam_deep_space_bitflip kam_static)

    add_executable(kam_can_spoofing examples/can_bus_spoofing_defense.cpp)
    target_link_libraries(kam_can_spoofing kam_static)

    add_executable(kam_thermal_mitigation examples/thermal_runaway_mitigation.cpp)
    target_link_libraries(kam_thermal_mitigation kam_static)

    add_executable(kam_swarm_loss examples/swarm_mesh_loss_resilience.cpp)
    target_link_libraries(kam_swarm_loss kam_static)

    add_executable(kam_liquid_demo examples/liquid_neural_ode_demo.cpp)
    target_link_libraries(kam_liquid_demo kam_static)
endif()

# Kurulum Kuralları
install(TARGETS kam_static DESTINATION lib)
install(DIRECTORY core/include/ DESTINATION include/kam/core)
install(DIRECTORY ebpf_hooks/include/ DESTINATION include/kam/ebpf)
install(DIRECTORY active_inference/include/ DESTINATION include/kam/active_inference)
install(DIRECTORY llm_agent/include/ DESTINATION include/kam/llm)
install(DIRECTORY ros2_bridge/include/ DESTINATION include/kam/ros2)
install(DIRECTORY hardware/include/ DESTINATION include/kam/hardware)
install(DIRECTORY sensor_fusion/include/ DESTINATION include/kam/sensor_fusion)
install(DIRECTORY ew_mesh/include/ DESTINATION include/kam/ew_mesh)
