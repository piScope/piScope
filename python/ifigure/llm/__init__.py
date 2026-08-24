"""Utilities for LLM-driven piScope sessions."""

import os
import re
import stat
import tempfile
from pathlib import Path


SOCKET_DIR = Path(tempfile.gettempdir()) / f"piscope-llm-{os.getuid()}"


def socket_path(session_id: str) -> Path:
    """Return the Unix-domain socket path for a piScope LLM session."""
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", session_id):
        raise ValueError(
            "session ID must contain 1-64 letters, digits, underscores, or hyphens"
        )
    return SOCKET_DIR / f"session-{session_id}.sock"


def ensure_socket_dir() -> Path:
    """Create the private directory used for piScope LLM sockets."""
    SOCKET_DIR.mkdir(mode=0o700, exist_ok=True)
    directory_stat = SOCKET_DIR.stat()
    if directory_stat.st_uid != os.getuid():
        raise RuntimeError(f"{SOCKET_DIR} is not owned by the current user")
    if stat.S_IMODE(directory_stat.st_mode) != 0o700:
        SOCKET_DIR.chmod(0o700)
    return SOCKET_DIR
