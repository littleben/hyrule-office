#!/usr/bin/env python3
"""
Hyrule Office — Status API (Python, zero deps)
Port: 8901  |  Endpoints: /status  /health
"""
import json, os, time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import urlopen
from urllib.error import URLError
from pathlib import Path

HOME     = Path.home()
OPENCLAW = HOME / '.openclaw'
PORT     = 8901

AGENTS = [
    {'id': 'main',             'name': 'West Bot',    'role': '主控・智慧之神', 'avatar': '🤖'},
    {'id': 'xunge',            'name': '迅哥',          'role': '写作・风之神庙', 'avatar': '✍️'},
    {'id': 'lufei',            'name': '路飞',          'role': '建站・水之神庙', 'avatar': '🌐'},
    {'id': 'backlink',         'name': '外链助手',      'role': 'SEO・火之神庙',  'avatar': '🔗'},
    {'id': 'evomap',           'name': 'EvoMap',      'role': '进化・影之神庙', 'avatar': '🗺️'},
    {'id': 'openai-assistant', 'name': 'OpenAI小助手', 'role': '模型・光之神庙', 'avatar': '🤝'},
]

def last_activity_ms(agent_id: str):
    d = OPENCLAW / 'agents' / agent_id / 'sessions'
    if not d.exists():
        return None
    latest = max(
        (f.stat().st_mtime for f in d.glob('*.jsonl') if '.deleted.' not in f.name),
        default=None
    )
    return latest * 1000 if latest else None

def activity_status(last_ms):
    if not last_ms:
        return 'offline'
    diff = (time.time() * 1000 - last_ms) / 1000
    if diff < 300:   return 'active'
    if diff < 3600:  return 'online'
    if diff < 86400: return 'idle'
    return 'offline'

def get_cron_jobs():
    p = OPENCLAW / 'cron' / 'jobs.json'
    try:
        data = json.loads(p.read_text())
        jobs = [j for j in data.get('jobs', []) if j.get('state', {}).get('lastRunAtMs')]
        jobs.sort(key=lambda j: j['state']['lastRunAtMs'], reverse=True)
        return [{'id': j['id'], 'name': j['name'], 'agentId': j['agentId'],
                 'lastRunAtMs': j['state']['lastRunAtMs'],
                 'lastStatus': j['state'].get('lastStatus', '?'),
                 'enabled': j.get('enabled', True)} for j in jobs[:5]]
    except Exception:
        return []

def get_clawfeed():
    try:
        url = 'http://127.0.0.1:8767/api/digests?limit=1&key=64cf587fe57cd7192ebc80c5d05f66da'
        with urlopen(url, timeout=2) as r:
            data = json.loads(r.read())
        if not data:
            return None
        d = data[0]
        meta = json.loads(d['metadata']) if isinstance(d.get('metadata'), str) else (d.get('metadata') or {})
        return {'id': d['id'], 'created_at': d['created_at'],
                'hn_count': meta.get('hn_count'), 'github_count': meta.get('github_count')}
    except Exception:
        return None

def build_status():
    agents = []
    for a in AGENTS:
        last_ms = last_activity_ms(a['id'])
        agents.append({**a, 'status': activity_status(last_ms), 'lastActiveMs': last_ms})
    online = sum(1 for a in agents if a['status'] != 'offline')
    return {
        'ts': int(time.time() * 1000),
        'agents': agents,
        'onlineCount': online,
        'recentCrons': get_cron_jobs(),
        'clawfeed': get_clawfeed(),
    }

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):  # 静默日志
        pass

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        if self.path == '/health':
            self.wfile.write(b'{"ok":true}')
        elif self.path == '/status':
            self.wfile.write(json.dumps(build_status(), ensure_ascii=False).encode())
        else:
            self.wfile.write(b'{"error":"not found"}')

if __name__ == '__main__':
    server = HTTPServer(('127.0.0.1', PORT), Handler)
    print(f'Hyrule Office API → http://127.0.0.1:{PORT}/status')
    server.serve_forever()
