# Insecure Integrated Components Lab Solution

## Overview
This lab is solved by exploiting an `IDOR` issue in the chatbot history endpoint:

- Authenticated users can request `GET /query/<id>`
- Conversation IDs are predictable integers
- The endpoint returns other users' chatbot conversations instead of enforcing ownership checks

By enumerating query IDs and searching responses for `HTB{...}`, we can recover the flag.

## Vulnerability Identified
The vulnerable component is the integrated web application's query retrieval route:

- Endpoint pattern: `/query/<id>`
- Weakness: missing or broken authorization checks on object access
- Impact: cross-user data disclosure (chat history and sensitive content)

## Exploitation Approach
The solver automates the following flow:

1. Register a random user via `POST /register`
2. Log in via `POST /login` to get a valid session cookie
3. Enumerate conversation IDs from `1..N` against `GET /query/<id>`
4. Scan each response body for a flag regex: `HTB\{[^}]+\}`
5. Print and stop on first match

## Solver Script
File:

- `insecure_integrated_components_solver.py`

Main logic:

- `register_and_login(...)` creates/authenticates a fresh user
- Loop over `query_id` in a configurable range (`--max-id`)
- `try_extract_flag(...)` applies regex search to each response

## Run Instructions
Use the required virtual environment:

```bash
source ~/htb/venv/bin/activate
python3 insecure_integrated_components_solver.py \
  --base-url http://154.57.164.64:31128 \
  --max-id 120
```

## Result
The script successfully returned the lab flag from a leaked query record.

Example output:

```text
[+] Flag found in query/3: HTB{ade4fa4767f947f62d540e39d2610ed5}
```

## Why This Works
The application trusts that knowing a query ID implies authorization. Since IDs are sequential and guessable, an attacker with any valid session can iterate IDs and access objects belonging to other users.

## Mitigation Notes
To prevent this class of issue:

- Enforce object-level authorization on every `/query/<id>` request
- Scope database queries by both `query_id` and `current_user_id`
- Use non-enumerable object identifiers only as defense-in-depth (not as primary auth)
- Add audit logging and detection for query ID enumeration behavior
