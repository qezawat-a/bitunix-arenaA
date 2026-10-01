# Explanation of the Order Units in Futures Trading

Source: https://www.bitunix.com/hub/helpcenter/article/explanation-of-the-order-units-in-futures-trading?id=170
Retrieved: 2026-10-01 UTC. Article body transcription, navigation removed.
Last updated in source: 2026-05-28.
Article image: https://img.bitunix.com/config/kv/949028.png

Perpetual futures have no expiration date. Quantity unit, cost value and nominal value
represent position size, actual cost and market value. Bitunix offers all three as order units.

## Nominal Value

The contract size/value in USDT, representing the position's market value. Used to calculate
position value and PnL; no leverage or margin is involved in the nominal value itself.

Example: nominal order 1000 USDT, leverage 10x, price 10000 USDT:
- Cost excluding commission: nominal / leverage = 1000 / 10 = 100 USDT.
- Quantity: nominal / price = 1000 / 10000 = 0.1 BTC.

## Cost Value

The actual cost to open the position, including initial margin and transaction fees.
Used to assess trading cost, margin requirements and risk.

Example: cost order 1000 USDT, leverage 10x, price 10000 USDT:
- Quantity excluding commission: cost * leverage / price = 1000 * 10 / 10000 = 1 BTC.

## Quantity Unit

Quantity of the underlying asset bought/sold; the trading system's base unit. It determines
order size and margin, and helps control exposure.

Example: quantity 1 BTC, price 10000 USDT, leverage 10x:
- Cost excluding commission = qty * price / leverage = 1 * 10000 / 10 = 1000 USDT.
- Nominal value = qty * price = 10000 USDT.

## Notes

1. Nominal value is contract size, cost value is actual paid cost, quantity unit is the underlying amount.
2. Cost generally includes initial margin and opening transaction fees.
3. Leverage increases position size and risk of profit/loss.
4. Understand trading rules and exchange fees to manage cost and risk.
5. Perpetual futures are high risk and can cause loss; use informed risk management.

## J+rock calculator

Order APIs receive **base-coin qty**, not cost/notional amounts. The calculator supports:
- QUANTITY: use base qty.
- NOMINAL: qty = notional / price.
- COST: solve qty = cost / (price/leverage + price*fee_rate), including configurable opening fee.
Rounding is **down** to live basePrecision and rejects values below minTradeVolume or above maxMarketOrderVolume.
It returns estimated margin, notional and opening fee; real fees, fill price and funding can differ.
