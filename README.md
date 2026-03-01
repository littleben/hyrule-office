# Hyrule Office 🗡️

> West Bot 的海拉鲁传说 · AI Agent 实时状态指挥所

A Zelda-pixel-themed dashboard for tracking your AI agent fleet — real-time status, token usage, cron logs, and yesterday's memo. Pure Python backend, no framework, no build step.

![Hyrule Office Screenshot](screenshot.jpg)

---

## ✨ Features

- 🎮 **Pixel-art game scene** — canvas-drawn Link patrols the world, speech bubbles reflect live state
- ⚔️ **Status tabs** — Idle / Exploring / Executing / Docs / Syncing / Boss Fight
- 🧝 **Live agent roster** — real online/idle/offline status from OpenClaw session files, with "last active" time
- 📊 **Stats cards** — today's token count, USD cost, cron runs, enabled jobs
- 📖 **Adventure log** — last 8 cron job runs with time + summary preview
- 📝 **Yesterday's memo** — reads from `memory/*.md`, auto-sanitizes secrets
- 🕐 **Live clock** — real-time with Japanese day-of-week
- 🌑 **Dark terminal aesthetic** — green-on-black, gold accents, pixel font
- 📱 **Mobile-friendly** — responsive layout for quick checks on the go

---

## 🚀 Quick Start

```bash
git clone https://github.com/littleben/hyrule-office.git
cd hyrule-office

# Set your ClawFeed API key (optional)
echo "CLAWFEED_KEY=your_key_here" > .env

# Start the server (static files + API on one port)
python3 server.py
```

Open: **http://localhost:8899**

---

## 🌐 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/status` | GET | Full status: agents, tokens, cron, clawfeed |
| `/api/health` | GET | Health check |
| `/api/yesterday-memo` | GET | Yesterday's memory note (sanitized) |
| `/api/set_state` | POST | Push agent state from CLI/cron |

### Push state from CLI / cron job:

```bash
curl -X POST http://localhost:8899/api/set_state \
  -H 'Content-Type: application/json' \
  -d '{"status": "executing", "message": "正在处理任务 ⚔️"}'
```

Valid statuses: `idle` · `researching` · `executing` · `writing` · `syncing` · `error`

---

## 🛠️ Customization

Edit `AGENTS` list in `server.py` to match your own agent crew:

```python
AGENTS = [
    {'id': 'main', 'name': 'My Bot', 'role': 'Main Agent', 'avatar': '🤖'},
    # add more...
]
```

The server reads OpenClaw's `~/.openclaw/` directory for live data. If you're not using OpenClaw, the page degrades gracefully to static defaults.

---

## 📁 File structure

```
hyrule-office/
├── index.html      # Single-file frontend (HTML + CSS + JS)
├── server.py       # Python backend (static + API, zero deps)
├── screenshot.jpg  # Preview image
├── .env            # Local secrets (not committed)
├── .gitignore
└── README.md
```

---

## 🚢 Deploy

```bash
# As a systemd user service
cp hyrule-office.service.example ~/.config/systemd/user/hyrule-office.service
systemctl --user enable --now hyrule-office
```

Works on any Linux VPS. Accessible over Tailscale without opening firewall ports.

---

## 💡 Inspiration

Inspired by **[Star Office UI](https://github.com/ringhyacinth/Star-Office-UI)** by [@ring_hyacinth](https://x.com/ring_hyacinth) — a pixel office dashboard for multi-agent collaboration with area-based status mapping, yesterday's memo, and guest agent support. Check it out if you want a more fully-featured multi-agent experience with animated pixel characters.

Hyrule Office takes the same idea and adapts it to a Zelda theme with deep OpenClaw integration.

---

## License

MIT — code is yours to fork and adapt.

> *Built with ❤️ and way too much Zelda lore.*
