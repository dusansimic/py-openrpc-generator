import argparse
import sys
from pathlib import Path
from py_openrpc_generator.generators.base import OpenRPCSpec
from py_openrpc_generator.generators.typescript import TypeScriptGenerator
from py_openrpc_generator.generators.golang import GolangGenerator


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
        help="Generate code from OpenRPC specification",
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
        default=None,
        help=(
            "Output file path. "
            "Defaults to ./client.ts for typescript, ./server.go for go-gorilla."
        ),
    )

    generate_parser.add_argument(
        "-l",
        "--language",
        type=str,
        choices=["typescript", "go-gorilla"],
        default="typescript",
        help="Target language (default: typescript)",
    )

    generate_parser.add_argument(
        "-c",
        "--class-name",
        type=str,
        default="RPCClient",
        help="[TypeScript only] Generated client class name (default: RPCClient)",
    )

    generate_parser.add_argument(
        "-p",
        "--package-name",
        type=str,
        default="main",
        help="[Go only] Go package name for the generated file (default: main)",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    if args.command == "generate":
        try:
            # Resolve default output path per language
            output_path = args.output
            if output_path is None:
                if args.language == "go-gorilla":
                    output_path = "./server.go"
                else:
                    output_path = "./client.ts"

            # Load OpenRPC spec
            spec = OpenRPCSpec.from_file(args.spec)

            # Generate based on language
            if args.language == "typescript":
                generator = TypeScriptGenerator()
                generator.generate(spec, output_path, args.class_name)
            elif args.language == "go-gorilla":
                generator = GolangGenerator()
                generator.generate(spec, output_path, args.package_name)

            print(f"Successfully generated {args.language} output: {output_path}")
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
