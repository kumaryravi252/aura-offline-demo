#!/usr/bin/env python3
"""AURA local server. Python standard library is sufficient for the simulator."""
import argparse
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import json
import math
from pathlib import Path
import threading
import time
from urllib.parse import urlsplit
from backend.simulation import Simulation, SCENARIOS

ROOT=Path(__file__).resolve().parent

def create_server(host='127.0.0.1',port=8000,vision=None):
 lock=threading.Lock()
 session={'sim':Simulation(),'vision':vision,'latest':None}
 class Handler(SimpleHTTPRequestHandler):
  def __init__(self,*a,**kw): super().__init__(*a,directory=str(ROOT/'frontend'),**kw)
  def log_message(self,*a): pass
  def send_json(self,data,status=200):
   payload=json.dumps(data,allow_nan=False).encode()
   self.send_response(status); self.send_header('Content-Type','application/json'); self.send_header('Cache-Control','no-store'); self.send_header('Content-Length',str(len(payload))); self.end_headers(); self.wfile.write(payload)
  def do_GET(self):
   path=urlsplit(self.path).path
   if path=='/api/health': return self.send_json({'ok':True,'offline':True,'vision':vision is not None,'scenarios':SCENARIOS})
   if path=='/api/export':
    with lock: data={'version':1,'mode':'vision' if vision else 'simulation','scenario':session['sim'].scenario,'history':list(session['sim'].history),'latest':session['latest']}
    return self.send_json(data)
   if path.startswith('/api/'): return self.send_json({'error':'Not found'},404)
   return super().do_GET()
  def do_POST(self):
   # Deny cross-origin writes. The UI and API are served from the same local origin.
   origin=self.headers.get('Origin')
   if origin and urlsplit(origin).netloc!=self.headers.get('Host'): return self.send_json({'error':'Cross-origin request denied'},403)
   try:
    length=int(self.headers.get('Content-Length','0'))
    if length<0 or length>65536: raise ValueError('Request too large')
    body=json.loads(self.rfile.read(length) or b'{}')
    if not isinstance(body,dict): raise ValueError('Expected JSON object')
    with lock:
     if self.path=='/api/reset':
      scenario=body.get('scenario','mixed')
      if scenario not in SCENARIOS: raise ValueError('Unknown scenario')
      session['sim']=Simulation(scenario); session['latest']=None
      return self.send_json({'ok':True})
     if self.path!='/api/step': return self.send_json({'error':'Not found'},404)
     def number(key,default,lo,hi):
      value=body.get(key,default)
      if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not lo<=value<=hi: raise ValueError(f'{key} must be between {lo} and {hi}')
      return value
     if not isinstance(body.get('memory',True),bool): raise ValueError('memory must be boolean')
     options=dict(dt=number('dt',.1,.01,.5),horizon=number('horizon',3,1,5),multiplier=number('multiplier',1,.5,2),memory=body.get('memory',True),corridor=number('corridor',5,2,7))
     start=time.perf_counter()
     state=(vision or session['sim']).step(**options)
     state['latency_ms']=round((time.perf_counter()-start)*1000,1)
     session['latest']=state
     self.send_json(state)
   except (ValueError,TypeError,json.JSONDecodeError) as e: self.send_json({'error':str(e)},400)
   except Exception as e:
    print(f'Processing error: {e}')
    self.send_json({'error':'Local processing failed. Check the server terminal.'},500)
 return ThreadingHTTPServer((host,port),Handler)

if __name__=='__main__':
 p=argparse.ArgumentParser(description='AURA offline demo')
 p.add_argument('--strictPort',action='store_true',help=argparse.SUPPRESS)
 p.add_argument('--host',default='127.0.0.1'); p.add_argument('--port',type=int,default=8000)
 p.add_argument('--model',help='Existing local YOLO .pt weights'); p.add_argument('--source',default='0',help='Camera index or local video path')
 args=p.parse_args(); vision=None
 if args.model:
  from backend.vision import Vision
  try: vision=Vision(args.model,args.source)
  except (ImportError,ValueError) as e: p.error(str(e))
 server=create_server(args.host,args.port,vision)
 print(f'AURA running at http://{args.host}:{args.port} — {"local vision" if vision else "simulation"}',flush=True)
 try: server.serve_forever()
 except KeyboardInterrupt: pass
 finally:
  server.server_close()
  if vision: vision.close()
