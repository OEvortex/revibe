"""Enhanced diff view widget for displaying file changes.

This module provides a rich diff view similar to Gemini CLI and QwenCode,
featuring:
- Line numbers on the left
- Colored backgrounds for added/removed lines
- Collapsible diff sections
- Summary header with file path and change description
"""

from __future__ import annotations

from dataclasses import dataclass
import difflib
from pathlib import Path
import re
from typing import Literal

from rich.style import Style
from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical
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

    for _block_idx, (search_text, replace_text) in enumerate(matches):
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


def get_syntax_style(token: str, token_type: str) -> Style:
    """Get Rich Style for a given syntax token type."""
    styles = {
        "keyword": Style(color="#c678dd", bold=True),
        "string": Style(color="#98c379"),
        "number": Style(color="#d19a66"),
        "comment": Style(color="#5c6370", italic=True),
        "function": Style(color="#61afef"),
        "class": Style(color="#e5c07b", bold=True),
        "operator": Style(color="#56b6c2"),
        "variable": Style(color="#e06c75"),
        "decorator": Style(color="#c678dd"),
        "builtin": Style(color="#e5c07b"),
        "default": Style(color="#abb2bf"),
    }
    return styles.get(token_type, styles["default"])


MAX_PATH_DISPLAY_LENGTH = 50
QUOTE_CHARS = {'"', "'"}
OPERATOR_CHARS = set("+-*/%=<>!&|^~")
HIGHLIGHTED_LINE_TYPES = {"added", "removed", "context"}


# Python keywords for syntax highlighting
PYTHON_KEYWORDS = {
    "def", "class", "if", "elif", "else", "for", "while", "try", "except",
    "finally", "with", "as", "import", "from", "return", "yield", "raise",
    "pass", "break", "continue", "in", "is", "not", "and", "or", "None",
    "True", "False", "lambda", "async", "await", "global", "nonlocal",
}

JS_KEYWORDS = {
    "function", "const", "let", "var", "if", "else", "for", "while", "do",
    "switch", "case", "break", "continue", "return", "try", "catch", "finally",
    "throw", "new", "class", "extends", "import", "export", "from", "default",
    "async", "await", "yield", "this", "super", "null", "undefined", "true", "false",
}


def _syntax_base_color(line_type: str) -> str:
    match line_type:
        case "removed":
            return "#e06c75"
        case "added":
            return "#98c379"
        case _:
            return "#abb2bf"


def _consume_string(content: str, start: int) -> tuple[str, int] | None:
    quote = content[start]
    if quote not in QUOTE_CHARS:
        return None

    i = start + 1
    content_len = len(content)
    while i < content_len and content[i] != quote:
        if content[i] == "\\" and i + 1 < content_len:
            i += 2
        else:
            i += 1
    if i < content_len:
        i += 1
    return content[start:i], i


def _consume_comment(content: str, start: int) -> tuple[str, int] | None:
    char = content[start]
    if char == "#":
        return content[start:], len(content)
    if char == "/" and start + 1 < len(content) and content[start + 1] == "/":
        return content[start:], len(content)
    return None


def _consume_number(content: str, start: int) -> tuple[str, int] | None:
    if not content[start].isdigit():
        return None
    i = start
    content_len = len(content)
    while i < content_len and (content[i].isdigit() or content[i] in ".xXoObB"):
        i += 1
    return content[start:i], i


def _consume_word(content: str, start: int) -> tuple[str, int] | None:
    if not (content[start].isalpha() or content[start] == "_"):
        return None
    i = start
    content_len = len(content)
    while i < content_len and (content[i].isalnum() or content[i] == "_"):
        i += 1
    return content[start:i], i


def _consume_operator(content: str, start: int) -> tuple[str, int] | None:
    if content[start] in OPERATOR_CHARS:
        return content[start], start + 1
    return None


def apply_simple_syntax_highlight(content: str, line_type: str) -> Text:
    """Apply simple syntax highlighting to code content."""
    text = Text()
    base_color = _syntax_base_color(line_type)

    i = 0
    content_len = len(content)
    while i < content_len:
        if string_token := _consume_string(content, i):
            value, i = string_token
            text.append(value, style=Style(color="#98c379"))
            continue

        if comment_token := _consume_comment(content, i):
            value, _ = comment_token
            text.append(value, style=Style(color="#5c6370", italic=True))
            break

        if number_token := _consume_number(content, i):
            value, i = number_token
            text.append(value, style=Style(color="#d19a66"))
            continue

        if word_token := _consume_word(content, i):
            word, i = word_token
            if word in PYTHON_KEYWORDS or word in JS_KEYWORDS:
                text.append(word, style=Style(color="#c678dd", bold=True))
            elif word[0].isupper():
                text.append(word, style=Style(color="#e5c07b", bold=True))
            else:
                text.append(word, style=Style(color=base_color))
            continue

        if operator_token := _consume_operator(content, i):
            value, i = operator_token
            text.append(value, style=Style(color="#56b6c2"))
            continue

        text.append(content[i], style=Style(color=base_color))
        i += 1

    return text


class DiffLineWidget(Static):
    """Widget for rendering a single diff line with line numbers, colors, and syntax highlighting.

    Features:
    - Dual line numbers (old file | new file) like git diff
    - Color-coded line indicators (+/-/ )
    - Syntax highlighting for code content
    - Background colors for additions/deletions
    """

    def __init__(
        self,
        diff_line: DiffLine,
        show_line_numbers: bool = True,
        enable_syntax_highlight: bool = True,
        file_extension: str = ""
    ) -> None:
        super().__init__()
        self.diff_line = diff_line
        self.show_line_numbers = show_line_numbers
        self.enable_syntax_highlight = enable_syntax_highlight
        self.file_extension = file_extension
        self._set_classes()

    def _set_classes(self) -> None:
        self.add_class("diff-line")
        self.add_class(f"diff-line-{self.diff_line.line_type}")

    def render(self) -> Text:
        line = self.diff_line
        text = Text()

        if line.line_type == "range":
            # Range header like @@ -1,3 +1,4 @@
            text.append("   ", style=Style(color="#5c6370", dim=True))  # Line number placeholder
            text.append(line.content, style=Style(color="#61afef", bold=True))
            return text

        # Dual line number columns (old | new)
        if self.show_line_numbers:
            if line.line_type == "removed":
                # Show old line number, empty new line number
                old_ln = str(line.old_line_number or line.line_number) if (line.old_line_number or line.line_number) else ""
                text.append(f"{old_ln:>4}", style=Style(color="#e06c75", dim=True))
                text.append(" │", style=Style(color="#3d3d3d"))
                text.append("    ", style=Style(dim=True))  # Empty new line number
                text.append(" ", style=Style(dim=True))
            elif line.line_type == "added":
                # Empty old line number, show new line number
                text.append("    ", style=Style(dim=True))  # Empty old line number
                text.append(" │", style=Style(color="#3d3d3d"))
                new_ln = str(line.line_number) if line.line_number else ""
                text.append(f"{new_ln:>4}", style=Style(color="#98c379", dim=True))
                text.append(" ", style=Style(dim=True))
            else:
                # Context: show both line numbers
                old_ln = str(line.old_line_number) if line.old_line_number else ""
                new_ln = str(line.line_number) if line.line_number else ""
                text.append(f"{old_ln:>4}", style=Style(color="#5c6370", dim=True))
                text.append(" │", style=Style(color="#3d3d3d"))
                text.append(f"{new_ln:>4}", style=Style(color="#5c6370", dim=True))
                text.append(" ", style=Style(dim=True))

        # Sign indicator (+/-/ )
        if line.line_type == "removed":
            text.append("- ", style=Style(color="#e06c75", bold=True))
        elif line.line_type == "added":
            text.append("+ ", style=Style(color="#98c379", bold=True))
        else:
            text.append("  ", style=Style(color="#5c6370"))

        # Content with optional syntax highlighting
        if self.enable_syntax_highlight and line.line_type in HIGHLIGHTED_LINE_TYPES:
            highlighted = apply_simple_syntax_highlight(line.content, line.line_type)
            text.append_text(highlighted)
        elif line.line_type == "removed":
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
        if len(str(path)) <= MAX_PATH_DISPLAY_LENGTH:
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
    """Complete diff view widget with header, hunks, and collapsible sections.

    Similar to the diff views in Gemini CLI and QwenCode TUIs.
    Features:
    - Line numbers on left side
    - Color-coded additions (green) and deletions (red)
    - Syntax highlighting for code
    - Collapsible hunks for large diffs
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
