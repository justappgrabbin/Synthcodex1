from io import BytesIO
import tempfile
import unittest
import wave
import numpy as np
from fastapi.testclient import TestClient
from api.server import create_app
from nsnf.acoustics import analyze_wav
from nsnf.runtime import Runtime


def tone():
    rate=16000
    values=(np.sin(2*np.pi*200*np.arange(rate)/rate)*12000).astype('<i2')
    stream=BytesIO()
    with wave.open(stream,'wb') as wav:
        wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(rate);wav.writeframes(values.tobytes())
    return stream.getvalue()


class AudioTests(unittest.TestCase):
    def test_native_frequency_timing_and_no_semantic_inference(self):
        result=analyze_wav(tone())
        self.assertEqual(result['duration_s'],1.)
        self.assertEqual(len(result['frames']),50)
        self.assertAlmostEqual(result['frames'][10]['candidate_f0_hz'],200,delta=3)
        self.assertIn('meaning',result['unknown'])
        self.assertEqual(result['frames'][-1]['end_s'],1.)
        with self.assertRaises(ValueError): analyze_wav(b'not audio')

    def test_real_audio_to_field_artifacts_and_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime=Runtime(directory)
            result=runtime.ingest_audio(tone())
            run=runtime.record(result['contact']['field_run'])['payload']
            self.assertEqual(run['features'],result['analysis']['neural_features'])
            self.assertEqual(runtime.artifact(result['source_hash'])[1],tone())
            self.assertTrue(runtime.replay(result['contact']['field_run'])['exact'])
            restarted=Runtime(directory)
            self.assertEqual(restarted.artifact(result['source_hash'])[1],tone())
            with self.assertRaises(KeyError): restarted.artifact(runtime.store.put({'private-model':'not-an-artifact'}))
            restarted.store.db.close();runtime.store.db.close()

    def test_http_receive_and_retrieve(self):
        with tempfile.TemporaryDirectory() as directory:
            app=create_app(directory)
            with TestClient(app) as client:
                result=client.post('/audio',content=tone(),headers={'content-type':'audio/wav'})
                self.assertEqual(result.status_code,200)
                saved=result.json()
                self.assertEqual(client.get('/artifacts/'+saved['source_hash']).content,tone())
                self.assertEqual(client.get('/artifacts/not-a-hash').status_code,404)
                self.assertEqual(client.post('/audio',content=b'invalid').status_code,400)
            app.state.runtime.store.db.close()
