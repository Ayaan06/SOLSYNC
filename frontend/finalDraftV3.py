import asyncio
import websockets
import json
import aiohttp
from solders.transaction import VersionedTransaction
from solders.keypair import Keypair
from solders.commitment_config import CommitmentLevel
from solders.rpc.requests import SendVersionedTransaction
from solders.rpc.config import RpcSendTransactionConfig

# Configuration
SOLANA_RPC_URL = "wss://api.mainnet-beta.solana.com"
TOKEN_PROGRAM_ID = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
PUBLIC_KEY = "2c6TyK9e92PfLuBSAnBjVhoa64X72qLJmfhhDgbwkVru"
FIXED_BUY_AMOUNT = 0.02  # Fixed amount for buy trades
SELL_AMOUNT = "100%"  # Sell 100% of token balance

# New Parameters for buy/sell from lastTransaction2
purchased_tokens = set()  # Track coins that have been bought
reported_sells = set()  # Track coins that have been sold and reported

# Function to execute trades
async def execute_trade(action, mint, amount, pool):
    """
    Execute a buy or sell trade via API and send the transaction asynchronously.
    """
    retries = 0
    max_retries = 3

    while retries < max_retries:
        payload = {
            "publicKey": PUBLIC_KEY,
            "action": action,  # "buy" or "sell"
            "mint": mint,  # contract address of the token
            "amount": amount,  # Amount to trade
            "denominatedInSol": "true",
            "slippage": 5,
            "priorityFee": 0.001,
            "pool": pool
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post("https://pumpportal.fun/api/trade-local", data=payload, timeout=5) as response:
                    if response.status == 200:
                        response_content = await response.read()
                        keypair = Keypair.from_base58_string(
                            "21tftw1Xyqx7zE4z2SzjFpeXRdEQm85bbrcw9RZqyW1hUo6jqZMAChRMdWN8LwK68ZfASxsymaXty7nM6CSE8Px1"
                        )
                        tx = VersionedTransaction(VersionedTransaction.from_bytes(response_content).message, [keypair])

                        commitment = CommitmentLevel.Confirmed
                        config = RpcSendTransactionConfig(preflight_commitment=commitment)
                        tx_payload = SendVersionedTransaction(tx, config)

                        async with session.post(
                            "https://api.mainnet-beta.solana.com/",
                            headers={"Content-Type": "application/json"},
                            data=tx_payload.to_json(),
                            timeout=5
                        ) as rpc_response:
                            tx_signature = await rpc_response.json()

                            if "error" in tx_signature or "result" not in tx_signature:
                                raise Exception("RPC Transaction Error")

                            print("-" * 50)
                            print(f"Receipt:\nAction: {action.capitalize()}\nMint: {mint}\nAmount: {amount} SOL\nPlatform: {pool}\nStatus: Successful\nSignature: {tx_signature['result']}")
                            print("-" * 50)
                            return True
        except Exception as e:
            print(f"Error during trade: {e}")

        # Retry logic
        pool = "raydium" if pool == "pump" else "pump"  # Rotate pools
        retries += 1

    # Print failure receipt
    print("-" * 50)
    print(f"Receipt:\nAction: {action.capitalize()}\nMint: {mint}\nAmount: {amount} SOL\nPlatform: {pool}\nStatus: Failed after {max_retries} attempts\nResuming tracking...")
    print("-" * 50)
    return False

async def monitor_tokens(wallet_address):
    """
    Monitor token accounts using programSubscribe.
    """
    token_balances = {}  # Track previous token balances
    initialized_tokens = set()  # Track tokens seen during initialization

    while True:
        try:
            print("Connecting to Solana WebSocket for tokens...")
            async with websockets.connect(SOLANA_RPC_URL, ping_interval=10) as websocket:
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
                                {"memcmp": {"offset": 32, "bytes": wallet_address}}  # Track wallet address
                            ]
                        }
                    ]
                }

                # Send subscription request
                await websocket.send(json.dumps(subscription_payload))
                print("Subscribed to token program updates.")

                while True:
                    try:
                        response = await websocket.recv()
                        data = json.loads(response)

                        if "params" in data:
                            account_notification = data["params"].get("result", {}).get("value", {}).get("account", {})

                            # Parse token details
                            parsed_data = account_notification.get("data", {}).get("parsed", {}).get("info", {})
                            if parsed_data and "mint" in parsed_data:
                                mint_address = parsed_data["mint"]
                                token_amount = parsed_data.get("tokenAmount", {}).get("uiAmount", 0)  # Use uiAmount

                                # Ensure token initialization
                                previous_balance = token_balances.get(mint_address, 0)
                                if mint_address not in initialized_tokens:
                                    initialized_tokens.add(mint_address)
                                    token_balances[mint_address] = token_amount

                                    # Treat any positive initial balance as a buy
                                    if token_amount > 0:
                                        print(f"New Coin Detected (Buy): Mint Address: {mint_address}, Amount: {token_amount}")
                                        await execute_trade("buy", mint_address, FIXED_BUY_AMOUNT, "pump")
                                        purchased_tokens.add(mint_address)
                                else:
                                    # Check for buy: balance increases and coin hasn't been bought before
                                    if token_amount > previous_balance and mint_address not in purchased_tokens:
                                        print(f"Buy Detected: Mint Address: {mint_address}, Amount: {token_amount - previous_balance}")
                                        await execute_trade("buy", mint_address, FIXED_BUY_AMOUNT, "pump")
                                        purchased_tokens.add(mint_address)

                                    # Check for sell: balance decreases and coin has been bought
                                    elif token_amount < previous_balance and mint_address in purchased_tokens:
                                        if mint_address not in reported_sells:
                                            print(f"Sell Detected: Mint Address: {mint_address}, Amount: {previous_balance - token_amount}")
                                            await execute_trade("sell", mint_address, SELL_AMOUNT, "pump")
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

async def main(wallet_address):
    """
    Monitor token balances and execute trades based on buy/sell detection.
    """
    await monitor_tokens(wallet_address)

if __name__ == "__main__":
    wallet_to_track = "suqh5sHtr8HyJ7q8scBimULPkPpA557prMG47xCHQfK"
    try:
        asyncio.run(main(wallet_to_track))
    except KeyboardInterrupt:
        print("\nProgram terminated by user.")
