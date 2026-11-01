"""Optional local inference. Never downloads weights or accepts a network video source."""
import base64
import os
from pathlib import Path
import time
from .engine import Tracker, Reasoner

class Vision:
 def __init__(self,model_path,source):
    if not Path(model_path).is_file(): raise ValueError('Supply an existing local .pt model file; automatic downloads are disabled.')
    if not source.isdigit() and not Path(source).is_file(): raise ValueError('Source must be a camera index or existing local video file.')
    os.environ['YOLO_OFFLINE']='true'
    import cv2
    from ultralytics import YOLO, settings
    settings.update({'sync':False})
    self.cv=cv2; self.model=YOLO(str(Path(model_path).resolve()))
    self.cap=cv2.VideoCapture(int(source) if source.isdigit() else str(Path(source).resolve()))
    if not self.cap.isOpened(): raise ValueError('Cannot open camera/video source.')
    self.tracker=Tracker(); self.reasoner=Reasoner(); self.last=time.monotonic(); self.time=0
    self.file_source=not source.isdigit(); self.fps=self.cap.get(cv2.CAP_PROP_FPS) or 25
 def step(self,dt=.1,horizon=3,multiplier=1,memory=True,corridor=5):
    cv=self.cv
    ok,frame=self.cap.read()
    if not ok: raise ValueError('Video ended or camera disconnected. Restart the server to replay.')
    now=time.monotonic()
    dt=1/self.fps if self.file_source else max(.02,min(.5,now-self.last))
    self.last=now; self.time+=dt
    h,w=frame.shape[:2]
    if w>960: frame=cv.resize(frame,(960,int(h*960/w))); h,w=frame.shape[:2]
    result=self.model.predict(frame,verbose=False,conf=.35,device='cpu')[0]
    mapping={'person':'human','cow':'animal','dog':'animal','cat':'animal','horse':'animal','sheep':'animal','elephant':'animal',
             'bus':'bus','car':'vehicle','truck':'vehicle','motorcycle':'bike','bicycle':'bike',
             'auto':'auto','autorickshaw':'auto','thela':'thela','handcart':'thela','cattle':'animal','human':'human','animal':'animal'}
    detections=[]; boxes=[]
    for box in result.boxes:
       label=result.names[int(box.cls.item())]; kind=mapping.get(label.lower())
       if not kind: continue
       x1,y1,x2,y2=box.xyxy[0].tolist(); conf=float(box.conf.item())
       # Image-space projection ONLY; no physical range or calibrated speed estimate.
       x=((x1+x2)/2/w-.5)*16; y=(1-y2/h)*30
       detections.append(dict(kind=kind,x=x,y=y,confidence=conf))
       boxes.append(dict(label=label,kind=kind,confidence=conf,xyxy=[x1/w,y1/h,x2/w,y2/h]))
    tracks=self.tracker.update(detections,dt)
    state=self.reasoner.analyze(tracks,0,horizon,multiplier,memory,dt,corridor)
    _,jpg=cv.imencode('.jpg',frame,[cv.IMWRITE_JPEG_QUALITY,75])
    state.update(time=round(self.time,2),speed=0,mode='vision',scenario='local source',detections=detections,boxes=boxes,
      frame='data:image/jpeg;base64,'+base64.b64encode(jpg).decode(),corridor=corridor,
      source_note='Local YOLO · image-space heuristic · manual corridor · no metric depth or road segmentation')
    return state
 def close(self): self.cap.release()
