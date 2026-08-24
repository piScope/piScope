import argparse
import socket

from . import socket_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Send a Python command to the persistent piScope session."
    )
    parser.add_argument(
        "--id",
        required=True,
        dest="session_id",
        help="Identifier reported by the target piScope LLM session",
    )
    parser.add_argument("command", help="Python command to execute in piScope")
    args = parser.parse_args()

    try:
        path = socket_path(args.session_id)
    except ValueError as error:
        parser.error(str(error))

    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.connect(str(path))
        client.sendall(args.command.encode("utf-8"))
        client.shutdown(socket.SHUT_WR)
        response = b""
        while chunk := client.recv(4096):
            response += chunk

    if response:
        print(response.decode("utf-8"))


if __name__ == "__main__":
    main()
