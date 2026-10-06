"""SecureVault — Single Instance Application Guard.

Ensures that only a single instance of SecureVault can run at a time for a given
user/data directory. If a second instance is launched:
1. It contacts the active instance via local IPC (QLocalSocket -> QLocalServer).
2. It requests the primary instance to restore and bring its window to the foreground.
3. The second instance exits cleanly without opening a duplicate window.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket

from app.core.logging import get_logger

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget

logger = get_logger("core.single_instance")


def generate_server_name(app_name: str = "SecureVault", data_dir: Path | str | None = None) -> str:
    """Generate a deterministic local server name scoped to the application and data directory.

    By scoping to data_dir, separate test environments or profiles do not conflict,
    while normal production launches always target the identical server key.
    """
    if data_dir is not None:
        target_path = str(Path(data_dir).resolve())
        dir_hash = hashlib.sha256(target_path.encode("utf-8")).hexdigest()[:12]
        return f"{app_name}_single_{dir_hash}"
    return f"{app_name}_single_default"


def bring_window_to_front(window: QWidget | None) -> None:
    """Restore, raise, and give focus to a Qt widget / top-level window.

    Includes Windows user32 API interop (ShowWindow / SetForegroundWindow) to guarantee
    that windows minimized or hidden behind other applications are brought directly
    to the foreground.
    """
    if window is None:
        return

    try:
        # Restore window if minimized
        if window.isMinimized():
            window.showNormal()

        window.show()
        window.raise_()
        window.activateWindow()

        # On Windows, enforce foreground activation via Win32 API
        if sys.platform == "win32":
            try:
                from PySide6.QtGui import QGuiApplication

                if QGuiApplication.platformName() != "offscreen":
                    import ctypes

                    hwnd = int(window.winId())
                    user32 = ctypes.windll.user32
                    if hwnd and user32.IsWindow(hwnd):
                        # SW_RESTORE = 9
                        user32.ShowWindow(hwnd, 9)
                        user32.SetForegroundWindow(hwnd)
            except Exception as win_err:
                logger.debug("Win32 foreground window activation note: %s", win_err)
    except Exception as exc:
        logger.warning("Error bringing window to front: %s", exc)


class SingleInstanceGuard(QObject):
    """Enforces single-instance execution via local inter-process communication."""

    instance_activated = Signal()

    def __init__(
        self,
        app_name: str = "SecureVault",
        data_dir: Path | str | None = None,
        server_name: str | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.server_name: str = server_name or generate_server_name(app_name, data_dir)
        self._server: QLocalServer | None = None

        # Auto-disconnect and clean up if QApplication is quitting
        try:
            from PySide6.QtWidgets import QApplication

            qapp = QApplication.instance()
            if qapp is not None:
                qapp.aboutToQuit.connect(self.close)
        except Exception:
            pass

    def is_another_instance_running(self, timeout_ms: int = 800) -> bool:
        """Check if another instance of the application is already active.

        If an active instance is discovered, notifies it to bring its window
        to the foreground and returns True. Otherwise, returns False.
        """
        socket = QLocalSocket()
        socket.connectToServer(self.server_name)
        if socket.waitForConnected(timeout_ms):
            logger.info("Detected running instance on server '%s'. Signaling focus.", self.server_name)
            try:
                # On Windows, permit the existing process to take foreground focus
                if sys.platform == "win32":
                    try:
                        import ctypes

                        # ASFW_ANY = -1
                        ctypes.windll.user32.AllowSetForegroundWindow(-1)
                    except Exception:
                        pass

                socket.write(b"ACTIVATE\n")
                socket.waitForBytesWritten(500)
                socket.flush()
                socket.disconnectFromServer()
                socket.waitForDisconnected(500)
            except Exception as exc:
                logger.warning("Error communicating with existing instance: %s", exc)
            finally:
                socket.close()
            return True

        return False

    def start_listening(self) -> bool:
        """Start the QLocalServer to listen for future launch attempts.

        Handles cleanup of stale server pipes from prior unclean terminations.
        """
        if self._server is not None and self._server.isListening():
            return True

        self._server = QLocalServer(self)
        self._server.newConnection.connect(self._on_new_connection)

        # Attempt listening; if address/name is in use (e.g. stale from a crash), remove it first
        if not self._server.listen(self.server_name):
            logger.debug("Local server listen failed on '%s', purging stale server.", self.server_name)
            QLocalServer.removeServer(self.server_name)
            if not self._server.listen(self.server_name):
                logger.error(
                    "Failed to bind single-instance server '%s': %s",
                    self.server_name,
                    self._server.errorString(),
                )
                return False

        logger.debug("Single-instance listener active on '%s'.", self.server_name)
        return True

    def _on_new_connection(self) -> None:
        """Handle incoming connection from a secondary instance launch."""
        if self._server is None:
            return

        while self._server.hasPendingConnections():
            client_socket = self._server.nextPendingConnection()
            if not client_socket:
                continue

            client_socket.disconnected.connect(client_socket.deleteLater)
            logger.info("Secondary instance launched. Activating current application window.")
            self.instance_activated.emit()

    def close(self) -> None:
        """Stop listening and clean up the server."""
        if self._server is not None:
            try:
                self._server.newConnection.disconnect(self._on_new_connection)
            except Exception:
                pass
            if self._server.isListening():
                self._server.close()
            self._server = None
        QLocalServer.removeServer(self.server_name)
        logger.debug("Single-instance listener closed for '%s'.", self.server_name)
