from __future__ import annotations

import argparse
from pathlib import Path
import sys

from rich import print as rprint

from revibe import __version__
from revibe.core.paths.config_paths import unlock_config_paths
from revibe.core.trusted_folders import trusted_folders_manager
from revibe.setup.trusted_folders.trust_folder_dialog import (
    TrustDialogQuitException,
    ask_trust_folder,
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the ReVibe interactive CLI")
    parser.add_argument(
        "-v", "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument(
        "initial_prompt",
        nargs="?",
        metavar="PROMPT",
        help="Initial prompt to start the interactive session with.",
    )
    parser.add_argument(
        "-p",
        "--prompt",
        nargs="?",
        const="",
        metavar="TEXT",
        help="Run in programmatic mode: send prompt, auto-approve all tools, "
        "output response, and exit.",
    )
    parser.add_argument(
        "--auto-approve",
        action="store_true",
        default=False,
        help="Start in auto-approve mode: never ask for approval before running tools.",
    )
    parser.add_argument(
        "--plan",
        action="store_true",
        default=False,
        help="Start in plan mode: read-only tools for exploration and planning.",
    )
    parser.add_argument(
        "--max-turns",
        type=int,
        metavar="N",
        help="Maximum number of assistant turns "
        "(only applies in programmatic mode with -p).",
    )
    parser.add_argument(
        "--max-price",
        type=float,
        metavar="DOLLARS",
        help="Maximum cost in dollars (only applies in programmatic mode with -p). "
        "Session will be interrupted if cost exceeds this limit.",
    )
    parser.add_argument(
        "--enabled-tools",
        action="append",
        metavar="TOOL",
        help="Enable specific tools. In programmatic mode (-p), this disables "
        "all other tools. "
        "Can use exact names, glob patterns (e.g., 'bash*'), or "
        "regex with 're:' prefix. Can be specified multiple times.",
    )
    parser.add_argument(
        "--output",
        type=str,
        choices=["text", "json", "streaming"],
        default="text",
        help="Output format for programmatic mode (-p): 'text' "
        "for human-readable (default), 'json' for all messages at end, "
        "'streaming' for newline-delimited JSON per message.",
    )
    parser.add_argument(
        "--agent",
        metavar="NAME",
        default=None,
        help="Load agent configuration from ~/.revibe/agents/NAME.toml",
    )
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Run interactive setup: choose provider, theme, and configure API key",
    )

    parser.add_argument(
        "--tool-format",
        type=str,
        choices=["native", "xml"],
        default=None,
        metavar="FORMAT",
        help="Tool calling format: 'native' for API function calling (default), "
        "'xml' for XML-based tool calling in prompts.",
    )

    parser.add_argument(
        "--installation-info",
        action="store_true",
        help="Show installation type and update instructions",
    )

    continuation_group = parser.add_mutually_exclusive_group()
    continuation_group.add_argument(
        "-c",
        "--continue",
        action="store_true",
        dest="continue_session",
        help="Continue from the most recent saved session",
    )
    continuation_group.add_argument(
        "--resume",
        metavar="SESSION_ID",
        help="Resume a specific session by its ID (supports partial matching)",
    )
    return parser.parse_args()


def check_and_resolve_trusted_folder() -> None:
    cwd = Path.cwd()
    if not (cwd / ".revibe").exists() or cwd.resolve() == Path.home().resolve():
        return

    is_folder_trusted = trusted_folders_manager.is_trusted(cwd)

    if is_folder_trusted is not None:
        return

    try:
        is_folder_trusted = ask_trust_folder(cwd)
    except (KeyboardInterrupt, EOFError, TrustDialogQuitException):
        sys.exit(0)
    except Exception as e:
        rprint(f"[yellow]Error showing trust dialog: {e}[/]")
        return

    if is_folder_trusted is True:
        trusted_folders_manager.add_trusted(cwd)
    elif is_folder_trusted is False:
        trusted_folders_manager.add_untrusted(cwd)


def main() -> None:
    args = parse_arguments()

    # Handle installation info flag
    if args.installation_info:
        from revibe.cli.utils.installation_utils import get_installation_info

        info = get_installation_info()
        rprint(f"[bold]ReVibe Installation Information[/]")
        rprint(f"Package: {info['package_name']}")
        rprint(f"Version: {info['version']}")
        rprint(f"Installation Type: {info['installation_type']}")
        rprint(f"Location: {info['location']}")
        rprint()
        rprint(f"[bold]Update Instructions:[/]")
        rprint(f"Command: {info['update_command']}")

        if info['installation_type'] == 'editable':
            rprint()
            rprint("[yellow]Note: You're using an editable installation.[/]")
            rprint("This means you're running directly from source code.")
            rprint("To update, pull the latest changes and reinstall:")
            rprint("  git pull")
            rprint("  pip install -e .")
        else:
            rprint()
            rprint("[green]You're using a regular installation.[/]")
            rprint("To update, use the command shown above.")
        return

    is_interactive = args.prompt is None
    if is_interactive:
        check_and_resolve_trusted_folder()
    unlock_config_paths()

    from revibe.cli.cli import run_cli

    run_cli(args)


if __name__ == "__main__":
    main()
