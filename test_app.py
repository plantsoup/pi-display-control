import unittest
import json
import os
from app import app, load_websites, load_images, load_slideshow_config, load_schedules

class PiDisplayControlTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.client = self.app.test_client()
        self.client.testing = True

    def test_status_endpoint(self):
        res = self.client.get('/api/status')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data['success'])
        self.assertIn('counts', data)
        self.assertIn('state', data)

    def test_websites_endpoints(self):
        # GET
        res = self.client.get('/api/websites')
        self.assertEqual(res.status_code, 200)
        websites = json.loads(res.data)
        self.assertIsInstance(websites, list)

        # POST
        res_post = self.client.post('/api/websites', json={
            'name': 'Test Dashboard',
            'url': 'https://dashboard.example.com'
        })
        self.assertEqual(res_post.status_code, 200)
        data_post = json.loads(res_post.data)
        self.assertTrue(data_post['success'])

        # DELETE last website
        last_idx = len(data_post['websites']) - 1
        res_del = self.client.delete(f'/api/websites/{last_idx}')
        self.assertEqual(res_del.status_code, 200)
        data_del = json.loads(res_del.data)
        self.assertTrue(data_del['success'])

    def test_slideshow_config(self):
        # GET
        res = self.client.get('/api/slideshow')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data['success'])
        self.assertIn('config', data)

        # POST update
        res_update = self.client.post('/api/slideshow', json={
            'mode': 'random',
            'interval': 45,
            'transition': 'fade',
            'fit': 'cover'
        })
        self.assertEqual(res_update.status_code, 200)
        data_update = json.loads(res_update.data)
        self.assertTrue(data_update['success'])
        self.assertEqual(data_update['config']['mode'], 'random')
        self.assertEqual(data_update['config']['interval'], 45)
        self.assertEqual(data_update['config']['fit'], 'cover')

    def test_viewer_data(self):
        res = self.client.get('/api/viewer/data')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data['success'])
        self.assertIn('images', data)
        self.assertIn('config', data)

    def test_schedules_crud(self):
        # POST
        res = self.client.post('/api/schedules', json={
            'name': 'Night Time Slideshow',
            'time': '20:00',
            'action': 'slideshow',
            'params': {'mode': 'random', 'interval': 20, 'monitor': 'both'}
        })
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data['success'])
        new_id = data['schedule']['id']

        # TOGGLE
        res_toggle = self.client.put(f'/api/schedules/{new_id}/toggle')
        self.assertEqual(res_toggle.status_code, 200)
        data_toggle = json.loads(res_toggle.data)
        self.assertTrue(data_toggle['success'])

        # DELETE
        res_del = self.client.delete(f'/api/schedules/{new_id}')
        self.assertEqual(res_del.status_code, 200)
        data_del = json.loads(res_del.data)
        self.assertTrue(data_del['success'])

    def test_dual_monitor_mixed_dispatch(self):
        # Mixed dispatch: Website on Monitor 1, Slideshow on Monitor 2
        res = self.client.post('/api/display', json={
            'monitor': 'both',
            'monitor1': {'type': 'website', 'url': 'https://autodarts.io'},
            'monitor2': {'type': 'slideshow', 'mode': 'random', 'interval': 15, 'fit': 'cover'}
        })
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data['success'])

        # Verify slideshow config mode remains 'random', not corrupted to 'slideshow'
        cfg = load_slideshow_config()
        self.assertEqual(cfg['mode'], 'random')

        # Single monitor update: Monitor 2 only with fit cover
        res2 = self.client.post('/api/display', json={
            'monitor': '2',
            'monitor2': {'type': 'image', 'image': 'test.jpg', 'fit': 'cover'}
        })
        self.assertEqual(res2.status_code, 200)
        data2 = json.loads(res2.data)
        self.assertTrue(data2['success'])

    def test_slideshow_launch_mode_preservation(self):
        # Launch slideshow with random mode
        res = self.client.post('/api/display', json={
            'mode': 'slideshow',
            'monitor': 'both',
            'interval': 30,
            'slideshow_mode': 'random',
            'fit': 'cover'
        })
        self.assertEqual(res.status_code, 200)
        cfg = load_slideshow_config()
        self.assertEqual(cfg['mode'], 'random')
        self.assertEqual(cfg['fit'], 'cover')

    def test_viewer_route(self):
        # Verify /viewer and / dashboard render correctly
        res = self.client.get('/viewer?monitor=1&mode=random&interval=30&fit=cover')
        self.assertEqual(res.status_code, 200)

        res_idx = self.client.get('/')
        self.assertEqual(res_idx.status_code, 200)
        html = res_idx.data.decode('utf-8')
        self.assertIn('nodeSwitcherBar', html)
        self.assertIn('nodesTab', html)
        self.assertIn('nodeModal', html)

    def test_display_blank_and_wake_endpoints(self):
        # Test DELETE /api/display (Blank)
        res_blank = self.client.delete('/api/display')
        self.assertEqual(res_blank.status_code, 200)
        data_blank = json.loads(res_blank.data)
        self.assertTrue(data_blank['success'])
        self.assertEqual(data_blank['state']['status'], 'blank')

        # Test POST /api/display/wake (Wake)
        res_wake = self.client.post('/api/display/wake')
        self.assertEqual(res_wake.status_code, 200)
        data_wake = json.loads(res_wake.data)
        self.assertTrue(data_wake['success'])
        self.assertEqual(data_wake['state']['status'], 'running')

    def test_display_manager_preferences_fix(self):
        import display_manager
        import tempfile
        import shutil
        
        temp_dir = tempfile.mkdtemp()
        try:
            default_dir = os.path.join(temp_dir, "Default")
            os.makedirs(default_dir, exist_ok=True)
            prefs_path = os.path.join(default_dir, "Preferences")
            with open(prefs_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "profile": {
                        "exit_type": "Crashed",
                        "exited_cleanly": False
                    }
                }, f)

            display_manager.fix_chromium_preferences(temp_dir)

            with open(prefs_path, 'r', encoding='utf-8') as f:
                fixed_data = json.load(f)

            self.assertEqual(fixed_data["profile"]["exit_type"], "Normal")
            self.assertTrue(fixed_data["profile"]["exited_cleanly"])
        finally:
            shutil.rmtree(temp_dir)

    def test_modular_package_structure(self):
        """Verify new modular packages can be imported directly"""
        import display
        import display.browser
        import display.monitors
        import display.power
        import display.window
        import display.manager
        import services.storage
        import services.display_service
        import services.scheduler
        import services.nodes_service
        import routes.views
        import routes.api_display
        import routes.api_media
        import routes.api_schedules
        import routes.api_nodes

        self.assertTrue(callable(display.start_display))
        self.assertTrue(callable(display.blank_screen))
        self.assertEqual(display.DEFAULT_AUTODARTS_URL, "https://play.autodarts.io")
        self.assertEqual(display.DEFAULT_AUTODARTS_URL2, "https://play.autodarts.io")
        self.assertTrue(callable(services.storage.load_websites))
        self.assertTrue(callable(services.display_service.trigger_display_action))
        self.assertTrue(callable(display.apply_monitor_rotation))
        self.assertTrue(callable(display.set_default_rotation))
        self.assertTrue(callable(display.get_monitor_rotation))
        self.assertTrue(callable(services.nodes_service.normalize_node_url))

    def test_display_rotation_and_default_persistence(self):
        """Test setting monitor rotations, saving defaults, and persistence"""
        from display.config import load_display_config, set_default_rotation, get_monitor_rotation

        # Set default rotation for monitor 1 and monitor 2
        set_default_rotation("1", "normal")
        set_default_rotation("2", "left")

        # Verify defaults are retrieved
        self.assertEqual(get_monitor_rotation("1"), "normal")
        self.assertEqual(get_monitor_rotation("2"), "left")

        # Verify invalid rotation raises ValueError
        with self.assertRaises(ValueError):
            set_default_rotation("1", "diagonal_invalid")

        # Verify GET /api/display/monitors
        res = self.client.get('/api/display/monitors')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data['success'])
        self.assertIn('defaults', data)
        self.assertEqual(data['defaults']['1'], 'normal')
        self.assertEqual(data['defaults']['2'], 'left')
        self.assertIn('available_rotations', data)
        self.assertIn('monitors', data)

        # Test POST /api/display/rotate with save_default=True
        res_rot = self.client.post('/api/display/rotate', json={
            'monitor': '1',
            'rotation': 'right',
            'save_default': True,
            'restart_browser': False
        })
        self.assertEqual(res_rot.status_code, 200)
        data_rot = json.loads(res_rot.data)
        self.assertTrue(data_rot['success'])
        self.assertEqual(data_rot['defaults']['1'], 'right')
        self.assertEqual(get_monitor_rotation("1"), "right")

        # Test POST /api/display/defaults (bulk save)
        res_def = self.client.post('/api/display/defaults', json={
            'rotations': {
                '1': 'left',
                '2': 'right'
            },
            'apply_now': False
        })
        self.assertEqual(res_def.status_code, 200)
        data_def = json.loads(res_def.data)
        self.assertTrue(data_def['success'])
        self.assertEqual(data_def['defaults']['1'], 'left')
        self.assertEqual(data_def['defaults']['2'], 'right')
        self.assertEqual(get_monitor_rotation("1"), "left")
        self.assertEqual(get_monitor_rotation("2"), "right")

        # Test POST /api/display/reset-defaults
        res_reset = self.client.post('/api/display/reset-defaults', json={
            'restart_browser': False
        })
        self.assertEqual(res_reset.status_code, 200)
        data_reset = json.loads(res_reset.data)
        self.assertTrue(data_reset['success'])

    def test_nodes_url_normalization_and_payload_streaming(self):
        """Test URL normalization for domains / .local / LAN IPs and remote viewer streaming"""
        from services.nodes_service import (
            normalize_node_url,
            is_self_node,
            prepare_remote_display_payload
        )

        self.assertEqual(normalize_node_url("pi.example.com"), "https://pi.example.com")
        self.assertEqual(normalize_node_url("pi2.example.com"), "https://pi2.example.com")
        self.assertEqual(normalize_node_url("https://pi2.example.com/api/status"), "https://pi2.example.com")
        self.assertEqual(normalize_node_url("192.168.1.45:5000"), "http://192.168.1.45:5000")
        self.assertEqual(normalize_node_url("pi2.local"), "http://pi2.local")

        with self.assertRaises(ValueError):
            normalize_node_url("ftp://pi2.example.com")

        self.assertTrue(is_self_node("https://pi2.example.com", request_host="pi2.example.com"))
        self.assertFalse(is_self_node("https://pi2.example.com", request_host="pi.example.com"))

        # Verify streaming Main Pi slideshow to remote Pi converts to Main Pi's /viewer URL
        streamed = prepare_remote_display_payload({
            "mode": "slideshow",
            "monitor": "both",
            "slideshow_mode": "random",
            "interval": 25,
            "fit": "cover",
            "stream_from_main": True
        }, "https://pi.example.com")

        self.assertEqual(streamed["monitor"], "both")
        self.assertEqual(streamed["monitor1"]["type"], "website")
        self.assertIn("https://pi.example.com/viewer?monitor=1&mode=random&interval=25&fit=cover", streamed["monitor1"]["url"])
        self.assertIn("https://pi.example.com/viewer?monitor=2&mode=random&interval=25&fit=cover", streamed["monitor2"]["url"])

        # Verify mixed monitor payload with main_image and website
        mixed_stream = prepare_remote_display_payload({
            "monitor": "both",
            "monitor1": {"type": "website", "url": "https://play.autodarts.io"},
            "monitor2": {"type": "main_image", "image": "poster.jpg", "fit": "contain"}
        }, "https://pi.example.com")
        self.assertEqual(mixed_stream["monitor1"]["url"], "https://play.autodarts.io")
        self.assertEqual(
            mixed_stream["monitor2"]["url"],
            "https://pi.example.com/viewer?single=poster.jpg&monitor=2&fit=contain"
        )

    def test_nodes_defaults_crud_and_live_peer_connection(self):
        """Test generic default node config, env var seeding, CRUD, proxy, broadcast, and sync with a live peer server"""
        import threading
        from unittest.mock import patch
        from werkzeug.serving import make_server
        from app import create_app, NODES_CONFIG_FILE

        had_existing = os.path.exists(NODES_CONFIG_FILE)
        backup_bytes = None
        if had_existing:
            with open(NODES_CONFIG_FILE, "rb") as f:
                backup_bytes = f.read()
            os.remove(NODES_CONFIG_FILE)

        peer_server = None
        peer_thread = None
        try:
            # 1. Verify generic defaults: local node auto-detects host URL and no fake remote nodes are pre-seeded
            res_list = self.client.get('/api/nodes')
            self.assertEqual(res_list.status_code, 200)
            list_data = json.loads(res_list.data)
            self.assertTrue(list_data['success'])
            self.assertEqual(list_data['local']['configured_url'], '')
            self.assertTrue(list_data['local']['url'].startswith(('http://', 'https://')))
            self.assertEqual(len(list_data['nodes']), 0)

            # Verify optional MAIN_PI_URL / SECONDARY_PI_URL environment variable seeding
            with patch.dict(os.environ, {
                'MAIN_PI_URL': 'https://pi.example.com',
                'SECONDARY_PI_URL': 'https://pi2.example.com'
            }):
                res_env = self.client.get('/api/nodes')
                env_data = json.loads(res_env.data)
                self.assertEqual(env_data['local']['url'], 'https://pi.example.com')
                self.assertEqual(len(env_data['nodes']), 1)
                self.assertEqual(env_data['nodes'][0]['url'], 'https://pi2.example.com')

            # Verify setting and clearing local public URL override
            res_set_local = self.client.put('/api/nodes/local', json={'url': 'pi.example.com'})
            self.assertEqual(res_set_local.status_code, 200)
            self.assertEqual(json.loads(res_set_local.data)['node']['configured_url'], 'https://pi.example.com')

            res_clear_local = self.client.put('/api/nodes/local', json={'url': ''})
            self.assertEqual(res_clear_local.status_code, 200)
            self.assertEqual(json.loads(res_clear_local.data)['node']['configured_url'], '')

            # Cannot delete local Pi
            res_del_local = self.client.delete('/api/nodes/local')
            self.assertEqual(res_del_local.status_code, 400)

            # Loop prevention check when X-Pi-Proxy-Hop header is present
            res_loop = self.client.post(
                '/api/nodes/broadcast',
                json={'action': 'wake'},
                headers={'X-Pi-Proxy-Hop': '1'}
            )
            self.assertEqual(res_loop.status_code, 400)

            # 2. Spin up a real secondary Pi Display Control server on an ephemeral port
            peer_app = create_app()
            peer_server = make_server('127.0.0.1', 0, peer_app)
            peer_port = peer_server.server_port
            peer_url = f"http://127.0.0.1:{peer_port}"
            peer_thread = threading.Thread(target=peer_server.serve_forever, daemon=True)
            peer_thread.start()

            # 3. Probe the live secondary Pi instance
            res_probe = self.client.post('/api/nodes/probe', json={
                'url': f"127.0.0.1:{peer_port}",
                'auto_discover': True
            })
            self.assertEqual(res_probe.status_code, 200)
            probe_data = json.loads(res_probe.data)
            self.assertTrue(probe_data['success'])
            self.assertTrue(probe_data['probe']['online'])
            self.assertEqual(probe_data['probe']['resolved_url'], peer_url)
            self.assertEqual(probe_data['probe']['monitor_count'], len(probe_data['probe']['monitors']))

            # 4. Connect the live secondary Pi via POST /api/nodes
            res_add = self.client.post('/api/nodes', json={
                'name': 'Live Test Pi 2',
                'url': f"127.0.0.1:{peer_port}",
                'role': 'secondary'
            })
            self.assertEqual(res_add.status_code, 200)
            add_data = json.loads(res_add.data)
            self.assertTrue(add_data['success'])
            peer_id = add_data['node']['id']
            self.assertEqual(add_data['node']['url'], peer_url)

            # Duplicate URL should be rejected
            res_dup = self.client.post('/api/nodes', json={
                'name': 'Duplicate Pi',
                'url': peer_url
            })
            self.assertEqual(res_dup.status_code, 400)

            # 5. Proxy GET /api/status and GET /api/display/monitors through Main Pi to Secondary Pi
            res_prox_status = self.client.get(f'/api/nodes/{peer_id}/proxy/api/status')
            self.assertEqual(res_prox_status.status_code, 200)
            prox_status_data = json.loads(res_prox_status.data)
            self.assertTrue(prox_status_data['success'])
            self.assertIn('state', prox_status_data)

            res_prox_mon = self.client.get(f'/api/nodes/{peer_id}/proxy/api/display/monitors')
            self.assertEqual(res_prox_mon.status_code, 200)
            prox_mon_data = json.loads(res_prox_mon.data)
            self.assertTrue(prox_mon_data['success'])
            self.assertIn('monitors', prox_mon_data)

            # Block invalid proxied paths
            res_bad_prox = self.client.get(f'/api/nodes/{peer_id}/proxy/api/nodes')
            self.assertEqual(res_bad_prox.status_code, 400)

            # 6. Dispatch wake & blank to the connected secondary Pi
            res_peer_blank = self.client.post(f'/api/nodes/{peer_id}/display', json={'action': 'blank'})
            self.assertEqual(res_peer_blank.status_code, 200)
            self.assertTrue(json.loads(res_peer_blank.data)['success'])

            res_peer_wake = self.client.post(f'/api/nodes/{peer_id}/display', json={'action': 'wake'})
            self.assertEqual(res_peer_wake.status_code, 200)
            self.assertTrue(json.loads(res_peer_wake.data)['success'])

            # 7. Broadcast wake across local + live peer
            res_bcast = self.client.post('/api/nodes/broadcast', json={
                'action': 'wake',
                'node_ids': ['local', peer_id]
            })
            self.assertEqual(res_bcast.status_code, 200)
            bcast_data = json.loads(res_bcast.data)
            self.assertTrue(bcast_data['success'])
            self.assertEqual(len(bcast_data['results']), 2)
            self.assertTrue(all(r['success'] for r in bcast_data['results']))

            # 8. Sync websites & slideshow config to live peer
            res_sync = self.client.post(f'/api/nodes/{peer_id}/sync', json={
                'websites': True,
                'slideshow': True,
                'images': False
            })
            self.assertEqual(res_sync.status_code, 200)
            self.assertTrue(json.loads(res_sync.data)['success'])

            # 9. Update & Delete connected Pi node
            res_upd = self.client.put(f'/api/nodes/{peer_id}', json={'name': 'Updated Pi 2'})
            self.assertEqual(res_upd.status_code, 200)
            self.assertEqual(json.loads(res_upd.data)['node']['name'], 'Updated Pi 2')

            res_del = self.client.delete(f'/api/nodes/{peer_id}')
            self.assertEqual(res_del.status_code, 200)
            self.assertTrue(json.loads(res_del.data)['success'])
        finally:
            if peer_server:
                peer_server.shutdown()
                peer_server.server_close()
            if had_existing and backup_bytes is not None:
                with open(NODES_CONFIG_FILE, "wb") as f:
                    f.write(backup_bytes)
            elif os.path.exists(NODES_CONFIG_FILE):
                os.remove(NODES_CONFIG_FILE)

    def test_available_monitors_only_detection_and_filtering(self):
        """Verify 0, 1, and 2 monitor topologies, headless virtual output filtering, and legacy peer filtering"""
        from unittest.mock import patch, MagicMock
        import display.monitors as mon_mod
        from services.nodes_service import filter_available_monitors

        # 1. Headless xrandr output with NOOP-1 virtual output + disconnected HDMI ports -> 0 monitors
        headless_xrandr = (
            "Screen 0: minimum 320 x 200, current 1920 x 1080, maximum 8192 x 8192\n"
            "NOOP-1 connected primary 1920x1080+0+0 (normal left inverted right) 0mm x 0mm\n"
            "   1920x1080     60.00*+\n"
            "HDMI-1 disconnected (normal left inverted right)\n"
            "HDMI-2 disconnected (normal left inverted right)\n"
        )
        mock_proc_headless = MagicMock(returncode=0, stdout=headless_xrandr)
        with patch("display.monitors.subprocess.run", return_value=mock_proc_headless):
            self.assertEqual(mon_mod.get_connected_monitors(), [])

        # 2. Blanked physical HDMI-1 (connected without active geometry) + disconnected HDMI-2 -> 1 monitor
        blanked_single_xrandr = (
            "Screen 0: minimum 320 x 200, current 320 x 200, maximum 8192 x 8192\n"
            "HDMI-1 connected (normal left inverted right x axis y axis) 527mm x 296mm\n"
            "   1920x1080     60.00 +\n"
            "HDMI-2 disconnected (normal left inverted right x axis y axis)\n"
        )
        mock_proc_single = MagicMock(returncode=0, stdout=blanked_single_xrandr)
        with patch("display.monitors.subprocess.run", return_value=mock_proc_single):
            detected = mon_mod.get_connected_monitors()
            self.assertEqual(len(detected), 1)
            self.assertEqual(detected[0]["name"], "HDMI-1")
            self.assertTrue(detected[0]["connected"])

        # 3. API endpoints with 0, 1, and 2 connected monitors
        with patch("routes.api_display.get_connected_monitors", return_value=[]), \
             patch("services.nodes_service.get_connected_monitors", return_value=[]):
            res0 = self.client.get("/api/display/monitors")
            data0 = json.loads(res0.data)
            self.assertTrue(data0["success"])
            self.assertEqual(data0["count"], 0)
            self.assertEqual(data0["monitors"], [])

            res_loc0 = self.client.get("/api/nodes/local/status")
            loc0 = json.loads(res_loc0.data)["node"]
            self.assertEqual(loc0["monitor_count"], 0)
            self.assertEqual(loc0["monitors"], [])

        one_mon = [{
            "name": "HDMI-A-1",
            "primary": True,
            "orig_width": 1920,
            "orig_height": 1080,
            "width": 1080,
            "height": 1920,
            "pos_x": 0,
            "pos_y": 0,
            "rotation": "left",
            "modes": ["1920x1080"],
            "connected": True
        }]
        with patch("routes.api_display.get_connected_monitors", return_value=one_mon):
            res1 = self.client.get("/api/display/monitors")
            data1 = json.loads(res1.data)
            self.assertEqual(data1["count"], 1)
            self.assertEqual(len(data1["monitors"]), 1)
            self.assertEqual(data1["monitors"][0]["name"], "HDMI-A-1")
            self.assertEqual(data1["monitors"][0]["index"], 1)
            self.assertTrue(data1["monitors"][0]["connected"])

        two_mons = one_mon + [{
            "name": "HDMI-A-2",
            "primary": False,
            "orig_width": 1920,
            "orig_height": 1080,
            "width": 1080,
            "height": 1920,
            "pos_x": 1080,
            "pos_y": 0,
            "rotation": "right",
            "modes": ["1920x1080"],
            "connected": True
        }]
        with patch("routes.api_display.get_connected_monitors", return_value=two_mons):
            res2 = self.client.get("/api/display/monitors")
            data2 = json.loads(res2.data)
            self.assertEqual(data2["count"], 2)
            self.assertEqual([m["index"] for m in data2["monitors"]], [1, 2])

        # 4. Backwards compatibility: filter out legacy synthetic connected=False slots from un-updated peers
        legacy_payload = [
            {"index": 1, "name": "HDMI-1 (Primary)", "connected": False},
            {"index": 2, "name": "HDMI-2 (Secondary)", "connected": False}
        ]
        self.assertEqual(filter_available_monitors(legacy_payload, reported_count=0), [])
        self.assertEqual(filter_available_monitors(legacy_payload, reported_count=2), [])

        mixed_legacy = [
            {"index": 1, "name": "HDMI-1", "connected": True},
            {"index": 2, "name": "HDMI-2 (Secondary)", "connected": False}
        ]
        filtered_mixed = filter_available_monitors(mixed_legacy)
        self.assertEqual(len(filtered_mixed), 1)
        self.assertEqual(filtered_mixed[0]["name"], "HDMI-1")

if __name__ == '__main__':
    unittest.main()


