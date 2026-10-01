# Bitunix Futures Position: A Guide to Four Take-Profit and Stop-Loss Methods (Web)

Source: https://www.bitunix.com/uk-ua/hub/helpcenter/article/bitunix-futures-position-a-guide-to-four-take-profit-and-stop-loss-methods-web?id=290
English equivalent: https://www.bitunix.com/hub/helpcenter/article/bitunix-futures-position-a-guide-to-four-take-profit-and-stop-loss-methods-web?id=290
Retrieved: 2026-10-01 UTC. Article body transcription, navigation removed.
Last updated in source: 2026-07-31.
Header image: https://img.bitunix.com/config/kv/597498.png

## What Are Take-Profit and Stop-Loss Orders?

TP and SL are commonly used risk-management tools for futures. Traders set trigger conditions
in advance; at the specified market price an automatic closing order attempts to lock profits or limit loss.
Bitunix offers position, partial, trailing and account TP/SL, selected according to strategy and risk tolerance.

## Four Typical Use Cases

### 1. Position TP/SL — basic single-position risk management

Example: BTC long at 60000 USDT, whole-position TP 65000 and SL 58000. At either target the
entire position is closed in an all-in/all-out exit. Simple predefined exits avoid constant monitoring.

### 2. Partial TP/SL — flexible position management

Example: close 30% of a BTC long at 65000, another 40% at 68000, leaving the remainder open.
Scale-out secures some profit while retaining potential upside.

### 3. Trailing TP/SL — dynamic trend following

Example: BTC long at 50000, activation 55000, callback 10%. Once active, if price climbs to
70000 then retraces to 63000 (10%), close to lock trend profits. Longs close after a rise/retrace;
shorts after a decline/rebound. The trigger tracks favorable price movement.

### 4. Account TP/SL — unified risk across positions

Example: BTC/ETH/SOL positions with TP at total profit 1000 USDT and SL at total loss 500 USDT.
Close all futures positions when the overall PnL threshold is reached, rather than individual asset targets.

## Setup Guide

1. Open https://www.bitunix.com/ and choose Futures, e.g. https://www.bitunix.com/contract-trade/BTCUSDT .
   Image: https://img.bitunix.com/config/kv/41622.png
2. Scroll to currently held futures positions.
   Image: https://img.bitunix.com/config/kv/915741.png
3. Click TP/SL to choose the method.
   Image: https://img.bitunix.com/config/kv/797593.png
4. Position: enter trigger price or adjust expected-return/price-change slider. Review calculated
   PnL and Confirm to activate.
   Image: https://img.bitunix.com/config/kv/182194.png
5. Partial: enter trigger price or adjust return/price-change slider, then position-ratio slider.
   Review calculated PnL and Confirm.
   Image: https://img.bitunix.com/config/kv/654366.png
6. Trailing: set activation price, retracement range, quantity and **Ratio or Interval** mode.
   Once activation price is reached, trailing starts. On callback, close at market. Confirm to activate.
   ETH example: entry/activation 2000 USDT, 5% callback. Peak 2500 -> trigger 2375.
   Image: https://img.bitunix.com/config/kv/57458.png
7. Account: click Account TP/SL in positions, set TP/SL PnL amounts, then Confirm.
   Images: https://img.bitunix.com/config/kv/974932.png and https://img.bitunix.com/config/kv/576825.png

Modify or cancel TP/SL if market conditions change.
Images: https://img.bitunix.com/config/kv/471611.png and https://img.bitunix.com/config/kv/517730.png

## Advantages

- Position: straightforward entire-position close at preset triggers; options include price, PnL
  amount or percentage; simple fundamental single-position risk management.
- Partial: multiple closing ratios at different levels; secures portions of profit while retaining a runner;
  more flexible adaptation to market conditions.
- Trailing: dynamically adjusts triggers to favorable market movement and retracement; reduces manual
  adjustment and suits trending markets.
- Account: whole futures account is the control unit; closes all positions at total PnL thresholds;
  unifies multi-position risk management without setting every individual TP separately.

## Disclaimer (source)

This is not investment advice, a recommendation, an offer/solicitation to buy/sell/hold digital assets,
or financial, accounting, legal or tax advice. Digital assets, including stablecoins and NFTs, involve
significant risks and volatility. Consider suitability for your finances. Consult qualified legal,
tax or investment professionals for personal advice. You are responsible for applicable local laws.

## J+rock mapping — no fabricated REST routes

`TP_MODE=POSITION|PARTIAL|TRAILING|ACCOUNT` is the four-method axis.
`TPSL_METHOD=ADAPTIVE|FIXED_R` controls target calculation, not exchange method type.
Position and partial use documented position/partial REST APIs.
**No native trailing-order or account-TP/SL endpoint is specified in the supplied futures REST pages.**
Trailing (ATR extension plus article's Ratio/Interval) and account PnL guards are **local engine features**.
They require a running, connected engine, not an assumed exchange-native capability. Always retain a
native exchange stop where possible; never cancel it merely because local protection is active.

Partial ladder `share@R` shares total <=100%; remainder is a runner. Share quantities round down;
reject dust-sized rungs rather than rounding up exposure. Account thresholds are USDT PnL amounts, 0 disables.
