import argparse
import sys
from pathlib import Path
from .generators.base import OpenRPCSpec
from .generators.typescript import TypeScriptGenerator


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="py-openrpc-generator",
        description="Python OpenRPC Client Generator CLI",
    )

    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Generate command
    generate_parser = subparsers.add_parser(
        "generate",
        help="Generate client code from OpenRPC specification",
    )

    generate_parser.add_argument(
        "spec",
        type=str,
        help="Path to OpenRPC specification file (JSON)",
    )

    generate_parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="./client.ts",
        help="Output file path (default: ./client.ts)",
    )

    generate_parser.add_argument(
        "-l",
        "--language",
        type=str,
        choices=["typescript"],
        default="typescript",
        help="Target language (default: typescript)",
    )

    generate_parser.add_argument(
        "-c",
        "--class-name",
        type=str,
        default="RPCClient",
        help="Generated client class name (default: RPCClient)",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    if args.command == "generate":
        try:
            # Load OpenRPC spec
            spec = OpenRPCSpec.from_file(args.spec)

            # Generate client based on language
            if args.language == "typescript":
                generator = TypeScriptGenerator()
                generator.generate(spec, args.output, args.class_name)

            print(f"✓ Successfully generated {args.language} client")
            return 0

        except FileNotFoundError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"Unexpected error: {e}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
