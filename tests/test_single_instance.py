"""Tests for SingleInstanceGuard and single-instance enforcement."""

from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtWidgets import QApplication

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from app.core.config import AppConfig
from app.core.single_instance import (
    SingleInstanceGuard,
    bring_window_to_front,
    generate_server_name,
)
from app.ui.app_window import ApplicationController, run_gui


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    """Ensure a singleton QApplication exists."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def test_generate_server_name_determinism(tmp_path: Path) -> None:
    """Verify that generate_server_name produces deterministic and unique names."""
    name1 = generate_server_name("SecureVault", tmp_path / "dir1")
    name2 = generate_server_name("SecureVault", tmp_path / "dir1")
    name3 = generate_server_name("SecureVault", tmp_path / "dir2")
    name_default = generate_server_name("SecureVault", None)

    assert name1 == name2
    assert name1 != name3
    assert "SecureVault_single_" in name1
    assert name_default == "SecureVault_single_default"


def test_single_instance_guard_lifecycle(qapp: QApplication) -> None:
    """Verify primary instance listens and secondary instance detects it and triggers signal."""
    test_key = f"sv_test_instance_{next(tempfile._get_candidate_names())}"

    primary_guard = SingleInstanceGuard(server_name=test_key)
    secondary_guard = SingleInstanceGuard(server_name=test_key)

    try:
        # Initially no instance is running
        assert not primary_guard.is_another_instance_running(timeout_ms=100)

        # Primary starts listening
        assert primary_guard.start_listening()

        # Track activation signal from primary
        activated_calls = []
        primary_guard.instance_activated.connect(lambda: activated_calls.append(True))

        # Secondary detects running primary instance
        assert secondary_guard.is_another_instance_running(timeout_ms=1000)

        # Process Qt events until activation signal is delivered
        deadline = time.time() + 2.0
        while not activated_calls and time.time() < deadline:
            qapp.processEvents()
            time.sleep(0.01)

        assert len(activated_calls) >= 1

    finally:
        secondary_guard.close()
        primary_guard.close()
        qapp.processEvents()


def test_single_instance_guard_after_primary_closed(qapp: QApplication) -> None:
    """Verify that when primary closes, secondary is no longer detected as duplicate."""
    test_key = f"sv_test_closed_{next(tempfile._get_candidate_names())}"

    primary_guard = SingleInstanceGuard(server_name=test_key)
    secondary_guard = SingleInstanceGuard(server_name=test_key)

    try:
        assert primary_guard.start_listening()
        assert secondary_guard.is_another_instance_running(timeout_ms=500)

        # Primary stops listening
        primary_guard.close()
        qapp.processEvents()

        # Secondary now reports no instance running
        assert not secondary_guard.is_another_instance_running(timeout_ms=200)

    finally:
        secondary_guard.close()
        primary_guard.close()
        qapp.processEvents()


def test_bring_window_to_front_restores_and_activates() -> None:
    """Verify bring_window_to_front restores a minimized window and activates it."""
    mock_window = MagicMock()
    mock_window.isMinimized.return_value = True

    bring_window_to_front(mock_window)

    mock_window.showNormal.assert_called_once()
    mock_window.show.assert_called_once()
    mock_window.raise_.assert_called_once()
    mock_window.activateWindow.assert_called_once()


def test_bring_window_to_front_handles_none() -> None:
    """Verify bring_window_to_front executes safely when window is None."""
    bring_window_to_front(None)


def test_application_controller_wires_single_instance_guard() -> None:
    """Verify ApplicationController connects single_instance_guard activation signal."""
    mock_guard = MagicMock()
    controller = ApplicationController(single_instance_guard=mock_guard)

    mock_guard.instance_activated.connect.assert_called_once_with(controller.activate_current_window)

    mock_window = MagicMock()
    controller.current_window = mock_window

    with patch("app.ui.app_window.bring_window_to_front") as mock_bring:
        controller.activate_current_window()
        mock_bring.assert_called_once_with(mock_window)


def test_run_gui_exits_early_when_duplicate_detected() -> None:
    """Verify run_gui returns 0 immediately if another instance is already running."""
    mock_guard = MagicMock()
    mock_guard.is_another_instance_running.return_value = True

    config = AppConfig()
    exit_code = run_gui(config=config, single_instance_guard=mock_guard)

    assert exit_code == 0
    # Listener should not be started when another instance was detected
    mock_guard.start_listening.assert_not_called()
