import tempfile
import unittest
from fastapi.testclient import TestClient
from api.server import create_app


class APITests(unittest.TestCase):
    def test_real_execute_feedback_replay_restore_and_failures(self):
        with tempfile.TemporaryDirectory() as directory:
            app = create_app(directory)
            with TestClient(app) as client:
                self.assertEqual(client.get('/').status_code,200)
                self.assertEqual(client.get('/health').status_code,200)
                self.assertEqual(len(client.get('/topology').json()['slots']),320)
                self.assertEqual(client.post('/execute',json={'features':[1]*7}).status_code,422)
                run=client.post('/execute',json={'features':[1,0,0,0,0,0,0,0]}).json()
                self.assertEqual(len(run['selected']),5)
                self.assertEqual(client.post('/feedback',json={'run_id':run['id'],'target':1,'evidence_ref':'test-label'}).status_code,200)
                self.assertTrue(client.post(f"/runs/{run['id']}/replay").json()['exact'])
                saved=client.post('/checkpoint').json()
                self.assertEqual(client.post('/restore',json={'id':saved['id']}).status_code,200)
                self.assertEqual(client.get('/runs/missing').status_code,404)
                self.assertEqual(client.post('/restore',json={}).status_code,400)
                self.assertEqual(client.post('/execute',json={'features':[1]*8,'tier':9}).status_code,422)
            app.state.runtime.store.db.close()
