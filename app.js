/* =============================
   HYRULE OFFICE — app.js
   ============================= */

// ── CONFIG ─────────────────────────────────────────────────────────────
// Edit this section to customize your agent roster and status messages.

const CONFIG = {
  diamonds: 260,      // your gem count (purely cosmetic)
  tasksDone: 4,       // today's completed tasks

  // Status definitions
  statuses: {
    idle: {
      label: '待命',
      desc: '在营地等待冒险召唤',
      bubble: '待命中...随时出发！',
      quest: '探索神庙・整理记忆碎片',
      dotClass: 'green',
    },
    exploring: {
      label: '探索调研',
      desc: '正在深入神庙收集情报',
      bubble: '发现了什么...继续挖！',
      quest: '收集稀有情报碎片',
      dotClass: 'green',
    },
    executing: {
      label: '执行任务',
      desc: '全力冲刺，任务进行中',
      bubble: '冲啊！⚔️',
      quest: '消灭 Boss，完成目标',
      dotClass: 'green',
    },
    docs: {
      label: '整理文档',
      desc: '回到营地归档战利品',
      bubble: '整理好了，归档中...',
      quest: '更新英雄纪录册',
      dotClass: 'orange',
    },
    sync: {
      label: '同步备份',
      desc: '向神庙水晶球同步数据',
      bubble: '上传中...勿打扰 🔄',
      quest: '备份所有记忆碎片',
      dotClass: 'orange',
    },
    boss: {
      label: '遭遇了魔王',
      desc: '拼死一战！援军快来！',
      bubble: '救命！！💀',
      quest: '击败盖农，拯救世界',
      dotClass: 'red',
    },
  },

  // Hero roster
  heroes: [
    { avatar: '🤖', name: 'West Bot',  role: '主控・智慧之神',   status: 'online' },
    { avatar: '🍞', name: '迅哥',      role: '写作・风之神庙',   status: 'online' },
    { avatar: '🌐', name: '路飞',      role: '建站・水之神庙',   status: 'online' },
    { avatar: '🔗', name: '外链助手',  role: 'SEO・火之神庙',    status: 'idle'   },
    { avatar: '📅', name: '日程助理',  role: '日程・时之神庙',   status: 'online' },
    { avatar: '🗞️', name: 'ClawFeed',  role: '资讯・风之神庙',   status: 'online' },
  ],
};

// ── STATUS LABELS ───────────────────────────────────────────────────────

const BADGE_LABEL = { online: '在线', idle: '待命', offline: '离线' };

// ── INIT ────────────────────────────────────────────────────────────────

document.getElementById('diamondCount').textContent = CONFIG.diamonds;
document.getElementById('tasksDone').textContent    = CONFIG.tasksDone;
document.getElementById('heroCount').textContent    =
  CONFIG.heroes.filter(h => h.status === 'online').length;

// Roster
const rosterGrid = document.getElementById('rosterGrid');
CONFIG.heroes.forEach(h => {
  const card = document.createElement('div');
  card.className = 'hero-card';
  card.innerHTML = `
    <div class="avatar">${h.avatar}</div>
    <div class="hname">${h.name}</div>
    <div class="hrole">${h.role}</div>
    <span class="hero-badge ${h.status}">${BADGE_LABEL[h.status]}</span>
  `;
  rosterGrid.appendChild(card);
});

// Apply initial status (idle)
applyStatus('idle');

// ── TABS ────────────────────────────────────────────────────────────────

document.querySelectorAll('.tab').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    applyStatus(btn.dataset.status);
  });
});

function applyStatus(key) {
  const s = CONFIG.statuses[key];
  if (!s) return;

  document.getElementById('statusLabel').textContent  = s.label;
  document.getElementById('statusDesc').textContent   = s.desc;
  document.getElementById('speechBubble').textContent = s.bubble;
  document.getElementById('currentQuestText').textContent = s.quest;

  const dot = document.querySelector('.status-dot-wrap .dot');
  dot.className = 'dot ' + s.dotClass;
}

// ── CLOCK ────────────────────────────────────────────────────────────────

const DAYS = ['日', '一', '二', '三', '四', '五', '六'];

function tick() {
  const now = new Date();
  const hh  = String(now.getHours()).padStart(2, '0');
  const mm  = String(now.getMinutes()).padStart(2, '0');
  const ss  = String(now.getSeconds()).padStart(2, '0');
  document.getElementById('clockTime').textContent =
    `${hh}:${mm}:${ss}`;
  document.getElementById('clockDate').textContent =
    `${now.getFullYear()}年${now.getMonth()+1}月${now.getDate()}日（${DAYS[now.getDay()]}）`;
}
tick();
setInterval(tick, 1000);

// ── HERO ANIMATION ───────────────────────────────────────────────────────

// Subtle patrol: hero drifts left/right a bit
let heroDir = 1;
let heroPos = 50; // %
const heroWrap = document.getElementById('heroWrap');

setInterval(() => {
  heroPos += heroDir * (0.5 + Math.random());
  if (heroPos > 60) { heroDir = -1; }
  if (heroPos < 40) { heroDir =  1; }
  heroWrap.style.left = heroPos + '%';
}, 800);
