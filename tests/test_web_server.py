import unittest
import sys
import os
import threading
import time
import json
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from kam.web_server import KamWebHandler, ThreadingHTTPServer, KamEngine, KamLiquidFoundationModel, LocalKnowledgeEngine

class TestWebServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        KamWebHandler.engine = KamEngine()
        KamWebHandler.model = KamLiquidFoundationModel()
        KamWebHandler.knowledge = LocalKnowledgeEngine()

        cls.port = 8899
        cls.server = ThreadingHTTPServer(("127.0.0.1", cls.port), KamWebHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever)
        cls.thread.daemon = True
        cls.thread.start()
        time.sleep(0.5)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_telemetry_api(self):
        url = f"http://127.0.0.1:{self.port}/api/telemetry"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertIn("entropy", data)
            self.assertIn("active_telemetry", data)

    def test_chat_api_tr_capital(self):
        url = f"http://127.0.0.1:{self.port}/api/chat"
        payload = json.dumps({"message": "tr nin başkenti neresi"}).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertIn("Ankara", data["reply"])

    def test_crisis_api(self):
        url = f"http://127.0.0.1:{self.port}/api/crisis"
        for c_type, expected_substr in [
            ("uav_uart_cut", "UART-2"),
            ("gnss_spoof", "Mahalanobis"),
            ("swarm_loss", "Bravo-2"),
            ("ew_radar_threat", "17.4 GHz"),
            ("cbf_envelope_breach", "DARPA ANSR"),
            ("intent_c2_mission", "S-400"),
        ]:
            payload = json.dumps({"crisis_type": c_type}).encode("utf-8")
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req) as resp:
                self.assertEqual(resp.status, 200)
                data = json.loads(resp.read().decode("utf-8"))
                self.assertIn(expected_substr, data["message"])
                self.assertIsNotNone(data["code"])

    def test_edge_plan_and_tactical_route_api(self):
        url_edge = f"http://127.0.0.1:{self.port}/api/edge_plan"
        with urllib.request.urlopen(urllib.request.Request(url_edge)) as resp:
            self.assertEqual(resp.status, 200)
            edge_data = json.loads(resp.read().decode("utf-8"))
            self.assertIn("tier1_micro_uav", edge_data)
            self.assertIn("bitnet_b158", edge_data)

        url_route = f"http://127.0.0.1:{self.port}/api/tactical_route"
        payload = json.dumps({"target_x_km": 40.0, "num_segments": 8}).encode("utf-8")
        req = urllib.request.Request(url_route, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            route_data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(len(route_data["waypoints"]), 9)
            self.assertGreater(route_data["mission_survival_probability_pct"], 75.0)

    def test_fleet_manifest_api(self):
        url = f"http://127.0.0.1:{self.port}/api/fleet_manifest"
        with urllib.request.urlopen(urllib.request.Request(url)) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["total_models"], 8)
            model_keys = [m["key"] for m in data["models"]]
            self.assertIn("kam:apex", model_keys)
            self.assertIn("kam:7b", model_keys)
            self.assertIn("kam:r1", model_keys)
            self.assertIn("kam:coder", model_keys)
            self.assertIn("kam:edge-moe-b158", model_keys)

    def test_lyapunov_status_api(self):
        url = f"http://127.0.0.1:{self.port}/api/lyapunov_status"
        with urllib.request.urlopen(urllib.request.Request(url)) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertIn("stability", data)
            self.assertIn("time_to_anomaly", data)
            self.assertIn("lyapunov_v", data["stability"])

    def test_ew_radar_api(self):
        url = f"http://127.0.0.1:{self.port}/api/ew_radar"
        payload = json.dumps({
            "rf_ghz": 17.4,
            "pri_us": 610.0,
            "pw_us": 0.25,
            "aoa_deg": 118.0,
            "chirp_bw_mhz": 240.0,
            "agility_score": 0.92,
        }).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertIn("classification", data)
            self.assertTrue(data["classification"]["is_novel_shapeshifting_emitter"])
            self.assertIn("ew_drfm_responder.cpp", data["countermeasure_code"])

    def test_c2_intent_api(self):
        url = f"http://127.0.0.1:{self.port}/api/c2_intent"
        payload = json.dumps({
            "commander_intent": "Sektör-4 S-400 bataryasını körelt ve vadi taarruzu icra et"
        }).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertIn("c2_plan", data)
            self.assertEqual(data["c2_plan"]["total_tasks_generated"], 4)
            self.assertIn("c2_task_executor.cpp", data["executor_code"])

    def test_safety_shield_api(self):
        url = f"http://127.0.0.1:{self.port}/api/safety_shield"
        payload = json.dumps({
            "target_altitude_agl_m": 12.0,
            "airspeed_mps": 15.0,
            "bank_angle_deg": 68.0,
            "battery_pct": 14.0,
        }).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertIn("shield_result", data)
            self.assertTrue(data["shield_result"]["intervention_occurred"])
            self.assertIn("cbf_safety_shield.cpp", data["cbf_code"])

if __name__ == "__main__":
    unittest.main()
