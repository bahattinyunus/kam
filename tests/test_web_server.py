import unittest
import sys
import os
import threading
import time
import json
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from kam.web_server import KamWebHandler, ThreadingHTTPServer, KamEngine, KamLiquidFoundationModel, LocalKnowledgeEngine
from kam.real_llm import UniversalLLMClient

class TestWebServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        KamWebHandler.engine = KamEngine()
        KamWebHandler.model = KamLiquidFoundationModel()
        KamWebHandler.knowledge = LocalKnowledgeEngine()
        KamWebHandler.llm_client = UniversalLLMClient(ollama_url="http://127.0.0.1:9")

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
            ("byzantine_swarm_attack", "Charlie-3"),
            ("trn_terrain_lock", "901.4"),
            ("kinetic_actuator_jam", "LEFT_ELEVON"),
            ("emcon_fso_switch", "1550nm"),
            ("radiation_seu_bitflip", "Hamming(72,64)"),
            ("sam_missile_lock", "Hamilton-Jacobi-Isaacs"),
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

    def test_bft_swarm_api(self):
        url = f"http://127.0.0.1:{self.port}/api/bft_swarm"
        payload = json.dumps({"inject_byzantine_traitor": True}).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertIn("bft_result", data)
            self.assertEqual(data["bft_result"]["quarantined_byzantine_nodes"], ["Charlie-3"])
            self.assertIn("byzantine_pqc_guard.cpp", data["pqc_code"])

    def test_trn_localize_api(self):
        url = f"http://127.0.0.1:{self.port}/api/trn_localize"
        payload = json.dumps({"true_x_km": 24.5, "true_y_km": -3.2}).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertIn("trn_result", data)
            self.assertGreater(data["trn_result"]["drift_reduction_pct"], 95.0)
            self.assertIn("trn_tercom_navigator.cpp", data["trn_code"])

    def test_actuator_reconfig_api(self):
        url = f"http://127.0.0.1:{self.port}/api/actuator_reconfig"
        payload = json.dumps({"jammed_actuator_index": 0, "jammed_angle_rad": 0.22}).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertIn("actuator_result", data)
            self.assertTrue(data["actuator_result"]["control_authority_preserved"])
            self.assertIn("actuator_mixer_reconfig.cpp", data["mixer_code"])

    def test_fso_link_api(self):
        url = f"http://127.0.0.1:{self.port}/api/fso_link"
        payload = json.dumps({"distance_km": 4.5, "visibility_km": 12.0}).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertIn("fso_result", data)
            self.assertEqual(data["fso_result"]["rf_emission_watts"], 0.0)
            self.assertIn("fso_laser_mesh_link.cpp", data["fso_code"])

    def test_ecc_scrub_api(self):
        url = f"http://127.0.0.1:{self.port}/api/ecc_scrub"
        payload = json.dumps({"injected_seu_bit": 19, "inject_tmr_bank_corruption": True}).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertIn("ecc_result", data)
            self.assertTrue(data["ecc_result"]["tmr_bitnet_weight_scrub"]["integrity_verified_100pct"])
            self.assertIn("radiation_tmr_scrubber.cpp", data["ecc_code"])

    def test_hji_evasion_api(self):
        url = f"http://127.0.0.1:{self.port}/api/hji_evasion"
        payload = json.dumps({"missile_range_m": 2850.0, "closing_velocity_mps": 980.0, "evader_max_g": 9.0}).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertIn("hji_result", data)
            self.assertTrue(data["hji_result"]["platform_survival_guaranteed"])
            self.assertIn("hji_evasion_maneuver.cpp", data["hji_code"])

    def test_autonomous_agent_api(self):
        url_tools = f"http://127.0.0.1:{self.port}/api/agent_tools"
        with urllib.request.urlopen(urllib.request.Request(url_tools)) as resp:
            self.assertEqual(resp.status, 200)
            tools_data = json.loads(resp.read().decode("utf-8"))
            self.assertGreaterEqual(tools_data["total_tools"], 12)

        url_exec = f"http://127.0.0.1:{self.port}/api/agent_execute"
        payload = json.dumps({
            "tool": "execute_python_code",
            "arguments": {"code": "print(7 * 8)"},
        }).encode("utf-8")
        req = urllib.request.Request(url_exec, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            exec_data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(exec_data["result"]["status"], "success")
            self.assertEqual(exec_data["result"]["stdout"], "56")

    def test_malformed_json_post_returns_http_400(self):
        import urllib.error

        # 1. Bozuk JSON gövdesi -> HTTP 400
        for route in ("/api/chat", "/api/config", "/api/crisis"):
            url = f"http://127.0.0.1:{self.port}{route}"
            req = urllib.request.Request(
                url,
                data=b"{broken json payload",
                headers={"Content-Type": "application/json"},
            )
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(req)
            self.assertEqual(ctx.exception.code, 400)
            err_body = json.loads(ctx.exception.read().decode("utf-8"))
            self.assertIn("error", err_body)

        # 2. JSON nesnesi (dict) olmayan dizi gövdesi -> HTTP 400
        req_arr = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/api/config",
            data=b"[1, 2, 3]",
            headers={"Content-Type": "application/json"},
        )
        with self.assertRaises(urllib.error.HTTPError) as ctx_arr:
            urllib.request.urlopen(req_arr)
        self.assertEqual(ctx_arr.exception.code, 400)

        # 3. Geçersiz UTF-8 baytları -> HTTP 400
        req_utf = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/api/chat",
            data=b"\xff\xfe\xfd",
            headers={"Content-Type": "application/json"},
        )
        with self.assertRaises(urllib.error.HTTPError) as ctx_utf:
            urllib.request.urlopen(req_utf)
        self.assertEqual(ctx_utf.exception.code, 400)

    def test_export_chat_markdown_and_json(self):
        orig_history = list(KamWebHandler.llm_client.conversation_history)
        try:
            KamWebHandler.llm_client.conversation_history = [
                {"role": "user", "content": "İstanbul'un fethi ve Kutadgu Bilig"},
                {"role": "assistant", "content": "Dirlik ve nizam kaimdir."},
            ]
            url_md = f"http://127.0.0.1:{self.port}/api/export_chat"
            with urllib.request.urlopen(urllib.request.Request(url_md)) as resp:
                self.assertEqual(resp.status, 200)
                self.assertIn("text/markdown", resp.headers.get("Content-Type", ""))
                self.assertIn("kam_chat_export.md", resp.headers.get("Content-Disposition", ""))
                md_body = resp.read().decode("utf-8")
                self.assertIn("# KAM Konuşma Kaydı", md_body)
                self.assertIn("İstanbul'un fethi ve Kutadgu Bilig", md_body)
                self.assertIn("Dirlik ve nizam kaimdir.", md_body)

            url_json = f"http://127.0.0.1:{self.port}/api/export_chat?format=json"
            with urllib.request.urlopen(urllib.request.Request(url_json)) as resp:
                self.assertEqual(resp.status, 200)
                j_data = json.loads(resp.read().decode("utf-8"))
                self.assertEqual(j_data["message_count"], 2)
                self.assertIn("markdown", j_data)
                self.assertIn("Dirlik ve nizam kaimdir.", j_data["markdown"])
        finally:
            KamWebHandler.llm_client.conversation_history = orig_history

    def test_config_validation_and_gemini_key_preservation(self):
        import urllib.error

        orig_key = KamWebHandler.llm_client.gemini_api_key
        orig_model = KamWebHandler.llm_client.current_model
        orig_backend = KamWebHandler.llm_client.active_backend
        try:
            KamWebHandler.llm_client.gemini_api_key = "secret-gemini-key-xyz"

            # Boş gemini_key gönderildiğinde mevcut anahtar silinmemeli
            req_keep = urllib.request.Request(
                f"http://127.0.0.1:{self.port}/api/config",
                data=json.dumps({"model": "kam:apex", "gemini_key": ""}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req_keep) as resp:
                self.assertEqual(resp.status, 200)
                cfg = json.loads(resp.read().decode("utf-8"))
                self.assertEqual(cfg["current_model"], "kam:apex")
            self.assertEqual(KamWebHandler.llm_client.gemini_api_key, "secret-gemini-key-xyz")

            # Geçersiz model tipi -> HTTP 400
            req_bad = urllib.request.Request(
                f"http://127.0.0.1:{self.port}/api/config",
                data=json.dumps({"model": 12345}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(req_bad)
            self.assertEqual(ctx.exception.code, 400)

            # Açık clear_gemini_key=True ile anahtar temizlenebilmeli
            req_clear = urllib.request.Request(
                f"http://127.0.0.1:{self.port}/api/config",
                data=json.dumps({"clear_gemini_key": True}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req_clear) as resp:
                self.assertEqual(resp.status, 200)
            self.assertEqual(KamWebHandler.llm_client.gemini_api_key, "")
        finally:
            KamWebHandler.llm_client.gemini_api_key = orig_key
            KamWebHandler.llm_client.set_model(orig_model)
            KamWebHandler.llm_client.active_backend = orig_backend

    def test_models_and_enriched_telemetry_api(self):
        with urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{self.port}/api/models")) as resp:
            self.assertEqual(resp.status, 200)
            m_data = json.loads(resp.read().decode("utf-8"))
            self.assertIn("models", m_data)
            names = [m["name"] for m in m_data["models"]]
            self.assertIn("kam:council", names)
            self.assertIn("kam-1-liquid-moe", names)

        with urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{self.port}/api/telemetry")) as resp:
            self.assertEqual(resp.status, 200)
            t_data = json.loads(resp.read().decode("utf-8"))
            self.assertIn("host_stats", t_data)
            self.assertIsInstance(t_data["host_stats"], dict)
            self.assertIn("cpu_percent", t_data)
            self.assertIn("ram_percent", t_data)

    def test_sessions_crud_activate_and_auto_sync_api(self):
        import tempfile
        import urllib.error
        from kam.web_server import _SessionStore

        orig_store = KamWebHandler.session_store
        orig_history = list(KamWebHandler.llm_client.conversation_history)
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                sess_file = os.path.join(tmpdir, "test_sessions.json")
                KamWebHandler.session_store = _SessionStore(sess_file)
                KamWebHandler.llm_client.conversation_history.clear()

                # 1. GET /api/sessions -> en az 1 varsayılan oturum + active_id
                with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/api/sessions") as resp:
                    self.assertEqual(resp.status, 200)
                    listed = json.loads(resp.read().decode("utf-8"))
                    self.assertIn("active_id", listed)
                    self.assertGreaterEqual(len(listed["sessions"]), 1)

                # 2. POST /api/sessions -> yeni oturum A oluştur
                req_a = urllib.request.Request(
                    f"http://127.0.0.1:{self.port}/api/sessions",
                    data=json.dumps({"title": "Oturum Alfa"}).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                )
                with urllib.request.urlopen(req_a) as resp:
                    self.assertEqual(resp.status, 200)
                    sess_a = json.loads(resp.read().decode("utf-8"))
                    sid_a = sess_a["id"]
                    self.assertEqual(sess_a["title"], "Oturum Alfa")

                # 3. /api/chat sonrası otomatik senkronizasyon
                req_chat = urllib.request.Request(
                    f"http://127.0.0.1:{self.port}/api/chat",
                    data=json.dumps({"message": "tr nin başkenti neresi"}).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                )
                with urllib.request.urlopen(req_chat) as resp:
                    self.assertEqual(resp.status, 200)
                    chat_data = json.loads(resp.read().decode("utf-8"))
                    self.assertIn("Ankara", chat_data["reply"])

                # Oturum A mesajlarını GET /api/sessions/<id> ile doğrula
                with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/api/sessions/{sid_a}") as resp:
                    self.assertEqual(resp.status, 200)
                    fetched_a = json.loads(resp.read().decode("utf-8"))
                    self.assertGreaterEqual(fetched_a["message_count"], 2)
                    self.assertTrue(os.path.isfile(sess_file))

                # 4. Oturum B oluştur -> geçmiş temizlenmeli, ardından Oturum A'yı tekrar aktive et
                req_b = urllib.request.Request(
                    f"http://127.0.0.1:{self.port}/api/sessions",
                    data=json.dumps({"title": "Oturum Beta"}).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                )
                with urllib.request.urlopen(req_b) as resp:
                    sess_b = json.loads(resp.read().decode("utf-8"))
                    sid_b = sess_b["id"]
                self.assertEqual(len(KamWebHandler.llm_client.conversation_history), 0)

                req_act = urllib.request.Request(
                    f"http://127.0.0.1:{self.port}/api/sessions/{sid_a}/activate",
                    data=b"{}",
                    headers={"Content-Type": "application/json"},
                )
                with urllib.request.urlopen(req_act) as resp:
                    self.assertEqual(resp.status, 200)
                    act_data = json.loads(resp.read().decode("utf-8"))
                    self.assertEqual(act_data["active_id"], sid_a)
                    self.assertGreaterEqual(len(KamWebHandler.llm_client.conversation_history), 2)

                # 5. DELETE /api/sessions/<sid_b> -> silme + bulunamayan oturum 404
                req_del = urllib.request.Request(
                    f"http://127.0.0.1:{self.port}/api/sessions/{sid_b}",
                    method="DELETE",
                )
                with urllib.request.urlopen(req_del) as resp:
                    self.assertEqual(resp.status, 200)
                    del_data = json.loads(resp.read().decode("utf-8"))
                    self.assertEqual(del_data["deleted_id"], sid_b)

                with self.assertRaises(urllib.error.HTTPError) as ctx_404:
                    urllib.request.urlopen(f"http://127.0.0.1:{self.port}/api/sessions/{sid_b}")
                self.assertEqual(ctx_404.exception.code, 404)
        finally:
            KamWebHandler.session_store = orig_store
            KamWebHandler.llm_client.conversation_history[:] = orig_history

    def test_upload_valid_path_traversal_400_and_oversize_413(self):
        import tempfile
        import urllib.error

        orig_uploads_dir = KamWebHandler.uploads_dir
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                KamWebHandler.uploads_dir = tmpdir
                url = f"http://127.0.0.1:{self.port}/api/upload"

                # 1. Geçerli dosya yükleme
                content = "KAM Otonom Sistem Raporu — Türkçe şğüöçıİ"
                req_ok = urllib.request.Request(
                    url,
                    data=json.dumps({"filename": "rapor_01.txt", "content": content}).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                )
                with urllib.request.urlopen(req_ok) as resp:
                    self.assertEqual(resp.status, 200)
                    up = json.loads(resp.read().decode("utf-8"))
                    self.assertEqual(up["status"], "ok")
                    self.assertEqual(up["path"], "data/uploads/rapor_01.txt")
                    self.assertEqual(up["size_bytes"], len(content.encode("utf-8")))
                    self.assertIn("Türkçe", up["preview"])
                saved_file = os.path.join(tmpdir, "rapor_01.txt")
                self.assertTrue(os.path.isfile(saved_file))

                # 2. Path traversal, ayırıcı ve ayrılmış Windows cihaz adı -> HTTP 400
                for bad_name in ("../evil.txt", "../../etc/passwd", "sub/file.txt", r"sub\file.txt", "CON.txt", ""):
                    req_bad = urllib.request.Request(
                        url,
                        data=json.dumps({"filename": bad_name, "content": "x"}).encode("utf-8"),
                        headers={"Content-Type": "application/json"},
                    )
                    with self.assertRaises(urllib.error.HTTPError, msg=f"Expected 400 for {bad_name!r}") as ctx:
                        urllib.request.urlopen(req_bad)
                    self.assertEqual(ctx.exception.code, 400)

                # 3. 2 MB üzeri içerik -> HTTP 413
                big_content = "A" * (2 * 1024 * 1024 + 64)
                req_big = urllib.request.Request(
                    url,
                    data=json.dumps({"filename": "huge.txt", "content": big_content}).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                )
                with self.assertRaises(urllib.error.HTTPError) as ctx_413:
                    urllib.request.urlopen(req_big)
                self.assertEqual(ctx_413.exception.code, 413)
        finally:
            KamWebHandler.uploads_dir = orig_uploads_dir

    def test_workflows_get_and_post_api(self):
        import urllib.error

        # 1. GET /api/workflows -> 3 yerleşik otonom iş akışı
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/api/workflows") as resp:
            self.assertEqual(resp.status, 200)
            wf_list = json.loads(resp.read().decode("utf-8"))
            wf_ids = {w["id"] for w in wf_list["workflows"]}
            self.assertEqual(wf_ids, {"system_health_audit", "repo_code_audit", "network_security_scan"})

        # 2. POST /api/workflows -> repo_code_audit icrası
        req_run = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/api/workflows",
            data=json.dumps({"workflow": "repo_code_audit"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req_run) as resp:
            self.assertEqual(resp.status, 200)
            wf_res = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(wf_res["status"], "ok")
            self.assertEqual(wf_res["workflow"], "repo_code_audit")
            self.assertEqual(len(wf_res["steps"]), 2)
            self.assertIn("summary", wf_res)

        # 3. Bilinmeyen iş akışı -> HTTP 404; boş -> HTTP 400
        req_404 = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/api/workflows",
            data=json.dumps({"workflow": "nonexistent_wf"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with self.assertRaises(urllib.error.HTTPError) as ctx_404:
            urllib.request.urlopen(req_404)
        self.assertEqual(ctx_404.exception.code, 404)

        req_400 = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/api/workflows",
            data=json.dumps({"workflow": ""}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with self.assertRaises(urllib.error.HTTPError) as ctx_400:
            urllib.request.urlopen(req_400)
        self.assertEqual(ctx_400.exception.code, 400)

if __name__ == "__main__":
    unittest.main()
