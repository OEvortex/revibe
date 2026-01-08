from __future__ import annotations

import asyncio
from enum import StrEnum, auto
from pathlib import Path
import shutil
from typing import TYPE_CHECKING, ClassVar

from pydantic import BaseModel, Field

from revibe.core.tools.base import (
    BaseTool,
    BaseToolConfig,
    BaseToolState,
    ToolError,
    ToolPermission,
)
from revibe.core.tools.ui import ToolCallDisplay, ToolResultDisplay, ToolUIData

if TYPE_CHECKING:
    from revibe.core.types import ToolCallEvent, ToolResultEvent


class FindBackend(StrEnum):
    RIPGREP = auto()
    GNU_GREP = auto()


class GrepToolConfig(BaseToolConfig):
    permission: ToolPermission = ToolPermission.ALWAYS

    max_output_bytes: int = Field(
        default=64_000, description="Hard cap for the total size of matched lines."
    )
    default_max_matches: int = Field(
        default=100, description="Default maximum number of matches to return."
    )
    default_timeout: int = Field(
        default=60, description="Default timeout for the search command in seconds."
    )
    exclude_patterns: list[str] = Field(
        default=[
            ".venv/",
            "venv/",
            ".env/",
            "env/",
            "node_modules/",
            ".git/",
            "__pycache__/",
            ".pytest_cache/",
            ".mypy_cache/",
            ".tox/",
            ".nox/",
            ".coverage/",
            "htmlcov/",
            "dist/",
            "build/",
            ".idea/",
            ".vscode/",
            "*.egg-info",
            "*.pyc",
            "*.pyo",
            "*.pyd",
            ".DS_Store",
            "Thumbs.db",
        ],
        description="List of glob patterns to exclude from search (dirs should end with /).",
    )
    ignore_file: str = Field(
        default=".revibeignore",
        description="Path to a file containing ignore patterns (glob format).",
    )


class GrepState(BaseToolState):
    search_history: list[str] = Field(default_factory=list)


class GrepArgs(BaseModel):
    pattern: str = Field(
        description=(
            "REQUIRED. Regex pattern to search for. Supports full regex syntax. "
            "Examples: 'def ', 'TODO|FIXME', 'class\\s+\\w+', 'import\\s+\\w+'. "
            "Special characters may need escaping. Use simple patterns when possible."
        )
    )
    path: str = Field(
        default=".",
        description=(
            "Optional. Directory or file path to search (relative to project root or absolute). "
            "Default: '.' (current directory). Examples: 'src/', 'tests/', './config.py'. "
            "Searches recursively in directories."
        ),
    )
    max_matches: int | None = Field(
        default=None,
        description=(
            "Optional. Maximum number of matches to return. Default: 100. "
            "Use to limit results for common patterns. Output may be truncated if exceeded."
        ),
    )
    use_default_ignore: bool = Field(
        default=True,
        description=(
            "Optional. Whether to respect .gitignore and .revibeignore files. Default: True. "
            "Set to False to search ignored files (e.g., node_modules, .venv). "
            "When using ripgrep, .gitignore is automatically respected."
        ),
    )


class GrepResult(BaseModel):
    matches: str
    match_count: int
    was_truncated: bool = Field(
        description="True if output was cut short by max_matches or max_output_bytes."
    )


class Find(
    BaseTool[GrepArgs, GrepResult, GrepToolConfig, GrepState],
    ToolUIData[GrepArgs, GrepResult],
):
    description: ClassVar[str] = (
        "Search files for text patterns using regex. REQUIRED: 'pattern' (regex to find). "
        "OPTIONAL: 'path' (search directory, default='.'), 'max_matches' (limit results, default=100), "
        "'use_default_ignore' (respect .gitignore, default=True). "
        "Uses ripgrep (rg) if available, falls back to grep. Respects .gitignore by default. "
        "Returns: matches (formatted results), match_count, was_truncated. "
        "Examples: grep(pattern='def ', path='src/'), grep(pattern='TODO|FIXME', max_matches=50)."
    )

    def _detect_backend(self) -> FindBackend:
        if shutil.which("rg"):
            return FindBackend.RIPGREP
        if shutil.which("grep"):
            return FindBackend.GNU_GREP
        raise ToolError(
            "Neither ripgrep (rg) nor grep is installed. "
            "Please install ripgrep: https://github.com/BurntSushi/ripgrep#installation"
        )

    async def run(self, args: GrepArgs) -> GrepResult:
        backend = self._detect_backend()
        self._validate_args(args)
        self.state.search_history.append(args.pattern)

        exclude_patterns = self._collect_exclude_patterns()
        cmd = self._build_command(args, exclude_patterns, backend)
        stdout = await self._execute_search(cmd)

        return self._parse_output(
            stdout, args.max_matches or self.config.default_max_matches
        )

    def _validate_args(self, args: GrepArgs) -> None:
        if not args.pattern.strip():
            raise ToolError("Empty search pattern provided.")

        path_obj = Path(args.path).expanduser()
        if not path_obj.is_absolute():
            path_obj = self.config.effective_workdir / path_obj

        if not path_obj.exists():
            raise ToolError(f"Path does not exist: {args.path}")

    def _collect_exclude_patterns(self) -> list[str]:
        patterns = list(self.config.exclude_patterns)

        codeignore_path = self.config.effective_workdir / self.config.ignore_file
        if codeignore_path.is_file():
            patterns.extend(self._load_codeignore_patterns(codeignore_path))

        return patterns

    def _load_codeignore_patterns(self, codeignore_path: Path) -> list[str]:
        patterns = []
        try:
            content = codeignore_path.read_text("utf-8")
            for line in content.splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    patterns.append(line)
        except OSError:
            pass

        return patterns

    def _build_command(
        self, args: GrepArgs, exclude_patterns: list[str], backend: FindBackend
    ) -> list[str]:
        if backend == FindBackend.RIPGREP:
            return self._build_ripgrep_command(args, exclude_patterns)
        return self._build_gnu_grep_command(args, exclude_patterns)

    def _build_ripgrep_command(
        self, args: GrepArgs, exclude_patterns: list[str]
    ) -> list[str]:
        max_matches = args.max_matches or self.config.default_max_matches

        cmd = [
            "rg",
            "--line-number",
            "--no-heading",
            "--smart-case",
            "--no-binary",
            # Request one extra to detect truncation
            "--max-count",
            str(max_matches + 1),
        ]

        if not args.use_default_ignore:
            cmd.append("--no-ignore")

        for pattern in exclude_patterns:
            cmd.extend(["--glob", f"!{pattern}"])

        cmd.extend(["-e", args.pattern, args.path])

        return cmd

    def _build_gnu_grep_command(
        self, args: GrepArgs, exclude_patterns: list[str]
    ) -> list[str]:
        max_matches = args.max_matches or self.config.default_max_matches

        cmd = ["grep", "-r", "-n", "-I", "-E", f"--max-count={max_matches + 1}"]

        if args.pattern.islower():
            cmd.append("-i")

        for pattern in exclude_patterns:
            if pattern.endswith("/"):
                dir_pattern = pattern.rstrip("/")
                cmd.append(f"--exclude-dir={dir_pattern}")
            else:
                cmd.append(f"--exclude={pattern}")

        cmd.extend(["-e", args.pattern, args.path])

        return cmd

    async def _execute_search(self, cmd: list[str]) -> str:
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.config.effective_workdir),
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(), timeout=self.config.default_timeout
                )
            except TimeoutError:
                proc.kill()
                await proc.wait()
                raise ToolError(
                    f"Search timed out after {self.config.default_timeout}s"
                )

            stdout = (
                stdout_bytes.decode("utf-8", errors="ignore") if stdout_bytes else ""
            )
            stderr = (
                stderr_bytes.decode("utf-8", errors="ignore") if stderr_bytes else ""
            )

            if proc.returncode not in {0, 1}:
                error_msg = stderr or f"Process exited with code {proc.returncode}"
                raise ToolError(f"grep error: {error_msg}")

            return stdout

        except ToolError:
            raise
        except Exception as exc:
            raise ToolError(f"Error running grep: {exc}") from exc

    def _parse_output(self, stdout: str, max_matches: int) -> GrepResult:
        output_lines = stdout.splitlines() if stdout else []

        truncated_lines = output_lines[:max_matches]
        truncated_output = "\n".join(truncated_lines)

        was_truncated = (
            len(output_lines) > max_matches
            or len(truncated_output) > self.config.max_output_bytes
        )

        final_output = truncated_output[: self.config.max_output_bytes]

        return GrepResult(
            matches=final_output,
            match_count=len(truncated_lines),
            was_truncated=was_truncated,
        )

    @classmethod
    def get_call_display(cls, event: ToolCallEvent) -> ToolCallDisplay:
        if not isinstance(event.args, GrepArgs):
            return ToolCallDisplay(summary="Find")

        MAX_PATTERN_DISPLAY_LENGTH = 20
        pattern = event.args.pattern
        if len(pattern) > MAX_PATTERN_DISPLAY_LENGTH:
            pattern = pattern[: MAX_PATTERN_DISPLAY_LENGTH - 3] + "..."

        summary = f"Find ({pattern})"
        return ToolCallDisplay(summary=summary)

    @classmethod
    def get_result_display(cls, event: ToolResultEvent) -> ToolResultDisplay:
        if not isinstance(event.result, GrepResult):
            return ToolResultDisplay(
                success=False, message=event.error or event.skip_reason or "No result"
            )

        message = f"Found {event.result.match_count} matches"
        if event.result.was_truncated:
            message += " (truncated)"

        warnings = []
        if event.result.was_truncated:
            warnings.append("Output was truncated due to size/match limits")

        return ToolResultDisplay(success=True, message=message, warnings=warnings)

    @classmethod
    def get_status_text(cls) -> str:
        return "Finding files"
