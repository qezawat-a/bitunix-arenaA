# Get Trading Pairs

Source: https://www.bitunix.com/api-docs/futures/market/get_trading_pairs.html

Retrieved: 2026-10-01 UTC. Table transcription, navigation removed.

Rate Limit: 10 req/sec/ip

## Description

Get future trading pair details

## HTTP Request

- GET /api/v1/futures/market/trading_pairs

## Request Parameters

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| symbols | string | false | Trading pairs, based on symbolName, i.e. BTCUSDT,ETHUSDT,XRPUSDT |

## Request example (query parameters or body)

```json
{
  "symbols": "BTCUSDT,ETHUSDT"
}
```

## Response Parameters

| Parameter | Type | Description |
| --- | --- | --- |
| symbol | string | Coin pair name i.e. BTCUSDT |
| base | string | Base currency; ETH in ETHUSDT |
| quote | string | Base currency (source wording); USDT in ETHUSDT |
| minTradeVolume | string | Minimum opening amount (base currency) |
| minBuyPriceOffset | string | Minimum price offset for buy orders |
| maxSellPriceOffset | string | Maximum price offset for sell orders |
| maxLimitOrderVolume | string | Maximum limit order base amount |
| maxMarketOrderVolume | string | Maximum market order base amount |
| basePrecision | int | Max precision of opening amount |
| quotePrecision | int | Max precision of order price |
| maxLeverage | int | Max leverage |
| minLeverage | int | Min leverage |
| defaultLeverage | int | Default leverage |
| defaultMarginMode | string | Default margin mode Isolation or Cross |
| priceProtectScope | string | Price protection scope. Mark 10000, scope 0.02: minimum sell 10000*(1-0.02)=9800; maximum buy 10000*(1+0.02)=10200. |
| symbolStatus | string | OPEN: trading normal; CANCEL_ONLY: cancel only; STOP: cannot open/close |
| isApiSupported | bool | true: API trading enabled; false: disabled |
| maxFundingRate | decimal | Max current funding rate |
| minFundingRate | decimal | Min current funding rate |
| launchTime | long | Contract launch time. Unix milliseconds UTC. null if not configured. |
| delistTime | long | Scheduled delisting time. Unix milliseconds UTC. Omitted if not configured or cleared. |

## Response Example

```json
{
  "code": 0,
  "data": [
    {
      "symbol": "BTCUSDT",
      "base": "BTC",
      "quote": "USDT",
      "minTradeVolume": "0.0001",
      "minBuyPriceOffset": "-0.95",
      "maxSellPriceOffset": "100",
      "maxLimitOrderVolume": "100000",
      "maxMarketOrderVolume": "50000",
      "basePrecision": 4,
      "quotePrecision": 1,
      "minLeverage": 1,
      "maxLeverage": 125,
      "defaultLeverage": 20,
      "defaultMarginMode": 1,
      "priceProtectScope": "0.02",
      "symbolStatus": "OPEN",
      "isApiSupported": true,
      "maxFundingRate": "0.3",
      "minFundingRate": "-0.3"
    }
  ],
  "msg": "Success"
}
```

## Upstream inconsistencies / implementation notes

defaultMarginMode example is numeric 1, but table lists string values. Engine explicitly sets ISOLATION rather than assuming defaults.
