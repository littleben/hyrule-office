#!/usr/bin/env python3
"""
Hyrule Office — All-in-one server
静态文件 + /api/status + /api/health + /api/set_state + /api/yesterday-memo
Port: 8899  |  绑定 0.0.0.0

Inspired by Star Office UI: https://github.com/ringhyacinth/Star-Office-UI
"""
import json, time, os, re
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.request import urlopen
from pathlib import Path
from datetime import datetime, timezone, timedelta

HOME      = Path.home()
OPENCLAW  = HOME / '.openclaw'
PORT      = 8899
SERVE_DIR = Path(__file__).parent

# 主 Agent 状态（内存中，重启清零）
_agent_state = {
    'status':  'idle',
    'message': '待命中...随时出发！',
    'updatedAt': int(time.time() * 1000),
}

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
        for run in all_runs[:8]:
            jid = run.get('jobId', '')
            job = job_map.get(jid, {})
            recent.append({
                'id': jid,
                'name': job.get('name', jid[:12]),
                'agentId': job.get('agentId', '?'),
                'lastRunAtMs': run.get('ts'),
                'lastStatus': run.get('status', '?'),
                'enabled': job.get('enabled', True),
                'summary': (run.get('summary') or '')[:120],
            })
        return {'total': len(jobs), 'enabled': enabled, 'todayRuns': run_count, 'recent': recent}
    except:
        return {'total': 0, 'enabled': 0, 'todayRuns': 0, 'recent': []}

def get_token_stats():
    # 官方定价 $/1M tokens
    PRICING = {
        'claude-sonnet-4-6':          {'in': 3.0,  'out': 15.0,  'cr': 0.30,  'cw': 3.75},
        'claude-sonnet-4-5-20250929': {'in': 3.0,  'out': 15.0,  'cr': 0.30,  'cw': 3.75},
        'claude-opus-4-6-20260205':   {'in': 15.0, 'out': 75.0,  'cr': 1.50,  'cw': 18.75},
        'claude-opus-4-20250514':     {'in': 15.0, 'out': 75.0,  'cr': 1.50,  'cw': 18.75},
        'gpt-5.3-codex':              {'in': 2.5,  'out': 10.0,  'cr': 1.25,  'cw': 0.0},
    }
    DEFAULT_PRICE = {'in': 3.0, 'out': 15.0, 'cr': 0.30, 'cw': 3.75}

    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    total_tokens = 0
    recorded_cost = 0.0   # API 返回的 cost（可能为 0）
    estimated_cost = 0.0  # 按官方定价估算
    by_agent = {}

    for agent_dir in (OPENCLAW / 'agents').iterdir():
        sess_dir = agent_dir / 'sessions'
        if not sess_dir.exists():
            continue
        a_tokens, a_recorded, a_estimated = 0, 0.0, 0.0
        for f in sess_dir.glob('*.jsonl'):
            if '.deleted.' in f.name:
                continue
            try:
                for line in f.read_text().strip().splitlines():
                    d = json.loads(line)
                    if not d.get('timestamp', '').startswith(today):
                        continue
                    msg = d.get('message') or {}
                    usage = msg.get('usage')
                    if not usage:
                        continue
                    model = msg.get('model') or msg.get('modelId') or ''
                    p = PRICING.get(model, DEFAULT_PRICE)
                    inp = usage.get('input', 0)
                    out = usage.get('output', 0)
                    cr  = usage.get('cacheRead', 0)
                    cw  = usage.get('cacheWrite', 0)
                    tok = usage.get('totalTokens', inp + out + cr + cw)
                    est = (inp/1e6*p['in'] + out/1e6*p['out'] +
                           cr/1e6*p['cr'] + cw/1e6*p['cw'])
                    a_tokens    += tok
                    a_recorded  += (usage.get('cost') or {}).get('total', 0)
                    a_estimated += est
            except:
                pass
        if a_tokens:
            by_agent[agent_dir.name] = {
                'tokens': a_tokens,
                'cost': round(a_recorded, 4),
                'estimatedCost': round(a_estimated, 4),
            }
            total_tokens    += a_tokens
            recorded_cost   += a_recorded
            estimated_cost  += a_estimated

    return {
        'totalTokens':    total_tokens,
        'totalCost':      round(recorded_cost, 4),
        'estimatedCost':  round(estimated_cost, 4),
        'hasBilling':     recorded_cost > 0,
        'byAgent':        by_agent,
    }

def get_clawfeed():
    try:
        key = os.environ.get('CLAWFEED_KEY', 'CLAWFEED_KEY_HERE')
        url = f'http://127.0.0.1:8767/api/digests?limit=1&key={key}'
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

def get_yesterday_memo():
    """从 memory/*.md 读取昨日小记，脱敏后返回"""
    mem_dir = OPENCLAW / 'workspace' / 'memory'
    if not mem_dir.exists():
        mem_dir = HOME / 'go-to-wild' / 'auto-writing-system' / 'memory'
    if not mem_dir.exists():
        return None

    # 找昨天或最近一天的日记
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    today = datetime.now().strftime('%Y-%m-%d')

    target = None
    for date in [yesterday, today]:
        p = mem_dir / f'{date}.md'
        if p.exists():
            target = p
            break

    if not target:
        # 找最近的一个
        files = sorted(mem_dir.glob('????-??-??.md'), reverse=True)
        if files:
            target = files[0]

    if not target:
        return None

    try:
        content = target.read_text(encoding='utf-8')
        # 基础脱敏：去掉 API key / token / 密码行
        lines = content.splitlines()
        clean = []
        for line in lines:
            if re.search(r'(api.?key|token|secret|password|sk-|bearer)\s*[:=]', line, re.I):
                continue
            clean.append(line)
        text = '\n'.join(clean).strip()
        # 截取前 600 字
        if len(text) > 600:
            text = text[:600] + '…'
        return {
            'date': target.stem,
            'content': text,
        }
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
        'agentState': _agent_state,
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
        pass

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        path = self.path.split('?')[0]
        if path == '/api/health':
            self.send_json({'ok': True})
        elif path == '/api/status':
            self.send_json(build_status())
        elif path == '/api/yesterday-memo':
            memo = get_yesterday_memo()
            self.send_json(memo or {'date': None, 'content': '暂无记录'})
        else:
            super().do_GET()

    def do_POST(self):
        path = self.path.split('?')[0]
        if path == '/api/set_state':
            try:
                length = int(self.headers.get('Content-Length', 0))
                body = json.loads(self.rfile.read(length) if length else b'{}')
                allowed = {'idle','researching','executing','writing','syncing','error'}
                state = body.get('status', 'idle')
                if state not in allowed:
                    self.send_json({'error': f'invalid status, allowed: {allowed}'}, 400)
                    return
                _agent_state['status']    = state
                _agent_state['message']   = body.get('message', '')
                _agent_state['updatedAt'] = int(time.time() * 1000)
                self.send_json({'ok': True, 'state': _agent_state})
            except Exception as e:
                self.send_json({'error': str(e)}, 500)
        else:
            self.send_json({'error': 'not found'}, 404)

if __name__ == '__main__':
    os.chdir(SERVE_DIR)
    server = HTTPServer(('0.0.0.0', PORT), Handler)
    print(f'Hyrule Office → http://0.0.0.0:{PORT}')
    print(f'API  → http://0.0.0.0:{PORT}/api/status')
    print(f'Memo → http://0.0.0.0:{PORT}/api/yesterday-memo')
    server.serve_forever()
