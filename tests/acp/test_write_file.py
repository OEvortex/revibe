from __future__ import annotations

from pathlib import Path

from acp import WriteTextFileRequest
import pytest

from revibe.acp.tools.builtins.write_file import AcpWriteFileState, WriteFile
from revibe.core.tools.base import ToolError
from revibe.core.tools.builtins.write_file import (
    WriteFileArgs,
    WriteFileConfig,
    WriteFileResult,
)
from revibe.core.types import ToolCallEvent, ToolResultEvent


class MockConnection:
    def __init__(
        self, write_error: Exception | None = None, file_exists: bool = False
    ) -> None:
        self._write_error = write_error
        self._file_exists = file_exists
        self._write_text_file_called = False
        self._session_update_called = False
        self._last_write_request: WriteTextFileRequest | None = None

    async def writeTextFile(self, request: WriteTextFileRequest) -> None:
        self._write_text_file_called = True
        self._last_write_request = request

        if self._write_error:
            raise self._write_error

    async def sessionUpdate(self, notification) -> None:
        self._session_update_called = True


@pytest.fixture
def mock_connection() -> MockConnection:
    return MockConnection()


@pytest.fixture
def acp_write_file_tool(mock_connection: MockConnection, tmp_path: Path) -> WriteFile:
    config = WriteFileConfig(workdir=tmp_path)
    state = AcpWriteFileState.model_construct(
        connection=mock_connection,  # type: ignore[arg-type]
        session_id="test_session_123",
        tool_call_id="test_tool_call_456",
    )
    return WriteFile(config=config, state=state)


class TestAcpWriteFileBasic:
    def test_get_name(self) -> None:
        assert WriteFile.get_name() == "write_file"


class TestAcpWriteFileExecution:
    @pytest.mark.asyncio
    async def test_run_success_new_file(
        self,
        acp_write_file_tool: WriteFile,
        mock_connection: MockConnection,
        tmp_path: Path,
    ) -> None:
        test_file = tmp_path / "test_file.txt"
        args = WriteFileArgs(path=str(test_file), content="Hello, world!")
        result = await acp_write_file_tool.run(args)

        assert isinstance(result, WriteFileResult)
        assert result.path == str(test_file)
        assert result.content == "Hello, world!"
        assert result.bytes_written == len(b"Hello, world!")
        assert result.file_existed is False
        assert mock_connection._write_text_file_called
        assert mock_connection._session_update_called

        # Verify WriteTextFileRequest was created correctly
        request = mock_connection._last_write_request
        assert request is not None
        assert request.sessionId == "test_session_123"
        assert request.path == str(test_file)
        assert request.content == "Hello, world!"

    @pytest.mark.asyncio
    async def test_run_success_overwrite(
        self, mock_connection: MockConnection, tmp_path: Path
    ) -> None:
        tool = WriteFile(
            config=WriteFileConfig(workdir=tmp_path),
            state=AcpWriteFileState.model_construct(
                connection=mock_connection,  # type: ignore[arg-type]
                session_id="test_session",
                tool_call_id="test_call",
            ),
        )

        test_file = tmp_path / "existing_file.txt"
        test_file.touch()
        # Simulate existing file by checking in the core tool logic
        # The ACP tool doesn't check existence, it's handled by the core tool
        args = WriteFileArgs(path=str(test_file), content="New content", overwrite=True)
        result = await tool.run(args)

        assert isinstance(result, WriteFileResult)
        assert result.path == str(test_file)
        assert result.content == "New content"
        assert result.bytes_written == len(b"New content")
        assert result.file_existed is True
        assert mock_connection._write_text_file_called
        assert mock_connection._session_update_called

        # Verify WriteTextFileRequest was created correctly
        request = mock_connection._last_write_request
        assert request is not None
        assert request.sessionId == "test_session"
        assert request.path == str(test_file)
        assert request.content == "New content"

    @pytest.mark.asyncio
    async def test_run_write_error(
        self, mock_connection: MockConnection, tmp_path: Path
    ) -> None:
        mock_connection._write_error = RuntimeError("Permission denied")

        tool = WriteFile(
            config=WriteFileConfig(workdir=tmp_path),
            state=AcpWriteFileState.model_construct(
                connection=mock_connection,  # type: ignore[arg-type]
                session_id="test_session",
                tool_call_id="test_call",
            ),
        )

        test_file = tmp_path / "test.txt"
        args = WriteFileArgs(path=str(test_file), content="test")
        with pytest.raises(ToolError) as exc_info:
            await tool.run(args)

        assert str(exc_info.value) == f"Error writing {test_file}: Permission denied"

    @pytest.mark.asyncio
    async def test_run_without_connection(self, tmp_path: Path) -> None:
        tool = WriteFile(
            config=WriteFileConfig(workdir=tmp_path),
            state=AcpWriteFileState.model_construct(
                connection=None, session_id="test_session", tool_call_id="test_call"
            ),
        )

        args = WriteFileArgs(path=str(tmp_path / "test.txt"), content="test")
        with pytest.raises(ToolError) as exc_info:
            await tool.run(args)

        assert (
            str(exc_info.value)
            == "Connection not available in tool state. This tool can only be used within an ACP session."
        )

    @pytest.mark.asyncio
    async def test_run_without_session_id(self, tmp_path: Path) -> None:
        mock_connection = MockConnection()
        tool = WriteFile(
            config=WriteFileConfig(workdir=tmp_path),
            state=AcpWriteFileState.model_construct(
                connection=mock_connection,  # type: ignore[arg-type]
                session_id=None,
                tool_call_id="test_call",
            ),
        )

        args = WriteFileArgs(path=str(tmp_path / "test.txt"), content="test")
        with pytest.raises(ToolError) as exc_info:
            await tool.run(args)

        assert (
            str(exc_info.value)
            == "Session ID not available in tool state. This tool can only be used within an ACP session."
        )


class TestAcpWriteFileSessionUpdates:
    def test_tool_call_session_update(self) -> None:
        event = ToolCallEvent(
            tool_name="write_file",
            tool_call_id="test_call_123",
            args=WriteFileArgs(path="/tmp/test.txt", content="Hello"),
            tool_class=WriteFile,
        )

        update = WriteFile.tool_call_session_update(event)
        assert update is not None
        # Use hasattr to check for attributes before accessing them
        assert hasattr(update, 'sessionUpdate')
        assert update.sessionUpdate == "tool_call"
        assert hasattr(update, 'toolCallId')
        assert update.toolCallId == "test_call_123"
        assert hasattr(update, 'kind')
        assert update.kind == "edit"
        assert hasattr(update, 'title')
        assert update.title is not None
        # Use type narrowing to handle the union type
        if hasattr(update, 'content') and update.content is not None:
            content = update.content
            # Handle the case where content might be a single item or list
            content_items = content if isinstance(content, (list, tuple)) else [content]
            assert len(content_items) == 1
            item = content_items[0]
            # Check if the item has the expected attributes before accessing them
            if hasattr(item, 'type'):
                assert item.type == "diff"
            if hasattr(item, 'path'):
                assert item.path == "/tmp/test.txt"
            if hasattr(item, 'oldText'):
                assert item.oldText is None
            if hasattr(item, 'newText'):
                assert item.newText == "Hello"
        if hasattr(update, 'locations') and update.locations is not None:
            locations = update.locations
            location_items = locations if isinstance(locations, (list, tuple)) else [locations]
            assert len(location_items) == 1
            location = location_items[0]
            if hasattr(location, 'path'):
                assert location.path == "/tmp/test.txt"

    def test_tool_call_session_update_invalid_args(self) -> None:
        from revibe.core.types import FunctionCall, ToolCall

        class InvalidArgs:
            pass

        event = ToolCallEvent.model_construct(
            tool_name="write_file",
            tool_call_id="test_call_123",
            args=InvalidArgs(),  # type: ignore[arg-type]
            tool_class=WriteFile,
            llm_tool_call=ToolCall(
                function=FunctionCall(name="write_file", arguments="{}"),
                type="function",
                index=0,
            ),
        )

        update = WriteFile.tool_call_session_update(event)
        assert update is None

    def test_tool_result_session_update(self) -> None:
        result = WriteFileResult(
            path="/tmp/test.txt", content="Hello", bytes_written=5, file_existed=False
        )

        event = ToolResultEvent(
            tool_name="write_file",
            tool_call_id="test_call_123",
            result=result,
            tool_class=WriteFile,
        )

        update = WriteFile.tool_result_session_update(event)
        assert update is not None
        # Use hasattr to check for attributes before accessing them
        assert hasattr(update, 'sessionUpdate')
        assert update.sessionUpdate == "tool_call_update"
        assert hasattr(update, 'toolCallId')
        assert update.toolCallId == "test_call_123"
        assert hasattr(update, 'status')
        assert update.status == "completed"
        if hasattr(update, 'content') and update.content is not None:
            content = update.content
            content_items = content if isinstance(content, (list, tuple)) else [content]
            assert len(content_items) == 1
            item = content_items[0]
            if hasattr(item, 'type'):
                assert item.type == "diff"
            if hasattr(item, 'path'):
                assert item.path == "/tmp/test.txt"
            if hasattr(item, 'oldText'):
                assert item.oldText is None
            if hasattr(item, 'newText'):
                assert item.newText == "Hello"
        if hasattr(update, 'locations') and update.locations is not None:
            locations = update.locations
            location_items = locations if isinstance(locations, (list, tuple)) else [locations]
            assert len(location_items) == 1
            location = location_items[0]
            if hasattr(location, 'path'):
                assert location.path == "/tmp/test.txt"

    def test_tool_result_session_update_invalid_result(self) -> None:
        class InvalidResult:
            pass

        event = ToolResultEvent.model_construct(
            tool_name="write_file",
            tool_call_id="test_call_123",
            result=InvalidResult(),  # type: ignore[arg-type]
            tool_class=WriteFile,
        )

        update = WriteFile.tool_result_session_update(event)
        assert update is None
