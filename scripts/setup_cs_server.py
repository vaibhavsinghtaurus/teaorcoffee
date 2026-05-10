"""
One-time setup script — run this on the server before starting TeaOrCoffee.

What it does:
  1. Downloads SteamCMD
  2. Uses SteamCMD to download CS 1.6 client assets (App ID 10, free on Steam)
  3. Zips valve/ and cstrike/ into static/assets/valve.zip  (served to browsers)
  4. Downloads HLDS (App ID 90) into hlds/ (the dedicated game server)

Run:
    python scripts/setup_cs_server.py

Requires: Python 3.10+, internet access.
SteamCMD download is ~2 MB; CS assets ~600 MB; HLDS ~350 MB.
"""

import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT       = Path(__file__).resolve().parent.parent   # project root
STATIC_DIR = ROOT / "static" / "assets"
STEAM_DIR  = ROOT / "steamcmd"
CS_DIR     = ROOT / "cs_assets"
HLDS_DIR   = ROOT / "hlds"
ZIP_OUT    = STATIC_DIR / "valve.zip"

IS_WIN = sys.platform == "win32"


def step(msg: str):
    print(f"\n{'='*60}\n  {msg}\n{'='*60}")


def download_steamcmd():
    step("Downloading SteamCMD")
    STEAM_DIR.mkdir(exist_ok=True)

    if IS_WIN:
        url  = "https://steamcdn-a.akamaihd.net/client/installer/steamcmd.zip"
        dest = STEAM_DIR / "steamcmd.zip"
        if not (STEAM_DIR / "steamcmd.exe").exists():
            print(f"Fetching {url}")
            urllib.request.urlretrieve(url, dest)
            with zipfile.ZipFile(dest, "r") as z:
                z.extractall(STEAM_DIR)
            dest.unlink()
        exe = STEAM_DIR / "steamcmd.exe"
    else:
        url  = "https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz"
        dest = STEAM_DIR / "steamcmd_linux.tar.gz"
        if not (STEAM_DIR / "steamcmd.sh").exists():
            print(f"Fetching {url}")
            urllib.request.urlretrieve(url, dest)
            subprocess.run(["tar", "-xzf", str(dest), "-C", str(STEAM_DIR)], check=True)
            dest.unlink()
        exe = STEAM_DIR / "steamcmd.sh"

    print(f"SteamCMD ready at {exe}")
    return exe


def run_steamcmd(exe: Path, install_dir: Path, app_id: str):
    install_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(exe),
        "+login", "anonymous",
        "+force_install_dir", str(install_dir),
        "+app_update", app_id, "validate",
        "+quit",
    ]
    print(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


def build_valve_zip(cs_dir: Path, out: Path):
    step("Building valve.zip for browser")
    out.parent.mkdir(parents=True, exist_ok=True)

    folders = ["valve", "cstrike"]
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for folder in folders:
            src = cs_dir / folder
            if not src.exists():
                print(f"  WARNING: {src} not found, skipping")
                continue
            for fpath in src.rglob("*"):
                if fpath.is_file():
                    arcname = fpath.relative_to(cs_dir)
                    zf.write(fpath, arcname)
                    print(f"  + {arcname}")

    size_mb = out.stat().st_size / 1024 / 1024
    print(f"\nCreated {out} ({size_mb:.1f} MB)")


def main():
    print(__doc__)

    steamcmd_exe = download_steamcmd()

    step("Downloading CS 1.6 client assets (App ID 10)")
    run_steamcmd(steamcmd_exe, CS_DIR, "10")

    step("Downloading HLDS dedicated server (App ID 90)")
    run_steamcmd(steamcmd_exe, HLDS_DIR, "90")

    build_valve_zip(CS_DIR, ZIP_OUT)

    step("Done")
    print(f"""
  Browser assets : {ZIP_OUT}
  Game server    : {HLDS_DIR}

  Start the server via the admin API:
    POST /cs/server/start?password=<ADMIN_PASS>

  Then open the game in any browser:
    http://<your-host>:8000/game/game.html
""")


if __name__ == "__main__":
    main()
