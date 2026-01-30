"""
Test runner for the MTF indicators test suite
Provides a simple command-line interface for running tests
"""

import asyncio
import sys
import argparse
from pathlib import Path
from datetime import datetime
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from test_all_indicators import IndicatorTestSuite


def print_header():
    """Print test runner header"""
    print("\n" + "="*70)
    print(" "*15 + "HYPERLIQUID MTF INDICATORS TEST RUNNER")
    print(" "*20 + f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)


def print_footer(results):
    """Print test runner footer with results"""
    print("\n" + "="*70)
    if results['failed'] == 0:
        print(" "*25 + "✅ ALL TESTS PASSED! ✅")
    else:
        print(" "*25 + f"❌ {results['failed']} TESTS FAILED ❌")
    print(" "*20 + f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)


async def run_tests(args):
    """Run the test suite"""
    print_header()
    
    # Create test suite
    test_suite = IndicatorTestSuite()
    
    # Run selected tests or all tests
    if args.test:
        print(f"\nRunning specific test: {args.test}")
        # Run specific test method
        if hasattr(test_suite, f"test_{args.test}"):
            await getattr(test_suite, f"test_{args.test}")()
            results = test_suite.results.get_summary()
        else:
            print(f"Error: Test '{args.test}' not found")
            print("Available tests:")
            print("  - initialization")
            print("  - data_calculation")
            print("  - database_save")
            print("  - rate_limiting")
            print("  - error_handling")
            print("  - integration")
            sys.exit(1)
    else:
        # Run all tests
        results = await test_suite.run_all_tests()
    
    print_footer(results)
    
    # Save results if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to: {args.output}")
    
    # Return appropriate exit code
    return 0 if results['failed'] == 0 else 1


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Run MTF Indicators Test Suite')
    parser.add_argument(
        '--test', '-t',
        help='Run specific test (e.g., initialization, data_calculation, etc.)',
        default=None
    )
    parser.add_argument(
        '--output', '-o',
        help='Save results to JSON file',
        default=None
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    args = parser.parse_args()
    
    # Run tests
    try:
        exit_code = asyncio.run(run_tests(args))
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nTest run interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nTest runner error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()