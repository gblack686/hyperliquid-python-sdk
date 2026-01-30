# DeFi Overview Command

Get DeFi protocol TVL data from DeFiLlama (completely free, no auth).

## Usage

```bash
cd $REPO_ROOT
python integrations/news/crypto_news_aggregator.py defi
```

JSON output:
```bash
python integrations/news/crypto_news_aggregator.py defi --json
```

## Sample Output

```
Top DeFi Protocols by TVL:
  Binance CEX: $159.33B (CEX)
  Lido: $25.12B (Liquid Staking)
  AAVE: $18.45B (Lending)
  EigenLayer: $12.67B (Restaking)
  Uniswap: $8.92B (DEX)
  MakerDAO: $7.34B (CDP)
  Rocket Pool: $5.21B (Liquid Staking)
  Compound: $4.89B (Lending)
  Curve: $3.45B (DEX)
  Convex: $2.98B (Yield)
```

## Data Fields

- `name`: Protocol name
- `tvl`: Total Value Locked (USD)
- `category`: Protocol type (DEX, Lending, Staking, etc.)
- `chain`: Primary chain or Multi-Chain
- `change_1d`: 24h TVL change %
- `change_7d`: 7d TVL change %
- `url`: Protocol website
- `symbol`: Token symbol (if any)

## JSON Response

```json
{
  "top_protocols": [
    {
      "name": "Binance CEX",
      "tvl": 159327517163.09,
      "chain": "Multi-Chain",
      "category": "CEX",
      "symbol": "-",
      "url": "https://www.binance.com",
      "change_1d": 0.5,
      "change_7d": 2.3
    }
  ],
  "chains": [
    {"name": "Ethereum", "tvl": 89000000000},
    {"name": "Solana", "tvl": 12000000000}
  ]
}
```

## API Endpoints Used

- `https://api.llama.fi/protocols` - All protocols
- `https://api.llama.fi/v2/chains` - Chain TVL data

## Rate Limits

- Completely free, no authentication
- Generous rate limits for public data
