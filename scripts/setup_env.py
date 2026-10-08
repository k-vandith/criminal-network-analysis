#!/usr/bin/env python3
"""Cross-platform virtualenv bootstrap. Usage: python3 scripts/setup_env.py"""
from __future__ import annotations
import os, platform, shutil, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
VENV = ROOT / ".venv"
REQ = ROOT / "requirements.txt"
IS_WIN = platform.system() == "Windows"

def _run(cmd, **kw):
    print(f"  $ {' '.join(cmd)}")
    return subprocess.run(cmd, check=True, **kw)

def create_venv():
    if VENV.exists():
        print(f"[ok] Virtualenv exists: {VENV}")
        return
    print(f"[..] Creating {VENV}")
    for cmd in [
        [sys.executable, "-m", "venv", str(VENV), "--copies"],
        [sys.executable, "-m", "venv", str(VENV)],
        [sys.executable, "-m", "venv", str(VENV), "--copies", "--without-pip"],
        [sys.executable, "-m", "venv", str(VENV), "--without-pip"],
    ]:
        try:
            _run(cmd)
            print("[ok] venv created")
            return
        except (subprocess.CalledProcessError, OSError) as e:
            if VENV.exists():
                shutil.rmtree(VENV, ignore_errors=True)
            print(f"[warn] {e}")
    raise SystemExit("Could not create venv. Install python3-venv / python3-pip and retry.")

def venv_python():
    return VENV / ("Scripts/python.exe" if IS_WIN else "bin/python")

def ensure_pip(py):
    try:
        _run([str(py), "-m", "pip", "--version"], capture_output=True)
        return
    except Exception:
        pass
    try:
        _run([str(py), "-m", "ensurepip", "--upgrade"])
    except Exception:
        import urllib.request
        gp = ROOT / "scripts" / "_get_pip.py"
        urllib.request.urlretrieve("https://bootstrap.pypa.io/get-pip.py", str(gp))
        _run([str(py), str(gp)])
        gp.unlink(missing_ok=True)

def main():
    os.chdir(ROOT)
    create_venv()
    py = venv_python()
    ensure_pip(py)
    _run([str(py), "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"])
    _run([str(py), "-m", "pip", "install", "-r", str(REQ)])
    print("\nActivate:")
    print(r"  .venv\Scripts\Activate.ps1" if IS_WIN else "  source .venv/bin/activate")
    print("Then: pytest -v")

if __name__ == "__main__":
    main()
