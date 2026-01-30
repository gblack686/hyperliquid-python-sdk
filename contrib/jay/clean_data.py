"""
ES Futures Data Cleaning Script
=================================
Cleans and standardizes ES futures data from multiple sources
"""

import pandas as pd
import os
from datetime import datetime
import glob

class ESDataCleaner:
    """Clean and standardize ES futures data"""

    def __init__(self, data_dir='jay/data'):
        self.data_dir = data_dir
        self.cleaned_data = {}

    def clean_csv_files(self):
        """Clean CSV format files (daily data)"""
        print("\n" + "="*60)
        print("CLEANING CSV FILES (Daily Data)")
        print("="*60)

        csv_files = glob.glob(f"{self.data_dir}/*.csv")

        for file_path in csv_files:
            print(f"\nProcessing: {os.path.basename(file_path)}")

            try:
                # Read CSV - first column contains dates
                df = pd.read_csv(file_path, skiprows=[1, 2])  # Skip ticker and "Date" rows

                # First column contains dates, rename it
                df.columns = ['date', 'close', 'high', 'low', 'open', 'volume']

                # Convert date to datetime
                df['date'] = pd.to_datetime(df['date'])
                df = df.set_index('date')

                # Remove any rows with missing data
                initial_rows = len(df)
                df = df.dropna()
                dropped = initial_rows - len(df)

                # Ensure all price columns are numeric
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

                # Validate data integrity
                issues = self.validate_ohlc(df)

                # Store cleaned data
                file_name = os.path.basename(file_path).replace('.csv', '')
                self.cleaned_data[file_name] = df

                print(f"  OK: {len(df)} rows cleaned")
                if dropped > 0:
                    print(f"  WARNING: Dropped {dropped} rows with missing data")
                if issues > 0:
                    print(f"  WARNING: Found {issues} OHLC validation issues")

            except Exception as e:
                print(f"  ERROR: Failed to process {file_path}: {e}")

    def clean_txt_files(self):
        """Clean TXT format files (minute data)"""
        print("\n" + "="*60)
        print("CLEANING TXT FILES (Minute Data)")
        print("="*60)

        txt_files = glob.glob(f"{self.data_dir}/*.txt")

        for file_path in txt_files:
            print(f"\nProcessing: {os.path.basename(file_path)}")

            try:
                # Read TXT file (semicolon-separated)
                df = pd.read_csv(
                    file_path,
                    sep=';',
                    header=None,
                    names=['datetime', 'open', 'high', 'low', 'close', 'volume']
                )

                # Parse datetime (format: YYYYMMDD HHMMSS)
                df['datetime'] = pd.to_datetime(df['datetime'], format='%Y%m%d %H%M%S')
                df = df.set_index('datetime')

                # Remove any rows with missing data
                initial_rows = len(df)
                df = df.dropna()
                dropped = initial_rows - len(df)

                # Ensure all columns are numeric
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

                # Validate data integrity
                issues = self.validate_ohlc(df)

                # Check for gaps in minute data
                gaps = self.check_time_gaps(df)

                # Store cleaned data
                file_name = os.path.basename(file_path).replace('.txt', '')
                self.cleaned_data[file_name] = df

                print(f"  OK: {len(df)} rows cleaned")
                print(f"  Time range: {df.index[0]} to {df.index[-1]}")
                if dropped > 0:
                    print(f"  WARNING: Dropped {dropped} rows with missing data")
                if issues > 0:
                    print(f"  WARNING: Found {issues} OHLC validation issues")
                if gaps > 0:
                    print(f"  INFO: Found {gaps} time gaps (normal for non-trading hours)")

            except Exception as e:
                print(f"  ERROR: Failed to process {file_path}: {e}")

    def validate_ohlc(self, df):
        """Validate OHLC relationships"""
        issues = 0

        # High should be >= Open, Close, Low
        if (df['high'] < df['open']).any():
            issues += (df['high'] < df['open']).sum()
        if (df['high'] < df['close']).any():
            issues += (df['high'] < df['close']).sum()
        if (df['high'] < df['low']).any():
            issues += (df['high'] < df['low']).sum()

        # Low should be <= Open, Close, High
        if (df['low'] > df['open']).any():
            issues += (df['low'] > df['open']).sum()
        if (df['low'] > df['close']).any():
            issues += (df['low'] > df['close']).sum()
        if (df['low'] > df['high']).any():
            issues += (df['low'] > df['high']).sum()

        return issues

    def check_time_gaps(self, df, expected_interval_minutes=1):
        """Check for gaps in time series data"""
        time_diff = df.index.to_series().diff()
        expected_gap = pd.Timedelta(minutes=expected_interval_minutes)

        # Gaps larger than expected (accounting for weekends/non-trading hours)
        large_gaps = time_diff[time_diff > pd.Timedelta(hours=2)]

        return len(large_gaps)

    def merge_minute_data(self):
        """Merge all minute data files into single DataFrame"""
        print("\n" + "="*60)
        print("MERGING MINUTE DATA FILES")
        print("="*60)

        minute_dfs = []

        for name, df in self.cleaned_data.items():
            if 'Last Minute' in name:
                minute_dfs.append(df)

        if minute_dfs:
            merged = pd.concat(minute_dfs)
            merged = merged.sort_index()

            # Remove duplicates (keep first occurrence)
            initial_rows = len(merged)
            merged = merged[~merged.index.duplicated(keep='first')]
            duplicates = initial_rows - len(merged)

            self.cleaned_data['merged_minute_data'] = merged

            print(f"  OK: Merged {len(minute_dfs)} files")
            print(f"  Total rows: {len(merged)}")
            print(f"  Time range: {merged.index[0]} to {merged.index[-1]}")
            if duplicates > 0:
                print(f"  INFO: Removed {duplicates} duplicate timestamps")

            return merged
        else:
            print("  WARNING: No minute data files found to merge")
            return None

    def save_cleaned_data(self, output_dir='jay/data/cleaned'):
        """Save cleaned data to CSV files"""
        print("\n" + "="*60)
        print("SAVING CLEANED DATA")
        print("="*60)

        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

        for name, df in self.cleaned_data.items():
            output_path = f"{output_dir}/{name}_cleaned.csv"

            try:
                df.to_csv(output_path)
                print(f"  OK: Saved {output_path} ({len(df)} rows)")
            except Exception as e:
                print(f"  ERROR: Failed to save {output_path}: {e}")

    def generate_summary_report(self):
        """Generate summary statistics for all cleaned data"""
        print("\n" + "="*60)
        print("DATA SUMMARY REPORT")
        print("="*60)

        for name, df in self.cleaned_data.items():
            print(f"\n{name}")
            print("-" * 40)
            print(f"  Rows: {len(df):,}")
            print(f"  Time range: {df.index[0]} to {df.index[-1]}")

            if len(df) > 0:
                print(f"\n  Price statistics:")
                print(f"    Close min:  ${df['close'].min():,.2f}")
                print(f"    Close max:  ${df['close'].max():,.2f}")
                print(f"    Close mean: ${df['close'].mean():,.2f}")

                print(f"\n  Volume statistics:")
                print(f"    Total volume: {df['volume'].sum():,.0f}")
                print(f"    Avg volume:   {df['volume'].mean():,.0f}")

                # Calculate daily returns for minute data
                if 'minute' in name.lower() or 'last' in name.lower():
                    returns = df['close'].pct_change()
                    print(f"\n  Returns (minute):")
                    print(f"    Mean:   {returns.mean()*100:.4f}%")
                    print(f"    Std:    {returns.std()*100:.4f}%")
                else:
                    returns = df['close'].pct_change()
                    print(f"\n  Returns (daily):")
                    print(f"    Mean:   {returns.mean()*100:.2f}%")
                    print(f"    Std:    {returns.std()*100:.2f}%")

    def run_full_cleaning(self):
        """Run complete data cleaning pipeline"""
        print("\n" + "="*80)
        print("ES FUTURES DATA CLEANING PIPELINE")
        print("="*80)

        # Clean all files
        self.clean_csv_files()
        self.clean_txt_files()

        # Merge minute data
        self.merge_minute_data()

        # Generate report
        self.generate_summary_report()

        # Save cleaned data
        self.save_cleaned_data()

        print("\n" + "="*80)
        print("CLEANING COMPLETE")
        print("="*80)
        print(f"Total datasets cleaned: {len(self.cleaned_data)}")
        print("Cleaned data saved to: jay/data/cleaned/")


def main():
    """Main execution"""
    cleaner = ESDataCleaner()
    cleaner.run_full_cleaning()

    # Return cleaner object for interactive use
    return cleaner


if __name__ == "__main__":
    cleaner = main()
