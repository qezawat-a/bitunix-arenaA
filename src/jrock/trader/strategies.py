from __future__ import annotations

import math
import time
from collections import Counter

import numpy as np

from jrock.trader.indicators import arrays, atr, bollinger, ema, ichimoku, macd, rsi, supertrend
from jrock.trader.models import Candle, Signal, TradeConfig, Vote

STRATEGY_NAMES = ("ema", "rsi", "macd", "volume", "momentum", "atr_breakout", "funding_rate", "supertrend", "bollinger", "ichimoku")


def vote(name: str, direction: str, confidence: float, reason: str) -> Vote:
    return Vote(name, direction, min(95.0, max(0.0, float(confidence))), reason)


def evaluate(candles: list[Candle], funding_rate: float | None, enabled: list[str] | None = None) -> list[Vote]:
    enabled = list(STRATEGY_NAMES) if enabled is None else enabled
    if len(candles) < 80:
        return [vote(name, "NEUTRAL", 0, "Need at least 80 complete closed candles") for name in enabled]
    close, high, low, volume = arrays(candles)
    volatility = float(atr(high, low, close)[-1])
    if not math.isfinite(volatility) or volatility <= 0:
        return [vote(name, "NEUTRAL", 0, "Zero/invalid ATR; no signal") for name in enabled]
    votes = {}
    fast, slow = ema(close, 9)[-1], ema(close, 21)[-1]
    direction = "LONG" if fast > slow else "SHORT" if fast < slow else "NEUTRAL"
    votes["ema"] = vote("ema", direction, 60 + min(abs(fast - slow) / volatility * 18, 35), "EMA 9 versus EMA 21, normalized by ATR")
    strength = rsi(close)[-1]
    direction = "LONG" if 52 <= strength <= 72 else "SHORT" if 28 <= strength <= 48 else "NEUTRAL"
    votes["rsi"] = vote("rsi", direction, 60 + min(abs(strength - 50) * 1.1, 30) if direction != "NEUTRAL" else 0,
                         "RSI 14 trend zone; extremes abstain rather than assume reversal")
    _, _, histogram = macd(close)
    direction = "LONG" if histogram[-1] > volatility * 0.01 else "SHORT" if histogram[-1] < -volatility * 0.01 else "NEUTRAL"
    votes["macd"] = vote("macd", direction, 60 + min(abs(histogram[-1]) / volatility * 50, 35) if direction != "NEUTRAL" else 0, "MACD 12/26/9 histogram")
    average_volume = np.mean(volume[-21:-1])
    ratio = volume[-1] / average_volume if average_volume > 0 else 0
    direction = ("LONG" if close[-1] > close[-2] else "SHORT") if ratio >= 1.2 else "NEUTRAL"
    votes["volume"] = vote("volume", direction, 60 + min((ratio - 1) * 30, 35) if direction != "NEUTRAL" else 0,
                            "Volume expansion >=1.2x previous 20 bars, confirmed by price change")
    momentum = close[-1] - close[-11]
    direction = "LONG" if momentum > volatility else "SHORT" if momentum < -volatility else "NEUTRAL"
    votes["momentum"] = vote("momentum", direction, 60 + min(abs(momentum) / volatility * 8, 35) if direction != "NEUTRAL" else 0, "10-bar momentum exceeds ATR")
    upper, lower = np.max(high[-21:-1]) + volatility * 0.1, np.min(low[-21:-1]) - volatility * 0.1
    direction = "LONG" if close[-1] > upper else "SHORT" if close[-1] < lower else "NEUTRAL"
    votes["atr_breakout"] = vote("atr_breakout", direction, 80 if direction != "NEUTRAL" else 0, "Breakout of PRIOR 20 bars plus 0.1 ATR; no current-bar look-ahead")
    if funding_rate is None or not math.isfinite(funding_rate):
        votes["funding_rate"] = vote("funding_rate", "NEUTRAL", 0, "Funding missing; no invented rate")
    else:
        direction = "SHORT" if funding_rate >= 0.0005 else "LONG" if funding_rate <= -0.0005 else "NEUTRAL"
        votes["funding_rate"] = vote("funding_rate", direction, 65 + min(abs(funding_rate) * 10000, 25) if direction != "NEUTRAL" else 0,
                                      "Contrarian funding crowding threshold; funding alone never opens a trade")
    line, trend = supertrend(high, low, close)
    direction = "LONG" if trend[-1] > 0 else "SHORT" if trend[-1] < 0 else "NEUTRAL"
    votes["supertrend"] = vote("supertrend", direction, 65 + min(abs(close[-1] - line[-1]) / volatility * 10, 30), "Supertrend 10 periods, 3 ATR")
    upper, middle, lower = bollinger(close)
    direction = "LONG" if close[-1] > middle[-1] and middle[-1] > middle[-2] else "SHORT" if close[-1] < middle[-1] and middle[-1] < middle[-2] else "NEUTRAL"
    width = upper[-1] - lower[-1]
    votes["bollinger"] = vote("bollinger", direction, 60 + min(abs(close[-1] - middle[-1]) / width * 50, 35) if width > 0 else 0,
                               "Bollinger 20/2 trend confirmation; center slope and price location")
    tenkan, kijun, cloud_a, cloud_b = ichimoku(high, low)
    direction = "LONG" if close[-1] > max(cloud_a[-1], cloud_b[-1]) and tenkan[-1] > kijun[-1] else "SHORT" if close[-1] < min(cloud_a[-1], cloud_b[-1]) and tenkan[-1] < kijun[-1] else "NEUTRAL"
    votes["ichimoku"] = vote("ichimoku", direction, 80 if direction != "NEUTRAL" else 0, "9/26/52 Ichimoku, cloud displaced 26 bars; no future data")
    return [votes[name] for name in enabled]


def timeframe_consensus(votes: list[Vote], config: TradeConfig) -> dict:
    # Confidence is a HEURISTIC score, not a calibrated success probability.
    active = [v for v in votes if v.direction != "NEUTRAL" and v.confidence >= config.tf_min_confidence]
    counts = Counter(v.direction for v in active)
    if not counts or counts["LONG"] == counts["SHORT"]:
        return {"direction": "NEUTRAL", "confidence": 0, "agreeing": 0, "votes": [vars(v) for v in votes]}
    direction, count = counts.most_common(1)[0]
    winners = [v for v in active if v.direction == direction]
    agreement = count / len(active)
    confidence = float(np.mean([v.confidence for v in winners])) * agreement
    # Never allow funding-only or fewer than user's strategy threshold to win.
    if count < config.min_agreeing_strategies or all(v.strategy == "funding_rate" for v in winners):
        direction, confidence = "NEUTRAL", 0
    return {"direction": direction, "confidence": round(confidence, 2), "agreeing": count, "votes": [vars(v) for v in votes]}


def combine(symbol: str, candles: dict[str, list[Candle]], funding: float | None, config: TradeConfig) -> Signal:
    frames = {tf: timeframe_consensus(evaluate(values, funding, config.enabled_strategies), config) for tf, values in candles.items()}
    usable = [v for v in frames.values() if v["direction"] != "NEUTRAL" and v["confidence"] >= config.tf_min_confidence]
    counts = Counter(v["direction"] for v in usable)
    direction, confidence, agreeing = "NEUTRAL", 0.0, 0
    if counts and counts["LONG"] != counts["SHORT"]:
        winner, count = counts.most_common(1)[0]
        winning = [v for v in usable if v["direction"] == winner]
        # Penalize missing/neutral/disagreeing timeframes; won't treat missing data as confirmation.
        confidence = float(np.mean([v["confidence"] for v in winning])) * count / len(config.timeframes)
        agreeing = min(v["agreeing"] for v in winning)
        if count >= config.min_agreeing_timeframes and confidence >= config.min_confidence:
            direction = winner
    primary = next((candles[tf] for tf in config.timeframes if tf in candles), [])
    volatility = 0.0
    if len(primary) >= 14:
        close, high, low, _ = arrays(primary)
        volatility = float(atr(high, low, close)[-1])
    return Signal(symbol, direction, round(confidence, 2), agreeing, frames, volatility,
                  primary[-1].close if primary else 0, int(time.time() * 1000),
                  evaluate(primary, funding, config.enabled_strategies))
