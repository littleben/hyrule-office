#!/usr/bin/env node
/**
 * Hyrule Office — Local Status API
 * Reads OpenClaw data files and serves live agent/cron/clawfeed status.
 * Port: 8901
 */

import { createServer } from 'node:http';
import { readFile, readdir, stat } from 'node:fs/promises';
import { join } from 'node:path';
import { homedir } from 'node:os';

const PORT = 8901;
const HOME = homedir();
const OPENCLAW = join(HOME, '.openclaw');
const CLAWFEED_API = 'http://127.0.0.1:8767';

// ── Agent definitions ────────────────────────────────────────────────
const AGENTS = [
  { id: 'main',            name: 'West Bot',   role: '主控・智慧之神', avatar: '🤖' },
  { id: 'xunge',           name: '迅哥',        role: '写作・风之神庙', avatar: '✍️' },
  { id: 'lufei',           name: '路飞',        role: '建站・水之神庙', avatar: '🌐' },
  { id: 'backlink',        name: '外链助手',    role: 'SEO・火之神庙',  avatar: '🔗' },
  { id: 'evomap',          name: 'EvoMap',     role: '进化・影之神庙', avatar: '🗺️' },
  { id: 'openai-assistant',name: 'OpenAI小助手',role: '模型・光之神庙', avatar: '🤝' },
];

// ── Helpers ──────────────────────────────────────────────────────────
async function getLastActivity(agentId) {
  const dir = join(OPENCLAW, 'agents', agentId, 'sessions');
  try {
    const files = await readdir(dir);
    const jsonls = files.filter(f => f.endsWith('.jsonl') && !f.includes('.deleted.'));
    if (!jsonls.length) return null;
    let latest = 0;
    for (const f of jsonls) {
      const s = await stat(join(dir, f));
      if (s.mtimeMs > latest) latest = s.mtimeMs;
    }
    return latest;
  } catch { return null; }
}

function activityStatus(lastMs) {
  if (!lastMs) return 'offline';
  const diffS = (Date.now() - lastMs) / 1000;
  if (diffS < 300)   return 'active';   // < 5 min
  if (diffS < 3600)  return 'online';   // < 1 hour
  if (diffS < 86400) return 'idle';     // < 1 day
  return 'offline';
}

async function getCronJobs() {
  try {
    const raw = await readFile(join(OPENCLAW, 'cron', 'jobs.json'), 'utf8');
    return JSON.parse(raw).jobs || [];
  } catch { return []; }
}

async function getClawFeedDigest() {
  try {
    const res = await fetch(`${CLAWFEED_API}/api/digests?limit=1&key=64cf587fe57cd7192ebc80c5d05f66da`);
    if (!res.ok) return null;
    const data = await res.json();
    if (!data.length) return null;
    const d = data[0];
    const meta = typeof d.metadata === 'string' ? JSON.parse(d.metadata) : (d.metadata || {});
    return {
      id: d.id,
      created_at: d.created_at,
      hn_count: meta.hn_count,
      github_count: meta.github_count,
    };
  } catch { return null; }
}

// ── Build response ───────────────────────────────────────────────────
async function buildStatus() {
  const [agents, cronJobs, digest] = await Promise.all([
    Promise.all(AGENTS.map(async a => {
      const lastMs = await getLastActivity(a.id);
      const status = activityStatus(lastMs);
      return { ...a, status, lastActiveMs: lastMs };
    })),
    getCronJobs(),
    getClawFeedDigest(),
  ]);

  const onlineCount = agents.filter(a => a.status !== 'offline').length;

  // Recent cron runs
  const recentCrons = cronJobs
    .filter(j => j.state?.lastRunAtMs)
    .sort((a, b) => (b.state.lastRunAtMs || 0) - (a.state.lastRunAtMs || 0))
    .slice(0, 5)
    .map(j => ({
      id: j.id,
      name: j.name,
      agentId: j.agentId,
      lastRunAtMs: j.state.lastRunAtMs,
      lastStatus: j.state.lastStatus,
      enabled: j.enabled,
    }));

  return {
    ts: Date.now(),
    agents,
    onlineCount,
    recentCrons,
    clawfeed: digest,
  };
}

// ── HTTP server ──────────────────────────────────────────────────────
const server = createServer(async (req, res) => {
  const url = new URL(req.url, `http://localhost:${PORT}`);

  // CORS for local file access
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Content-Type', 'application/json');

  if (url.pathname === '/status') {
    try {
      const data = await buildStatus();
      res.writeHead(200);
      res.end(JSON.stringify(data));
    } catch (err) {
      res.writeHead(500);
      res.end(JSON.stringify({ error: String(err) }));
    }
    return;
  }

  if (url.pathname === '/health') {
    res.writeHead(200);
    res.end(JSON.stringify({ ok: true }));
    return;
  }

  res.writeHead(404);
  res.end(JSON.stringify({ error: 'not found' }));
});

server.listen(PORT, '127.0.0.1', () => {
  console.log(`Hyrule Office API → http://127.0.0.1:${PORT}/status`);
});
