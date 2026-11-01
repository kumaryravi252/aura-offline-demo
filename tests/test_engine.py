import json
import threading
import unittest
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from backend.engine import Track, Tracker, Reasoner, uncertainty, point_risk
from backend.simulation import Simulation, SCENARIOS
from server import create_server

class EngineTests(unittest.TestCase):
 def test_animal_envelope_grows_faster(self):
  a,h=Track(1,'animal',0,12),Track(2,'human',0,12)
  self.assertGreater(uncertainty(a,3),uncertainty(h,3))
  self.assertGreater(uncertainty(a,3)-uncertainty(a,1),uncertainty(h,3)-uncertainty(h,1))
 def test_animal_larger_risk_footprint(self):
  self.assertGreater(point_risk(3,12,3,[Track(1,'animal',0,12)]),point_risk(3,12,3,[Track(1,'human',0,12)]))
 def test_tracker_identity_and_speed(self):
  tracker=Tracker()
  for n in range(30): tracks=tracker.update([dict(kind='human',x=n*.1,y=10)],.1)
  self.assertEqual(tracks[0].id,1); self.assertAlmostEqual(tracks[0].vx,1,delta=.02)
 def test_coasting_and_expiry(self):
  tracker=Tracker(); tracker.update([dict(kind='human',x=0,y=8)],.1)
  for _ in range(15): tracker.update([],.1)
  self.assertEqual(len(tracker.tracks),1); self.assertGreater(tracker.tracks[0].missed,1)
  for _ in range(6): tracker.update([],.1)
  self.assertEqual(tracker.tracks,[])
 def test_occlusion_memory_changes_risk(self):
  tracks=[Track(1,'human',0,5,missed=1)]
  enabled=Reasoner().analyze(tracks,4,memory=True)
  disabled=Reasoner().analyze(tracks,4,memory=False)
  self.assertGreater(enabled['risk'],disabled['risk']); self.assertEqual(enabled['action'],'STOP')
 def test_stop_and_hysteresis(self):
  engine=Reasoner(); self.assertEqual(engine.analyze([Track(1,'bus',0,4)],4)['action'],'STOP')
  self.assertEqual(engine.analyze([],4)['action'],'STOP')
  for _ in range(10): result=engine.analyze([],4)
  self.assertEqual(result['action'],'CONTINUE')
 def test_candidate_paths_stay_inside_corridor(self):
  out=Reasoner().analyze([],4,corridor=2)
  self.assertTrue(all(abs(p['x'])<=1 for c in out['candidates'] for p in c['points']))
 def test_all_scenarios_finite(self):
  for key in SCENARIOS:
   sim=Simulation(key)
   for _ in range(60): state=sim.step()
   json.dumps(state,allow_nan=False); self.assertTrue(0<=state['risk']<=1)
   self.assertEqual(len(state['grid']),30); self.assertTrue(all(len(row)==16 for row in state['grid']))
 def test_occlusion_scenario_reacquires_id(self):
  sim=Simulation('occlusion'); original=None; saw_ghost=False
  for _ in range(50):
   state=sim.step(); human=next(t for t in state['tracks'] if t['kind']=='human')
   original=original or human['id']; self.assertEqual(human['id'],original); saw_ghost |= human['missed']>0
  self.assertTrue(saw_ghost); self.assertEqual(human['missed'],0)

class APITests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.server=create_server(port=0); cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True); cls.thread.start()
  cls.base='http://127.0.0.1:'+str(cls.server.server_port)
 @classmethod
 def tearDownClass(cls): cls.server.shutdown(); cls.server.server_close(); cls.thread.join()
 def post(self,path,data):
  return urlopen(Request(self.base+path,data=json.dumps(data).encode(),headers={'Content-Type':'application/json'}))
 def test_health_and_frontend(self):
  self.assertTrue(json.load(urlopen(self.base+'/api/health'))['offline']); self.assertIn(b'AURA',urlopen(self.base+'/').read())
 def test_step_reset_export(self):
  self.post('/api/reset',{'scenario':'clear'})
  self.assertEqual(json.load(self.post('/api/step',{}))['scenario'],'clear')
  self.assertTrue(json.load(urlopen(self.base+'/api/export'))['history'])
 def test_bad_input_rejected(self):
  for data in ({'horizon':99},{'dt':-1},{'horizon':'three'},{'memory':'yes'},{'multiplier':float('nan')}):
   with self.assertRaises(HTTPError) as context:self.post('/api/step',data)
   self.assertEqual(context.exception.code,400)
 def test_bad_scenario_rejected(self):
  with self.assertRaises(HTTPError) as context:self.post('/api/reset',{'scenario':'missing'})
  self.assertEqual(context.exception.code,400)
 def test_cross_origin_write_rejected(self):
  req=Request(self.base+'/api/step',data=b'{}',headers={'Origin':'https://example.org'})
  with self.assertRaises(HTTPError) as context:urlopen(req)
  self.assertEqual(context.exception.code,403)

if __name__=='__main__':unittest.main()
