"""Console entrypoint for the call4paper MCP server."""

import argparse

from call4paper.server import main


def app() -> None:
    """Run the MCP server."""
    parser = argparse.ArgumentParser(prog="call4paper")
    parser.add_argument(
        "command",
        nargs="?",
        default="serve",
        choices=["serve"],
        help="Start the MCP server.",
    )
    parser.parse_args()
    main()
