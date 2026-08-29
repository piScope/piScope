import argparse


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Send Python source to a running piScope server."
    )
    parser.add_argument(
        "--port",
        required=True,
        type=int,
        help="Port reported by scripts/launch.py",
    )
    parser.add_argument("--host", default="localhost", help="piScope server host")
    parser.add_argument("command", help="Python command to execute in piScope")
    args = parser.parse_args()

    from ifigure.client import connect, execute

    connect(args.port, args.host)
    result = execute(args.command)

    if result is not None:
        print(repr(result))


if __name__ == "__main__":
    main()
