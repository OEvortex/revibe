"""Simple, responsive welcome banner for Revibe CLI."""
from __future__ import annotations

from rich.align import Align
from rich.console import Group
from rich.text import Text
from textual.widgets import Static

from revibe import __version__
from revibe.core.config import VibeConfig


# Color palette
ORANGE = "#FF8C00"
GOLD = "#FFD700"
WHITE = "#FFFFFF"
GRAY = "#6B7280"
DARK_GRAY = "#374151"


class WelcomeBanner(Static):
    """Compact, auto-sizing welcome banner."""

    # Minimal ASCII art - scales better in small terminals
    LOGO_SMALL = [
        "██████╗ ███████╗██╗   ██╗██╗██████╗ ███████╗",
        "██╔══██╗██╔════╝██║   ██║██║██╔══██╗██╔════╝",
        "██████╔╝█████╗  ██║   ██║██║██████╔╝█████╗  ",
        "██╔══██╗██╔══╝  ╚██╗ ██╔╝██║██╔══██╗██╔══╝  ",
        "██║  ██║███████╗ ╚████╔╝ ██║██████╔╝███████╗",
        "╚═╝  ╚═╝╚══════╝  ╚═══╝  ╚═╝╚═════╝ ╚══════╝",
    ]

    def __init__(self, config: VibeConfig) -> None:
        super().__init__()
        self.config = config

    def on_mount(self) -> None:
        """Render the banner on mount."""
        self._render_banner()

    def _render_banner(self) -> None:
        """Build and display the banner content."""
        lines: list[Text] = []

        # Logo with gradient effect
        for i, line in enumerate(self.LOGO_SMALL):
            color = ORANGE if i < 3 else GOLD
            lines.append(Text.from_markup(f"[bold {color}]{line}[/]"))

        # Spacing
        lines.append(Text(""))

        # Version and model info - compact single line
        model = self.config.active_model or "No model selected"
        info = f"[{WHITE}]v{__version__}[/]  [{GRAY}]•[/]  [{GOLD}]{model}[/]"
        lines.append(Text.from_markup(info))

        # Stats line
        model_count = len(self.config.models)
        mcp_count = len(self.config.mcp_servers)
        stats = f"[{GRAY}]{model_count} models • {mcp_count} MCP servers[/]"
        lines.append(Text.from_markup(stats))

        # Workspace path - truncated if too long
        workspace = str(self.config.effective_workdir)
        if len(workspace) > 50:
            workspace = "..." + workspace[-47:]
        lines.append(Text.from_markup(f"[{DARK_GRAY}]{workspace}[/]"))

        self.update(Align.center(Group(*lines)))
