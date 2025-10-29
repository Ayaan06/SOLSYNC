<div align="center">

  <img src="frontend/Logo.png" alt="MarketMinerAI" height="72" />

  <h1>SolSync / MarketMinerAI</h1>
  <p>AI‑assisted copy‑trading bot on Solana with a slick local web controller.</p>

  <p>
    <sub>Built with Python · Flask · websockets · aiohttp · solders</sub>
  </p>

  <p>
    🚀 Mirrors a master wallet · ⚡ Low‑latency execution · 🔁 Fault‑tolerant retries · 🔒 Local key signing
  </p>

</div>

Why You’ll Like It
- 🔧 Runs locally with a simple web UI — no cloud required.
- 👀 Real‑time logs and status so you always know what’s happening.
- 🧩 Configurable via form or CLI (wallets, amounts, slippage, RPCs, pool).
- 🔐 Keys never leave your machine; transactions are signed locally.

Architecture (At a Glance)
| Layer | Component | What it does |
| --- | --- | --- |
| UI | `frontend/web/*` | Static site with form, status, and live logs |
| Controller | `frontend/python/control_server.py` | Serves the UI, starts/stops the bot, aggregates logs via subprocess |
| Bot | `frontend/python/finalDraftV3.py` | Subscribes to token updates, detects buys/sells, executes trades |
| Chain / APIs | Solana RPC, Pump.fun, Raydium | WebSocket subscribe + HTTP submit, trade-local fetch and local signing |

Workflow
| Step | Action | Detail |
| --- | --- | --- |
| 1️⃣ | Start | You click “Start Bot” in the UI; controller launches the bot with your inputs |
| 2️⃣ | Subscribe | Bot opens a WebSocket to Solana and filters SPL Token accounts for the tracked wallet |
| 3️⃣ | Detect | Balance increase → buy signal; decrease after buy → sell signal |
| 4️⃣ | Execute | Fetch tx from Pump trade‑local → sign locally with your Base58 secret → submit via HTTP RPC |
| 5️⃣ | Retry | On failure, alternate pool (Pump ↔ Raydium), up to 3 attempts |
| 6️⃣ | Observe | Controller streams `[BOT]` output + timestamps to the UI logs |

Quick Start (3 commands)
```bash
git clone <your-repo-url>
cd <repo>
pip install -r requirements.txt
python frontend/python/control_server.py
# Open http://127.0.0.1:5000 and click Start Bot
```

Dependencies
- Python 3.10+ (3.12 tested). Create a venv if desired.
- Install all deps:
  ```bash
  pip install -r requirements.txt
  ```
  What’s included:
  - Flask — controller HTTP server
  - websockets — WebSocket client for Solana
  - aiohttp — HTTP client for Pump trade‑local and RPC submit
  - solders — Solana transaction + key utilities

Form → Flags Mapping
| UI Field | CLI Flag | Example |
| --- | --- | --- |
| Trading Wallet Secret (Base58) | `--secret-key-base58` or `--secret-key-file` | `--secret-key-file C:\\keys\\hot.txt` |
| Wallet To Track (public key) | `--track-wallet` | `--track-wallet 9x...abc` |
| Fixed Buy Amount (SOL) | `--fixed-buy` | `--fixed-buy 0.02` |
| Sell Percent (%) | `--sell-percent` | `--sell-percent 100` |
| Slippage (%) | `--slippage` | `--slippage 5` |
| Priority Fee (SOL) | `--priority-fee` | `--priority-fee 0.001` |
| Pool | `--pool` | `--pool pump` |
| Denominated In SOL | `--denominated-in-sol`/`--no-denominated-in-sol` | `--denominated-in-sol` |
| WebSocket RPC URL | `--rpc-ws-url` | `--rpc-ws-url wss://api.mainnet-beta.solana.com` |
| HTTP RPC URL | `--rpc-http-url` | `--rpc-http-url https://api.mainnet-beta.solana.com/` |

Bot CLI (Run without the UI)
```bash
python frontend/python/finalDraftV3.py \
  --track-wallet <PUBKEY> \
  --secret-key-file C:\\keys\\hot.txt \
  --fixed-buy 0.02 --sell-percent 100 \
  --slippage 5 --priority-fee 0.001 \
  --pool pump \
  --rpc-ws-url wss://api.mainnet-beta.solana.com \
  --rpc-http-url https://api.mainnet-beta.solana.com/
```

Key Concepts (Plain English)
- 🔑 Base58 keys (not Base52): Solana uses Base58 to encode keys (removes look‑alike characters). Your “secret key (Base58)” is a long string representing your private key bytes. Keep it private.
- 🏦 Public key: The address of a wallet, also Base58. Safe to share.
- 📡 WebSocket subscribe: Fast push updates from the chain for the tracked wallet’s token accounts.
- 🧾 Local signing: The controller/bot signs transactions on your machine before submit; secrets are not uploaded.

Security (Read Me!)
- Use a dedicated hot wallet with limited funds.
- Do not expose the controller publicly without HTTPS + authentication (and ideally VPN/Zero‑Trust/IP allow‑listing).
- Never commit or share your Base58 secret. Rotate if leaked.

Project Anatomy (Deeper Dive)
- `frontend/python/finalDraftV3.py`
  - WebSocket subscribe → buy/sell detection → trade‑local fetch → local signing → RPC submit → retry with pool rotation.
- `frontend/python/control_server.py`
  - Serves UI, starts/stops the bot, timestamps and streams logs: `POST /start`, `POST /stop`, `GET /status`, `GET /logs`.
- `frontend/web/*`
  - `index.html` (form + status + logs), `help.html`, `styles.css`, `script.js`, `logo.png`.

Troubleshooting ⚙️
| Symptom | Cause | Fix |
| --- | --- | --- |
| 127.0.0.1 refused to connect | Controller not running | Start with `python frontend/python/control_server.py` |
| ModuleNotFoundError (Flask/websockets/…) | Packages not installed | `pip install -r requirements.txt` |
| No logs on the site | Bot not started or polling off | Click “Start Bot”; verify controller console for messages |
| Slow or rate‑limited | Free public RPC endpoint | Try a paid Solana RPC plan for better WebSocket + limits |

License
- Add your preferred license here.

