#!/usr/bin/env python3
"""
Discord Authentication Utility

Logs into Discord programmatically to fetch a fresh token.
Supports 2FA (TOTP) if enabled on the account.

WARNING: This is against Discord's ToS. Use at your own risk.
Store credentials securely (use environment variables or AWS Secrets).
"""

import os
import sys
import asyncio
import aiohttp
import getpass
from pathlib import Path

try:
    from dotenv import load_dotenv, set_key
    load_dotenv()
    HAS_DOTENV = True
except ImportError:
    HAS_DOTENV = False

# File paths
ENV_FILE = Path(__file__).parent.parent / ".env"

# Discord API
DISCORD_API = "https://discord.com/api/v9"
LOGIN_URL = f"{DISCORD_API}/auth/login"
MFA_URL = f"{DISCORD_API}/auth/mfa/totp"
USER_URL = f"{DISCORD_API}/users/@me"

# Headers to mimic browser
HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "X-Super-Properties": "eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiQ2hyb21lIiwiZGV2aWNlIjoiIiwic3lzdGVtX2xvY2FsZSI6ImVuLVVTIiwiYnJvd3Nlcl91c2VyX2FnZW50IjoiTW96aWxsYS81LjAgKFdpbmRvd3MgTlQgMTAuMDsgV2luNjQ7IHg2NCkgQXBwbGVXZWJLaXQvNTM3LjM2IChLSFRNTCwgbGlrZSBHZWNrbykgQ2hyb21lLzEyMC4wLjAuMCBTYWZhcmkvNTM3LjM2IiwiYnJvd3Nlcl92ZXJzaW9uIjoiMTIwLjAuMC4wIiwib3NfdmVyc2lvbiI6IjEwIiwicmVmZXJyZXIiOiIiLCJyZWZlcnJpbmdfZG9tYWluIjoiIiwicmVmZXJyZXJfY3VycmVudCI6IiIsInJlZmVycmluZ19kb21haW5fY3VycmVudCI6IiIsInJlbGVhc2VfY2hhbm5lbCI6InN0YWJsZSIsImNsaWVudF9idWlsZF9udW1iZXIiOjI1NTkyMSwiY2xpZW50X2V2ZW50X3NvdXJjZSI6bnVsbH0=",
}


async def login(email: str, password: str) -> dict:
    """
    Login to Discord and return response.

    Returns:
        {"token": "..."} on success
        {"mfa": True, "ticket": "..."} if 2FA required
        {"captcha_key": [...]} if captcha required
        {"message": "...", "code": ...} on error
    """
    async with aiohttp.ClientSession() as session:
        payload = {
            "login": email,
            "password": password,
            "undelete": False,
            "login_source": None,
            "gift_code_sku_id": None,
        }

        async with session.post(LOGIN_URL, json=payload, headers=HEADERS) as resp:
            return await resp.json()


async def submit_2fa(ticket: str, code: str) -> dict:
    """Submit 2FA code and return token"""
    async with aiohttp.ClientSession() as session:
        payload = {
            "code": code,
            "ticket": ticket,
            "login_source": None,
            "gift_code_sku_id": None,
        }

        async with session.post(MFA_URL, json=payload, headers=HEADERS) as resp:
            return await resp.json()


async def validate_token(token: str) -> dict:
    """Validate token and return user info"""
    headers = {**HEADERS, "Authorization": token}

    async with aiohttp.ClientSession() as session:
        async with session.get(USER_URL, headers=headers) as resp:
            if resp.status == 200:
                return await resp.json()
            return None


def save_token(token: str):
    """Save token to .env file"""
    if HAS_DOTENV:
        set_key(str(ENV_FILE), "DISCORD_TOKEN", token)
        print(f"Token saved to {ENV_FILE}")
    else:
        # Manual save
        lines = []
        token_found = False

        if ENV_FILE.exists():
            with open(ENV_FILE, 'r') as f:
                lines = f.readlines()

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


def save_credentials(email: str, password: str):
    """Optionally save credentials to .env for auto-refresh"""
    response = input("\nSave credentials for auto-refresh? (y/N): ").strip().lower()
    if response == 'y':
        if HAS_DOTENV:
            set_key(str(ENV_FILE), "DISCORD_EMAIL", email)
            set_key(str(ENV_FILE), "DISCORD_PASSWORD", password)
        else:
            with open(ENV_FILE, 'a') as f:
                f.write(f'DISCORD_EMAIL={email}\n')
                f.write(f'DISCORD_PASSWORD={password}\n')
        print("Credentials saved. Token will auto-refresh when expired.")
        print("WARNING: Credentials are stored in plaintext. Consider using AWS Secrets Manager.")


async def auto_refresh() -> str:
    """Auto-refresh token using stored credentials"""
    email = os.getenv('DISCORD_EMAIL')
    password = os.getenv('DISCORD_PASSWORD')

    if not email or not password:
        return None

    print("Auto-refreshing token with stored credentials...")
    result = await login(email, password)

    if 'token' in result:
        save_token(result['token'])
        return result['token']
    elif result.get('mfa'):
        print("2FA required - cannot auto-refresh without TOTP code")
        return None
    else:
        print(f"Auto-refresh failed: {result.get('message', 'Unknown error')}")
        return None


def get_password(prompt="Password: "):
    """Get password - try getpass first, fall back to regular input on Windows"""
    try:
        # Try getpass first
        import msvcrt
        return getpass.getpass(prompt)
    except Exception:
        pass

    # Fallback to regular input (password will be visible)
    print("(Note: password will be visible as you type)")
    return input(prompt).strip()


async def interactive_login(email_arg=None, password_arg=None):
    """Interactive login flow"""
    print("""
================================================================================
                      DISCORD LOGIN (Token Refresh)
================================================================================
    """)

    # Use arguments if provided
    if email_arg and password_arg:
        email = email_arg
        password = password_arg
    else:
        # Check for stored credentials
        stored_email = os.getenv('DISCORD_EMAIL')
        if stored_email:
            print(f"Found stored email: {stored_email}")
            use_stored = input("Use stored credentials? (Y/n): ").strip().lower()
            if use_stored != 'n':
                email = stored_email
                password = os.getenv('DISCORD_PASSWORD', '')
                if not password:
                    password = get_password("Password: ")
            else:
                email = input("Email: ").strip()
                password = get_password("Password: ")
        else:
            email = input("Email: ").strip()
            password = get_password("Password: ")

    if not email or not password:
        print("Email and password required.")
        return

    print("\nLogging in...")
    result = await login(email, password)

    # Handle response
    if 'token' in result:
        # Success - no 2FA
        token = result['token']
        user = await validate_token(token)
        if user:
            print(f"\nSuccess! Logged in as: {user.get('username')}#{user.get('discriminator')}")
            save_token(token)
            save_credentials(email, password)
        else:
            print("Got token but validation failed. Token may be invalid.")

    elif result.get('mfa'):
        # 2FA required
        print("\n2FA is enabled on this account.")
        ticket = result['ticket']

        code = input("Enter 2FA code from your authenticator: ").strip()
        if not code:
            print("2FA code required.")
            return

        mfa_result = await submit_2fa(ticket, code)

        if 'token' in mfa_result:
            token = mfa_result['token']
            user = await validate_token(token)
            if user:
                print(f"\nSuccess! Logged in as: {user.get('username')}#{user.get('discriminator')}")
                save_token(token)
                # Don't save credentials if 2FA - can't auto-refresh anyway
                print("\nNote: Auto-refresh is not available with 2FA enabled.")
            else:
                print("Got token but validation failed.")
        else:
            print(f"\n2FA failed: {mfa_result.get('message', 'Invalid code')}")

    elif result.get('captcha_key'):
        # Captcha required
        print("\nCaptcha required. Discord is blocking automated login.")
        print("Please use the browser method instead:")
        print("  python scripts/discord_token_refresh.py")

    elif result.get('code') == 50035:
        # Invalid login
        print(f"\nLogin failed: Invalid email or password")

    else:
        # Other error
        print(f"\nLogin failed: {result.get('message', 'Unknown error')}")
        if 'errors' in result:
            print(f"Details: {result['errors']}")


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Discord Authentication")
    parser.add_argument('--auto', action='store_true', help='Auto-refresh using stored credentials')
    parser.add_argument('--email', type=str, help='Discord email')
    parser.add_argument('--password', type=str, help='Discord password')
    args = parser.parse_args()

    if args.auto:
        token = await auto_refresh()
        if token:
            print(f"Token refreshed: {token[:25]}...")
            sys.exit(0)
        else:
            print("Auto-refresh failed. Running interactive login...")

    await interactive_login(args.email, args.password)


if __name__ == "__main__":
    asyncio.run(main())
