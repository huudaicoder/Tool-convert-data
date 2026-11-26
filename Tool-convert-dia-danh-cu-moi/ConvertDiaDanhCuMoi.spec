# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import collect_all

root = Path.cwd()
binaries = []
datas = []
hiddenimports = []
for package in ('oracledb', 'cryptography'):
    collected = collect_all(package)
    datas += collected[0]
    binaries += collected[1]
    hiddenimports += collected[2]
for folder, target in ((root / 'assets' / 'tcl', 'tcl'), (root / 'assets' / 'tk', 'tk')):
    if folder.exists():
        datas.append((str(folder), target))

a = Analysis(
    ['app.py'], pathex=[str(root)], binaries=binaries, datas=datas,
    hiddenimports=hiddenimports, hookspath=[], hooksconfig={}, runtime_hooks=[],
    excludes=[], noarchive=False, optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [], name='ConvertDiaDanhCuMoi',
    debug=False, bootloader_ignore_signals=False, strip=False, upx=True,
    console=False, disable_windowed_traceback=False,
)
