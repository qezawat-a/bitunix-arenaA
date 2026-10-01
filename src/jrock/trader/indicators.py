from __future__ import annotations

import numpy as np

from jrock.trader.models import Candle


def arrays(candles: list[Candle]) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    return tuple(np.array([getattr(c, field) for c in candles], dtype=float) for field in ("close", "high", "low", "volume"))


def ema(values: np.ndarray, period: int) -> np.ndarray:
    result = np.full(len(values), np.nan)
    if len(values) < period:
        return result
    result[period - 1] = np.mean(values[:period])
    alpha = 2 / (period + 1)
    for i in range(period, len(values)):
        result[i] = values[i] * alpha + result[i - 1] * (1 - alpha)
    return result


def wilder(values: np.ndarray, period: int) -> np.ndarray:
    result = np.full(len(values), np.nan)
    if len(values) < period:
        return result
    result[period - 1] = np.mean(values[:period])
    for i in range(period, len(values)):
        result[i] = (result[i - 1] * (period - 1) + values[i]) / period
    return result


def rsi(close: np.ndarray, period: int = 14) -> np.ndarray:
    if len(close) < 2:
        return np.full(len(close), np.nan)
    changes = np.diff(close)
    gains = wilder(np.maximum(changes, 0), period)
    losses = wilder(np.maximum(-changes, 0), period)
    result = np.full(len(close), np.nan)
    for i in range(len(gains)):
        if not np.isfinite(gains[i]) or not np.isfinite(losses[i]):
            continue
        result[i + 1] = 50 if gains[i] == losses[i] == 0 else (100 if losses[i] == 0 else 100 - 100 / (1 + gains[i] / losses[i]))
    return result


def atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
    previous = np.r_[close[0], close[:-1]]
    true_range = np.maximum(high - low, np.maximum(np.abs(high - previous), np.abs(low - previous)))
    return wilder(true_range, period)


def macd(close: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    line = ema(close, 12) - ema(close, 26)
    signal = np.full(len(close), np.nan)
    valid = np.where(np.isfinite(line))[0]
    if len(valid):
        start = valid[0]
        signal[start:] = ema(line[start:], 9)
    return line, signal, line - signal


def bollinger(close: np.ndarray, period: int = 20, deviations: float = 2) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    middle = np.full(len(close), np.nan)
    sigma = middle.copy()
    for i in range(period - 1, len(close)):
        window = close[i - period + 1:i + 1]
        middle[i], sigma[i] = np.mean(window), np.std(window)
    return middle + deviations * sigma, middle, middle - deviations * sigma


def supertrend(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 10, multiple: float = 3) -> tuple[np.ndarray, np.ndarray]:
    vol = atr(high, low, close, period)
    upper, lower = (high + low) / 2 + multiple * vol, (high + low) / 2 - multiple * vol
    trend = np.zeros(len(close), dtype=int)
    line = np.full(len(close), np.nan)
    start = period - 1
    if len(close) <= start:
        return line, trend
    trend[start], line[start] = 1, lower[start]
    for i in range(start + 1, len(close)):
        upper[i] = upper[i] if upper[i] < upper[i - 1] or close[i - 1] > upper[i - 1] else upper[i - 1]
        lower[i] = lower[i] if lower[i] > lower[i - 1] or close[i - 1] < lower[i - 1] else lower[i - 1]
        trend[i] = (-1 if close[i] < lower[i] else 1) if trend[i - 1] == 1 else (1 if close[i] > upper[i] else -1)
        line[i] = lower[i] if trend[i] == 1 else upper[i]
    return line, trend


def rolling_mid(high: np.ndarray, low: np.ndarray, period: int) -> np.ndarray:
    result = np.full(len(high), np.nan)
    for i in range(period - 1, len(high)):
        result[i] = (np.max(high[i - period + 1:i + 1]) + np.min(low[i - period + 1:i + 1])) / 2
    return result


def ichimoku(high: np.ndarray, low: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    tenkan, kijun = rolling_mid(high, low, 9), rolling_mid(high, low, 26)
    raw_a, raw_b = (tenkan + kijun) / 2, rolling_mid(high, low, 52)
    # Compare price to the cloud at NOW (projected 26 periods earlier), not future cloud.
    a, b = np.full(len(high), np.nan), np.full(len(high), np.nan)
    if len(high) > 26:
        a[26:], b[26:] = raw_a[:-26], raw_b[:-26]
    return tenkan, kijun, a, b
