import os
import sys
import threading
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from flask import Flask, request, jsonify, send_from_directory

ROOT = Path(__file__).resolve().parents[1]  # .../frontend
WEB_DIR = ROOT / 'web'
PY_DIR = ROOT / 'python'
BOT_PATH = PY_DIR / 'finalDraftV3.py'

app = Flask(__name__, static_folder=str(WEB_DIR), static_url_path='')

bot_proc: Optional[subprocess.Popen] = None
log_lock = threading.Lock()
log_lines: List[str] = []
MAX_LOG_LINES = 2000


def _ts() -> str:
    return datetime.now().strftime('%H:%M:%S')


def append_log(line: str) -> None:
    msg = f"[{_ts()}] {line.rstrip('\n')}"
    with log_lock:
        log_lines.append(msg)
        if len(log_lines) > MAX_LOG_LINES:
            del log_lines[: len(log_lines) - MAX_LOG_LINES]


def reader_thread(proc: subprocess.Popen):
    try:
        for raw in iter(proc.stdout.readline, b''):
            if not raw:
                break
            try:
                decoded = raw.decode('utf-8', errors='replace').rstrip('\n')
                append_log(f"[BOT] {decoded}")
            except Exception:
                pass
    finally:
        append_log('[INFO] bot process ended')


def is_running() -> bool:
    return bot_proc is not None and bot_proc.poll() is None


@app.route('/')
def index():
    return send_from_directory(str(WEB_DIR), 'index.html')


@app.post('/start')
def start():
    global bot_proc
    if is_running():
        append_log('[ERROR] start requested but bot already running')
        return jsonify({ 'error': 'Bot already running' }), 409

    data = request.get_json(silent=True) or {}

    # Required fields
    secret = (data.get('secretKeyBase58') or '').strip()
    track_wallet = (data.get('trackWallet') or '').strip()
    if not secret or not track_wallet:
        append_log('[ERROR] missing required fields in start (secret or track wallet)')
        return jsonify({ 'error': 'secretKeyBase58 and trackWallet are required' }), 400

    # Numeric + options
    fixed_buy = float(data.get('fixedBuy') or 0.02)
    sell_percent = float(data.get('sellPercent') or 100)
    slippage = int(data.get('slippage') or 5)
    priority_fee = float(data.get('priorityFee') or 0.001)
    pool = (data.get('pool') or 'pump').lower()
    denominated_in_sol = bool(data.get('denominatedInSol') if 'denominatedInSol' in data else True)
    rpc_ws = (data.get('rpcWsUrl') or 'wss://api.mainnet-beta.solana.com').strip()
    rpc_http = (data.get('rpcHttpUrl') or 'https://api.mainnet-beta.solana.com/').strip()

    args = [
        sys.executable,
        str(BOT_PATH),
        '--track-wallet', track_wallet,
        '--secret-key-base58', secret,
        '--fixed-buy', str(fixed_buy),
        '--sell-percent', str(int(sell_percent)),
        '--slippage', str(int(slippage)),
        '--priority-fee', str(priority_fee),
        '--pool', pool,
        '--rpc-ws-url', rpc_ws,
        '--rpc-http-url', rpc_http,
    ]
    if denominated_in_sol:
        args.append('--denominated-in-sol')
    else:
        args.append('--no-denominated-in-sol')

    try:
        with log_lock:
            log_lines.clear()
        append_log('[INFO] starting bot process')
        append_log('[INFO] args: '
                   f'track_wallet={track_wallet} fixed_buy={fixed_buy} sell_percent={sell_percent} '
                   f'slippage={slippage} priority_fee={priority_fee} pool={pool} denom_sol={denominated_in_sol} '
                   f'rpc_ws={rpc_ws} rpc_http={rpc_http}')
        bot = subprocess.Popen(
            args,
            cwd=str(PY_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
        )
    except Exception as e:
        append_log(f'[ERROR] failed to start: {e}')
        return jsonify({ 'error': f'Failed to start: {e}' }), 500

    bot.daemon = True  # type: ignore[attr-defined]
    t = threading.Thread(target=reader_thread, args=(bot,), daemon=True)
    t.start()

    bot_proc = bot
    append_log(f'[INFO] started bot pid={bot.pid}')
    return jsonify({ 'ok': True, 'pid': bot.pid })


@app.post('/stop')
def stop():
    global bot_proc
    if not is_running():
        append_log('[INFO] stop requested but bot not running')
        return jsonify({ 'ok': True, 'message': 'Not running' })
    try:
        bot_proc.terminate()
        append_log('[INFO] sent terminate to bot')
        exit_code = bot_proc.wait(timeout=10)
        append_log(f'[INFO] bot exited with code {exit_code}')
    except Exception:
        try:
            bot_proc.kill()
            append_log('[ERROR] bot killed after terminate timeout')
        except Exception:
            pass
    finally:
        bot_proc = None
    return jsonify({ 'ok': True })


@app.get('/status')
def status():
    running = is_running()
    return jsonify({ 'running': running, 'pid': (bot_proc.pid if running else None) })


@app.get('/logs')
def logs():
    limit = int(request.args.get('limit', 200))
    with log_lock:
        out = log_lines[-limit:]
    return jsonify({ 'logs': out })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', '5000'))
    print(f'Control server listening on http://127.0.0.1:{port}')
    app.run(host='127.0.0.1', port=port, debug=False)

