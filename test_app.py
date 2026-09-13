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

    def test_render_index_and_viewer(self):
        res_idx = self.client.get('/')
        self.assertEqual(res_idx.status_code, 200)
        self.assertIn(b'Slideshow Studio', res_idx.data)

        res_viewer = self.client.get('/viewer')
        self.assertEqual(res_viewer.status_code, 200)
        self.assertIn(b'Display Viewer', res_viewer.data)

if __name__ == '__main__':
    unittest.main()
