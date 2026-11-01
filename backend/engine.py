"""Deterministic local risk reasoning. SI units in simulation; heuristic units in vision."""
from dataclasses import dataclass, asdict
import math

PROFILES = {
    'human': {'sigma': .35, 'growth': .25, 'radius': .35, 'weight': .9},
    'animal': {'sigma': .65, 'growth': .65, 'radius': .65, 'weight': 1.0},
    'auto': {'sigma': .45, 'growth': .38, 'radius': .8, 'weight': .9},
    'bike': {'sigma': .35, 'growth': .35, 'radius': .5, 'weight': .85},
    'bus': {'sigma': .4, 'growth': .15, 'radius': 1.2, 'weight': 1.0},
    'thela': {'sigma': .35, 'growth': .18, 'radius': .7, 'weight': .8},
    'vehicle': {'sigma': .4, 'growth': .2, 'radius': .9, 'weight': .9},
}

@dataclass
class Track:
    id: int
    kind: str
    x: float
    y: float
    vx: float = 0
    vy: float = 0
    confidence: float = 1
    missed: float = 0
    age: float = 0
    acceleration: float = 0

class Tracker:
    """Class-gated nearest-neighbour association and alpha-beta filtering.
    Tracks coast for 2 seconds during missed observations, with growing uncertainty.
    IDs are inferred from detections, never copied from simulator ground truth.
    """
    def __init__(self):
        self.tracks = []
        self.next_id = 1

    def update(self, detections, dt):
        dt = max(.01, min(dt, .5))
        predictions = [(t.x+t.vx*dt, t.y+t.vy*dt) for t in self.tracks]
        candidates = []
        for i, t in enumerate(self.tracks):
            for j, d in enumerate(detections):
                distance = math.hypot(predictions[i][0]-d['x'], predictions[i][1]-d['y'])
                if t.kind == d['kind'] and distance < 2.5:
                    candidates.append((distance, i, j))
        used_t, used_d, matches = set(), set(), {}
        for _, i, j in sorted(candidates):
            if i not in used_t and j not in used_d:
                used_t.add(i); used_d.add(j); matches[i] = j
        kept = []
        for i, t in enumerate(self.tracks):
            px, py = predictions[i]
            if i in matches:
                d = detections[matches[i]]
                rx, ry = d['x']-px, d['y']-py
                old_speed = math.hypot(t.vx, t.vy)
                t.x, t.y = px+.8*rx, py+.8*ry
                t.vx += .2*rx/dt; t.vy += .2*ry/dt
                t.acceleration = (math.hypot(t.vx,t.vy)-old_speed)/dt
                t.missed = 0
                t.confidence = d.get('confidence', 1)
            else:
                t.x, t.y = px, py
                t.missed += dt
            t.age += dt
            if t.missed <= 2.0:
                kept.append(t)
        for j, d in enumerate(detections):
            if j not in used_d:
                kept.append(Track(self.next_id, d['kind'], d['x'], d['y'], confidence=d.get('confidence', 1)))
                self.next_id += 1
        self.tracks = kept
        return kept

def uncertainty(t, future, multiplier=1):
    p = PROFILES[t.kind]
    return p['radius'] + multiplier*(p['sigma'] + p['growth']*future + .6*t.missed + .1*min(abs(t.acceleration),3))

def point_risk(x, y, future, tracks, multiplier=1):
    survival = 1.0
    for t in tracks:
        px, py = t.x+t.vx*future, t.y+t.vy*future
        sigma = uncertainty(t, future, multiplier)
        # Includes ego footprint; uncertainty is a heuristic envelope, not a calibrated probability.
        dx, dy = (x-px)/(sigma+.65), (y-py)/(sigma+1.0)
        value = PROFILES[t.kind]['weight'] * math.exp(-.5*(dx*dx+dy*dy))
        survival *= 1-value
    return 1-survival

def behavior(t):
    if t.missed > 0: return 'Occluded · predicted only'
    if t.kind == 'animal': return 'Uncertain movement prior'
    if abs(t.vx) > .6: return 'Crossing / lateral movement'
    if t.acceleration < -1: return 'Decelerating'
    if math.hypot(t.vx,t.vy) < .25: return 'Stationary / initializing'
    return 'Steady movement'

class Reasoner:
    def __init__(self):
        self.action = 'STOP'
        self.clear_for = 0

    def analyze(self, tracks, speed, horizon=3, multiplier=1, memory=True, dt=.1, corridor=5):
        active = tracks if memory else [t for t in tracks if t.missed == 0]
        grid = []
        for row in range(30):
            y = row+0.5
            grid.append([round(max(point_risk(-7.5+col, y, tau, active,multiplier) for tau in (0,horizon/2,horizon)),3) for col in range(16)])
        # Evaluate time-aligned trajectories, not the maximum-over-time display grid.
        candidates = []
        for target in (-3., -1.5, 0., 1.5, 3.):
            if abs(target)+1 > corridor: continue
            path, risk = [], 0
            for n in range(1,13):
                tau = horizon*n/12
                blend = min(1,tau/2)
                x = target*blend*blend*(3-2*blend)
                y = 3+speed*tau
                if y > 29: break
                r = point_risk(x,y,tau,active,multiplier)
                path.append({'x':x,'y':y,'t':tau,'risk':r})
                risk = max(risk,r)
            candidates.append({'target':target,'risk':risk,'cost':risk+.025*abs(target),'points':path})
        best = min(candidates,key=lambda c:c['cost'])
        forward = next(c for c in candidates if c['target']==0)
        # Stopping corridor uses reaction distance + v^2/(2a), conservative near-field check.
        stopping = speed*.7+speed*speed/(2*4)+2
        near = max((point_risk(0,3+y,0,active,multiplier) for y in (0,1,2, min(stopping,12))),default=0)
        score = max(best['risk'], near*.9)
        desired = 'STOP' if score >= .68 else 'SLOW' if score >= .28 else 'CONTINUE'
        rank = {'CONTINUE':0,'SLOW':1,'STOP':2}
        if rank[desired]>=rank[self.action]:
            self.action = desired; self.clear_for=0
        else:
            self.clear_for += dt
            if self.clear_for >= .8: self.action=desired; self.clear_for=0
        reason = ('Predicted occupancy intersects all sampled paths.' if desired=='STOP' else
                  'Uncertainty overlaps the stopping or travel corridor.' if desired=='SLOW' else
                  'Selected path has low modeled occupancy risk.')
        if any(t.missed for t in active): reason += ' Occluded tracks retained.'
        if desired!=self.action: reason += ' Holding caution during release hysteresis.'
        output_tracks=[]
        for t in tracks:
            data=asdict(t)
            data.update(behavior=behavior(t), envelope=uncertainty(t,horizon,multiplier),
                        future=[{'x':t.x+t.vx*s,'y':t.y+t.vy*s,'sigma':uncertainty(t,s,multiplier),'t':s} for s in (0,1,2,horizon)])
            output_tracks.append(data)
        return dict(tracks=output_tracks,grid=grid,path=best['points'],candidates=candidates,
                    action=self.action,risk=round(score,3),baseline_risk=round(forward['risk'],3),
                    reason=reason,stopping_distance=round(stopping,2),steering=best['target'],
                    target_speed=0 if self.action=='STOP' else 2 if self.action=='SLOW' else 6,
                    brake=self.action=='STOP',horizon=horizon)
