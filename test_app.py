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
        # Verify /viewer renders correctly
        res = self.client.get('/viewer?monitor=1&mode=random&interval=30&fit=cover')
        self.assertEqual(res.status_code, 200)

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
        import routes.views
        import routes.api_display
        import routes.api_media
        import routes.api_schedules

        self.assertTrue(callable(display.start_display))
        self.assertTrue(callable(display.blank_screen))
        self.assertTrue(callable(services.storage.load_websites))
        self.assertTrue(callable(services.display_service.trigger_display_action))

if __name__ == '__main__':
    unittest.main()

