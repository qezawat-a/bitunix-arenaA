from __future__ import annotations

import asyncio
import time

from jrock.exchange.client import BitunixClient, ExchangeError
from jrock.trader.models import Candle, PairRules, TradeConfig

INTERVAL_MS = {"1m": 60_000, "3m": 180_000, "5m": 300_000, "15m": 900_000, "30m": 1_800_000,
               "1h": 3_600_000, "2h": 7_200_000, "4h": 14_400_000, "6h": 21_600_000,
               "8h": 28_800_000, "12h": 43_200_000, "1d": 86_400_000, "3d": 259_200_000, "1w": 604_800_000}


def closed_candles(rows: list[dict], interval_ms: int, now_ms: int | None = None) -> list[Candle]:
    now_ms = int(time.time() * 1000) if now_ms is None else now_ms
    parsed = {}
    for row in rows:
        if "time" not in row:
            raise ExchangeError("protocol", "Candle time missing; cannot confirm candle close")
        timestamp = int(row["time"])
        if timestamp + interval_ms > now_ms:
            continue  # Open candle is never used for strategies.
        candle = Candle(timestamp, *[float(row[k]) for k in ("open", "high", "low", "close", "baseVol")],
                        float(row.get("quoteVol", 0)))
        parsed[timestamp] = candle
    return sorted(parsed.values(), key=lambda c: c.time)


def aggregate_3m(values: list[Candle], now_ms: int | None = None) -> list[Candle]:
    now_ms = int(time.time() * 1000) if now_ms is None else now_ms
    groups = {}
    for candle in values:
        bucket = candle.time // 180_000 * 180_000
        groups.setdefault(bucket, {})[candle.time] = candle
    result = []
    for start, group in sorted(groups.items()):
        if start + 180_000 > now_ms or set(group) != {start, start + 60_000, start + 120_000}:
            continue  # Missing candle or incomplete group cannot masquerade as a full 3m bar.
        bars = sorted(group.values(), key=lambda c: c.time)
        result.append(Candle(start, bars[0].open, max(c.high for c in bars), min(c.low for c in bars),
                             bars[-1].close, sum(c.volume for c in bars), sum(c.quote_volume for c in bars)))
    return result


class MarketData:
    def __init__(self, client: BitunixClient):
        self.client = client
        self.rules: dict[str, PairRules] = {}
        self.tickers: dict[str, dict] = {}
        self.funding: dict[str, dict] = {}
        self.updated = 0.0
        self.metadata_updated = 0.0
        self.candle_cache: dict[tuple[str, str], tuple[int, list[Candle]]] = {}

    async def refresh(self) -> None:
        tickers = await self.client.get_tickers()
        funding = await self.client.get_funding_rate_batch()
        if not isinstance(tickers, list) or not isinstance(funding, list):
            raise ExchangeError("protocol", "Expected market arrays")
        if time.monotonic() - self.metadata_updated > 300 or not self.rules:
            pairs = await self.client.get_trading_pairs()
            self.rules = {r["symbol"]: PairRules.from_api(r) for r in pairs}
            self.metadata_updated = time.monotonic()
        self.tickers = {r["symbol"]: r for r in tickers}
        self.funding = {r["symbol"]: r for r in funding}
        self.updated = time.monotonic()

    def universe(self, config: TradeConfig) -> list[str]:
        rows = []
        for symbol, ticker in self.tickers.items():
            rule = self.rules.get(symbol)
            if not rule or rule.status != "OPEN" or not rule.api_supported or rule.quote != "USDT":
                continue
            if config.symbols != ["*"] and symbol not in config.symbols:
                continue
            volume = float(ticker.get("quoteVol", 0))
            if volume < config.min_24h_volume_usd:
                continue
            opening, last = float(ticker.get("open", 0)), float(ticker.get("lastPrice", 0))
            change = (last / opening - 1) * 100 if opening > 0 else 0
            rank = {"VOLUME": volume, "GAINERS": change, "LOSERS": -change, "MOVERS": abs(change)}[config.universe_rank]
            rows.append((rank, symbol))
        return [symbol for _, symbol in sorted(rows, reverse=True)[:config.max_scan_symbols]]

    async def candles(self, symbol: str, tf: str, count: int = 120) -> list[Candle]:
        now = int(time.time() * 1000)
        bucket = now // INTERVAL_MS[tf]
        cached = self.candle_cache.get((symbol, tf))
        if cached and cached[0] == bucket:
            return cached[1]
        if tf == "3m":
            # REST max 200; paginate 1m backward until 3*count + alignment margin are available.
            needed = count * 3 + 3
            all_rows = {}
            end = now
            for _ in range(5):
                rows = await self.client.get_kline(symbol=symbol, interval="1m", limit=200, endTime=end)
                if not rows:
                    break
                for row in rows:
                    all_rows[int(row["time"])] = row
                oldest = min(int(r["time"]) for r in rows)
                if len(all_rows) >= needed or oldest >= end:
                    break
                end = oldest - 1
            result = aggregate_3m(closed_candles(list(all_rows.values()), 60_000, now), now)[-count:]
        else:
            rows = await self.client.get_kline(symbol=symbol, interval=tf, limit=min(count + 1, 200))
            result = closed_candles(rows, INTERVAL_MS[tf], now)[-count:]
        if not result or result[-1].time + INTERVAL_MS[tf] < now - INTERVAL_MS[tf] * 1.5:
            raise ExchangeError("stale", f"Stale/missing {tf} candles for {symbol}")
        if any(b.time - a.time != INTERVAL_MS[tf] for a, b in zip(result, result[1:], strict=False)):
            raise ExchangeError("gap", f"Missing candle in {symbol} {tf}; signal rejected")
        self.candle_cache[symbol, tf] = bucket, result
        return result

    async def frames(self, symbol: str, config: TradeConfig) -> dict[str, list[Candle]]:
        results = await asyncio.gather(*(self.candles(symbol, tf) for tf in config.timeframes), return_exceptions=True)
        frames = {}
        for tf, result in zip(config.timeframes, results, strict=True):
            if isinstance(result, BaseException):
                raise ExchangeError("candles", f"Incomplete market data for {symbol} {tf}") from result
            frames[tf] = result
        return frames
