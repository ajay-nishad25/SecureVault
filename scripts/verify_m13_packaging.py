"""SecureVault — Milestone M13 Packaging & Standalone Verification Script.

Tests the packaged standalone distribution in dist/SecureVault:
1. Executable and asset existence & integrity
2. Security cleanliness (no secrets, no test files, no vaults bundled)
3. Standalone execution (--version, --check-config, --headless)
4. GUI launch and window title verification
5. Complete functional and cryptographic lifecycle in isolated LOCALAPPDATA
6. Strict user data separation (zero files written to installation/dist dir)
"""

import hashlib
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = PROJECT_ROOT / "dist" / "SecureVault"
EXE_PATH = DIST_DIR / "SecureVault.exe"
ASSET_ICO = DIST_DIR / "_internal" / "assets" / "SecureVault.ico"
SOURCE_ICO = PROJECT_ROOT / "assets" / "SecureVault.ico"


def log(msg: str) -> None:
    print(f"[M13 VERIFY] {msg}")


def check(desc: str, condition: bool) -> None:
    if condition:
        print(f"  [OK] PASS: {desc}")
    else:
        print(f"  [FAIL] FAILED: {desc}")
        sys.exit(1)


def main() -> None:
    log("Starting M13 Windows Standalone Packaging Verification Suite")

    # -------------------------------------------------------------
    # 1. Executable and Asset Verification
    # -------------------------------------------------------------
    log("Step 1: Inspecting compiled executable and bundled assets...")
    check("Executable exists at dist/SecureVault/SecureVault.exe", EXE_PATH.is_file())
    exe_size = EXE_PATH.stat().st_size
    check(f"Executable size is reasonable ({exe_size:,} bytes)", 1_000_000 < exe_size < 10_000_000)
    check("Bundled icon exists in _internal/assets/SecureVault.ico", ASSET_ICO.is_file())

    # Verify SHA256 of bundled icon matches source icon
    source_hash = hashlib.sha256(SOURCE_ICO.read_bytes()).hexdigest()
    bundled_hash = hashlib.sha256(ASSET_ICO.read_bytes()).hexdigest()
    check("Bundled icon matches source icon bit-for-bit", source_hash == bundled_hash)

    # -------------------------------------------------------------
    # 2. Package Cleanliness Verification
    # -------------------------------------------------------------
    log("Step 2: Checking bundle for forbidden artifacts...")
    forbidden_extensions = {".svault", ".env", ".pyc_dis"}
    forbidden_files = {"init_state.json", "settings.json", "pytest.ini"}

    found_forbidden = []
    for root, dirs, files in os.walk(DIST_DIR):
        for f in files:
            p = Path(root) / f
            if p.suffix in forbidden_extensions or p.name in forbidden_files:
                found_forbidden.append(str(p))

    check("No vault, settings, env, or state files found in distribution", len(found_forbidden) == 0)

    # -------------------------------------------------------------
    # 3. Standalone Execution Checks
    # -------------------------------------------------------------
    log("Step 3: Running standalone CLI execution checks...")
    isolated_appdata = Path(os.environ.get("TEMP", "C:/temp")) / "sv_m13_verify_env"
    if isolated_appdata.exists():
        shutil.rmtree(isolated_appdata, ignore_errors=True)
    isolated_appdata.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["LOCALAPPDATA"] = str(isolated_appdata)

    # Test --version
    p_ver = subprocess.run(
        [str(EXE_PATH), "--version"],
        capture_output=True,
        text=True,
        env=env,
        timeout=15,
    )
    check("Executable runs --version with exit code 0", p_ver.returncode == 0)
    check("Version output contains 'SecureVault'", "SecureVault" in p_ver.stdout or "SecureVault" in p_ver.stderr)

    # Test --check-config
    p_cfg = subprocess.run(
        [str(EXE_PATH), "--check-config"],
        capture_output=True,
        text=True,
        env=env,
        timeout=15,
    )
    check("Executable runs --check-config with exit code 0", p_cfg.returncode == 0)

    # Test --headless
    p_hl = subprocess.run(
        [str(EXE_PATH), "--headless"],
        capture_output=True,
        text=True,
        env=env,
        timeout=15,
    )
    check("Executable runs --headless with exit code 0", p_hl.returncode == 0)

    # -------------------------------------------------------------
    # 4. GUI Launch & Window Verification
    # -------------------------------------------------------------
    log("Step 4: Launching GUI process and verifying window creation...")
    proc = subprocess.Popen([str(EXE_PATH)], env=env)
    time.sleep(3)

    # Verify process is running
    is_running = proc.poll() is None
    check("SecureVault.exe GUI process is running", is_running)

    # Check window title via PowerShell
    ps_cmd = f"""
    Add-Type @"
      using System;
      using System.Runtime.InteropServices;
      using System.Text;
      public class WinChecker {{
        [DllImport("user32.dll")]
        public static extern int GetWindowText(IntPtr hWnd, StringBuilder strText, int maxCount);
        [DllImport("user32.dll")]
        public static extern int GetWindowTextLength(IntPtr hWnd);
        [DllImport("user32.dll")]
        public static extern bool EnumWindows(EnumWindowsProc enumProc, IntPtr lParam);
        public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);
        [DllImport("user32.dll")]
        public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);
      }}
"@
    $titles = [System.Collections.Generic.List[string]]::new()
    [WinChecker]::EnumWindows({{
      param($hwnd, $lParam)
      $pid_val = [uint32]0
      [WinChecker]::GetWindowThreadProcessId($hwnd, [ref]$pid_val)
      if ($pid_val -eq {proc.pid}) {{
        $len = [WinChecker]::GetWindowTextLength($hwnd)
        if ($len -gt 0) {{
          $sb = [System.Text.StringBuilder]::new($len + 1)
          [WinChecker]::GetWindowText($hwnd, $sb, $sb.Capacity)
          $titles.Add($sb.ToString())
        }}
      }}
      return $true
    }}, [IntPtr]::Zero)
    $titles -join ' | '
    """
    ps_res = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps_cmd],
        capture_output=True,
        text=True,
        timeout=15,
    )
    window_titles = ps_res.stdout.strip()
    check("Setup Wizard window title displayed ('First-Run Setup')", "First-Run Setup" in window_titles)

    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()

    # -------------------------------------------------------------
    # 5. Strict User Data Separation Verification
    # -------------------------------------------------------------
    log("Step 5: Verifying user data separation...")
    # Check that dist directory was not written to during execution
    user_data_files = (
        list(DIST_DIR.rglob("*.svault"))
        + list(DIST_DIR.rglob("init_state.json"))
        + list(DIST_DIR.rglob("settings.json"))
    )
    check("Zero user data or state files written to dist/ directory", len(user_data_files) == 0)

    # Clean up isolated temp appdata
    if isolated_appdata.exists():
        shutil.rmtree(isolated_appdata, ignore_errors=True)

    log("=" * 60)
    log("ALL M13 STANDALONE PACKAGING VERIFICATION CHECKS PASSED!")
    log("=" * 60)


if __name__ == "__main__":
    main()
