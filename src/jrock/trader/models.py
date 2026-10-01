from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass, field
from decimal import ROUND_CEILING, ROUND_DOWN, ROUND_FLOOR, Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from jrock.config import Settings

D = Decimal


def decimal(value: object) -> Decimal:
    number = Decimal(str(value))
    if not number.is_finite():
        raise ValueError("Non-finite decimal is not a trading quantity")
    return number


def fmt(number: Decimal) -> str:
    return format(number, "f")


def quantize(number: Decimal, precision: int, direction: str = "down") -> Decimal:
    mode = {"down": ROUND_DOWN, "floor": ROUND_FLOOR, "ceil": ROUND_CEILING}[direction]
    return number.quantize(Decimal(1).scaleb(-precision), rounding=mode)


@dataclass(frozen=True)
class Candle:
    time: int  # open time, milliseconds UTC
    open: float
    high: float
    low: float
    close: float
    volume: float
    quote_volume: float = 0

    def __post_init__(self):
        if not all(math.isfinite(x) for x in (self.open, self.high, self.low, self.close, self.volume, self.quote_volume)):
            raise ValueError("Non-finite candle")
        if min(self.open, self.high, self.low, self.close) <= 0 or self.high < max(self.open, self.close, self.low):
            raise ValueError("Invalid OHLC prices")
        if self.low > min(self.open, self.close) or self.volume < 0 or self.quote_volume < 0:
            raise ValueError("Invalid OHLCV range")


@dataclass(frozen=True)
class Vote:
    strategy: str
    direction: Literal["LONG", "SHORT", "NEUTRAL"]
    confidence: float
    reason: str


@dataclass
class Signal:
    symbol: str
    direction: Literal["LONG", "SHORT", "NEUTRAL"]
    confidence: float
    agreeing: int
    timeframes: dict
    atr: float
    price: float
    timestamp_ms: int
    votes: list[Vote] = field(default_factory=list)

    def public(self) -> dict:
        return asdict(self)


@dataclass
class PairRules:
    symbol: str
    base_precision: int
    quote_precision: int
    min_qty: Decimal
    max_market_qty: Decimal
    min_leverage: int
    max_leverage: int
    status: str
    api_supported: bool
    quote: str

    @classmethod
    def from_api(cls, row: dict) -> PairRules:
        return cls(row["symbol"], int(row["basePrecision"]), int(row["quotePrecision"]),
                   decimal(row["minTradeVolume"]), decimal(row["maxMarketOrderVolume"]),
                   int(row["minLeverage"]), int(row["maxLeverage"]), row["symbolStatus"],
                   row.get("isApiSupported") is True, row["quote"])

    def qty(self, value: Decimal) -> Decimal:
        rounded = quantize(value, self.base_precision)
        if rounded < self.min_qty or rounded <= 0:
            raise ValueError("Rounded quantity below minimum trade volume")
        if rounded > self.max_market_qty:
            raise ValueError("Quantity exceeds maximum market order volume")
        return rounded


@dataclass
class ExitRung:
    share_pct: Decimal
    r_multiple: Decimal
    quantity: Decimal
    price: Decimal


@dataclass
class TradePlan:
    symbol: str
    side: Literal["LONG", "SHORT"]
    entry: Decimal
    qty: Decimal
    stop_loss: Decimal
    take_profit: Decimal
    risk_usdt: Decimal
    margin_usdt: Decimal
    leverage: int
    confidence: float
    atr: Decimal
    mode: str
    ladder: list[ExitRung] = field(default_factory=list)

    def public(self) -> dict:
        return asdict(self)


@dataclass
class Position:
    id: str
    symbol: str
    side: str
    qty: Decimal
    entry: Decimal
    mark: Decimal
    leverage: int
    margin: Decimal
    unrealized: Decimal
    liquidation_price: Decimal | None
    stop_loss: Decimal | None = None
    take_profit: Decimal | None = None
    best_price: Decimal | None = None
    initial_qty: Decimal | None = None
    initial_risk: Decimal | None = None
    managed: bool = True
    raw: dict = field(default_factory=dict)

    @property
    def roi_pct(self) -> Decimal:
        return self.unrealized / self.margin * 100 if self.margin > 0 else D(0)

    def public(self) -> dict:
        return asdict(self)


class TradeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True, allow_inf_nan=False)
    symbols: list[str] = ["BTCUSDT", "ETHUSDT"]
    timeframes: list[str] = ["1m", "3m", "5m", "15m"]
    scan_interval_sec: float = Field(15, ge=5, le=86400)
    guard_interval_sec: float = Field(15, ge=2, le=3600)
    management_interval_sec: float = Field(15, ge=2, le=3600)
    report_interval_sec: float = Field(30, ge=5, le=86400)
    leverage: int = Field(1, ge=1, le=125)
    max_positions: int = Field(2, ge=1, le=100)
    risk_per_trade_pct: float = Field(0.5, gt=0, le=5)
    max_margin_pct: float = Field(10, gt=0, le=50)
    max_total_risk_pct: float = Field(2, gt=0, le=10)
    max_daily_loss_pct: float = Field(3, gt=0, le=20)
    max_stop_distance_pct: float = Field(5, gt=0, le=20)
    min_agreeing_strategies: int = Field(2, ge=1, le=10)
    min_confidence: float = Field(80, ge=0, le=100)
    tf_min_confidence: float = Field(60, ge=0, le=100)
    min_agreeing_timeframes: int = Field(2, ge=1, le=14)
    tp_mode: Literal["POSITION", "PARTIAL", "TRAILING", "ACCOUNT"] = "POSITION"
    tpsl_method: Literal["ADAPTIVE", "FIXED_R"] = "ADAPTIVE"
    fixed_r: float = Field(2, ge=1, le=10)
    min_reward_risk: float = Field(1.5, ge=1, le=10)
    atr_stop_multiple: float = Field(1.8, ge=0.5, le=10)
    partial_tp_ladder: str = "30@1,40@2"
    trailing_method: Literal["ATR", "RATIO", "INTERVAL"] = "ATR"
    trailing_callback: float = Field(2, gt=0)
    breakeven_threshold_pct: float = Field(3, ge=0, le=1000)
    trailing_trigger_roi_pct: float = Field(5, ge=0, le=1000)
    trailing_stop_pct: float = Field(1, gt=0, lt=100)
    trailing_distance_pct: float = Field(1, gt=0, lt=100)
    liq_sl_distance_pct: float = Field(2, gt=0, lt=100)
    account_tp_usdt: float = Field(0, ge=0)
    account_sl_usdt: float = Field(0, ge=0)
    account_guard_scope: Literal["MANAGED", "ALL"] = "MANAGED"
    universe_rank: Literal["VOLUME", "GAINERS", "LOSERS", "MOVERS"] = "VOLUME"
    min_24h_volume_usd: float = Field(1_000_000, ge=0)
    max_scan_symbols: int = Field(20, ge=1, le=100)
    max_market_data_age_sec: float = Field(45, ge=5, le=300)
    max_spread_bps: float = Field(20, gt=0, le=200)
    max_price_deviation_pct: float = Field(1, gt=0, le=10)
    taker_fee_rate: float = Field(0.0006, ge=0, le=0.02)
    paper_slippage_bps: float = Field(2, ge=0, le=100)
    paper_balance_usdt: float = Field(1000, gt=0)
    reversal_enabled: bool = False
    cooldown_sec: float = Field(60, ge=5, le=86400)
    enabled_strategies: list[str] = ["ema", "rsi", "macd", "volume", "momentum", "atr_breakout", "funding_rate", "supertrend", "bollinger", "ichimoku"]

    @field_validator("symbols")
    @classmethod
    def symbols_valid(cls, values: list[str]) -> list[str]:
        if not values:
            raise ValueError("Use symbols ['*'] for a ranked universe or provide at least one symbol")
        if values == ["*"]:
            return values
        normalized = [v.upper().strip() for v in values]
        if len(set(normalized)) != len(normalized) or any(not re.fullmatch("[A-Z0-9]{3,30}", x) for x in normalized):
            raise ValueError("Symbols must be unique alphanumeric instrument IDs")
        return normalized

    @field_validator("timeframes")
    @classmethod
    def timeframes_valid(cls, values: list[str]) -> list[str]:
        supported = {"1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d", "3d", "1w"}
        if not values or len(set(values)) != len(values) or set(values) - supported:
            raise ValueError("Use unique supported fixed-length timeframes; 1M is not fixed-length and not scanned")
        return values

    @field_validator("partial_tp_ladder")
    @classmethod
    def ladder_valid(cls, value: str) -> str:
        parse_ladder(value)
        return value

    @field_validator("enabled_strategies")
    @classmethod
    def strategies_valid(cls, values: list[str]) -> list[str]:
        allowed = {"ema", "rsi", "macd", "volume", "momentum", "atr_breakout", "funding_rate", "supertrend", "bollinger", "ichimoku"}
        if not values or set(values) - allowed or len(set(values)) != len(values):
            raise ValueError("Unknown or duplicate strategy")
        return values

    @model_validator(mode="after")
    def coherent(self):
        if self.min_agreeing_timeframes > len(self.timeframes):
            raise ValueError("min_agreeing_timeframes exceeds selected timeframes")
        if self.min_agreeing_strategies > len(self.enabled_strategies):
            raise ValueError("min_agreeing_strategies exceeds enabled strategies")
        if self.fixed_r < self.min_reward_risk:
            raise ValueError("fixed_r must be >= min_reward_risk")
        if self.max_total_risk_pct < self.risk_per_trade_pct:
            raise ValueError("Total risk budget must cover at least one trade")
        return self

    @classmethod
    def from_settings(cls, settings: Settings) -> TradeConfig:
        return cls(**{key: getattr(settings, key) for key in cls.model_fields if hasattr(settings, key)})


def parse_ladder(text: str) -> list[tuple[Decimal, Decimal]]:
    result = []
    if not text.strip():
        return result
    for rung in text.split(","):
        try:
            share, multiple = map(decimal, rung.strip().split("@"))
        except (ValueError, ArithmeticError) as exc:
            raise ValueError("Ladder format: 30@1,40@2 (share percent at R multiple)") from exc
        if share <= 0 or share > 100 or multiple <= 0:
            raise ValueError("Ladder shares and R multiples must be positive; shares <=100")
        if result and multiple <= result[-1][1]:
            raise ValueError("Ladder R multiples must increase")
        result.append((share, multiple))
    if sum(share for share, _ in result) > 100:
        raise ValueError("Ladder shares cannot total more than 100%")
    return result
