SolSync / MarketMinerAI
AI‑assisted copy‑trading bot for the Solana blockchain with a local web controller.

Overview
- Mirrors a “master” wallet’s SPL token balance changes and automatically places buy/sell orders.
- Uses a Python bot for WebSocket monitoring and trade execution, plus a small Flask server to run it from a local web UI.

Repository Structure
- frontend/web: Static site (index.html, help.html, styles.css, script.js).
- frontend/python: Bot (finalDraftV3.py) and controller (control_server.py).
- frontend/Logo.png: Branding used by the web UI.
- venv: Optional local virtual environment (Windows layout).

How It Works (High Level)
- Subscribe: The bot watches SPL Token accounts for the tracked wallet via Solana WebSocket (programSubscribe on Token Program).
- Detect: Balance increases → buy signal; decreases after a buy → sell signal.
- Execute: Requests a serialized transaction from Pump’s trade‑local API, signs with your keypair locally, and submits to your HTTP RPC. Retries rotate between Pump and Raydium.

Key Concepts
- Base58 keys: Solana public/secret keys are Base58‑encoded (not Base52). Base58 avoids ambiguous characters (0/O, I/l). Your “secret key (base58)” is a long Base58 string representing private key bytes. Keep it secret.
- Public key: Your wallet address (safe to share). Also Base58.
- RPC endpoints: WebSocket endpoint for subscriptions; HTTP endpoint for submitting transactions. Public endpoints work but paid tiers are more reliable.

Prerequisites
- Python 3.10+ (3.12 tested). Recommended: a virtual environment.
- Python dependencies:
  - Flask (controller HTTP server)
  - websockets (WebSocket client for Solana subscriptions)
  - aiohttp (HTTP client for Pump trade-local and RPC submit)
  - solders (Solana transaction and key utilities)
  - Install all: `pip install -r requirements.txt`
  - Or individually: `pip install Flask websockets aiohttp solders`

Running the Local Web Controller
1) From the repo root:
   - Windows: `python frontend\python\control_server.py`
   - macOS/Linux: `python3 frontend/python/control_server.py`
2) Open `http://127.0.0.1:5000` in your browser.
3) Fill out the form and click Start Bot. Use Stop Bot to terminate.

Form Fields
- Trading Wallet Secret (base58): Your Base58‑encoded secret key (private key). Used locally to sign transactions.
- Wallet To Track (public key): Master wallet to mirror.
- Fixed Buy Amount (SOL): Spend this much SOL per buy signal.
- Sell Percent (%): Percentage of token balance to sell on sell signal (e.g., 100).
- Slippage (%), Priority Fee (SOL): Trade execution parameters.
- Pool: Preferred route (Pump or Raydium). The bot alternates on retries.
- RPC WS/HTTP URLs: Solana endpoints to subscribe and submit transactions.

Bot CLI (Advanced, without the web UI)
- The bot accepts flags and will prompt for anything missing:
  - `--track-wallet <PUBKEY>`
  - `--secret-key-base58 <BASE58_SECRET>` or `--secret-key-file <PATH>`
  - `--fixed-buy <SOL>`
  - `--sell-percent <0-100>`
  - `--slippage <int>`
  - `--priority-fee <SOL>`
  - `--pool pump|raydium`
  - `--rpc-ws-url <WS>`
  - `--rpc-http-url <HTTP>`
  - `--denominated-in-sol` (default) or `--no-denominated-in-sol`
- Example: `python frontend/python/finalDraftV3.py --track-wallet <PUBKEY> --secret-key-file C:\keys\mykey.txt --fixed-buy 0.02 --sell-percent 100`

Security Notes
- Never commit or share your Base58 secret key. Use a dedicated hot wallet with limited funds.
- If you publish the controller on a public domain, put it behind HTTPS + authentication and ideally IP allow‑listing / Zero‑Trust.
- Rotate keys if exposed.

Project Components (Deeper Dive)
- frontend/python/finalDraftV3.py
  - WebSocket subscribe (programSubscribe) with filters for the tracked wallet’s token accounts.
  - Buy/Sell detection and trade execution via Pump trade‑local → local signing → RPC submit.
  - Retries with pool rotation (pump ↔ raydium).
- frontend/python/control_server.py
  - Serves the static UI, starts/stops the bot as a subprocess, aggregates logs.
  - Endpoints: `POST /start`, `POST /stop`, `GET /status`, `GET /logs`.
- frontend/web/index.html, script.js, styles.css
  - Form for all inputs; status + timestamped logs; calls controller endpoints.
  - help.html with a concise usage guide and key concepts.

Cloning & First Run
1) `git clone <your-repo-url>`
2) (Optional) Create and activate a venv.
3) `pip install Flask websockets aiohttp solders`
4) `python frontend/python/control_server.py`
5) Visit `http://127.0.0.1:5000` and start the bot.

Troubleshooting
- 127.0.0.1 refused to connect → Start the controller first; check firewall prompts.
- ModuleNotFoundError: Flask (or websockets/aiohttp/solders) → `pip install -r requirements.txt` in the active interpreter.
- No logs → Ensure you’re on `http://127.0.0.1:5000` and click Start Bot; watch the UI and controller console.

License
- Add your preferred license here.
