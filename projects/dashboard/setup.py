#!/usr/bin/env python
import os
import sys
import subprocess
from pathlib import Path

def setup_project():
    print("🚀 Setting up Hyperliquid Trading Dashboard...")
    
    # Create virtual environment
    print("\n📦 Creating virtual environment...")
    subprocess.run([sys.executable, "-m", "venv", "venv"])
    
    # Determine pip path based on OS
    if sys.platform == "win32":
        pip_path = Path("venv/Scripts/pip")
        python_path = Path("venv/Scripts/python")
    else:
        pip_path = Path("venv/bin/pip")
        python_path = Path("venv/bin/python")
    
    # Upgrade pip
    print("\n⬆️ Upgrading pip...")
    subprocess.run([str(python_path), "-m", "pip", "install", "--upgrade", "pip"])
    
    # Install requirements
    print("\n📚 Installing dependencies...")
    subprocess.run([str(pip_path), "install", "-r", "requirements.txt"])
    
    # Create .env file if it doesn't exist
    if not Path(".env").exists():
        print("\n🔑 Creating .env file...")
        with open(".env", "w") as f:
            f.write("""# Supabase Configuration
SUPABASE_URL=your_supabase_url_here
SUPABASE_KEY=your_supabase_anon_key_here

# Hyperliquid Configuration (Optional - for authenticated endpoints)
HYPERLIQUID_API_KEY=
HYPERLIQUID_SECRET=

# Application Settings
APP_ENV=development
LOG_LEVEL=INFO
WEBSOCKET_RECONNECT_INTERVAL=5
MAX_RECONNECT_ATTEMPTS=10

# Trading Settings
DEFAULT_SYMBOL=BTC
DEFAULT_TIMEFRAME=15m
""")
        print("✅ .env file created. Please update it with your credentials.")
    
    print("\n✨ Setup complete!")
    print("\n📝 Next steps:")
    print("1. Update the .env file with your Supabase and Hyperliquid credentials")
    print("2. Activate the virtual environment:")
    if sys.platform == "win32":
        print("   venv\\Scripts\\activate")
    else:
        print("   source venv/bin/activate")
    print("3. Run the dashboard:")
    print("   streamlit run app.py")

if __name__ == "__main__":
    setup_project()