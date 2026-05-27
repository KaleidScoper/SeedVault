#!/usr/bin/env python3
"""SeedVault 一键启动调试脚本。

用法:
    python tools/debug.py           # 启动后端 + 前端
    python tools/debug.py --backend # 仅启动后端
    python tools/debug.py --frontend # 仅启动前端
    python tools/debug.py --install # 启动前先安装依赖
"""

import argparse
import os
import signal
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(ROOT, "backend")
FRONTEND_DIR = os.path.join(ROOT, "frontend")

GREEN = "\033[92m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"

procs = []


def log(msg: str, color: str = ""):
    print(f"{color}{msg}{RESET}")


def kill_port(port: int):
    pids = []
    try:
        result = subprocess.run(
            ["lsof", "-t", "-i", f":{port}"], capture_output=True, text=True
        )
        pids = [p for p in result.stdout.strip().split() if p]
    except Exception:
        pass
    # Also try fuser as fallback
    if not pids:
        try:
            result = subprocess.run(
                ["fuser", f"{port}/tcp"], capture_output=True, text=True
            )
            pids = [p for p in result.stdout.strip().split() if p]
        except Exception:
            pass
    for pid in pids:
        try:
            os.kill(int(pid), signal.SIGTERM)
        except Exception:
            pass


def install_deps():
    log("Installing backend dependencies...", BLUE)
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q", "-r", "requirements.txt"],
        cwd=BACKEND_DIR,
        check=True,
    )
    log("Installing frontend dependencies...", BLUE)
    subprocess.run(["npm", "install"], cwd=FRONTEND_DIR, check=True)
    log("Dependencies installed.", GREEN)


def start_backend():
    log("Starting backend on http://localhost:8000 ...", BLUE)
    kill_port(8000)
    time.sleep(0.5)
    p = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn", "app.main:app",
            "--host", "0.0.0.0", "--port", "8000",
        ],
        cwd=BACKEND_DIR,
    )
    procs.append(("Backend", p))
    time.sleep(2)
    log("  Backend  ready: http://localhost:8000", GREEN)
    log("  API docs ready: http://localhost:8000/docs", GREEN)


def start_frontend():
    log("Starting frontend on http://localhost:5173 ...", BLUE)
    kill_port(5173)
    time.sleep(0.5)
    p = subprocess.Popen(
        ["npx", "vite", "--host", "0.0.0.0"],
        cwd=FRONTEND_DIR,
    )
    procs.append(("Frontend", p))
    time.sleep(2)
    log("  Frontend ready: http://localhost:5173", GREEN)


def print_info():
    print()
    log("=" * 60, BOLD)
    log("  SeedVault 调试环境已就绪", BOLD + GREEN)
    log("=" * 60, BOLD)
    print()
    log("  前端:          http://localhost:5173", BLUE)
    log("  后端 API:      http://localhost:8000/api/v1", BLUE)
    log("  API 文档:      http://localhost:8000/docs", BLUE)
    log("  开发登录:      http://localhost:5173/login", BLUE)
    print()
    log("  开发登录用户 (选择任意一个):", YELLOW)
    log("    1  Kaleid_5coper  (Admin, Java 正版)", YELLOW)
    log("    2  方块猎人        (Player, Java 正版)", YELLOW)
    log("    3  建筑大师        (Player, 未绑 MC)", YELLOW)
    log("    4  速通玩家        (Player, Java 正版)", YELLOW)
    print()
    log("  Ctrl+C 停止所有服务", RESET)
    log("=" * 60, BOLD)
    print()


def cleanup():
    print()
    log("正在停止服务...", YELLOW)
    for name, p in procs:
        try:
            p.terminate()
            p.wait(timeout=5)
            log(f"  {name} 已停止", GREEN)
        except subprocess.TimeoutExpired:
            p.kill()
            log(f"  {name} 已强制终止", RED)
    kill_port(8000)
    kill_port(5173)
    log("所有服务已停止。", GREEN)


def main():
    parser = argparse.ArgumentParser(description="SeedVault 一键调试启动")
    parser.add_argument("--backend", action="store_true", help="仅启动后端")
    parser.add_argument("--frontend", action="store_true", help="仅启动前端")
    parser.add_argument("--install", action="store_true", help="启动前安装依赖")
    args = parser.parse_args()

    both = not args.backend and not args.frontend

    signal.signal(signal.SIGINT, lambda *_: cleanup() or sys.exit(0))
    signal.signal(signal.SIGTERM, lambda *_: cleanup() or sys.exit(0))

    if args.install:
        install_deps()

    try:
        if both or args.backend:
            start_backend()
        if both or args.frontend:
            start_frontend()
        print_info()

        while True:
            time.sleep(1)
            for name, p in procs:
                if p.poll() is not None:
                    log(f"{name} 异常退出 (code={p.returncode})", RED)
                    return
    except KeyboardInterrupt:
        pass
    finally:
        cleanup()


if __name__ == "__main__":
    main()
