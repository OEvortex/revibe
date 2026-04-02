from __future__ import annotations

from collections.abc import Callable
from contextlib import contextmanager
from typing import Any

from revibe.core.llm.backend.factory import get_backend_for_provider


@contextmanager
def mock_backend_factory(factory_func: Callable[..., Any]):
    """Monkeypatch get_backend_for_provider to return a custom factory.

    The factory_func receives (provider, **kwargs) and should return a
    backend-like object.
    """
    original = get_backend_for_provider

    def _patched(provider: Any) -> Callable[..., Any]:
        return lambda **kw: factory_func(provider, **kw)

    import revibe.core.agent as agent_module
    import revibe.core.llm.backend.factory as factory_module

    factory_module.get_backend_for_provider = _patched
    agent_module.get_backend_for_provider = _patched
    try:
        yield
    finally:
        factory_module.get_backend_for_provider = original
        agent_module.get_backend_for_provider = original
