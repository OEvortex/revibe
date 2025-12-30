from __future__ import annotations

import argparse
from dataclasses import dataclass
import io
import sys

from revibe import __version__
from revibe.core.paths.config_paths import unlock_config_paths

# Configure line buffering for subprocess communication
if isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout.reconfigure(line_buffering=True)
if isinstance(sys.stderr, io.TextIOWrapper):
    sys.stderr.reconfigure(line_buffering=True)
if isinstance(sys.stdin, io.TextIOWrapper):
    sys.stdin.reconfigure(line_buffering=True)


@dataclass
class Arguments:
    setup: bool


def parse_arguments() -> Arguments:
    parser = argparse.ArgumentParser(description="Run Mistral Vibe in ACP mode")
    parser.add_argument(
        "-v", "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument("--setup", action="store_true", help="Setup API key and exit")
    args = parser.parse_args()
    return Arguments(setup=args.setup)


def main() -> None:
    unlock_config_paths()

    from revibe.acp.acp_agent import run_acp_server
    from revibe.setup.onboarding import run_onboarding

    args = parse_arguments()
    if args.setup:
        run_onboarding()
        sys.exit(0)
    run_acp_server()


if __name__ == "__main__":
    main()
