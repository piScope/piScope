import argparse


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Launch piScope and print its server port and process ID."
    )
    parser.add_argument(
        "--exe",
        help="Python executable used to launch piScope",
    )
    args = parser.parse_args()

    from ifigure.interactive import launch

    port, process_id = launch(exe=args.exe)
    print(port, process_id, flush=True)

    import sys
    sys.stdout.flush()

if __name__ == "__main__":
    main()
