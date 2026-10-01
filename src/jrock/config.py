from __future__ import annotations

from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore", allow_inf_nan=False)

    telegram_bot_token: SecretStr = SecretStr("")
    telegram_allowed_user_ids: list[int] = []
    ai_base_url: str = ""
    ai_api_key: SecretStr = SecretStr("")
    ai_models_path: str = "/models"
    ai_chat_path: str = "/chat/completions"
    ai_extra_body: dict = {}
    ai_discovery_max_models: int = Field(100, ge=1, le=1000)
    ai_probe_concurrency: int = Field(3, ge=1, le=10)
    ai_max_tool_rounds: int = Field(8, ge=1, le=30)
    bitunix_base_url: str = "https://fapi.bitunix.com"
    bitunix_api_key: SecretStr = SecretStr("")
    bitunix_api_secret: SecretStr = SecretStr("")
    trading_mode: Literal["paper", "live"] = "paper"
    live_trading_enabled: bool = False
    allow_host_terminal: bool = False
    allow_raw_exchange_mutations: bool = False
    workspace_dir: Path = Path("workspace")
    data_dir: Path = Path("data")
    auto_approve_on_edit: bool = False
    learning_enabled: bool = False
    dashboard_token: SecretStr = SecretStr("")
    search_url: str = ""
    search_api_key: SecretStr = SecretStr("")
    image_model: str = ""
    tts_model: str = ""
    tts_voice: str = ""
    video_connector: str = ""

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
    min_agreeing_timeframes: int = Field(2, ge=1, le=14)
    fixed_r: float = Field(2, ge=1, le=10)
    min_reward_risk: float = Field(1.5, ge=1, le=10)
    atr_stop_multiple: float = Field(1.8, ge=0.5, le=10)
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
    min_agreeing_strategies: int = Field(2, ge=1, le=10)
    min_confidence: float = Field(80, ge=0, le=100)
    tf_min_confidence: float = Field(60, ge=0, le=100)
    tp_mode: Literal["POSITION", "PARTIAL", "TRAILING", "ACCOUNT"] = "POSITION"
    tpsl_method: Literal["ADAPTIVE", "FIXED_R"] = "ADAPTIVE"
    partial_tp_ladder: str = "30@1,40@2"
    trailing_method: Literal["ATR", "RATIO", "INTERVAL"] = "ATR"
    trailing_callback: float = Field(2, gt=0)
    breakeven_threshold_pct: float = Field(3, ge=0)
    trailing_trigger_roi_pct: float = Field(5, ge=0)
    trailing_stop_pct: float = Field(1, gt=0, lt=100)
    trailing_distance_pct: float = Field(1, gt=0, lt=100)
    liq_sl_distance_pct: float = Field(2, gt=0, lt=100)
    account_tp_usdt: float = Field(0, ge=0)
    account_sl_usdt: float = Field(0, ge=0)
    account_guard_scope: Literal["MANAGED", "ALL"] = "MANAGED"
    universe_rank: Literal["VOLUME", "GAINERS", "LOSERS", "MOVERS"] = "VOLUME"
    min_24h_volume_usd: float = Field(1_000_000, ge=0)

    @field_validator("ai_base_url", "bitunix_base_url", "search_url")
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        if value:
            parsed = urlparse(value)
            if parsed.scheme not in {"https", "http"} or not parsed.hostname:
                raise ValueError("Expected an absolute http(s) URL")
            if parsed.username or parsed.password or parsed.query or parsed.fragment:
                raise ValueError("Base URLs cannot contain credentials, query strings or fragments")
            if parsed.scheme != "https" and parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
                raise ValueError("Remote API credentials require HTTPS")
        return value.rstrip("/")

    @field_validator("ai_models_path", "ai_chat_path")
    @classmethod
    def validate_api_path(cls, value: str) -> str:
        if not value.startswith("/") or "://" in value or value.startswith("//") or ".." in value:
            raise ValueError("API paths must be relative to the configured base URL")
        return value

    @field_validator("ai_extra_body")
    @classmethod
    def reserved_fields(cls, value: dict) -> dict:
        if set(value) & {"model", "messages", "tools", "tool_choice", "stream"}:
            raise ValueError("AI_EXTRA_BODY cannot override model, messages, tools or streaming")
        return value

    def initialize_directories(self) -> None:
        for path in (self.workspace_dir, self.data_dir):
            path.mkdir(parents=True, exist_ok=True, mode=0o700)
            path.chmod(0o700)

    def public_dict(self) -> dict:
        """Whitelist fields: never leak keys, tokens or arbitrary provider extra-body values."""
        exclude = {
            "telegram_bot_token", "telegram_allowed_user_ids", "ai_api_key", "bitunix_api_key",
            "bitunix_api_secret", "dashboard_token", "search_api_key", "ai_extra_body",
        }
        return self.model_dump(mode="json", exclude=exclude)
