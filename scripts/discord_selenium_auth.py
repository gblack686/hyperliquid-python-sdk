#!/usr/bin/env python3
"""
Discord Authentication via Selenium

Uses undetected-chromedriver to login to Discord like a real browser,
then extracts the token from localStorage.
"""

import os
import sys
import time
import json
from pathlib import Path

try:
    import undetected_chromedriver as uc
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.keys import Keys
    from selenium import webdriver
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.chrome.service import Service
except ImportError:
    print("Installing required packages...")
    os.system("pip install undetected-chromedriver selenium webdriver-manager")
    import undetected_chromedriver as uc
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.keys import Keys
    from selenium import webdriver
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.chrome.service import Service

ENV_FILE = Path(__file__).parent.parent / ".env"


def save_to_env(token: str, email: str = None, password: str = None):
    """Save token and optionally credentials to .env"""
    other_vars = []

    if ENV_FILE.exists():
        with open(ENV_FILE, 'r') as f:
            for line in f:
                if line.strip() and not line.startswith("DISCORD_"):
                    other_vars.append(line.rstrip())

    with open(ENV_FILE, 'w') as f:
        for line in other_vars:
            f.write(line + "\n")
        f.write(f"DISCORD_TOKEN={token}\n")
        if email:
            f.write(f"DISCORD_EMAIL={email}\n")
        if password:
            f.write(f'DISCORD_PASSWORD={password}\n')

    print(f"Saved to {ENV_FILE}")


def login_and_get_token(email: str, password: str, headless: bool = False) -> str:
    """
    Login to Discord via browser and extract token.

    Args:
        email: Discord email
        password: Discord password
        headless: Run browser in headless mode (invisible)

    Returns:
        Discord token string
    """
    print("Starting browser...")

    options = uc.ChromeOptions()
    if headless:
        options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')

    driver = None
    try:
        # Force version 144 to match installed Chrome
        driver = uc.Chrome(options=options, version_main=144)
        driver.set_window_size(1280, 800)

        print("Navigating to Discord login...")
        driver.get("https://discord.com/login")

        # Wait for login form
        wait = WebDriverWait(driver, 20)

        # Find and fill email - try multiple selectors
        print("Entering email...")
        email_input = None
        selectors = [
            (By.NAME, "email"),
            (By.CSS_SELECTOR, "input[name='email']"),
            (By.CSS_SELECTOR, "input[type='email']"),
            (By.CSS_SELECTOR, "input[aria-label*='email' i]"),
            (By.CSS_SELECTOR, "input[autocomplete='email']"),
            (By.XPATH, "//input[contains(@name, 'email') or contains(@name, 'login')]"),
        ]

        for by, selector in selectors:
            try:
                email_input = wait.until(EC.presence_of_element_located((by, selector)))
                if email_input:
                    print(f"Found email input with: {selector}")
                    break
            except:
                continue

        if not email_input:
            # Last resort - find all inputs and use the first one
            inputs = driver.find_elements(By.TAG_NAME, "input")
            print(f"Found {len(inputs)} input fields")
            for inp in inputs:
                print(f"  - type={inp.get_attribute('type')}, name={inp.get_attribute('name')}")
            if inputs:
                email_input = inputs[0]

        if not email_input:
            print("Could not find email input!")
            driver.save_screenshot("discord_no_email_field.png")
            return None

        # Click and type character by character (React-compatible)
        print("Typing email character by character...")
        email_input.click()
        time.sleep(0.2)
        email_input.clear()
        time.sleep(0.1)

        # Type each character with small delay
        for char in email:
            email_input.send_keys(char)
            time.sleep(0.03)

        print(f"Email typed: {email}")
        time.sleep(0.3)

        # Find password field
        print("Finding password field...")
        password_input = driver.find_element(By.NAME, "password")
        password_input.click()
        time.sleep(0.2)
        password_input.clear()
        time.sleep(0.1)

        # Type password character by character
        print("Typing password...")
        for char in password:
            password_input.send_keys(char)
            time.sleep(0.03)

        print("Password typed")

        # Take screenshot to verify
        time.sleep(0.5)
        driver.save_screenshot("discord_after_fill.png")
        print("Saved screenshot after typing")

        time.sleep(0.5)

        # Click login button
        print("Clicking login...")
        try:
            login_button = driver.find_element(By.XPATH, "//button[@type='submit']")
            login_button.click()
        except Exception as e:
            print(f"Could not find/click submit button: {e}")
            # Try alternative selectors
            try:
                login_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
                login_button.click()
            except:
                # Press Enter in password field
                print("Pressing Enter to submit...")
                password_input.send_keys(Keys.RETURN)

        # Wait for login to complete (URL changes or app loads)
        print("Waiting for login to complete...")

        # Check for various outcomes
        for i in range(60):  # Wait up to 60 seconds
            time.sleep(1)
            current_url = driver.current_url
            page_source = driver.page_source.lower()

            # Check if we're logged in (redirected to app)
            if "/channels/" in current_url or "/app" in current_url:
                print("Login successful!")
                break

            # Check for CAPTCHA (hCaptcha)
            if "hcaptcha" in page_source or "captcha" in page_source:
                print("\nCAPTCHA detected! Please solve it in the browser window...")
                print("Waiting up to 2 minutes for CAPTCHA...")
                for j in range(120):
                    time.sleep(1)
                    if "/channels/" in driver.current_url:
                        print("CAPTCHA solved, login complete!")
                        break
                    # Check if still on login page without captcha
                    if "hcaptcha" not in driver.page_source.lower():
                        print("CAPTCHA seems solved, waiting for redirect...")
                        time.sleep(3)
                break

            # Check for 2FA
            if "two-factor" in page_source or "enter the code" in page_source or "6-digit" in page_source:
                print("\n2FA required! Please enter the code in the browser window...")
                for j in range(60):
                    time.sleep(1)
                    if "/channels/" in driver.current_url:
                        print("2FA completed!")
                        break
                break

            # Check for password reset required
            if "reset your password" in page_source:
                print("\nDiscord requires password reset!")
                return None

            # Check for invalid credentials (be specific)
            if i > 10 and ("login or password is invalid" in page_source or "invalid login" in page_source):
                print("\nLogin failed - invalid credentials")
                return None

            # Check for new location verification
            if "new login location" in page_source or "verify" in page_source:
                print("\nNew location verification required! Check your email and click the link.")
                print("Waiting up to 2 minutes...")
                for j in range(120):
                    time.sleep(1)
                    if "/channels/" in driver.current_url:
                        print("Verification complete!")
                        break

            if i % 10 == 0:
                print(f"Still waiting... ({i}s) URL: {current_url}")
                # Save screenshot for debugging
                if i == 10:
                    try:
                        driver.save_screenshot("discord_login_debug.png")
                        print("Screenshot saved to discord_login_debug.png")
                    except:
                        pass

        # Give it a moment to fully load
        time.sleep(3)

        # Extract token from localStorage
        print("Extracting token...")

        # Method 1: webpackChunk with proper module finding
        token = driver.execute_script("""
            try {
                let m = [];
                webpackChunkdiscord_app.push([
                    [Math.random()],
                    {},
                    (req) => {
                        for (const c of Object.keys(req.c)) {
                            m.push(req.c[c]);
                        }
                    }
                ]);

                for (const mod of m) {
                    try {
                        if (mod?.exports?.default?.getToken) {
                            const token = mod.exports.default.getToken();
                            if (token && typeof token === 'string') {
                                return token;
                            }
                        }
                        if (mod?.exports?.getToken) {
                            const token = mod.exports.getToken();
                            if (token && typeof token === 'string') {
                                return token;
                            }
                        }
                    } catch(e) {}
                }
            } catch (e) {
                console.log('Method 1 failed:', e);
            }
            return null;
        """)

        print(f"Method 1 result: {token}")

        if not token or not isinstance(token, str):
            # Method 2: Direct call
            print("Trying method 2...")
            token = driver.execute_script("""
                try {
                    return (webpackChunkdiscord_app.push([[],{},e=>{m=[];for(let c in e.c)m.push(e.c[c])}]),m)
                        .find(m=>m?.exports?.default?.getToken)?.exports?.default?.getToken() ||
                        (webpackChunkdiscord_app.push([[],{},e=>{m=[];for(let c in e.c)m.push(e.c[c])}]),m)
                        .find(m=>m?.exports?.getToken)?.exports?.getToken();
                } catch(e) { return null; }
            """)
            print(f"Method 2 result: {token}")

        if not token or not isinstance(token, str):
            # Method 3: Iterate all modules looking for token
            print("Trying method 3...")
            token = driver.execute_script("""
                try {
                    const cache = webpackChunkdiscord_app.push([[],{},e=>e]).c;
                    for (const id in cache) {
                        const mod = cache[id];
                        if (mod?.exports?.default?.getToken) {
                            const t = mod.exports.default.getToken();
                            if (typeof t === 'string' && t.length > 50) return t;
                        }
                        if (mod?.exports?.getToken) {
                            const t = mod.exports.getToken();
                            if (typeof t === 'string' && t.length > 50) return t;
                        }
                    }
                } catch(e) {}
                return null;
            """)
            print(f"Method 3 result: {token}")

        if token and isinstance(token, str) and len(token) > 20:
            print(f"Token extracted successfully!")
            return token
        else:
            print("Could not extract token via webpackChunk")
            print(f"Current URL: {driver.current_url}")
            return None

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return None

    finally:
        if driver:
            print("Closing browser...")
            driver.quit()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Discord Selenium Auth")
    parser.add_argument('--email', type=str, help='Discord email')
    parser.add_argument('--password', type=str, help='Discord password')
    parser.add_argument('--headless', action='store_true', help='Run headless (no visible browser)')
    parser.add_argument('--show', action='store_true', help='Show browser window')
    args = parser.parse_args()

    email = args.email or os.getenv('DISCORD_EMAIL')
    password = args.password or os.getenv('DISCORD_PASSWORD')

    if not email:
        email = input("Discord email: ").strip()
    if not password:
        password = input("Discord password: ").strip()

    if not email or not password:
        print("Email and password required")
        sys.exit(1)

    # Default to showing browser (more reliable, can handle CAPTCHA)
    headless = args.headless and not args.show

    token = login_and_get_token(email, password, headless=headless)

    if token:
        save_to_env(token, email, password)
        print(f"\nSuccess! Token saved.")
        print(f"Token: {token[:50]}...")
    else:
        print("\nFailed to get token")
        sys.exit(1)


if __name__ == "__main__":
    main()
