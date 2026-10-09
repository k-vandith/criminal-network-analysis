"""Start the CRIMENET workspace.

    python run.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> None:
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(ROOT / "src" / "app.py"),
        "--server.port",
        "8501",
        "--server.headless",
        "true",
    ]
    raise SystemExit(subprocess.call(cmd, cwd=ROOT))


if __name__ == "__main__":
    main()
