from __future__ import annotations

import difflib
from pathlib import Path
import re
import shutil
from typing import ClassVar, NamedTuple, final

import aiofiles
from pydantic import BaseModel, Field

from revibe.core.tools.base import BaseTool, BaseToolConfig, BaseToolState, ToolError
from revibe.core.tools.ui import ToolCallDisplay, ToolResultDisplay, ToolUIData
from revibe.core.types import ToolCallEvent, ToolResultEvent

SEARCH_REPLACE_BLOCK_RE = re.compile(
    r"<{5,} SEARCH\r?\n(.*?)\r?\n?={5,}\r?\n(.*?)\r?\n?>{5,} REPLACE", flags=re.DOTALL
)

SEARCH_REPLACE_BLOCK_WITH_FENCE_RE = re.compile(
    r"```[\s\S]*?\n<{5,} SEARCH\r?\n(.*?)\r?\n?={5,}\r?\n(.*?)\r?\n?>{5,} REPLACE\s*\n```",
    flags=re.DOTALL,
)


class SearchReplaceBlock(NamedTuple):
    search: str
    replace: str


class FuzzyMatch(NamedTuple):
    similarity: float
    start_line: int
    end_line: int
    text: str


class BlockApplyResult(NamedTuple):
    content: str
    applied: int
    errors: list[str]
    warnings: list[str]


class SearchReplaceArgs(BaseModel):
    file_path: str
    content: str


class SearchReplaceResult(BaseModel):
    file: str
    blocks_applied: int
    lines_changed: int
    content: str
    warnings: list[str] = Field(default_factory=list)


class SearchReplaceConfig(BaseToolConfig):
    max_content_size: int = 100_000
    create_backup: bool = False
    fuzzy_threshold: float = 0.9


class SearchReplaceState(BaseToolState):
    pass


class SearchReplace(
    BaseTool[
        SearchReplaceArgs, SearchReplaceResult, SearchReplaceConfig, SearchReplaceState
    ],
    ToolUIData[SearchReplaceArgs, SearchReplaceResult],
):
    description: ClassVar[str] = (
        "Make targeted edits to a file using SEARCH/REPLACE blocks. "
        "WORKFLOW: 1) Read file first with read_file  2) Copy EXACT text to change  3) Create SEARCH/REPLACE block. "
        "FORMAT: <<<<<<< SEARCH\\n[exact_text]\\n=======\\n[new_text]\\n>>>>>>> REPLACE. "
        "RULES: SEARCH must match file exactly (whitespace matters). Multiple blocks run in order. First match only."
    )

    @classmethod
    def get_call_display(cls, event: ToolCallEvent) -> ToolCallDisplay:
        if not isinstance(event.args, SearchReplaceArgs):
            return ToolCallDisplay(summary="Editing file")

        path = Path(event.args.file_path)
        # Count blocks in content
        content = event.args.content
        block_count = content.count("SEARCH") if content else 0

        # More descriptive summary
        if block_count > 1:
            summary = f"Editing {path.name} ({block_count} changes)"
        else:
            summary = f"Editing {path.name}"

        return ToolCallDisplay(summary=summary, content=event.args.content)

    @classmethod
    def get_result_display(cls, event: ToolResultEvent) -> ToolResultDisplay:
        if isinstance(event.result, SearchReplaceResult):
            blocks = event.result.blocks_applied
            lines = event.result.lines_changed

            # Build a more informative message
            if blocks == 1:
                msg = f"✓ Applied 1 change"
            else:
                msg = f"✓ Applied {blocks} changes"

            if lines != 0:
                msg += f" ({'+' if lines > 0 else ''}{lines} lines)"

            return ToolResultDisplay(
                success=True,
                message=msg,
                warnings=event.result.warnings,
            )

        return ToolResultDisplay(success=True, message="✓ File edited")

    @classmethod
    def get_status_text(cls) -> str:
        return "Editing file"

    @final
    async def run(self, args: SearchReplaceArgs) -> SearchReplaceResult:
        file_path, search_replace_blocks = self._prepare_and_validate_args(args)

        original_content = await self._read_file(file_path)

        block_result = self._apply_blocks(
            original_content,
            search_replace_blocks,
            file_path,
            self.config.fuzzy_threshold,
        )

        if block_result.errors:
            # Build a clear, actionable error message
            error_header = f"❌ Failed to edit {file_path.name}\n"
            error_details = "\n" + "─" * 50 + "\n".join(block_result.errors)

            error_message = error_header + error_details

            if block_result.warnings:
                error_message += "\n\n⚠ Warnings:\n" + "\n".join(block_result.warnings)

            raise ToolError(error_message)

        modified_content = block_result.content

        # Calculate line changes
        if modified_content == original_content:
            lines_changed = 0
        else:
            original_lines = len(original_content.splitlines())
            new_lines = len(modified_content.splitlines())
            lines_changed = new_lines - original_lines

            try:
                if self.config.create_backup:
                    await self._backup_file(file_path)
            except Exception:
                pass

            await self._write_file(file_path, modified_content)

        return SearchReplaceResult(
            file=str(file_path),
            blocks_applied=block_result.applied,
            lines_changed=lines_changed,
            warnings=block_result.warnings,
            content=args.content,
        )

    @final
    def _prepare_and_validate_args(
        self, args: SearchReplaceArgs
    ) -> tuple[Path, list[SearchReplaceBlock]]:
        file_path_str = args.file_path.strip()
        content = args.content.strip()

        if not file_path_str:
            raise ToolError("File path cannot be empty")

        if len(content) > self.config.max_content_size:
            raise ToolError(
                f"Content size ({len(content)} bytes) exceeds max_content_size "
                f"({self.config.max_content_size} bytes)"
            )

        if not content:
            raise ToolError("Empty content provided")

        project_root = self.config.effective_workdir
        file_path = Path(file_path_str).expanduser()
        if not file_path.is_absolute():
            file_path = project_root / file_path
        file_path = file_path.resolve()

        if not file_path.exists():
            raise ToolError(f"File does not exist: {file_path}")

        if not file_path.is_file():
            raise ToolError(f"Path is not a file: {file_path}")

        search_replace_blocks = self._parse_search_replace_blocks(content)
        if not search_replace_blocks:
            # Provide helpful error with the actual content received
            content_preview = content[:200] + "..." if len(content) > 200 else content
            raise ToolError(
                f"❌ Invalid SEARCH/REPLACE format\n\n"
                f"Could not parse any valid blocks from content.\n\n"
                f"Expected format:\n"
                f"┌─────────────────────────────────\n"
                f"│ <<<<<<< SEARCH\n"
                f"│ [exact text from file]\n"
                f"│ =======\n"
                f"│ [replacement text]\n"
                f"│ >>>>>>> REPLACE\n"
                f"└─────────────────────────────────\n\n"
                f"Received content:\n{content_preview}\n\n"
                f"Common issues:\n"
                f"• Missing/wrong delimiters (need 7+ chars: <<<<<<< not <<<<<)\n"
                f"• Missing ======= separator between search and replace\n"
                f"• Content wrapped in extra formatting"
            )

        return file_path, search_replace_blocks

    async def _read_file(self, file_path: Path) -> str:
        try:
            async with aiofiles.open(file_path, encoding="utf-8") as f:
                return await f.read()
        except UnicodeDecodeError as e:
            raise ToolError(f"Unicode decode error reading {file_path}: {e}") from e
        except PermissionError:
            raise ToolError(f"Permission denied reading file: {file_path}")
        except Exception as e:
            raise ToolError(f"Unexpected error reading {file_path}: {e}") from e

    async def _backup_file(self, file_path: Path) -> None:
        shutil.copy2(file_path, file_path.with_suffix(file_path.suffix + ".bak"))

    async def _write_file(self, file_path: Path, content: str) -> None:
        try:
            async with aiofiles.open(file_path, mode="w", encoding="utf-8") as f:
                await f.write(content)
        except PermissionError:
            raise ToolError(f"Permission denied writing to file: {file_path}")
        except OSError as e:
            raise ToolError(f"OS error writing to {file_path}: {e}") from e
        except Exception as e:
            raise ToolError(f"Unexpected error writing to {file_path}: {e}") from e

    @final
    @staticmethod
    def _apply_blocks(
        content: str,
        blocks: list[SearchReplaceBlock],
        filepath: Path,
        fuzzy_threshold: float = 0.9,
    ) -> BlockApplyResult:
        applied = 0
        errors: list[str] = []
        warnings: list[str] = []
        current_content = content

        for i, (search, replace) in enumerate(blocks, 1):
            if search not in current_content:
                # Find helpful context for debugging
                context = SearchReplace._find_search_context(current_content, search)
                fuzzy_context = SearchReplace._find_fuzzy_match_context(
                    current_content, search, fuzzy_threshold
                )

                # Build clear, visual error message
                search_preview = search[:300] + "..." if len(search) > 300 else search
                search_lines = search.count('\n') + 1

                error_msg = (
                    f"\n╭─ Block {i} Failed ─────────────────────────────────\n"
                    f"│ Could not find SEARCH text in {filepath.name}\n"
                    f"╰──────────────────────────────────────────────────────\n\n"
                )

                # Show what was searched for
                error_msg += (
                    f"🔍 Looking for ({search_lines} lines):\n"
                    f"┌──────────────────────────────────────\n"
                )
                for line in search_preview.split('\n'):
                    # Show whitespace visually
                    visible_line = line.replace(' ', '·').replace('\t', '→   ')
                    error_msg += f"│ {visible_line}\n"
                error_msg += f"└──────────────────────────────────────\n\n"

                # Add context analysis
                error_msg += f"📍 Context Analysis:\n{context}\n"

                if fuzzy_context:
                    error_msg += f"\n{fuzzy_context}\n"

                # Actionable fixes
                error_msg += (
                    "\n💡 How to fix:\n"
                    "  1. Run read_file first to see the EXACT current content\n"
                    "  2. Copy the text directly - don't retype it\n"
                    "  3. Whitespace must match exactly (spaces ≠ tabs, · = space, → = tab)\n"
                    "  4. Check if a previous block already changed this text"
                )

                errors.append(error_msg)
                continue

            occurrences = current_content.count(search)
            if occurrences > 1:
                warning_msg = (
                    f"⚠ Block {i}: Found {occurrences} matches, replacing first only. "
                    f"Add more context to target specific occurrence."
                )
                warnings.append(warning_msg)

            current_content = current_content.replace(search, replace, 1)
            applied += 1

        return BlockApplyResult(
            content=current_content, applied=applied, errors=errors, warnings=warnings
        )

    @final
    @staticmethod
    def _find_fuzzy_match_context(
        content: str, search_text: str, threshold: float = 0.9
    ) -> str | None:
        best_match = SearchReplace._find_best_fuzzy_match(
            content, search_text, threshold
        )

        if not best_match:
            return None

        diff = SearchReplace._create_unified_diff(
            search_text, best_match.text, "YOUR SEARCH", "ACTUAL FILE"
        )

        similarity_pct = best_match.similarity * 100

        # Visual similarity indicator
        if similarity_pct >= 95:
            match_quality = "🟢 Very close"
        elif similarity_pct >= 90:
            match_quality = "🟡 Close"
        else:
            match_quality = "🟠 Partial"

        return (
            f"🔄 {match_quality} match found ({similarity_pct:.0f}% similar) at lines {best_match.start_line}-{best_match.end_line}:\n\n"
            f"Differences between your SEARCH and actual file content:\n"
            f"(- = your search, + = actual file)\n"
            f"```diff\n{diff}\n```\n"
            f"💡 Copy the text from the '+' lines above to fix your SEARCH block."
        )

    @final
    @staticmethod
    def _find_best_fuzzy_match(  # noqa: PLR0914
        content: str, search_text: str, threshold: float = 0.9
    ) -> FuzzyMatch | None:
        content_lines = content.split("\n")
        search_lines = search_text.split("\n")
        window_size = len(search_lines)

        if window_size == 0:
            return None

        non_empty_search = [line for line in search_lines if line.strip()]
        if not non_empty_search:
            return None

        first_anchor = non_empty_search[0]
        last_anchor = (
            non_empty_search[-1] if len(non_empty_search) > 1 else first_anchor
        )

        candidate_starts = set()
        spread = 5

        for i, line in enumerate(content_lines):
            if first_anchor in line or last_anchor in line:
                start_min = max(0, i - spread)
                start_max = min(len(content_lines) - window_size + 1, i + spread + 1)
                for s in range(start_min, start_max):
                    candidate_starts.add(s)

        if not candidate_starts:
            max_positions = min(len(content_lines) - window_size + 1, 100)
            candidate_starts = set(range(0, max_positions))

        best_match = None
        best_similarity = 0.0

        for start in candidate_starts:
            end = start + window_size
            window_text = "\n".join(content_lines[start:end])

            matcher = difflib.SequenceMatcher(None, search_text, window_text)
            similarity = matcher.ratio()

            if similarity >= threshold and similarity > best_similarity:
                best_similarity = similarity
                best_match = FuzzyMatch(
                    similarity=similarity,
                    start_line=start + 1,  # 1-based line numbers
                    end_line=end,
                    text=window_text,
                )

        return best_match

    @final
    @staticmethod
    def _create_unified_diff(
        text1: str, text2: str, label1: str = "SEARCH", label2: str = "CLOSEST MATCH"
    ) -> str:
        lines1 = text1.splitlines(keepends=True)
        lines2 = text2.splitlines(keepends=True)

        lines1 = [line if line.endswith("\n") else line + "\n" for line in lines1]
        lines2 = [line if line.endswith("\n") else line + "\n" for line in lines2]

        diff = difflib.unified_diff(
            lines1, lines2, fromfile=label1, tofile=label2, lineterm="", n=3
        )

        diff_lines = list(diff)

        if diff_lines and not diff_lines[0].startswith("==="):
            diff_lines.insert(2, "=" * 67 + "\n")

        result = "".join(diff_lines)

        max_chars = 2000
        if len(result) > max_chars:
            result = result[:max_chars] + "\n...(diff truncated)"

        return result.rstrip()

    @final
    @staticmethod
    def _parse_search_replace_blocks(content: str) -> list[SearchReplaceBlock]:
        """Parse SEARCH/REPLACE blocks from content.

        Supports two formats:
        1. With code block fences (```...```)
        2. Without code block fences
        """
        matches = SEARCH_REPLACE_BLOCK_WITH_FENCE_RE.findall(content)

        if not matches:
            matches = SEARCH_REPLACE_BLOCK_RE.findall(content)

        return [
            SearchReplaceBlock(
                search=search.rstrip("\r\n"), replace=replace.rstrip("\r\n")
            )
            for search, replace in matches
        ]

    @final
    @staticmethod
    def _find_search_context(
        content: str, search_text: str, max_context: int = 3
    ) -> str:
        lines = content.split("\n")
        search_lines = search_text.split("\n")

        if not search_lines:
            return "❌ Search text is empty"

        first_search_line = search_lines[0].strip()
        if not first_search_line:
            return "❌ First line of search text is empty or whitespace-only"

        # Find potential matches for the first line
        matches = []
        for i, line in enumerate(lines):
            if first_search_line in line:
                matches.append(i)

        if not matches:
            # Try to find similar lines
            first_words = first_search_line.split()[:3]
            if first_words:
                partial_matches = []
                for i, line in enumerate(lines):
                    if any(word in line for word in first_words):
                        partial_matches.append(i)

                if partial_matches:
                    result = f"❌ Exact first line not found.\n\n"
                    result += f"Looking for: \"{first_search_line[:60]}{'...' if len(first_search_line) > 60 else ''}\"\n\n"
                    result += f"Similar lines found at:\n"
                    for idx in partial_matches[:3]:
                        result += f"  Line {idx + 1}: {lines[idx][:70]}{'...' if len(lines[idx]) > 70 else ''}\n"
                    return result

            return f"❌ First line of search not found anywhere in file:\n   \"{first_search_line[:80]}{'...' if len(first_search_line) > 80 else ''}\""

        # Show where the first line WAS found
        context_lines = []
        found_count = len(matches)

        if found_count == 1:
            context_lines.append(f"✓ First line found at line {matches[0] + 1}, but full block doesn't match.")
        else:
            context_lines.append(f"✓ First line found {found_count} times (lines: {', '.join(str(m+1) for m in matches[:5])}{'...' if found_count > 5 else ''})")

        context_lines.append("\nShowing context where first line appears:\n")

        for match_idx in matches[:2]:  # Show max 2 potential locations
            start = max(0, match_idx - max_context)
            end = min(len(lines), match_idx + max_context + 1)

            context_lines.append(f"┌─ Around line {match_idx + 1} ─────────────────────────")
            for i in range(start, end):
                if i == match_idx:
                    marker = "▶"
                    style = ""
                else:
                    marker = "│"
                    style = ""
                line_content = lines[i][:80] + ("..." if len(lines[i]) > 80 else "")
                context_lines.append(f"{marker} {i + 1:4d} │ {line_content}")
            context_lines.append("└────────────────────────────────────────────")

        return "\n".join(context_lines)
