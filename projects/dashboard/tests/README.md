# MTF Indicators Test Suite

Comprehensive testing suite for all 11 Multi-Timeframe indicators in the Hyperliquid Trading Dashboard.

## Test Structure

```
tests/
├── test_all_indicators.py    # Main comprehensive test suite
├── test_runner.py            # Command-line test runner
├── confluence/               # Confluence engine tests
├── data/                     # Data management tests
├── indicators/               # Individual indicator tests
└── integration/              # Integration tests
```

## Running Tests

### Run All Tests
```bash
python tests/test_runner.py
```

### Run Specific Test Category
```bash
# Run only initialization tests
python tests/test_runner.py --test initialization

# Run only data calculation tests  
python tests/test_runner.py --test data_calculation

# Run only database save tests
python tests/test_runner.py --test database_save

# Run only rate limiting tests
python tests/test_runner.py --test rate_limiting

# Run only error handling tests
python tests/test_runner.py --test error_handling

# Run only integration tests
python tests/test_runner.py --test integration
```

### Save Results to File
```bash
python tests/test_runner.py --output results.json
```

### Verbose Output
```bash
python tests/test_runner.py --verbose
```

## Test Categories

### 1. Initialization Tests
- Verifies all 11 indicators initialize correctly
- Checks that required methods exist
- Validates indicator configuration

### 2. Data Calculation Tests
- Tests each indicator's ability to calculate data
- Validates return data structure
- Tests with multiple symbols (BTC, ETH)

### 3. Database Save Tests
- Verifies indicators can save to Supabase
- Tests database connection
- Validates data persistence

### 4. Rate Limiting Tests
- Ensures rate limiting is properly configured
- Tests rapid API call handling
- Validates throttling behavior

### 5. Error Handling Tests
- Tests behavior with invalid inputs
- Validates graceful error handling
- Tests edge cases

### 6. Integration Tests
- Verifies indicators work together
- Tests MTF aggregator with multiple data sources
- Validates confluence scoring

## Indicators Tested

1. **Open Interest** - Track contract open interest
2. **Funding Rate** - Monitor funding rates
3. **Liquidations** - Track liquidation events
4. **Bollinger Bands** - Volatility bands
5. **VWAP** - Volume Weighted Average Price
6. **ATR** - Average True Range
7. **Order Book** - Market depth analysis
8. **Support/Resistance** - Key price levels
9. **Volume Profile** - Volume distribution (VPVR)
10. **Basis/Premium** - Spot vs perpetual differential
11. **MTF Aggregator** - Multi-timeframe confluence

## Test Results

Results are displayed in the console with:
- ✅ Passed tests
- ❌ Failed tests  
- ⚠️ Warnings (non-critical issues)

Summary statistics include:
- Total tests run
- Pass rate percentage
- Failed test details
- Warning messages

## Environment Requirements

Required environment variables:
```bash
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

## Continuous Integration

The test suite is designed to be run in CI/CD pipelines:

```bash
# Exit code 0 = all tests passed
# Exit code 1 = one or more tests failed
python tests/test_runner.py
```

## Troubleshooting

### Database Connection Issues
If tests fail with database connection errors in test environment:
- Warnings are expected for database tests without live connection
- Focus on calculation and initialization tests
- Database tests will pass in production environment

### Rate Limiting Failures
If rate limiting tests fail:
- Check quantpylib AsyncRateSemaphore configuration
- Verify API rate limits haven't changed
- Ensure proper async/await usage

### Missing Dependencies
```bash
pip install -r requirements.txt
```