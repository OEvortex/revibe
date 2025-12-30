from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import tomllib

import tomli_w

from revibe.core import config
from revibe.core.config import VibeConfig
from revibe.core.paths.config_paths import ConfigPath, unlock_config_paths


def _restore_dump_config(config_file: Path):
    original_dump_config = VibeConfig.dump_config

    def real_dump_config(cls, config_dict: dict) -> None:
        try:
            with config_file.open("wb") as f:
                tomli_w.dump(config_dict, f)
        except OSError:
            config_file.write_text(
                "\n".join(
                    f"{k} = {v!r}" for k, v in config_dict.items() if v is not None
                ),
                encoding="utf-8",
            )

    VibeConfig.dump_config = classmethod(real_dump_config)  # type: ignore[assignment]
    return original_dump_config


@contextmanager
def _migrate_config_file(tmp_path: Path, content: str):
    config_file = tmp_path / "config.toml"
    config_file.write_text(content, encoding="utf-8")

    original_config_file = config.CONFIG_FILE
    original_dump_config = _restore_dump_config(config_file)

    try:
        unlock_config_paths()
        # Create a ConfigPath instance from the Path
        config.CONFIG_FILE = ConfigPath(lambda: config_file)
        VibeConfig._migrate()
        yield config_file
    finally:
        config.CONFIG_FILE = original_config_file
        VibeConfig.dump_config = original_dump_config


def _load_migrated_config(config_file: Path) -> dict:
    with config_file.open("rb") as f:
        return tomllib.load(f)
