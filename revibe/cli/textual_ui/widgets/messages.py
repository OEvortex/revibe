from __future__ import annotations

from typing import Any

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Markdown, Static
from textual.widgets._markdown import MarkdownStream

from revibe.cli.textual_ui.widgets.spinner import SpinnerMixin, SpinnerType
from revibe.core.utils import redact_xml_tool_calls


class NonSelectableStatic(Static):
    @property
    def text_selection(self) -> None:
        return None

    @text_selection.setter
    def text_selection(self, value: Any) -> None:
        pass

    def get_selection(self, selection: Any) -> None:
        return None


class ExpandingBorder(NonSelectableStatic):
    def render(self) -> str:
        height = self.size.height
        return "\n".join(["⎢"] * (height - 1) + ["⎣"])

    def on_resize(self) -> None:
        self.refresh()


class UserMessage(Static):
    def __init__(self, content: str, pending: bool = False) -> None:
        super().__init__()
        self.add_class("user-message")
        self._content = content
        self._pending = pending

    def compose(self) -> ComposeResult:
        with Horizontal(classes="user-message-container"):
            yield NonSelectableStatic("> ", classes="user-message-prompt")
            yield Static(self._content, markup=False, classes="user-message-content")
            if self._pending:
                self.add_class("pending")

    async def set_pending(self, pending: bool) -> None:
        if pending == self._pending:
            return

        self._pending = pending

        if pending:
            self.add_class("pending")
            return

        self.remove_class("pending")


class StreamingMessageBase(Static):
    def __init__(self, content: str) -> None:
        super().__init__()
        self._content = content
        self._displayed_content = ""
        self._markdown: Markdown | None = None
        self._stream: MarkdownStream | None = None

    def _get_markdown(self) -> Markdown:
        if self._markdown is None:
            raise RuntimeError(
                "Markdown widget not initialized. compose() must be called first."
            )
        return self._markdown

    def _ensure_stream(self) -> MarkdownStream:
        if self._stream is None:
            self._stream = Markdown.get_stream(self._get_markdown())
        return self._stream

    async def append_content(self, content: str) -> None:
        if not content:
            return

        self._content += content
        if self._should_write_content():
            await self._update_display()

    async def _update_display(self) -> None:
        new_displayed = self._process_content_for_display(self._content)

        if len(new_displayed) > len(self._displayed_content):
            # Append new content to stream - MarkdownStream handles flushing
            diff = new_displayed[len(self._displayed_content) :]
            stream = self._ensure_stream()
            await stream.write(diff)
            self._displayed_content = new_displayed
        elif len(new_displayed) < len(self._displayed_content):
            # Content shrunk (e.g. tag started), reset and re-render
            if self._stream:
                await self._stream.stop()
                self._stream = None
            if self._markdown:
                await self._markdown.update("")
            self._displayed_content = ""
            await self._update_display()

    def _process_content_for_display(self, content: str) -> str:
        """Process content before it is shown in the UI. Overridden by subclasses."""
        return content

    async def write_initial_content(self) -> None:
        if self._content and self._should_write_content():
            await self._update_display()

    async def stop_stream(self) -> None:
        if self._stream is None:
            return

        await self._stream.stop()
        self._stream = None

    def _should_write_content(self) -> bool:
        return True


class AssistantMessage(StreamingMessageBase):
    def __init__(self, content: str) -> None:
        super().__init__(content)
        self.add_class("assistant-message")

    def compose(self) -> ComposeResult:
        with Horizontal(classes="assistant-message-container"):
            yield NonSelectableStatic("● ", classes="assistant-message-dot")
            with Vertical(classes="assistant-message-content"):
                markdown = Markdown("")
                self._markdown = markdown
                yield markdown

    def _process_content_for_display(self, content: str) -> str:
        return redact_xml_tool_calls(content)


class ReasoningMessage(SpinnerMixin, StreamingMessageBase):
    """Modern reasoning/thought display with smooth animations.

    Features:
    - Animated spinner indicator
    - Collapsible content
    - Modern minimal design
    """

    SPINNER_TYPE = SpinnerType.BRAILLE
    SPINNING_TEXT = "Thinking"
    COMPLETED_TEXT = "Thought"
    COMPLETED_ICON = "✓"

    def __init__(self, content: str, collapsed: bool = False) -> None:
        super().__init__(content)
        self.add_class("reasoning-message")
        self.collapsed = collapsed
        self._indicator_widget: Static | None = None
        self._triangle_widget: Static | None = None
        self._status_text_widget: Static | None = None
        self._is_complete = False
        self._thinking_duration: float | None = None
        self.init_spinner()

    def compose(self) -> ComposeResult:
        with Vertical(classes="reasoning-message-wrapper"):
            with Horizontal(classes="reasoning-message-header"):
                # Animated spinner
                self._indicator_widget = NonSelectableStatic(
                    self._spinner.current_frame(), classes="reasoning-indicator"
                )
                yield self._indicator_widget

                # Status text
                self._status_text_widget = Static(
                    self.SPINNING_TEXT, markup=False, classes="reasoning-status-text"
                )
                yield self._status_text_widget

                # Expand/collapse triangle
                self._triangle_widget = NonSelectableStatic(
                    "▼" if not self.collapsed else "▶", classes="reasoning-triangle"
                )
                yield self._triangle_widget

            # Content area with thought content
            markdown = Markdown("", classes="reasoning-message-content")
            markdown.display = not self.collapsed
            self._markdown = markdown
            yield markdown

    def on_mount(self) -> None:
        self.start_spinner_timer()
        # Add thinking class for animation
        wrapper = self.query_one(".reasoning-message-wrapper")
        if wrapper:
            wrapper.add_class("thinking")

    async def on_click(self) -> None:
        await self._toggle_collapsed()

    async def _toggle_collapsed(self) -> None:
        await self.set_collapsed(not self.collapsed)

    def _should_write_content(self) -> bool:
        return not self.collapsed

    async def set_collapsed(self, collapsed: bool) -> None:
        if self.collapsed == collapsed:
            return

        self.collapsed = collapsed

        # Update triangle direction
        if self._triangle_widget:
            self._triangle_widget.update("▶" if collapsed else "▼")

        # Update collapsed class
        if collapsed:
            self.add_class("collapsed")
        else:
            self.remove_class("collapsed")

        if self._markdown:
            self._markdown.display = not collapsed
            if not collapsed and self._content:
                if self._stream is not None:
                    await self._stream.stop()
                    self._stream = None
                await self._markdown.update("")
                self._displayed_content = ""
                await self._update_display()

    def set_thinking_duration(self, duration: float) -> None:
        """Set the thinking duration (in seconds)."""
        self._thinking_duration = duration
        self._update_status_text()

    def _update_status_text(self) -> None:
        """Update status text with duration if available."""
        if not self._status_text_widget:
            return

        status_text = self.COMPLETED_TEXT if self._is_complete else self.SPINNING_TEXT

        if self._thinking_duration is not None and self._is_complete:
            # Format duration similar to tool execution time display
            status_text = f"{self.COMPLETED_TEXT} ({self._thinking_duration:.1f}s)"

        self._status_text_widget.update(status_text)

    def stop_spinning(self, success: bool = True) -> None:
        """Override to update status and styling when complete, then auto-collapse."""
        super().stop_spinning(success)
        self._is_complete = True

        # Update status text with duration if available
        self._update_status_text()

        # Update indicator to checkmark
        if self._indicator_widget:
            self._indicator_widget.update(self.COMPLETED_ICON)
            self._indicator_widget.add_class("success")

        # Update wrapper styling
        try:
            wrapper = self.query_one(".reasoning-message-wrapper")
            if wrapper:
                wrapper.remove_class("thinking")
                wrapper.add_class("completed")
        except Exception:
            pass

        # Auto-collapse after a short delay to let user see the completion
        self.call_later(self._auto_collapse)

    async def _auto_collapse(self) -> None:
        """Auto-collapse the thought when thinking is complete."""
        await self.set_collapsed(True)

    def _process_content_for_display(self, content: str) -> str:
        return redact_xml_tool_calls(content)


class UserCommandMessage(Static):
    def __init__(self, content: str) -> None:
        super().__init__()
        self.add_class("user-command-message")
        self._content = content

    def compose(self) -> ComposeResult:
        with Horizontal(classes="user-command-container"):
            yield ExpandingBorder(classes="user-command-border")
            with Vertical(classes="user-command-content"):
                yield Markdown(self._content)


class InterruptMessage(Static):
    def __init__(self) -> None:
        super().__init__()
        self.add_class("interrupt-message")

    def compose(self) -> ComposeResult:
        with Horizontal(classes="interrupt-container"):
            yield ExpandingBorder(classes="interrupt-border")
            yield Static(
                "Interrupted · What should ReVibe do instead?",
                markup=False,
                classes="interrupt-content",
            )


class BashOutputMessage(Static):
    def __init__(self, command: str, cwd: str, output: str, exit_code: int) -> None:
        super().__init__()
        self.add_class("bash-output-message")
        self._command = command
        self._cwd = cwd
        self._output = output
        self._exit_code = exit_code

    def compose(self) -> ComposeResult:
        with Vertical(classes="bash-output-container"):
            with Horizontal(classes="bash-cwd-line"):
                yield Static(self._cwd, markup=False, classes="bash-cwd")
                yield Static("", classes="bash-cwd-spacer")
                if self._exit_code == 0:
                    yield Static("✓", classes="bash-exit-success")
                else:
                    yield Static("✗", classes="bash-exit-failure")
                    yield Static(f" ({self._exit_code})", classes="bash-exit-code")
            with Horizontal(classes="bash-command-line"):
                yield Static("> ", classes="bash-chevron")
                yield Static(self._command, markup=False, classes="bash-command")
                yield Static("", classes="bash-command-spacer")
            yield Static(self._output, markup=False, classes="bash-output")


class ErrorMessage(Static):
    """Error message display with collapsible full error details.

    Shows expanded by default for easier debugging. When collapsed,
    shows first line of error as summary.
    """

    def __init__(self, error: str, collapsed: bool = False) -> None:
        super().__init__()
        self.add_class("error-message")
        self._error = error
        self.collapsed = collapsed
        self._content_widget: Static | None = None

    def compose(self) -> ComposeResult:
        with Horizontal(classes="error-container"):
            yield ExpandingBorder(classes="error-border")
            self._content_widget = Static(
                self._get_text(), markup=False, classes="error-content"
            )
            yield self._content_widget

    def _get_first_line(self) -> str:
        """Get first meaningful line of error for summary."""
        lines = self._error.split("\n")
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("─"):
                # Truncate if too long
                if len(stripped) > 100:
                    return stripped[:100] + "..."
                return stripped
        return "Error occurred"

    def _get_text(self) -> str:
        if self.collapsed:
            return f"⚠ {self._get_first_line()} (ctrl+o to expand)"
        return f"⚠ Error Details:\n\n{self._error}"

    async def on_click(self) -> None:
        """Toggle collapsed state on click."""
        self.set_collapsed(not self.collapsed)

    def set_collapsed(self, collapsed: bool) -> None:
        if self.collapsed == collapsed:
            return

        self.collapsed = collapsed
        if self._content_widget:
            self._content_widget.update(self._get_text())


class WarningMessage(Static):
    def __init__(self, message: str, show_border: bool = True) -> None:
        super().__init__()
        self.add_class("warning-message")
        self._message = message
        self._show_border = show_border

    def compose(self) -> ComposeResult:
        with Horizontal(classes="warning-container"):
            if self._show_border:
                yield ExpandingBorder(classes="warning-border")
            yield Static(self._message, markup=False, classes="warning-content")
