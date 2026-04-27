# -*- mode: python ; coding: utf-8 -*-
# BeSafeFish - PyInstaller spec (onedir - folder)
# Buduje folder z programem, potem pakowany do .zip
# Uzytkownik rozpakowuje zip, uruchamia BeSafeFish.exe jako Admin
#
# Build (z rootu repo): py -m PyInstaller app/BeSafeFish.spec --clean -y
# Output: dist/BeSafeFish/BeSafeFish.exe
#
# UWAGA: PyInstaller 6.x ma niespojne dziedziczenie sciezek:
# - script (Analysis pierwszy argument), datas, icon = WZGLEDEM .spec (czyli app/)
# - pathex = WZGLEDEM CWD (czyli root repo)
# Dlatego ZAWSZE buildujemy z rootu repo: 'py -m PyInstaller app/BeSafeFish.spec'.

a = Analysis(
    ['besafefish.py'],  # wzgledem .spec (app/)
    pathex=[
        'app',  # wzgledem cwd (root repo)
        'versions\\tryb1_rybka_klik\\post_cnn',
    ],
    binaries=[],
    datas=[
        # wzgledem .spec (app/)
        ('gui\\fish.ico', 'gui'),
        ('gui\\assets', 'gui\\assets'),
        ('..\\versions\\tryb1_rybka_klik\\post_cnn\\cnn\\models\\fish_patch_cnn.onnx', 'cnn\\models'),
        ('..\\versions\\tryb1_rybka_klik\\post_cnn\\cnn\\models\\fish_patch_cnn.onnx.data', 'cnn\\models'),
    ],
    hiddenimports=[
        'PySide6.QtSvg',
        # Bot worker laduje moduly bota dynamicznie przez sys.path.insert (besafefish.py:27).
        # PyInstaller nie wykryje tych importow -> trzeba podac jawnie.
        'cv2',
        'numpy',
        'mss',
        'pyautogui',
        'pydirectinput',
        'pygetwindow',
        'PIL',
        'onnxruntime',  # importowany lazy w src/fishing_modes/fish_click.py
        'onnxruntime.capi',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['torch', 'torchvision', 'matplotlib', 'tkinter'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='BeSafeFish',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['gui\\fish.ico'],  # wzgledem .spec (app/)
    uac_admin=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='BeSafeFish',
)
