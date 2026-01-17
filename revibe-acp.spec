# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['revibe/acp/entrypoint.py'],
    pathex=[],
    binaries=[],
datas=[
    ('revibe/core/prompts/*.md', 'revibe/core/prompts'),
    ('revibe/core/tools/builtins/prompts/*.md', 'revibe/core/tools/builtins/prompts'),
    ('revibe/cli/textual_ui/tcss/*/*.tcss', 'revibe/cli/textual_ui/tcss'),
    ('revibe/setup/onboarding/tcss/*.tcss', 'revibe/setup/onboarding/tcss'),
    ('revibe/setup/trusted_folders/tcss/*.tcss', 'revibe/setup/trusted_folders/tcss'),
    ('revibe/setup/*', 'revibe/setup'),
    # This is necessary because tools are dynamically called in revibe, meaning there is no static reference to those files
    ('revibe/core/tools/builtins/*.py', 'revibe/core/tools/builtins'),
    ('revibe/acp/tools/builtins/*.py', 'revibe/acp/tools/builtins'),
],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='revibe-acp',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
