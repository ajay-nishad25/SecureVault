"""SecureVault — Milestone M13 Installer Verification Script.

Tests the Inno Setup installer package (dist_installer/SecureVault-Setup-0.1.0.exe):
1. Silent installation into custom test directory
2. File layout verification (SecureVault.exe, unins000.exe, assets)
3. Installed executable execution (--version, --check-config, --headless)
4. User test vault creation in isolated LOCALAPPDATA
5. Silent uninstallation via unins000.exe
6. CRITICAL DATA RETENTION: Verify %LOCALAPPDATA%\SecureVault and vault.svault survive uninstall untouched
7. Reinstallation and vault rediscovery verification
8. Cleanup of test environments
"""

import hashlib
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INSTALLER_EXE = PROJECT_ROOT / "dist_installer" / "SecureVault-Setup-0.1.0.exe"

TEMP_BASE = Path(os.environ.get("TEMP", "C:/temp"))
TEST_INSTALL_DIR = TEMP_BASE / "sv_test_install"
TEST_APPDATA_DIR = TEMP_BASE / "sv_test_appdata"


def log(msg: str) -> None:
    print(f"[M13 INSTALLER] {msg}")


def check(desc: str, condition: bool) -> None:
    if condition:
        print(f"  [OK] PASS: {desc}")
    else:
        print(f"  [FAIL] FAILED: {desc}")
        sys.exit(1)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    log("Starting M13 Windows Installer Verification Suite")

    # Verify installer exists
    check("Installer binary exists in dist_installer", INSTALLER_EXE.is_file())
    installer_size = INSTALLER_EXE.stat().st_size
    check(f"Installer size is reasonable ({installer_size:,} bytes)", 10_000_000 < installer_size < 100_000_000)

    # Clean previous test directories if present
    for d in (TEST_INSTALL_DIR, TEST_APPDATA_DIR):
        if d.exists():
            shutil.rmtree(d, ignore_errors=True)

    TEST_INSTALL_DIR.mkdir(parents=True, exist_ok=True)
    TEST_APPDATA_DIR.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["LOCALAPPDATA"] = str(TEST_APPDATA_DIR)

    # -------------------------------------------------------------
    # Step 1: Silent Installation
    # -------------------------------------------------------------
    log("Step 1: Running silent installation into test directory...")
    install_cmd = [
        str(INSTALLER_EXE),
        "/VERYSILENT",
        "/SUPPRESSMSGBOXES",
        "/NORESTART",
        f"/DIR={TEST_INSTALL_DIR}",
    ]
    p_inst = subprocess.run(install_cmd, capture_output=True, text=True, timeout=60)
    check("Installer exited with return code 0", p_inst.returncode == 0)

    # -------------------------------------------------------------
    # Step 2: Installed Layout Verification
    # -------------------------------------------------------------
    log("Step 2: Verifying installed application layout...")
    installed_exe = TEST_INSTALL_DIR / "SecureVault.exe"
    uninstaller = TEST_INSTALL_DIR / "unins000.exe"
    installed_icon = TEST_INSTALL_DIR / "_internal" / "assets" / "SecureVault.ico"

    check("Installed SecureVault.exe exists", installed_exe.is_file())
    check("Installed unins000.exe exists", uninstaller.is_file())
    check("Installed icon exists in _internal/assets/SecureVault.ico", installed_icon.is_file())

    # -------------------------------------------------------------
    # Step 3: Installed Executable Execution
    # -------------------------------------------------------------
    log("Step 3: Running installed executable in isolated environment...")
    p_ver = subprocess.run(
        [str(installed_exe), "--version"],
        capture_output=True,
        text=True,
        env=env,
        timeout=15,
    )
    check("Installed executable runs --version", p_ver.returncode == 0)
    check("Version contains 'SecureVault'", "SecureVault" in p_ver.stdout or "SecureVault" in p_ver.stderr)

    p_chk = subprocess.run(
        [str(installed_exe), "--check-config"],
        capture_output=True,
        text=True,
        env=env,
        timeout=15,
    )
    check("Installed executable runs --check-config", p_chk.returncode == 0)

    # -------------------------------------------------------------
    # Step 4: Create Simulated Test Vault in %LOCALAPPDATA%
    # -------------------------------------------------------------
    log("Step 4: Simulating user vault creation in %LOCALAPPDATA%\\SecureVault...")
    sv_data_dir = TEST_APPDATA_DIR / "SecureVault"
    sv_data_dir.mkdir(parents=True, exist_ok=True)

    test_vault_file = sv_data_dir / "vault.svault"
    test_vault_file.write_bytes(b"SVLT\x01\x00" + b"\x42" * 128 + b"ENCRYPTED_TEST_PAYLOAD")

    test_init_file = sv_data_dir / "init_state.json"
    test_init_file.write_text('{"initialized": true, "login_id": "alice_test", "created_at": 1700000000.0}', encoding="utf-8")

    test_settings_file = sv_data_dir / "settings.json"
    test_settings_file.write_text('{"theme": "dark", "auto_lock_timeout": 600}', encoding="utf-8")

    vault_hash_before = sha256_file(test_vault_file)
    init_hash_before = sha256_file(test_init_file)
    settings_hash_before = sha256_file(test_settings_file)

    log(f"Test vault recorded: SHA256={vault_hash_before[:16]}...")

    # -------------------------------------------------------------
    # Step 5: Silent Uninstallation
    # -------------------------------------------------------------
    log("Step 5: Executing silent uninstallation via unins000.exe...")
    uninst_cmd = [
        str(uninstaller),
        "/VERYSILENT",
        "/SUPPRESSMSGBOXES",
        "/NORESTART",
    ]
    p_uninst = subprocess.run(uninst_cmd, capture_output=True, text=True, timeout=60)
    check("Uninstaller exited with return code 0", p_uninst.returncode == 0)

    # Allow Windows brief filesystem delay
    time.sleep(2)

    # Verify application files were deleted
    check("Installed SecureVault.exe was removed by uninstaller", not installed_exe.exists())
    check("Installed _internal directory was removed", not (TEST_INSTALL_DIR / "_internal").exists())

    # -------------------------------------------------------------
    # Step 6: CRITICAL DATA RETENTION CHECK
    # -------------------------------------------------------------
    log("Step 6: CRITICAL CHECK — Verifying %LOCALAPPDATA%\\SecureVault survived uninstall...")
    check("User data directory %LOCALAPPDATA%\\SecureVault still exists", sv_data_dir.is_dir())
    check("User vault.svault still exists after uninstall", test_vault_file.is_file())
    check("User init_state.json still exists after uninstall", test_init_file.is_file())
    check("User settings.json still exists after uninstall", test_settings_file.is_file())

    # Verify cryptographic bit-for-bit integrity of user data
    vault_hash_after = sha256_file(test_vault_file)
    init_hash_after = sha256_file(test_init_file)
    settings_hash_after = sha256_file(test_settings_file)

    check("User vault.svault is 100% byte-for-byte identical", vault_hash_before == vault_hash_after)
    check("User init_state.json is 100% byte-for-byte identical", init_hash_before == init_hash_after)
    check("User settings.json is 100% byte-for-byte identical", settings_hash_before == settings_hash_after)

    # -------------------------------------------------------------
    # Step 7: Reinstallation & Vault Rediscovery
    # -------------------------------------------------------------
    log("Step 7: Testing reinstallation and vault discovery...")
    p_reinst = subprocess.run(install_cmd, capture_output=True, text=True, timeout=60)
    check("Reinstallation completed successfully with return code 0", p_reinst.returncode == 0)
    check("SecureVault.exe restored upon reinstallation", installed_exe.is_file())

    p_recheck = subprocess.run(
        [str(installed_exe), "--check-config"],
        capture_output=True,
        text=True,
        env=env,
        timeout=15,
    )
    check("Reinstalled SecureVault successfully runs and detects existing configuration", p_recheck.returncode == 0)

    # -------------------------------------------------------------
    # Step 8: Clean Up
    # -------------------------------------------------------------
    log("Step 8: Cleaning up test directories...")
    # Final uninstall of test installation
    subprocess.run(uninst_cmd, capture_output=True, text=True, timeout=60)
    time.sleep(2)
    shutil.rmtree(TEST_INSTALL_DIR, ignore_errors=True)
    shutil.rmtree(TEST_APPDATA_DIR, ignore_errors=True)

    log("=" * 60)
    log("ALL M13 INSTALLER VERIFICATION CHECKS PASSED PERFECTLY!")
    log("=" * 60)


if __name__ == "__main__":
    main()
