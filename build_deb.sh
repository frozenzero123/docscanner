#!/bin/bash
# =====================================================================
# 简易扫描仪 DEB 打包脚本 (LoongArch64 / 麒麟 V10 SP1)
# 用法:  bash build_deb.sh                 # 自动识别本机 dpkg 架构
#        ARCH=loongarch64 bash build_deb.sh  # 手动指定架构
# 产物:  docscanner_<版本>-1_<架构>.deb
# 架构说明:
#   麒麟 V10SP1 旧世界(ABI1.0): loongarch64
#   Debian/UOS 新世界:          loong64
#   纯 Python 应用, 包内无架构相关二进制
# =====================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VERSION="$(grep -oP 'VERSION\s*=\s*"\K[^"]+' docscanner.py)"
[ -z "$VERSION" ] && { echo "无法从 docscanner.py 读取版本号"; exit 1; }
PKG="docscanner"
# 架构: 环境变量 ARCH 优先, 否则取本机 dpkg 架构, 再回退 loong64
if [ -z "$ARCH" ]; then
    if command -v dpkg >/dev/null 2>&1; then
        ARCH="$(dpkg --print-architecture 2>/dev/null || true)"
    fi
fi
[ -z "$ARCH" ] && ARCH="loong64"
DEB_NAME="${PKG}_${VERSION}-1_${ARCH}.deb"

echo "========================================"
echo "  构建 ${PKG} ${VERSION} (${ARCH})"
echo "========================================"

BUILD="$(mktemp -d /tmp/docscanner-deb.XXXXXX)"
trap 'rm -rf "$BUILD"' EXIT
ROOT="$BUILD/pkg"
mkdir -p "$ROOT/DEBIAN"
mkdir -p "$ROOT/opt/docscanner"
mkdir -p "$ROOT/usr/bin"
mkdir -p "$ROOT/usr/share/applications"
mkdir -p "$ROOT/usr/share/icons/hicolor/256x256/apps"
mkdir -p "$ROOT/usr/share/icons/hicolor/64x64/apps"
mkdir -p "$ROOT/usr/share/icons/hicolor/48x48/apps"
mkdir -p "$ROOT/usr/share/doc/docscanner"

# ── 应用文件 ──
cp docscanner.py "$ROOT/opt/docscanner/docscanner.py"
chmod 0755 "$ROOT/opt/docscanner/docscanner.py"
cp docscanner_icon_256.png "$ROOT/opt/docscanner/icon.png"
chmod 0644 "$ROOT/opt/docscanner/icon.png"

# ── 文档 ──
if [ -f README.md ]; then
    cp README.md "$ROOT/usr/share/doc/docscanner/README.md"
    chmod 0644 "$ROOT/usr/share/doc/docscanner/README.md"
fi

# ── 启动器 (/usr/bin, Debian 规范路径) ──
cat > "$ROOT/usr/bin/docscanner" << 'EOF'
#!/bin/bash
exec python3 /opt/docscanner/docscanner.py "$@"
EOF
chmod 0755 "$ROOT/usr/bin/docscanner"

# ── 桌面菜单项 ──
cat > "$ROOT/usr/share/applications/docscanner.desktop" << 'EOF'
[Desktop Entry]
Name=简易扫描仪
Name[zh_CN]=简易扫描仪
Comment=手动双面扫描PDF
Comment[zh_CN]=手动双面扫描PDF
Exec=/usr/bin/docscanner
Terminal=false
Type=Application
Categories=Graphics;Scanning;Office;
Icon=docscanner
Keywords=scanner;scan;pdf;document;
StartupNotify=true
EOF
chmod 0644 "$ROOT/usr/share/applications/docscanner.desktop"

# ── 图标 (构建期生成 64/48) ──
cp docscanner_icon_256.png "$ROOT/usr/share/icons/hicolor/256x256/apps/docscanner.png"
if python3 -c "from PIL import Image" 2>/dev/null; then
python3 - << INNER_PYEOF
from PIL import Image
try:
    R = Image.Resampling.LANCZOS
except AttributeError:
    R = Image.LANCZOS
img = Image.open("docscanner_icon_256.png")
for size, path in [
    (64, "$ROOT/usr/share/icons/hicolor/64x64/apps/docscanner.png"),
    (48, "$ROOT/usr/share/icons/hicolor/48x48/apps/docscanner.png"),
]:
    img.resize((size, size), R).save(path, "PNG")
print("  64/48px 图标已生成")
INNER_PYEOF
else
    echo "  [警告] 构建机无 Pillow, 64/48px 用 256px 原图代替"
    cp "$ROOT/usr/share/icons/hicolor/256x256/apps/docscanner.png" \
       "$ROOT/usr/share/icons/hicolor/64x64/apps/docscanner.png"
    cp "$ROOT/usr/share/icons/hicolor/256x256/apps/docscanner.png" \
       "$ROOT/usr/share/icons/hicolor/48x48/apps/docscanner.png"
fi
find "$ROOT/usr/share/icons" -type f -exec chmod 0644 {} \;

# ── DEBIAN/control ──
INST_SIZE="$(du -sk "$ROOT" | cut -f1)"
cat > "$ROOT/DEBIAN/control" << EOF
Package: ${PKG}
Version: ${VERSION}-1
Architecture: ${ARCH}
Maintainer: DocScanner <support@local>
Installed-Size: ${INST_SIZE}
Depends: python3, python3-tk, python3-pil, python3-pil.imagetk, python3-fitz, sane-utils
Section: graphics
Priority: optional
Homepage: https://local/docscanner
Description: 简易扫描仪 (DocScanner)
 基于 SANE/scanimage 的图形化扫描工具, 支持平板与 ADF,
 手动双面合并、多页 PDF/PNG/JPEG 导出, 标准 A4 页面尺寸,
 兼容麒麟系统 python3-fitz 1.16 (PyMuPDF)。
EOF
chmod 0644 "$ROOT/DEBIAN/control"

# ── postinst: 清理旧 tar 版遗留 + 各用户桌面快捷方式 + 缓存 ──
cat > "$ROOT/DEBIAN/postinst" << 'EOF'
#!/bin/bash
set -e

# 旧版 tar 包安装方式把启动器放在 /usr/local/bin, deb 版改用 /usr/bin
if [ -e /usr/local/bin/docscanner ]; then
    rm -f /usr/local/bin/docscanner
fi

# 为每个已存在的用户主目录补桌面快捷方式
for d in /home/*/Desktop /home/*/桌面; do
    [ -d "$d" ] || continue
    cp -f /usr/share/applications/docscanner.desktop "$d/docscanner.desktop"
    chmod 0755 "$d/docscanner.desktop"
    owner="$(stat -c '%U' "$d" 2>/dev/null || echo root)"
    group="$(stat -c '%G' "$d" 2>/dev/null || echo root)"
    chown "$owner:$group" "$d/docscanner.desktop" 2>/dev/null || true
done

if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -q -f /usr/share/icons/hicolor 2>/dev/null || true
fi
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database -q 2>/dev/null || true
fi

echo ""
echo "========================================"
echo " 简易扫描仪 安装完成"
echo "========================================"
echo " 启动: 应用菜单「简易扫描仪」或终端执行 docscanner"
if ! python3 -c "import fitz" >/dev/null 2>&1; then
    echo " [提示] 未检测到 PyMuPDF, PDF 将走回退方案; 建议: sudo apt install python3-fitz"
fi
if ! python3 -c "from PIL import ImageTk" >/dev/null 2>&1; then
    echo " [提示] 未检测到 python3-pil.imagetk, 缩略图功能受限"
fi
if ! command -v scanimage >/dev/null 2>&1; then
    echo " [提示] 未检测到 scanimage: sudo apt install sane-utils"
fi
echo ""
exit 0
EOF
chmod 0755 "$ROOT/DEBIAN/postinst"

# ── prerm: 停止运行中的进程 ──
cat > "$ROOT/DEBIAN/prerm" << 'EOF'
#!/bin/bash
pkill -f "/opt/docscanner/docscanner.py" 2>/dev/null || true
exit 0
EOF
chmod 0755 "$ROOT/DEBIAN/prerm"

# ── postrm: 清除各用户桌面残留 ──
cat > "$ROOT/DEBIAN/postrm" << 'EOF'
#!/bin/bash
for d in /home/*/Desktop /home/*/桌面; do
    [ -d "$d" ] || continue
    rm -f "$d/docscanner.desktop" 2>/dev/null || true
done
rm -rf /opt/docscanner 2>/dev/null || true
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -q -f /usr/share/icons/hicolor 2>/dev/null || true
fi
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database -q 2>/dev/null || true
fi
exit 0
EOF
chmod 0755 "$ROOT/DEBIAN/postrm"

# ── 构建 (强制 root:root 属主) ──
if dpkg-deb --help 2>&1 | grep -q root-owner-group; then
    dpkg-deb --root-owner-group -b "$ROOT" "$SCRIPT_DIR/$DEB_NAME"
else
    # 老版 dpkg-deb 不支持 --root-owner-group, 需以 root 身份运行
    if [ "$(id -u)" -ne 0 ]; then
        echo "当前 dpkg-deb 不支持 --root-owner-group, 请用 sudo 运行本脚本"
        exit 1
    fi
    dpkg-deb -b "$ROOT" "$SCRIPT_DIR/$DEB_NAME"
fi

echo ""
echo "✓ 已生成: $SCRIPT_DIR/$DEB_NAME"
dpkg-deb -I "$SCRIPT_DIR/$DEB_NAME" | sed 's/^/  /'
