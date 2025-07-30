Intel Mac使用pyinstaller打包配置参数。

默认配置，打包体积57M

```python
# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
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
    name='main',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['claudewarp/gui/resources/icons/claudewarp.ico'],
)
app = BUNDLE(
    exe,
    name='main.app',
    icon='claudewarp/gui/resources/icons/claudewarp.ico',
    bundle_identifier=None,
)

```

修改添加了exclude，打包体积54M

```python
# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "PySide6.Qt3DCore",
        "PySide6.Qt3DRender",
        "PySide6.QtCharts",
        "PySide6.QtDataVisualization",
        "PySide6.QtMultimedia",
        "PySide6.QtMultimediaWidgets",
        "PySide6.QtNetwork",
        "PySide6.QtOpenGL",
        "PySide6.QtPositioning",
        "PySide6.QtPrintSupport",
        "PySide6.QtQml",
        "PySide6.QtQuick",
        "PySide6.QtQuickWidgets",
        "PySide6.QtRemoteObjects",
        "PySide6.QtSensors",
        "PySide6.QtSerialPort",
        "PySide6.QtSql",
        "PySide6.QtTest",
        "PySide6.QtTextToSpeech",
        "PySide6.QtWebChannel",
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets",
        "PySide6.QtWebSockets",
        "PySide6.QtXml",
        "PySide6.QtXmlPatterns",
    ],
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
    name="main",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=["claudewarp/gui/resources/icons/claudewarp.ico"],
)
app = BUNDLE(
    exe,
    name="main.app",
    icon="claudewarp/gui/resources/icons/claudewarp.ico",
    bundle_identifier=None,
)

```

将optimize设置为2，`optimize=2`，打包后体积为53M

使用nuitka直接打包，构建体积为44M。优化命令为：

```bash
uv run nuitka \
    --standalone \
    --onefile \
    --enable-plugin=pyside6 \
    --macos-create-app-bundle \
    --macos-app-icon=claudewarp/gui/resources/icons/claudewarp.ico \
    --output-dir=build \
    --assume-yes-for-download \
    --report=report.html \
    --nofollow-import-to=PySide6.QtOpenGL \
    --nofollow-import-to=PySide6.QtMultimedia \
    --nofollow-import-to=PySide6.QtMultimediaWidgets \
    --nofollow-import-to=PySide6.QtWebEngineWidgets \
    --nofollow-import-to=PySide6.QtQml \
    --nofollow-import-to=PySide6.QtQuick \
    --nofollow-import-to=PySide6.QtNetwork \
    --nofollow-import-to=imageio \
    --nofollow-import-to=numpy \
    --nofollow-import-to=PIL \
    --nofollow-import-to=markdown_it_py \
    --nofollow-import-to=mdurl \
    --nofollow-import-to=pygments \
    --nofollow-import-to=shellingham \
    --nofollow-import-to=bump2version \
    --nofollow-import-to=deptry \
    --nofollow-import-to=pyright \
    --nofollow-import-to=pre_commit \
    --nofollow-import-to=pytest \
    --nofollow-import-to=pytest_cov \
    --nofollow-import-to=pytest_qt \
    --nofollow-import-to=iniconfig \
    --nofollow-import-to=pluggy \
    --nofollow-import-to=virtualenv \
    --nofollow-import-to=platformdirs \
    --nofollow-import-to=filelock \
    --nofollow-import-to=cfgv \
    --nofollow-import-to=identify \
    --nofollow-import-to=nodeenv \
    --nofollow-import-to=pyyaml \
    --nofollow-import-to=claudewarp.cli \
    --nofollow-import-to=bdb \
    --nofollow-import-to=bz2 \
    --nofollow-import-to=calendar \
    --nofollow-import-to=cgi \
    --nofollow-import-to=cgitb \
    --nofollow-import-to=chunk \
    --nofollow-import-to=pdb \
    --nofollow-import-to=trace \
    --nofollow-import-to=tracemalloc \
    --nofollow-import-to=uu \
    --nofollow-import-to=xdrlib \
    --nofollow-import-to=imaplib \
    --nofollow-import-to=poplib \
    --nofollow-import-to=ftplib \
    --nofollow-import-to=socketserver \
    --include-module=typing_inspection \
    --include-data-dir=claudewarp/gui/resources=claudewarp/gui/resources \
    main.py
```

优化后的构建体积为34M
