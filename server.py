#!/usr/bin/env python3
"""
Hyrule Office — All-in-one server
静态文件 + /api/status + /api/health
Port: 8899  |  绑定 0.0.0.0（外网可访问）
"""
import json, time
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.request import urlopen
from pathlib import Path
from datetime import datetime, timezone
import os

HOME     = Path.home()
OPENCLAW = HOME / '.openclaw'
PORT     = 8899
SERVE_DIR = Path(__file__).parent  # 同目录下的静态文件

AGENTS = [
    {'id': 'main',             'name': 'West Bot',    'role': '主控・智慧之神', 'avatar': '🤖'},
    {'id': 'xunge',            'name': '迅哥',          'role': '写作・风之神庙', 'avatar': '✍️'},
    {'id': 'lufei',            'name': '路飞',          'role': '建站・水之神庙', 'avatar': '🌐'},
    {'id': 'backlink',         'name': '外链助手',      'role': 'SEO・火之神庙',  'avatar': '🔗'},
    {'id': 'evomap',           'name': 'EvoMap',      'role': '进化・影之神庙', 'avatar': '🗺️'},
    {'id': 'openai-assistant', 'name': 'OpenAI小助手', 'role': '模型・光之神庙', 'avatar': '🤝'},
]

# ── Data helpers ─────────────────────────────────────────────────────

def last_activity_ms(agent_id):
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
    if diff < 300:    return 'active'
    if diff < 3600:   return 'online'
    if diff < 86400:  return 'idle'
    return 'offline'

def get_cron_stats():
    p = OPENCLAW / 'cron' / 'jobs.json'
    try:
        jobs = json.loads(p.read_text()).get('jobs', [])
        enabled = sum(1 for j in jobs if j.get('enabled'))
        today_ms = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        ).timestamp() * 1000
        run_count = 0
        all_runs = []
        runs_dir = OPENCLAW / 'cron' / 'runs'
        for f in runs_dir.glob('*.jsonl'):
            try:
                for line in f.read_text().strip().splitlines():
                    d = json.loads(line)
                    if d.get('action') == 'finished':
                        if d.get('ts', 0) >= today_ms:
                            run_count += 1
                        all_runs.append(d)
            except:
                pass
        all_runs.sort(key=lambda x: x.get('ts', 0), reverse=True)
        job_map = {j['id']: j for j in jobs}
        recent = []
        for run in all_runs[:5]:
            jid = run.get('jobId', '')
            job = job_map.get(jid, {})
            recent.append({
                'id': jid,
                'name': job.get('name', jid[:12]),
                'agentId': job.get('agentId', '?'),
                'lastRunAtMs': run.get('ts'),
                'lastStatus': run.get('status', '?'),
                'enabled': job.get('enabled', True),
            })
        return {'total': len(jobs), 'enabled': enabled, 'todayRuns': run_count, 'recent': recent}
    except:
        return {'total': 0, 'enabled': 0, 'todayRuns': 0, 'recent': []}

def get_token_stats():
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    total_tokens, total_cost = 0, 0.0
    by_agent = {}
    for agent_dir in (OPENCLAW / 'agents').iterdir():
        sess_dir = agent_dir / 'sessions'
        if not sess_dir.exists():
            continue
        a_tokens, a_cost = 0, 0.0
        for f in sess_dir.glob('*.jsonl'):
            if '.deleted.' in f.name:
                continue
            try:
                for line in f.read_text().strip().splitlines():
                    d = json.loads(line)
                    if not d.get('timestamp', '').startswith(today):
                        continue
                    usage = (d.get('message') or {}).get('usage')
                    if usage:
                        a_tokens += usage.get('totalTokens', 0)
                        a_cost += (usage.get('cost') or {}).get('total', 0)
            except:
                pass
        if a_tokens:
            by_agent[agent_dir.name] = {'tokens': a_tokens, 'cost': round(a_cost, 4)}
            total_tokens += a_tokens
            total_cost += a_cost
    return {'totalTokens': total_tokens, 'totalCost': round(total_cost, 4), 'byAgent': by_agent}

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
    except:
        return None

def build_status():
    agents = []
    for a in AGENTS:
        last_ms = last_activity_ms(a['id'])
        agents.append({**a, 'status': activity_status(last_ms), 'lastActiveMs': last_ms})
    online = sum(1 for a in agents if a['status'] != 'offline')
    cron = get_cron_stats()
    return {
        'ts': int(time.time() * 1000),
        'agents': agents,
        'onlineCount': online,
        'cron': cron,
        'recentCrons': cron['recent'],
        'tokens': get_token_stats(),
        'clawfeed': get_clawfeed(),
    }

# ── HTTP Handler ─────────────────────────────────────────────────────

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(SERVE_DIR), **kwargs)

    def log_message(self, fmt, *args):
        pass  # 静默

    def do_GET(self):
        if self.path in ('/api/status', '/api/health'):
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            if self.path == '/api/health':
                self.wfile.write(b'{"ok":true}')
            else:
                self.wfile.write(json.dumps(build_status(), ensure_ascii=False).encode())
        else:
            super().do_GET()

if __name__ == '__main__':
    os.chdir(SERVE_DIR)
    server = HTTPServer(('0.0.0.0', PORT), Handler)
    print(f'Hyrule Office → http://0.0.0.0:{PORT}')
    print(f'API → http://0.0.0.0:{PORT}/api/status')
    server.serve_forever()
