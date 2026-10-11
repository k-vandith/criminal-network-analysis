"""Launch LinkLens with: python run.py."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> None:
    # LinkLens has no authentication or multi-user access controls. Keep the
    # Streamlit listener on loopback so uploads cannot be exposed by accident.
    raise SystemExit(
        subprocess.call(
            [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                str(ROOT / "src" / "app.py"),
                "--server.address",
                "127.0.0.1",
                "--server.port",
                "8501",
                "--server.headless",
                "true",
                "--server.enableCORS",
                "true",
                "--server.enableXsrfProtection",
                "true",
                "--browser.gatherUsageStats",
                "false",
            ],
            cwd=ROOT,
        )
    )


if __name__ == "__main__":
    main()
