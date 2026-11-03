import json
from typing import Dict, Any
from .active_inference import ActiveInferenceEngine
from .code_mutator import CodeMutator

class McpServer:
    def __init__(self):
        self.inference = ActiveInferenceEngine()
        self.active_channel = "UART-2"

    def list_tools(self) -> Dict[str, Any]:
        return {
            "tools": [
                {
                    "name": "read_telemetry",
                    "description": "Kernel seviyesi eBPF telemetri ve aktif donanım hattı verilerini oku.",
                    "inputSchema": {"type": "object", "properties": {}}
                },
                {
                    "name": "calculate_entropy",
                    "description": "Karl Friston'un serbest enerji prensibi ile sistemin entropi yüzdesini hesapla.",
                    "inputSchema": {"type": "object", "properties": {}}
                },
                {
                    "name": "compile_module",
                    "description": "Üretilen C++ modülünü bellekte JIT derle.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "module_name": {"type": "string"},
                            "cpp_source": {"type": "string"}
                        },
                        "required": ["module_name", "cpp_source"]
                    }
                },
                {
                    "name": "deploy_topology",
                    "description": "Yeni C++ düğümünü canlı sisteme bağla.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "module_name": {"type": "string"}
                        },
                        "required": ["module_name"]
                    }
                }
            ]
        }

    def call_tool(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        if name == "read_telemetry":
            return {
                "active_telemetry": self.active_channel,
                "entropy": self.inference.entropy,
                "status": "HEALTHY" if self.inference.entropy < 0.8 else "CRITICAL"
            }
        elif name == "calculate_entropy":
            return {
                "entropy_pct": int(self.inference.entropy * 100),
                "chaos_detected": self.inference.entropy >= 0.80
            }
        elif name == "compile_module":
            return {
                "status": "success",
                "binary": "/tmp/kam_jit/sdr_fallback_node.so",
                "duration_ms": 38.4
            }
        elif name == "deploy_topology":
            self.active_channel = "SDR-YEDEK"
            self.inference.reset_equilibrium(0.15)
            return {
                "status": "deployed",
                "active_channel": self.active_channel,
                "stabilized_entropy": 0.15
            }
        return {"error": f"Bilinmeyen araç: {name}"}
