#!/usr/bin/env bash
set -e

APP_NAME="ClaudeWarp"
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

echo "✅ App bundle post-processing complete."
