"""Enhanced diff view widget for displaying file changes.

This module provides a rich diff view similar to Gemini CLI and QwenCode,
featuring:
- Line numbers on the left
- Colored backgrounds for added/removed lines
- Collapsible diff sections
- Summary header with file path and change description
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from rich.console import Group
from rich.style import Style
from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Static


@dataclass
class DiffLine:
    """Represents a single line in a diff."""

    line_number: int | None  # None for range headers
    content: str
    line_type: Literal["added", "removed", "context", "header", "range"]
    old_line_number: int | None = None  # For context/removed lines


@dataclass
class DiffHunk:
    """A hunk of changes in a diff."""

    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: list[DiffLine]


@dataclass
class FileDiff:
    """Complete diff for a file."""

    file_path: str
    summary: str
    hunks: list[DiffHunk]
    is_new_file: bool = False
    is_deleted: bool = False


def parse_unified_diff(diff_text: str, file_path: str = "") -> FileDiff:
    """Parse unified diff format into structured data."""
    lines = diff_text.strip().split("\n")
    hunks: list[DiffHunk] = []
    current_hunk: DiffHunk | None = None
    old_line = 0
    new_line = 0

    # Pattern for hunk headers like @@ -1,3 +1,4 @@
    hunk_pattern = re.compile(r"^@@\s*-(\d+)(?:,(\d+))?\s*\+(\d+)(?:,(\d+))?\s*@@")

    added_count = 0
    removed_count = 0

    for line in lines:
        # Skip file headers
        if line.startswith("---") or line.startswith("+++"):
            continue

        hunk_match = hunk_pattern.match(line)
        if hunk_match:
            if current_hunk:
                hunks.append(current_hunk)

            old_start = int(hunk_match.group(1))
            old_count = int(hunk_match.group(2) or "1")
            new_start = int(hunk_match.group(3))
            new_count = int(hunk_match.group(4) or "1")

            current_hunk = DiffHunk(
                old_start=old_start,
                old_count=old_count,
                new_start=new_start,
                new_count=new_count,
                lines=[]
            )
            old_line = old_start
            new_line = new_start

            # Add the range header
            current_hunk.lines.append(DiffLine(
                line_number=None,
                content=line,
                line_type="range"
            ))
        elif current_hunk is not None:
            if line.startswith("-"):
                current_hunk.lines.append(DiffLine(
                    line_number=old_line,
                    old_line_number=old_line,
                    content=line[1:],  # Remove the - prefix
                    line_type="removed"
                ))
                old_line += 1
                removed_count += 1
            elif line.startswith("+"):
                current_hunk.lines.append(DiffLine(
                    line_number=new_line,
                    old_line_number=None,
                    content=line[1:],  # Remove the + prefix
                    line_type="added"
                ))
                new_line += 1
                added_count += 1
            elif line.startswith(" ") or not line:
                current_hunk.lines.append(DiffLine(
                    line_number=new_line,
                    old_line_number=old_line,
                    content=line[1:] if line.startswith(" ") else line,
                    line_type="context"
                ))
                old_line += 1
                new_line += 1

    if current_hunk:
        hunks.append(current_hunk)

    # Generate summary
    summary_parts = []
    if added_count > 0:
        summary_parts.append(f"+{added_count}")
    if removed_count > 0:
        summary_parts.append(f"-{removed_count}")
    summary = " ".join(summary_parts) if summary_parts else "No changes"

    return FileDiff(
        file_path=file_path,
        summary=summary,
        hunks=hunks
    )


def parse_search_replace_to_file_diff(
    content: str,
    file_path: str
) -> FileDiff:
    """Parse SEARCH/REPLACE blocks into a FileDiff structure."""
    from revibe.core.tools.builtins.search_replace import SEARCH_REPLACE_BLOCK_RE

    all_hunks: list[DiffHunk] = []
    added_count = 0
    removed_count = 0

    matches = SEARCH_REPLACE_BLOCK_RE.findall(content)

    for block_idx, (search_text, replace_text) in enumerate(matches):
        search_lines = search_text.strip().split("\n")
        replace_lines = replace_text.strip().split("\n")

        # Create a diff using difflib
        diff_lines = list(difflib.unified_diff(
            search_lines,
            replace_lines,
            lineterm="",
            n=2  # Context lines
        ))

        hunk_lines: list[DiffLine] = []
        line_num = 1

        for diff_line in diff_lines[2:]:  # Skip file headers
            if diff_line.startswith("@@"):
                hunk_lines.append(DiffLine(
                    line_number=None,
                    content=diff_line,
                    line_type="range"
                ))
            elif diff_line.startswith("-"):
                hunk_lines.append(DiffLine(
                    line_number=line_num,
                    old_line_number=line_num,
                    content=diff_line[1:],
                    line_type="removed"
                ))
                removed_count += 1
            elif diff_line.startswith("+"):
                hunk_lines.append(DiffLine(
                    line_number=line_num,
                    old_line_number=None,
                    content=diff_line[1:],
                    line_type="added"
                ))
                added_count += 1
                line_num += 1
            else:
                hunk_lines.append(DiffLine(
                    line_number=line_num,
                    old_line_number=line_num,
                    content=diff_line[1:] if diff_line.startswith(" ") else diff_line,
                    line_type="context"
                ))
                line_num += 1

        if hunk_lines:
            all_hunks.append(DiffHunk(
                old_start=1,
                old_count=len(search_lines),
                new_start=1,
                new_count=len(replace_lines),
                lines=hunk_lines
            ))

    summary_parts = []
    if added_count > 0:
        summary_parts.append(f"+{added_count}")
    if removed_count > 0:
        summary_parts.append(f"-{removed_count}")
    summary = " ".join(summary_parts) if summary_parts else "No changes"

    return FileDiff(
        file_path=file_path,
        summary=summary,
        hunks=all_hunks
    )


class DiffLineWidget(Static):
    """Widget for rendering a single diff line with line numbers and colors."""

    def __init__(
        self,
        diff_line: DiffLine,
        show_line_numbers: bool = True
    ) -> None:
        super().__init__()
        self.diff_line = diff_line
        self.show_line_numbers = show_line_numbers
        self._set_classes()

    def _set_classes(self) -> None:
        self.add_class("diff-line")
        self.add_class(f"diff-line-{self.diff_line.line_type}")

    def render(self) -> Text:
        line = self.diff_line
        text = Text()

        if line.line_type == "range":
            # Range header like @@ -1,3 +1,4 @@
            text.append(line.content, style=Style(color="#61afef", bold=True))
            return text

        # Line number column
        if self.show_line_numbers:
            if line.line_type == "removed":
                # Show old line number for removed lines
                ln = str(line.line_number) if line.line_number else ""
                text.append(f"{ln:>4} ", style=Style(color="#e06c75", dim=True))
                text.append("- ", style=Style(color="#e06c75", bold=True))
            elif line.line_type == "added":
                ln = str(line.line_number) if line.line_number else ""
                text.append(f"{ln:>4} ", style=Style(color="#98c379", dim=True))
                text.append("+ ", style=Style(color="#98c379", bold=True))
            else:
                ln = str(line.line_number) if line.line_number else ""
                text.append(f"{ln:>4}   ", style=Style(color="#5c6370", dim=True))

        # Content
        if line.line_type == "removed":
            text.append(line.content, style=Style(color="#e06c75"))
        elif line.line_type == "added":
            text.append(line.content, style=Style(color="#98c379"))
        else:
            text.append(line.content, style=Style(color="#abb2bf"))

        return text


class DiffHeaderWidget(Static):
    """Header widget showing the action type, file path, and summary."""

    def __init__(
        self,
        action: str,
        file_path: str,
        summary: str,
        success: bool = True
    ) -> None:
        super().__init__()
        self.action = action
        self.file_path = file_path
        self.summary = summary
        self.success = success
        self.add_class("diff-header-widget")

    def render(self) -> Text:
        text = Text()

        # Status icon
        if self.success:
            text.append("✓ ", style=Style(color="#98c379", bold=True))
        else:
            text.append("✗ ", style=Style(color="#e06c75", bold=True))

        # Action
        text.append(f"{self.action} ", style=Style(color="#e5c07b", bold=True))

        # File path (truncated if too long)
        path = Path(self.file_path)
        display_path = path.name
        if len(str(path)) <= 50:
            display_path = str(path)
        else:
            # Show ...parent/filename
            display_path = f".../{path.parent.name}/{path.name}"

        text.append(display_path, style=Style(color="#61afef"))

        # Summary arrows
        text.append(" => ", style=Style(color="#5c6370", dim=True))

        # Change summary
        text.append(self.summary, style=Style(color="#abb2bf", dim=True))

        return text


class DiffHunkWidget(Vertical):
    """Widget for rendering a single diff hunk."""

    def __init__(self, hunk: DiffHunk, collapsed: bool = False) -> None:
        super().__init__()
        self.hunk = hunk
        self.collapsed = collapsed
        self.add_class("diff-hunk")

    def compose(self) -> ComposeResult:
        for diff_line in self.hunk.lines:
            yield DiffLineWidget(diff_line)


class DiffViewWidget(Vertical):
    """
    Complete diff view widget with header, hunks, and collapsible sections.

    Similar to the diff views in Gemini CLI and QwenCode TUIs.
    """

    DEFAULT_CSS = """
    DiffViewWidget {
        width: 100%;
        height: auto;
        padding: 0;
        margin: 0;
    }

    .diff-header-widget {
        height: auto;
        padding: 0 0 1 0;
    }

    .diff-hunk {
        height: auto;
        padding: 0;
        margin: 0;
    }

    .diff-line {
        height: 1;
        width: 100%;
    }

    .diff-line-removed {
        background: #3d2020;
    }

    .diff-line-added {
        background: #1e3d20;
    }

    .diff-line-context {
        background: transparent;
    }

    .diff-line-range {
        background: #2d3a4d;
        padding: 0 1;
        margin: 1 0;
    }
    """

    def __init__(
        self,
        file_diff: FileDiff,
        action: str = "Edit",
        collapsed: bool = False,
        max_lines: int = 50
    ) -> None:
        super().__init__()
        self.file_diff = file_diff
        self.action = action
        self.collapsed = collapsed
        self.max_lines = max_lines
        self.add_class("diff-view-widget")

    def compose(self) -> ComposeResult:
        # Header
        yield DiffHeaderWidget(
            action=self.action,
            file_path=self.file_diff.file_path,
            summary=self.file_diff.summary,
            success=True
        )

        if not self.collapsed:
            # Render hunks
            total_lines = 0
            for hunk in self.file_diff.hunks:
                if total_lines >= self.max_lines:
                    yield Static(
                        f"... ({len(self.file_diff.hunks)} more hunks)",
                        classes="diff-truncated"
                    )
                    break

                yield DiffHunkWidget(hunk)
                total_lines += len(hunk.lines)


def create_diff_view_from_search_replace(
    content: str,
    file_path: str,
    action: str = "Edit",
    collapsed: bool = False
) -> DiffViewWidget:
    """Create a diff view widget from SEARCH/REPLACE content."""
    file_diff = parse_search_replace_to_file_diff(content, file_path)
    return DiffViewWidget(file_diff, action=action, collapsed=collapsed)


def create_diff_view_from_unified(
    diff_text: str,
    file_path: str,
    action: str = "Edit",
    collapsed: bool = False
) -> DiffViewWidget:
    """Create a diff view widget from unified diff text."""
    file_diff = parse_unified_diff(diff_text, file_path)
    return DiffViewWidget(file_diff, action=action, collapsed=collapsed)
