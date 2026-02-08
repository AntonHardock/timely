# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['pyinstaller_entrypoint.py'],
    pathex=['C:/Users/anton/Documents/coding/remote/timely'],
    binaries=[],
    datas=[
        ('configs', 'configs'),
        ('db', 'db'),
        ('static', 'static'),
        ('javascript', 'javascript'),
        ('templates', 'templates'),
        ('app/routers/agg_time_by_cost_unit.sql', 'app/routers')
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
    [],
    exclude_binaries=True,
    name='timely',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='timely',
)
