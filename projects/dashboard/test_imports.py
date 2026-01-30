#!/usr/bin/env python
"""Test all imports to identify missing dependencies."""

import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'quantpylib'))

def test_imports():
    """Test all imports and report missing modules."""
    
    missing_modules = []
    successful_imports = []
    
    # List of imports to test
    imports_to_test = [
        ("streamlit", "streamlit"),
        ("asyncio", "asyncio"),
        ("pandas", "pandas"),
        ("plotly.graph_objects", "plotly"),
        ("plotly", "plotly"),
        ("loguru", "loguru"),
        ("msgpack", "msgpack"),
        ("orjson", "orjson"),
        ("numba", "numba"),
        ("matplotlib.pyplot", "matplotlib"),
        ("scipy", "scipy"),
        ("web3", "web3"),
        ("websockets", "websockets"),
        ("aiohttp", "aiohttp"),
        ("eth_utils", "eth_utils"),
        ("eth_account", "eth_account"),
        ("ta", "ta"),
        ("pandas_ta", "pandas_ta"),
        ("sklearn", "scikit-learn"),
        ("supabase", "supabase"),
        ("dotenv", "python-dotenv"),
        ("pydantic", "pydantic"),
        ("pytest", "pytest"),
        ("psycopg2", "psycopg2"),
        ("sqlalchemy", "sqlalchemy"),
        ("bs4", "beautifulsoup4"),
        ("lxml", "lxml"),
        ("seaborn", "seaborn"),
        ("statsmodels", "statsmodels"),
        ("httpx", "httpx"),
        ("starknet_py", "starknet_py"),
        ("yaml", "yaml"),
        ("dill", "dill"),
    ]
    
    print("Testing imports...")
    print("=" * 50)
    
    for import_name, package_name in imports_to_test:
        try:
            if '.' in import_name:
                __import__(import_name)
            else:
                __import__(import_name)
            successful_imports.append(import_name)
            print(f"[OK] {import_name}")
        except (ImportError, AttributeError) as e:
            missing_modules.append((import_name, package_name, str(e)))
            print(f"[MISSING] {import_name}: {e}")
    
    # Now test quantpylib specific imports
    print("\n" + "=" * 50)
    print("Testing quantpylib imports...")
    print("=" * 50)
    
    quantpylib_imports = [
        "quantpylib.wrappers.hyperliquid",
        "quantpylib.standards",
        "quantpylib.hft.lob",
        "quantpylib.utilities.general",
        "quantpylib.utilities.numba",
    ]
    
    for import_name in quantpylib_imports:
        try:
            __import__(import_name)
            successful_imports.append(import_name)
            print(f"[OK] {import_name}")
        except (ImportError, AttributeError) as e:
            missing_modules.append((import_name, import_name, str(e)))
            print(f"[MISSING] {import_name}: {e}")
    
    # Summary
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    print(f"Successful imports: {len(successful_imports)}")
    print(f"Failed imports: {len(missing_modules)}")
    
    if missing_modules:
        print("\nMissing packages to install:")
        print("-" * 30)
        
        # Create unique list of packages to install
        packages_to_install = set()
        for _, package_name, _ in missing_modules:
            if package_name and package_name != import_name:
                packages_to_install.add(package_name)
        
        if packages_to_install:
            print("Run this command to install missing packages:")
            print(f"\npip install {' '.join(sorted(packages_to_install))}")
    else:
        print("\n[SUCCESS] All imports successful! The app should run without import errors.")
    
    return len(missing_modules) == 0

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)