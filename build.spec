# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
import tomllib
from domichess import __version__


def domichess_name():
	"""
	Get the name of DomiChess app from the pyproject.toml file.
	"""
	pyproject_path = Path(__name__).resolve().parent / Path("pyproject.toml")
	if pyproject_path.is_file():
		try:
			with pyproject_path.open('rb') as pyproject_file:
				pyproject_toml = tomllib.load(pyproject_file)
			return pyproject_toml['project']['name']
		except tomllib.TOMLDecodeError:
			return
	else:
		return

block_cipher = None

binary_files = [
				('domichess/engines', 'domichess/engines')
				]

data_files = [
			('domichess/themes', 'domichess/themes'),
			('domichess/icons', 'domichess/icons'),
			('pyproject.toml', '.')
			]

a = Analysis(
    ['domichess/main.py'],
    pathex=[],
    binaries=binary_files,
    datas=data_files,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
	a.binaries,
    a.zipfiles,
    a.datas,
    [],
    exclude_binaries=False,
    name=f'{domichess_name()}_{__version__}',
	icon=[
		str(Path('domichess') / Path('icons') / Path('chess_512px.ico')),
		str(Path('domichess') / Path('icons') / Path('chess_256px.ico')),
		str(Path('domichess') / Path('icons') / Path('chess_128px.ico')),
		str(Path('domichess') / Path('icons') / Path('chess_96px.ico')),
		str(Path('domichess') / Path('icons') / Path('chess_72px.ico')),
		str(Path('domichess') / Path('icons') / Path('chess_64px.ico')),
		str(Path('domichess') / Path('icons') / Path('chess_32px.ico'))
		],
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

