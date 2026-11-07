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

if __name__ == "__main__":
    unittest.main()
