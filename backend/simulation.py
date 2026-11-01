import math
from .engine import Tracker, Reasoner

SCENARIOS = {
 'mixed': ('Unstructured street', 'Six road-user classes on a road with no lane markings.'),
 'animal': ('Human vs animal', 'Equal positions and motion: compare class-dependent uncertainty envelopes.'),
 'crossing': ('Pedestrian crossing', 'A pedestrian enters the ego travel corridor.'),
 'occlusion': ('Hidden pedestrian', 'A bus hides a pedestrian for 1.5 seconds. Toggle track memory to compare.'),
 'bus': ('Sudden bus stop', 'A moving bus brakes ahead of the ego vehicle.'),
 'clear': ('Clear road', 'Baseline for CONTINUE and low risk.'),
}
class Simulation:
 def __init__(self, scenario='mixed'):
    self.scenario=scenario; self.time=0.; self.speed=4.; self.distance=0.
    self.tracker=Tracker(); self.reasoner=Reasoner(); self.history=[]
 def detections(self):
    t=self.time
    if self.scenario=='clear': return []
    if self.scenario=='animal': return [dict(kind=k,x=x,y=14,confidence=.98) for k,x in [('human',-3),('animal',3)]]
    if self.scenario=='crossing': return [dict(kind='human',x=-5+min(t*.8,10),y=11,confidence=.96)]
    if self.scenario=='occlusion':
       obs=[dict(kind='bus',x=2.7,y=17,confidence=.98)]
       if not 3<t%10<4.5: obs.append(dict(kind='human',x=-4+(t%10)*.7,y=10,confidence=.95))
       return obs
    if self.scenario=='bus': return [dict(kind='bus',x=0,y=max(8,22-self.distance+min(t,2)*4),confidence=.98)]
    return [dict(kind=k,x=x,y=y,confidence=.96) for k,x,y in [
      ('animal',3+math.sin(t*1.2)*1.2,12),('human',-4+math.sin(t*.4)*1.8,20),
      ('auto',math.sin(t*.8)*1.4,25),('bike',-2.8,28-(t*1.3)%18),
      ('bus',3.5,27),('thela',-3.5,7+(t*.4)%10)]]
 def step(self,dt=.1,horizon=3,multiplier=1,memory=True,corridor=5):
    self.time+=dt; self.distance+=self.speed*dt
    detections=self.detections()
    tracks=self.tracker.update(detections,dt)
    result=self.reasoner.analyze(tracks,self.speed,horizon,multiplier,memory,dt,corridor)
    target=result['target_speed']
    self.speed=max(0,self.speed+max(-4*dt,min(1.5*dt,target-self.speed)))
    result.update(time=round(self.time,2),speed=round(self.speed,2),scenario=self.scenario,
                  mode='simulation',detections=detections,corridor=corridor,
                  source_note='Synthetic detections · metric simulation · no learned vision model')
    self.history.append({k:result[k] for k in ('time','speed','action','risk','steering')})
    self.history=self.history[-3000:]
    return result
