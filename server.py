#!/usr/bin/env python3
"""Exposes ONLY: GET / (dashboard), POST /refresh (rebuild+push, max once/min)."""
import http.server, subprocess, time, threading, json, os
D=os.path.dirname(os.path.abspath(__file__)); last=[0.0]; lock=threading.Lock()
class H(http.server.BaseHTTPRequestHandler):
    def cors(s):
        s.send_header('Access-Control-Allow-Origin','*'); s.send_header('Access-Control-Allow-Methods','POST, GET, OPTIONS'); s.send_header('Cache-Control','no-store')
    def send(s,code,body,ct='application/json'):
        b=body.encode(); s.send_response(code); s.cors(); s.send_header('Content-Type',ct); s.send_header('Content-Length',str(len(b))); s.end_headers(); s.wfile.write(b)
    def do_OPTIONS(s): s.send_response(204); s.cors(); s.send_header('Access-Control-Allow-Headers','Content-Type'); s.end_headers()
    def do_GET(s):
        if s.path.split('?')[0] in ('/','/index.html'): s.send(200,open(f'{D}/index.html').read(),'text/html; charset=utf-8')
        elif s.path=='/health': s.send(200,'{"ok":true}')
        else: s.send(404,'{"error":"not found"}')
    def do_POST(s):
        if s.path!='/refresh': return s.send(404,'{"error":"not found"}')
        with lock:
            wait=60-(time.time()-last[0])
            if wait>0: return s.send(429,json.dumps({"ok":False,"retry_in":int(wait)+1}))
            last[0]=time.time()
            r=subprocess.run([f'{D}/refresh.sh'],cwd=D,capture_output=True,text=True,timeout=120)
        s.send(200 if r.returncode==0 else 500,json.dumps({"ok":r.returncode==0}))
    def log_message(s,*a): pass
http.server.ThreadingHTTPServer(('127.0.0.1',8787),H).serve_forever()
