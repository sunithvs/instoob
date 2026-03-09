#!/usr/bin/env python3
"""Get your Instagram session ID for instoob.

How to get it:
1. Open Instagram in your browser and make sure you're logged in
2. Open DevTools (F12) > Application > Cookies > instagram.com
3. Find the cookie named 'sessionid' and copy its value
4. Paste it when this script asks, or add it directly as a GitHub Secret

That's it. No password, no 2FA, no Instaloader.
"""

import sys


def main():
    print("=" * 50)
    print("  Instoob - Instagram Session Setup")
    print("=" * 50)
    print()
    print("Steps:")
    print("  1. Open https://instagram.com in your browser")
    print("  2. Open DevTools (F12 or Cmd+Option+I)")
    print("  3. Go to Application > Cookies > instagram.com")
    print("  4. Find 'sessionid' and copy the value")
    print()

    session_id = input("Paste your sessionid here: ").strip()

    if not session_id:
        print("No session ID provided.")
        sys.exit(1)

    if len(session_id) < 10:
        print("That doesn't look like a valid session ID.")
        sys.exit(1)

    print()
    print("=" * 50)
    print("Add this as a GitHub Secret:")
    print("  Name:  IG_SESSION_ID")
    print(f"  Value: {session_id}")
    print("=" * 50)
    print()
    print("For local testing, add to .env:")
    print(f'  IG_SESSION_ID={session_id}')


if __name__ == "__main__":
    main()
