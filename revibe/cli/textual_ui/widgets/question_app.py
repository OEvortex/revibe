from __future__ import annotations

import itertools
from typing import ClassVar

from textual import events
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Container, Horizontal, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Input, Static

from revibe.core.tools.builtins.ask_user_question import QuestionItem, QuestionOption


class QuestionApp(Container):
    """Interactive question UI for ask_user_question tool.

    Supports single-select and multi-select questions with 2-4 options
    each, plus an automatic "Other" option for free-text responses.
    Multiple questions are shown as tabs.
    """

    MAX_OPTIONS: ClassVar[int] = 4

    can_focus = True
    can_focus_children = False

    current_question_idx: reactive[int] = reactive(0)
    selected_option: reactive[int] = reactive(0)

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("up", "move_up", "Up", show=False),
        Binding("down", "move_down", "Down", show=False),
        Binding("enter", "select", "Select", show=False),
        Binding("escape", "cancel", "Cancel", show=False),
    ]

    class Answered(Message):
        def __init__(self, answers: list[dict[str, list[str]]]) -> None:
            super().__init__()
            self.answers = answers

    class Cancelled(Message):
        pass

    def __init__(self, questions: list[QuestionItem]) -> None:
        super().__init__(id="question-app")
        self.questions = questions

        self.answers: dict[int, tuple[str, bool]] = {}
        self.multi_selections: dict[int, set[int]] = {}
        self.other_texts: dict[int, str] = {}

        self.option_widgets: list[Static] = []
        self.title_widget: Static | None = None
        self.other_prefix: Static | None = None
        self.other_input: Input | None = None
        self.other_static: Static | None = None
        self.submit_widget: Static | None = None
        self.help_widget: Static | None = None
        self.tabs_widget: Static | None = None

    @property
    def _current_question(self) -> QuestionItem:
        return self.questions[self.current_question_idx]

    @property
    def _has_other(self) -> bool:
        return True

    @property
    def _total_options(self) -> int:
        base = len(self._current_question.options)
        if self._has_other:
            base += 1
        if self._current_question.multiple:
            base += 1
        return base

    @property
    def _other_option_idx(self) -> int:
        if not self._has_other:
            return -1
        return len(self._current_question.options)

    @property
    def _submit_option_idx(self) -> int:
        if not self._current_question.multiple:
            return -1
        if self._has_other:
            return self._other_option_idx + 1
        return len(self._current_question.options)

    @property
    def _is_other_selected(self) -> bool:
        return self._has_other and self.selected_option == self._other_option_idx

    @property
    def _is_submit_selected(self) -> bool:
        return (
            self._current_question.multiple
            and self.selected_option == self._submit_option_idx
        )

    def compose(self) -> ComposeResult:
        with Vertical(id="question-content"):
            if len(self.questions) > 1:
                self.tabs_widget = Static("", classes="question-tabs")
                yield self.tabs_widget

            self.title_widget = Static("", classes="question-title")
            yield self.title_widget

            for _ in range(self.MAX_OPTIONS):
                widget = Static("", classes="question-option")
                self.option_widgets.append(widget)
                yield widget

            with Horizontal(classes="question-other-row"):
                self.other_prefix = Static("", classes="question-other-prefix")
                yield self.other_prefix
                self.other_input = Input(
                    placeholder="Type your answer...", classes="question-other-input"
                )
                yield self.other_input
                self.other_static = Static(
                    "Type your answer...", classes="question-other-static"
                )
                yield self.other_static

            self.submit_widget = Static("", classes="question-submit")
            yield self.submit_widget

            self.help_widget = Static("", classes="question-help")
            yield self.help_widget

    async def on_mount(self) -> None:
        self._update_display()
        self.focus()

    def _watch_current_question_idx(self) -> None:
        self._update_display()

    def _watch_selected_option(self) -> None:
        self._update_display()

    def _update_display(self) -> None:
        self._update_tabs()
        self._update_title()
        self._update_options()
        self._update_other_row()
        self._update_submit()
        self._update_help()

    def _update_tabs(self) -> None:
        if not self.tabs_widget or len(self.questions) <= 1:
            return
        tabs = []
        for i, question in enumerate(self.questions):
            header = question.header or f"Q{i + 1}"
            if i in self.answers:
                header += " ✓"
            if i == self.current_question_idx:
                tabs.append(f"[{header}]")
            else:
                tabs.append(f" {header} ")
        self.tabs_widget.update("  ".join(tabs))

    def _update_title(self) -> None:
        if self.title_widget:
            self.title_widget.update(self._current_question.question)

    def _update_options(self) -> None:
        q = self._current_question
        options = q.options
        is_multi = q.multiple
        multi_selected = self.multi_selections.get(self.current_question_idx, set())

        for i, widget in enumerate(self.option_widgets):
            if i < len(options):
                is_focused = i == self.selected_option
                is_selected = i in multi_selected
                self._render_option(
                    widget, i, options[i], is_multi, is_focused, is_selected
                )
            else:
                widget.update("")
                widget.display = False

    def _format_option_prefix(
        self, idx: int, is_focused: bool, is_multi: bool, is_selected: bool
    ) -> str:
        cursor = "› " if is_focused else "  "
        if is_multi:
            check = "[x]" if is_selected else "[ ]"
            return f"{cursor}{idx + 1}. {check} "
        return f"{cursor}{idx + 1}. "

    def _render_option(
        self,
        widget: Static,
        idx: int,
        opt: QuestionOption,
        is_multi: bool,
        is_focused: bool,
        is_selected: bool,
    ) -> None:
        prefix = self._format_option_prefix(idx, is_focused, is_multi, is_selected)
        text = f"{prefix}{opt.label}"

        if opt.description:
            text += f" - {opt.description}"

        widget.update(text)
        widget.display = True
        widget.remove_class("question-option-focused")
        if is_focused:
            widget.add_class("question-option-focused")

    def _update_other_row(self) -> None:
        if not self.other_prefix or not self.other_input or not self.other_static:
            return

        if not self._has_other:
            self.other_prefix.display = False
            self.other_input.display = False
            self.other_static.display = False
            return

        q = self._current_question
        is_multi = q.multiple
        multi_selected = self.multi_selections.get(self.current_question_idx, set())
        other_idx = self._other_option_idx
        is_focused = self._is_other_selected
        is_selected = other_idx in multi_selected

        prefix = self._format_option_prefix(
            other_idx, is_focused, is_multi, is_selected
        )
        self.other_prefix.update(prefix)

        stored_text = self.other_texts.get(self.current_question_idx, "")
        if self.other_input.value != stored_text:
            self.other_input.value = stored_text

        show_input = is_focused or bool(stored_text)

        self.other_prefix.display = True
        self.other_input.display = show_input
        self.other_static.display = not show_input

        self.other_prefix.remove_class("question-option-focused")
        if is_focused:
            self.other_prefix.add_class("question-option-focused")

        if is_focused and show_input:
            self.other_input.focus()
        elif not is_focused and not self._is_submit_selected:
            self.focus()

    def _update_submit(self) -> None:
        if not self.submit_widget:
            return

        q = self._current_question
        if not q.multiple:
            self.submit_widget.display = False
            return

        self.submit_widget.display = True
        is_focused = self._is_submit_selected
        cursor = "› " if is_focused else "  "

        text = (
            "Submit"
            if len(set(self.answers.keys()) | {self.current_question_idx})
            == len(self.questions)
            else "Next"
        )
        self.submit_widget.update(f"{cursor}   {text} →")
        self.submit_widget.remove_class("question-option-focused")
        if is_focused:
            self.submit_widget.add_class("question-option-focused")
            self.focus()

    def _update_help(self) -> None:
        if not self.help_widget:
            return
        if self._current_question.multiple:
            help_text = "↑↓ navigate  Enter toggle  Esc cancel"
        else:
            help_text = "↑↓ navigate  Enter select  Esc cancel"
        if len(self.questions) > 1:
            help_text = "←→ questions  " + help_text
        self.help_widget.update(help_text)

    def _store_other_text(self) -> None:
        if self.other_input:
            self.other_texts[self.current_question_idx] = self.other_input.value

    def action_move_up(self) -> None:
        self.selected_option = (self.selected_option - 1) % self._total_options

    def action_move_down(self) -> None:
        self.selected_option = (self.selected_option + 1) % self._total_options

    def _switch_question(self, new_idx: int) -> None:
        self.current_question_idx = new_idx
        self.selected_option = 0

    def action_next_question(self) -> None:
        if self._is_other_selected:
            other_text = self.other_texts.get(self.current_question_idx, "").strip()
            if not other_text:
                return
        new_idx = (self.current_question_idx + 1) % len(self.questions)
        self._switch_question(new_idx)

    def action_prev_question(self) -> None:
        new_idx = (self.current_question_idx - 1) % len(self.questions)
        self._switch_question(new_idx)

    def action_select(self) -> None:
        if self._current_question.multiple:
            self._handle_multi_select_action()
        else:
            self._handle_single_select_action()

    def _handle_multi_select_action(self) -> None:
        if self._is_submit_selected:
            self._save_current_answer()
            self._advance_or_submit()
        elif self._is_other_selected:
            if self.other_input:
                self.other_input.focus()
        else:
            self._toggle_selection(self.selected_option)

    def _handle_single_select_action(self) -> None:
        if self._is_other_selected:
            if self.other_input:
                other_text = self.other_texts.get(self.current_question_idx, "").strip()
                if other_text:
                    self._save_current_answer()
                    self._advance_or_submit()
                else:
                    self.other_input.focus()
        else:
            self._save_current_answer()
            self._advance_or_submit()

    def _toggle_selection(self, option_idx: int) -> None:
        selections = self.multi_selections.setdefault(self.current_question_idx, set())
        if option_idx in selections:
            selections.discard(option_idx)
        else:
            selections.add(option_idx)
        self._update_display()

    def _advance_or_submit(self) -> None:
        if self._all_answered():
            self._submit()
        else:
            new_idx = next(
                i
                for i in itertools.chain(
                    range(self.current_question_idx + 1, len(self.questions)),
                    range(self.current_question_idx),
                )
                if i not in self.answers
            )
            self._switch_question(new_idx)

    def action_cancel(self) -> None:
        self.post_message(self.Cancelled())

    def on_input_submitted(self, _event: Input.Submitted) -> None:
        if not self.other_input or not self.other_input.value.strip():
            return

        q = self._current_question
        if q.multiple:
            self.selected_option = self._submit_option_idx
        else:
            self._save_current_answer()
            self._advance_or_submit()

    def on_input_changed(self, _event: Input.Changed) -> None:
        self._store_other_text()
        self._sync_other_selection_with_text()
        self._update_display()

    def _sync_other_selection_with_text(self) -> None:
        if not self._current_question.multiple or not self.other_input:
            return

        other_idx = self._other_option_idx
        selections = self.multi_selections.setdefault(self.current_question_idx, set())
        has_text = bool(self.other_input.value.strip())

        if has_text and other_idx not in selections:
            selections.add(other_idx)
        elif not has_text and other_idx in selections:
            selections.discard(other_idx)

    def on_key(self, event: events.Key) -> None:
        if len(self.questions) <= 1:
            return
        if self.other_input and self.other_input.has_focus:
            return
        if event.key == "left":
            self.action_prev_question()
            event.stop()
        elif event.key == "right":
            self.action_next_question()
            event.stop()

    def _save_current_answer(self) -> None:
        if self._current_question.multiple:
            self._save_multi_select_answer()
        else:
            self._save_single_select_answer()

    def _save_multi_select_answer(self) -> None:
        q = self._current_question
        idx = self.current_question_idx
        selections = self.multi_selections.get(idx, set())

        if not selections:
            return

        other_text = self.other_texts.get(idx, "").strip()
        answers = []
        other_idx = len(q.options)

        for sel_idx in sorted(selections):
            if sel_idx < len(q.options):
                answers.append(q.options[sel_idx].label)
            elif sel_idx == other_idx and other_text:
                answers.append(other_text)

        if answers:
            self.answers[idx] = (", ".join(answers), False)

    def _save_single_select_answer(self) -> None:
        idx = self.current_question_idx

        if self._is_other_selected:
            other_text = self.other_texts.get(idx, "").strip()
            if other_text:
                self.answers[idx] = (other_text, True)
        else:
            self.answers[idx] = (
                self._current_question.options[self.selected_option].label,
                False,
            )

    def _all_answered(self) -> bool:
        return all(i in self.answers for i in range(len(self.questions)))

    def _submit(self) -> None:
        result: list[dict[str, list[str]]] = []
        for i, q in enumerate(self.questions):
            answer_text, _ = self.answers.get(i, ("", False))
            result.append({q.question: [answer_text]})
        self.post_message(self.Answered(answers=result))

    def on_blur(self, _event: events.Blur) -> None:
        self.call_after_refresh(self._refocus_if_needed)

    def on_input_blurred(self, _event: Input.Blurred) -> None:
        self.call_after_refresh(self._refocus_if_needed)

    def _refocus_if_needed(self) -> None:
        if self.has_focus or (self.other_input and self.other_input.has_focus):
            return
        self.focus()
