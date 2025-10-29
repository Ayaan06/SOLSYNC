import asyncio
import websockets
import json
import aiohttp
import argparse
import os
from dataclasses import dataclass
from getpass import getpass
from typing import Optional

from solders.transaction import VersionedTransaction
from solders.keypair import Keypair
from solders.commitment_config import CommitmentLevel
from solders.rpc.requests import SendVersionedTransaction
from solders.rpc.config import RpcSendTransactionConfig


TOKEN_PROGRAM_ID = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"


@dataclass
class BotConfig:
    rpc_ws_url: str
    rpc_http_url: str
    track_wallet: str
    fixed_buy_amount: float
    sell_percent: float  # 0-100
    slippage: int
    priority_fee: float
    pool_preferred: str  # "pump" or "raydium"
    denominated_in_sol: bool
    keypair: Keypair

    @property
    def user_pubkey(self) -> str:
        return str(self.keypair.pubkey())


# State for buy/sell detection
purchased_tokens = set()  # Track coins that have been bought
reported_sells = set()  # Track coins that have been sold and reported


def parse_args_and_prompt() -> BotConfig:
    parser = argparse.ArgumentParser(
        description="SolSync: Copy-trade by mirroring a master wallet's token movements on Solana."
    )
    parser.add_argument("--rpc-ws-url", default=os.getenv("SOLANA_RPC_WS", "wss://api.mainnet-beta.solana.com"), help="WebSocket RPC URL")
    parser.add_argument("--rpc-http-url", default=os.getenv("SOLANA_RPC_HTTP", "https://api.mainnet-beta.solana.com/"), help="HTTP RPC URL for sending transactions")
    parser.add_argument("--track-wallet", default=os.getenv("TRACK_WALLET"), help="Master wallet (public key) to track")
    parser.add_argument("--fixed-buy", type=float, default=float(os.getenv("FIXED_BUY_AMOUNT", "0.02")), help="Fixed buy amount in SOL")
    parser.add_argument("--sell-percent", type=float, default=float(os.getenv("SELL_PERCENT", "100")), help="Percent of token balance to sell (0-100)")
    parser.add_argument("--slippage", type=int, default=int(os.getenv("SLIPPAGE", "5")), help="Slippage percent for trades")
    parser.add_argument("--priority-fee", type=float, default=float(os.getenv("PRIORITY_FEE", "0.001")), help="Priority fee in SOL")
    parser.add_argument("--pool", choices=["pump", "raydium"], default=os.getenv("POOL", "pump"), help="Preferred pool to route trades")
    parser.add_argument("--denominated-in-sol", action="store_true", help="Denominate buy amount in SOL (default on)")
    parser.add_argument("--no-denominated-in-sol", action="store_true", help="Denominate buy amount in USD (if supported)")
    parser.add_argument("--secret-key-base58", help="Base58-encoded secret key for the trading wallet")
    parser.add_argument("--secret-key-file", help="Path to a file containing the base58-encoded secret key")

    args = parser.parse_args()

    # Determine denominatedInSol flag
    if args.no_denominated_in_sol:
        denominated_in_sol = False
    else:
        denominated_in_sol = True  # default

    # Resolve secret key
    secret_b58: Optional[str] = args.secret_key_base58
    if not secret_b58 and args.secret_key_file:
        if not os.path.exists(args.secret_key_file):
            raise FileNotFoundError(f"Secret key file not found: {args.secret_key_file}")
        with open(args.secret_key_file, "r", encoding="utf-8") as f:
            secret_b58 = f.read().strip()
    if not secret_b58:
        # Interactive prompt (hidden input)
        secret_b58 = getpass("Paste your wallet's base58 secret key (input hidden): ")
    if not secret_b58:
        raise ValueError("A base58 secret key is required.")

    try:
        keypair = Keypair.from_base58_string(secret_b58)
    except Exception as e:
        raise ValueError(f"Invalid base58 secret key: {e}")

    # Prompt track wallet if missing
    track_wallet = args.track_wallet or input("Enter the master wallet to track (public key): ").strip()
    if not track_wallet:
        raise ValueError("A wallet to track is required.")

    # Validate ranges
    fixed_buy_amount = max(0.0, float(args.fixed_buy))
    sell_percent = min(100.0, max(0.0, float(args.sell_percent)))
    slippage = max(0, int(args.slippage))
    priority_fee = max(0.0, float(args.priority_fee))

    cfg = BotConfig(
        rpc_ws_url=args.rpc_ws_url,
        rpc_http_url=args.rpc_http_url,
        track_wallet=track_wallet,
        fixed_buy_amount=fixed_buy_amount,
        sell_percent=sell_percent,
        slippage=slippage,
        priority_fee=priority_fee,
        pool_preferred=args.pool,
        denominated_in_sol=denominated_in_sol,
        keypair=keypair,
    )

    # Summary
    print("-" * 50)
    print("SolSync configuration:")
    print(f"Trading wallet: {cfg.user_pubkey}")
    print(f"Tracking wallet: {cfg.track_wallet}")
    print(f"RPC WS: {cfg.rpc_ws_url}")
    print(f"RPC HTTP: {cfg.rpc_http_url}")
    print(f"Fixed buy: {cfg.fixed_buy_amount} SOL (denominatedInSol={cfg.denominated_in_sol})")
    print(f"Sell percent: {cfg.sell_percent}%")
    print(f"Slippage: {cfg.slippage}% | Priority fee: {cfg.priority_fee} SOL | Pool: {cfg.pool_preferred}")
    print("-" * 50)

    return cfg

# Function to execute trades
async def execute_trade(cfg: BotConfig, action: str, mint: str, amount: str | float) -> bool:
    """Execute a buy or sell trade via API and send the transaction asynchronously."""

    retries = 0
    max_retries = 3
    pool = cfg.pool_preferred

    while retries < max_retries:
        payload = {
            "publicKey": cfg.user_pubkey,
            "action": action,  # "buy" or "sell"
            "mint": mint,  # contract address of the token
            "amount": amount,  # Amount to trade (float in SOL for buys, e.g., "100%" for sells)
            "denominatedInSol": "true" if cfg.denominated_in_sol else "false",
            "slippage": cfg.slippage,
            "priorityFee": cfg.priority_fee,
            "pool": pool,
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post("https://pumpportal.fun/api/trade-local", data=payload, timeout=10) as response:
                    if response.status != 200:
                        raise Exception(f"Pump portal error: HTTP {response.status}")

                    response_content = await response.read()

                    tx = VersionedTransaction(
                        VersionedTransaction.from_bytes(response_content).message,
                        [cfg.keypair],
                    )

                    commitment = CommitmentLevel.Confirmed
                    config = RpcSendTransactionConfig(preflight_commitment=commitment)
                    tx_payload = SendVersionedTransaction(tx, config)

                    async with session.post(
                        cfg.rpc_http_url,
                        headers={"Content-Type": "application/json"},
                        data=tx_payload.to_json(),
                        timeout=10,
                    ) as rpc_response:
                        tx_signature = await rpc_response.json()

                        if isinstance(tx_signature, dict) and ("error" in tx_signature or "result" not in tx_signature):
                            raise Exception(f"RPC Transaction Error: {tx_signature}")

                        print("-" * 50)
                        print(
                            f"Receipt:\nAction: {action.capitalize()}\nMint: {mint}\nAmount: {amount}"
                            + (" SOL" if isinstance(amount, float) else "")
                            + f"\nPlatform: {pool}\nStatus: Successful\nSignature: {tx_signature.get('result', tx_signature)}"
                        )
                        print("-" * 50)
                        return True
        except Exception as e:
            print(f"Error during trade (attempt {retries + 1}/{max_retries}) on {pool}: {e}")

        # Retry logic: rotate pool and retry
        pool = "raydium" if pool == "pump" else "pump"
        retries += 1

    # Print failure receipt
    print("-" * 50)
    print(
        f"Receipt:\nAction: {action.capitalize()}\nMint: {mint}\nAmount: {amount}"
        + (" SOL" if isinstance(amount, float) else "")
        + f"\nStatus: Failed after {max_retries} attempts\nResuming tracking..."
    )
    print("-" * 50)
    return False

async def monitor_tokens(cfg: BotConfig) -> None:
    """Monitor token accounts using programSubscribe and act on balance changes."""

    token_balances: dict[str, float] = {}  # Track previous token balances
    initialized_tokens = set()  # Track tokens seen during initialization

    while True:
        try:
            print("Connecting to Solana WebSocket for tokens...")
            async with websockets.connect(cfg.rpc_ws_url, ping_interval=10) as websocket:
                # Subscription payload for programSubscribe
                subscription_payload = {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "programSubscribe",
                    "params": [
                        TOKEN_PROGRAM_ID,
                        {
                            "encoding": "jsonParsed",
                            "commitment": "processed",  # Faster updates
                            "filters": [
                                {"dataSize": 165},
                                {"memcmp": {"offset": 32, "bytes": cfg.track_wallet}},  # Track wallet address
                            ],
                        },
                    ],
                }

                # Send subscription request
                await websocket.send(json.dumps(subscription_payload))
                print("Subscribed to token program updates.")

                while True:
                    try:
                        response = await websocket.recv()
                        data = json.loads(response)

                        if "params" in data:
                            account_notification = (
                                data["params"].get("result", {}).get("value", {}).get("account", {})
                            )

                            # Parse token details
                            parsed_data = (
                                account_notification.get("data", {}).get("parsed", {}).get("info", {})
                            )
                            if parsed_data and "mint" in parsed_data:
                                mint_address = parsed_data["mint"]
                                token_amount = (
                                    parsed_data.get("tokenAmount", {}).get("uiAmount", 0) or 0
                                )  # Use uiAmount

                                # Ensure token initialization
                                previous_balance = token_balances.get(mint_address, 0)
                                if mint_address not in initialized_tokens:
                                    initialized_tokens.add(mint_address)
                                    token_balances[mint_address] = token_amount

                                    # Treat any positive initial balance as a buy
                                    if token_amount > 0:
                                        print(
                                            f"New Coin Detected (Buy): Mint Address: {mint_address}, Amount: {token_amount}"
                                        )
                                        await execute_trade(
                                            cfg,
                                            "buy",
                                            mint_address,
                                            float(cfg.fixed_buy_amount),
                                        )
                                        purchased_tokens.add(mint_address)
                                else:
                                    # Check for buy: balance increases and coin hasn't been bought before
                                    if (
                                        token_amount > previous_balance
                                        and mint_address not in purchased_tokens
                                    ):
                                        print(
                                            f"Buy Detected: Mint Address: {mint_address}, Amount: {token_amount - previous_balance}"
                                        )
                                        await execute_trade(
                                            cfg,
                                            "buy",
                                            mint_address,
                                            float(cfg.fixed_buy_amount),
                                        )
                                        purchased_tokens.add(mint_address)

                                    # Check for sell: balance decreases and coin has been bought
                                    elif (
                                        token_amount < previous_balance
                                        and mint_address in purchased_tokens
                                    ):
                                        if mint_address not in reported_sells:
                                            print(
                                                f"Sell Detected: Mint Address: {mint_address}, Amount: {previous_balance - token_amount}"
                                            )
                                            sell_amount_str = f"{int(cfg.sell_percent)}%"
                                            await execute_trade(
                                                cfg, "sell", mint_address, sell_amount_str
                                            )
                                            reported_sells.add(mint_address)

                                # Update token balance
                                token_balances[mint_address] = token_amount

                    except websockets.exceptions.ConnectionClosedError:
                        print("WebSocket connection closed. Reconnecting...")
                        break  # Exit to reconnect
                    except Exception as e:
                        print(f"Error during processing: {e}")
                        continue

        except Exception as e:
            print(f"Unexpected error: {e}. Retrying in 5 seconds...")
            await asyncio.sleep(5)

async def main() -> None:
    """Entry point: parse config, then monitor tokens and trade."""
    cfg = parse_args_and_prompt()
    await monitor_tokens(cfg)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram terminated by user.")
