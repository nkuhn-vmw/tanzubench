"""CLI entry point — dispatches to export and import commands."""
import sys
from cli.cmd_export import run_export
from cli.cmd_import import run_import


def main(args=None):
    if args is None:
        args = sys.argv[1:]

    if not args:
        print("Usage: cli <export|import> <file>")
        sys.exit(1)

    command, *rest = args
    if command == "export":
        return run_export(rest)
    elif command == "import":
        return run_import(rest)
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
