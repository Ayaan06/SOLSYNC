# Frontend Directory Overview

This directory contains the assets for the MarketMinerAI interface and a companion Python utility used for live Solana wallet tracking.

## Structure

- `web/` – Static web assets for the landing page (`index.html`, `styles.css`, and `script.js`).
- `python/` – Automation scripts for market monitoring (`finalDraftV3.py`).

## Python Automation

The `python/finalDraftV3.py` script listens to the Solana `programSubscribe` WebSocket feed for the configured wallet, keeps track of token balances, and automatically places buy or sell orders through the Pump.fun API based on detected balance changes. Trades are retried across the Pump and Raydium pools, and receipts are printed for both successes and failures.

No application code was modified—this reorganization simply groups related files to make the Python automation easier to find.
