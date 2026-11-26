# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_submodules
root = Path(SPECPATH)
binaries=[]; datas=[]; hiddenimports=collect_submodules('tkinter') + ['_tkinter']
for package in ('oracledb','cryptography'):
    result=collect_all(package); datas+=result[0]; binaries+=result[1]; hiddenimports+=result[2]
python_dlls = Path(__import__('sys').executable).parent / 'DLLs'
binaries += [(str(python_dlls / '_tkinter.pyd'), '.')]
for dll in ('tcl86t.dll','tk86t.dll'):
    binaries += [(str(python_dlls / dll), '.')]
datas += [(str(root / 'assets' / 'tcl'), 'tcl'), (str(root / 'assets' / 'tk'), 'tk')]
a=Analysis(['app.py'],pathex=[str(root)],binaries=binaries,datas=datas,hiddenimports=hiddenimports,hookspath=[],hooksconfig={},runtime_hooks=[],excludes=[],noarchive=False,optimize=0)
pyz=PYZ(a.pure)
exe=EXE(pyz,a.scripts,a.binaries,a.datas,[],name='ChuyenDiaPhuongTienAn',debug=False,bootloader_ignore_signals=False,strip=False,upx=True,console=False,disable_windowed_traceback=False,argv_emulation=False,target_arch=None,codesign_identity=None,entitlements_file=None)
