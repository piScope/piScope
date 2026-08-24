import argparse
import os
import signal
import socket
import traceback

from . import ensure_socket_dir, socket_path


def _stop_session(signum: int, frame: object) -> None:
    raise SystemExit


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Start a persistent piScope session for LLM commands."
    )
    parser.add_argument(
        "--id",
        required=True,
        dest="session_id",
        help="Unique identifier for this piScope LLM session",
    )
    args = parser.parse_args()

    try:
        path = socket_path(args.session_id)
    except ValueError as error:
        parser.error(str(error))

    ensure_socket_dir()
    if path.exists():
        parser.error(f"session ID is already in use: {args.session_id}")

    old_umask = os.umask(0o077)
    try:
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        listener.bind(str(path))
    finally:
        os.umask(old_umask)
    listener.listen()
    previous_sigterm_handler = signal.signal(signal.SIGTERM, _stop_session)

    try:
        from ifigure.client import execute, figure

        figure()
        print(f"piScope LLM session ID: {args.session_id}", flush=True)

        while True:
            connection, _ = listener.accept()
            with connection:
                source = connection.makefile("r", encoding="utf-8").read()
                try:
                    result = execute(source)
                    connection.sendall(repr(result).encode("utf-8"))
                except Exception:
                    connection.sendall(traceback.format_exc().encode("utf-8"))
    finally:
        signal.signal(signal.SIGTERM, previous_sigterm_handler)
        listener.close()
        try:
            path.unlink()
        except FileNotFoundError:
            pass


if __name__ == "__main__":
    main()
