#!/usr/bin/env bash

uv run nuitka \
    --standalone \
    --onefile \
    --enable-plugin=pyside6 \
    --macos-create-app-bundle \
    --macos-app-name=ClaudeWarp \
    --macos-app-icon=claudewarp/gui/resources/icons/claudewarp.icns \
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
    main.py &&
    du -h -d1 build

APP_NAME="main"
APP_DIR="build/${APP_NAME}.app"
INFO_PLIST="${APP_DIR}/Contents/Info.plist"
RESOURCES_DIR="${APP_DIR}/Contents/Resources"
ICNS_SRC="claudewarp/gui/resources/icons/claudewarp.icns"
ICNS_DST="${RESOURCES_DIR}/claudewarp.icns"

# 1. 创建 Resources 目录
mkdir -p "$RESOURCES_DIR"

# 2. 如果 Info.plist 不存在，写入自定义模板
if [ ! -f "$INFO_PLIST" ]; then
    echo "Injecting custom Info.plist..."
    cat >"$INFO_PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>main</string>
    <key>CFBundleIdentifier</key>
    <string>com.belingud.ClaudeWarp</string>
    <key>CFBundleName</key>
    <string>${APP_NAME}</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>CFBundleVersion</key>
    <string>1.0</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.15</string>
    <key>CFBundleIconFile</key>
    <string>claudewarp.icns</string>
</dict>
</plist>
EOF
fi

# 3. 拷贝 icns 文件
if [ -f "$ICNS_SRC" ]; then
    echo "Copying .icns file to Resources..."
    cp "$ICNS_SRC" "$ICNS_DST"
else
    echo "Warning: $ICNS_SRC not found, skipping icon copy"
fi
