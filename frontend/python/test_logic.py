import asyncio
import json
import sys
import types


class FakeExceptions:
    class ConnectionClosedError(Exception):
        pass


class FakeWebSocketConn:
    def __init__(self, messages):
        self._messages = messages
        self._i = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def send(self, _):
        return

    async def recv(self):
        if self._i >= len(self._messages):
            raise FakeExceptions.ConnectionClosedError()
        msg = self._messages[self._i]
        self._i += 1
        return json.dumps(msg)


class FakeWebsocketsModule:
    def __init__(self, messages):
        self._messages = messages
        self.exceptions = FakeExceptions

    def connect(self, *_args, **_kwargs):
        return FakeWebSocketConn(self._messages)


def make_msg(mint: str, ui_amount: float):
    return {
        "params": {
            "result": {
                "value": {
                    "account": {
                        "data": {
                            "parsed": {
                                "info": {
                                    "mint": mint,
                                    "tokenAmount": {"uiAmount": ui_amount},
                                }
                            }
                        }
                    }
                }
            }
        }
    }


async def run_test():
    # Stub third‑party deps before importing the bot module so the import doesn't require them
    # Minimal stubs for solders and aiohttp (unused in this logic test)
    solders = types.ModuleType("solders")
    solders.transaction = types.ModuleType("solders.transaction")
    class DummyVT:  # placeholder
        def __init__(self, *a, **k):
            pass
        @classmethod
        def from_bytes(cls, *_):
            return cls()
        @property
        def message(self):
            return b""
    solders.transaction.VersionedTransaction = DummyVT
    solders.keypair = types.ModuleType("solders.keypair")
    class DummyKP:
        def __init__(self, *a, **k):
            pass
        @classmethod
        def from_base58_string(cls, *_):
            return cls()
        def pubkey(self):
            return "DummyPubkey"
    solders.keypair.Keypair = DummyKP
    solders.commitment_config = types.ModuleType("solders.commitment_config")
    class DummyCommit:
        Confirmed = "confirmed"
    solders.commitment_config.CommitmentLevel = DummyCommit
    solders.rpc = types.ModuleType("solders.rpc")
    solders.rpc.requests = types.ModuleType("solders.rpc.requests")
    class DummySend:
        def __init__(self, *a, **k):
            pass
        def to_json(self):
            return "{}"
    solders.rpc.requests.SendVersionedTransaction = DummySend
    solders.rpc.config = types.ModuleType("solders.rpc.config")
    class DummyCfg:
        def __init__(self, *a, **k):
            pass
    solders.rpc.config.RpcSendTransactionConfig = DummyCfg
    sys.modules["solders"] = solders
    sys.modules["solders.transaction"] = solders.transaction
    sys.modules["solders.keypair"] = solders.keypair
    sys.modules["solders.commitment_config"] = solders.commitment_config
    sys.modules["solders.rpc"] = solders.rpc
    sys.modules["solders.rpc.requests"] = solders.rpc.requests
    sys.modules["solders.rpc.config"] = solders.rpc.config

    aiohttp = types.ModuleType("aiohttp")
    sys.modules["aiohttp"] = aiohttp

    # Provide a minimal websockets module so import succeeds; we'll replace it later with Fake
    ws_placeholder = types.SimpleNamespace(exceptions=FakeExceptions, connect=lambda *a, **k: None)
    sys.modules["websockets"] = ws_placeholder

    # Now import the module under test
    import finalDraftV3 as mod  # type: ignore

    stream = [
        make_msg("MintTest", 1.0),
        make_msg("MintTest", 0.6),
    ]

    mod.websockets = FakeWebsocketsModule(stream)

    calls = []

    async def fake_execute_trade(cfg, action, mint, amount):
        calls.append((action, mint, amount))
        print(f"EXECUTE {action} mint={mint} amount={amount}")
        return True

    mod.execute_trade = fake_execute_trade  # type: ignore

    cfg = mod.BotConfig(
        rpc_ws_url="wss://example",
        rpc_http_url="https://example",
        track_wallet="DummyTrackedWallet",
        fixed_buy_amount=0.02,
        sell_percent=100.0,
        slippage=5,
        priority_fee=0.001,
        pool_preferred="pump",
        denominated_in_sol=True,
        keypair=DummyKP(),
    )

    try:
        await asyncio.wait_for(mod.monitor_tokens(cfg), timeout=0.5)
    except asyncio.TimeoutError:
        pass

    buy_calls = [c for c in calls if c[0] == "buy"]
    sell_calls = [c for c in calls if c[0] == "sell"]

    assert buy_calls, "Expected at least one buy call from initial positive balance"
    assert sell_calls, "Expected at least one sell call after balance decrease"
    assert isinstance(buy_calls[0][2], float) and abs(buy_calls[0][2] - 0.02) < 1e-9
    assert isinstance(sell_calls[0][2], str) and sell_calls[0][2].endswith("%")

    print("TEST PASS: wallet read + buy/sell logic works with simulated stream.")


if __name__ == "__main__":
    asyncio.run(run_test())
