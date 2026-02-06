#!/usr/bin/env python3
"""
Discord Token Refresh Utility

Prompts for a new Discord token and saves it to .env file.
Also validates the token by making a test API call.
"""

import os
import sys
import asyncio
import aiohttp
from pathlib import Path

# Find .env file
ENV_FILE = Path(__file__).parent.parent / ".env"


def get_current_token():
    """Get current token from environment or .env file"""
    token = os.getenv('DISCORD_TOKEN')
    if token:
        return token

    if ENV_FILE.exists():
        with open(ENV_FILE, 'r') as f:
            for line in f:
                if line.startswith('DISCORD_TOKEN='):
                    return line.split('=', 1)[1].strip().strip('"\'')
    return None


async def validate_token(token: str) -> bool:
    """Validate token by fetching user info"""
    headers = {
        "Authorization": token,
        "Content-Type": "application/json",
    }

    async with aiohttp.ClientSession() as session:
        async with session.get("https://discord.com/api/v9/users/@me", headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                print(f"Token valid! Logged in as: {data.get('username')}#{data.get('discriminator')}")
                return True
            elif resp.status == 401:
                print("Token invalid or expired")
                return False
            else:
                print(f"Unexpected response: {resp.status}")
                return False


def save_token(token: str):
    """Save token to .env file"""
    lines = []
    token_found = False

    if ENV_FILE.exists():
        with open(ENV_FILE, 'r') as f:
            lines = f.readlines()

        # Update existing token
        for i, line in enumerate(lines):
            if line.startswith('DISCORD_TOKEN='):
                lines[i] = f'DISCORD_TOKEN={token}\n'
                token_found = True
                break

    if not token_found:
        lines.append(f'DISCORD_TOKEN={token}\n')

    with open(ENV_FILE, 'w') as f:
        f.writelines(lines)

    print(f"Token saved to {ENV_FILE}")


def print_instructions():
    """Print instructions for getting a new token"""
    print("""
================================================================================
                         DISCORD TOKEN REFRESH
================================================================================

To get a new Discord token:

1. Open Discord in your browser: https://discord.com/app

2. Press F12 to open Developer Tools

3. Go to the Console tab

4. Paste this code and press Enter:

   (webpackChunkdiscord_app.push([[],{},e=>{m=[];for(let c in e.c)m.push(e.c[c])}]),m).find(m=>m?.exports?.default?.getToken).exports.default.getToken()

5. Copy the token that appears (without the quotes)

================================================================================
""")


async def main():
    print_instructions()

    # Show current token status
    current = get_current_token()
    if current:
        print(f"Current token: {current[:20]}...")
        print("Validating current token...")
        if await validate_token(current):
            print("\nCurrent token is still valid!")
            response = input("\nDo you want to update it anyway? (y/N): ").strip().lower()
            if response != 'y':
                print("Keeping current token.")
                return
        else:
            print("\nCurrent token is expired. Please enter a new one.")
    else:
        print("No token currently configured.")

    # Get new token
    print()
    new_token = input("Paste your new Discord token: ").strip()

    if not new_token:
        print("No token provided. Exiting.")
        return

    # Remove quotes if present
    new_token = new_token.strip('"\'')

    # Validate new token
    print("\nValidating new token...")
    if await validate_token(new_token):
        save_token(new_token)
        print("\nDone! Your Discord token has been updated.")
        print("You can now run the signal feed scripts.")
    else:
        print("\nThe token you provided is not valid.")
        print("Please try again with a fresh token from Discord.")


if __name__ == "__main__":
    asyncio.run(main())
