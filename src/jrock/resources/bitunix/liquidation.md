# Bitunix Futures Liquidation Mechanism and Tiered Risk Limit

Source: https://support.bitunix.com/hc/en-us/articles/32152530856601-Bitunix-Futures-Liquidation-Mechanism-and-Tiered-Risk-Limit
Retrieved: 2026-10-01 UTC. Article transcription, related navigation removed.

To reduce forced liquidation of large positions while providing higher trading limits,
Bitunix futures adopts tiered risk limits for all futures trading.

## Tiered Risk Limit

Tiers include level, nominal value, maximum leverage, maintenance margin rate. They affect
order placement and liquidation. The article's BTC illustrative table is an image:
https://support.bitunix.com/hc/article_attachments/41293616920345
It is illustrative, not a permanent table of current risk limits. Query get_position_tiers.

## Liquidation Mechanism

Before fully triggering liquidation, the system withdraws current orders to release margin.
If still subject to liquidation, the position may be partially closed to lower the risk tier.

- Cross: check for positions above tier 1, reduce by priority and re-detect risk after each
  reduction. If all positions are tier 1 and liquidation is still triggered, forced liquidation occurs.
- Isolated: check the related position's tier. Above tier 1, cascading reduction/recalculation
  attempts preserve part of the position; at tier 1, forced liquidation occurs.

## Reduction Priority

1. Higher risk-limit tiers.
2. Higher release of maintenance margin after reduction.
3. Higher nominal values.

## Examples and process

When using 50x leverage on BTC in the article example, the risk tier is 3 and maximum
combined order/position value is 2,500,000 USDT. Limits may change; this is NOT hardcoded.
Maintenance margin is calculated from actual position/order value and corresponding tier,
then used to calculate current margin rate and liquidation price.

When liquidation is triggered: cancel open orders, release margin, then check whether the
position is at the lowest tier. At tier 1: if releasing order margin is insufficient, liquidate.
At tier 2 or above: attempt to lower the tier and its required maintenance margin; repeat
reductions if liquidation persists until saved or tier 1/full liquidation.

To partially close a position, a FOK order is used. If that fails, the whole position can be liquidated.

Article example: BTC position value 5,000,000 USDT, tier 4. Reduce by
5,000,000 - 2,500,000 = 2,500,000 USDT, lowering to tier 3. Recompute maintenance margin
and risk. If still at risk, repeat reductions until saved or liquidated.

## Upstream ambiguity / implementation

One paragraph says both "tier 1 partially closed" and "tier 1 liquidated"; the later step-by-step
section distinguishes tier 1 from tier 2+. This project preserves the ambiguity here, rather than
inventing an exact exchange liquidation formula. Exchange `liqPrice`, tier table, and margin fields
are authoritative. `liqPrice <= 0` means no liquidation price at present, NOT a trading price.

Bot stop-loss protection does not guarantee an exit before liquidation: gaps, liquidity, server outages,
mark-price divergence and exchange rejection can defeat protection. The engine does not reproduce
Bitunix's liquidation engine and does not estimate cross-account liquidation from a simplified formula.
