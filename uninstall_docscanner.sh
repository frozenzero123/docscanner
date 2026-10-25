#!/bin/bash
# 简易扫描仪 卸载脚本 (v12 / v3.7 通用)

if [ "$EUID" -ne 0 ]; then
    echo "请使用 sudo 运行: sudo bash uninstall_docscanner.sh"
    exit 1
fi

APP_DIR="/opt/docscanner"
BIN_PATH="/usr/local/bin/docscanner"
DESKTOP_PATH="/usr/share/applications/docscanner.desktop"
ICON_PATH="/usr/share/icons/hicolor/256x256/apps/docscanner.png"
ICON_PATH_64="/usr/share/icons/hicolor/64x64/apps/docscanner.png"
ICON_PATH_48="/usr/share/icons/hicolor/48x48/apps/docscanner.png"

echo "========================================"
echo "  简易扫描仪 卸载程序"
echo "========================================"
echo ""

# 0. 停掉正在跑的进程
pkill -f "python3 $APP_DIR/docscanner.py" 2>/dev/null
sleep 0.5
echo "[0/7] 已停止运行中的进程"
echo ""

# 1. 应用目录
echo "[1/7] 删除应用目录..."
if [ -d "$APP_DIR" ]; then
    rm -rf "$APP_DIR"
    echo "  ✓ 已删除 $APP_DIR"
else
    echo "  - 目录不存在, 跳过"
fi
echo ""

# 2. 启动脚本
echo "[2/7] 删除启动脚本..."
if [ -f "$BIN_PATH" ]; then
    rm -f "$BIN_PATH"
    echo "  ✓ 已删除 $BIN_PATH"
else
    echo "  - 文件不存在, 跳过"
fi
echo ""

# 3. 桌面快捷方式文件
echo "[3/7] 删除系统级桌面文件..."
if [ -f "$DESKTOP_PATH" ]; then
    rm -f "$DESKTOP_PATH"
    echo "  ✓ 已删除 $DESKTOP_PATH"
else
    echo "  - 文件不存在, 跳过"
fi
echo ""

# 4. 删除各用户桌面上的快捷方式
echo "[4/7] 删除各用户桌面快捷方式..."
found=0
for desktop_dir in /home/*/.桌面 /home/*/Desktop /home/*/桌面; do
    if [ -d "$desktop_dir" ] && [ -f "$desktop_dir/docscanner.desktop" ]; then
        rm -f "$desktop_dir/docscanner.desktop"
        echo "  ✓ 已删除 $desktop_dir/docscanner.desktop"
        found=1
    fi
done
if [ "$found" -eq 0 ]; then
    echo "  - 未找到, 跳过"
fi
echo ""

# 5. 删除图标
echo "[5/7] 删除图标..."
for f in "$ICON_PATH" "$ICON_PATH_64" "$ICON_PATH_48"; do
    if [ -f "$f" ]; then
        rm -f "$f"
        echo "  ✓ 已删除 $f"
    fi
done
echo ""

# 6. 更新图标/桌面数据库
echo "[6/7] 更新系统缓存..."
gtk-update-icon-cache -f /usr/share/icons/hicolor 2>/dev/null
update-desktop-database 2>/dev/null
echo "  ✓ 缓存已更新"
echo ""

# 7. 清理 pip 装的 Pillow / PyMuPDF (可选, 问一下)
echo "[7/7] 可选: 清理 pip 包"
echo "  注意: Pillow 可能被其他软件依赖, 不建议卸载"
echo "  PyMuPDF 建议卸载后由新版安装脚本重新装"
read -rp "  是否卸载 PyMuPDF? [y/N]: " answer
case "$answer" in
    [yY][eE][sS]|[yY])
        pip3 uninstall -y PyMuPDF 2>/dev/null && echo "  ✓ PyMuPDF 已卸载" || echo "  - 未安装, 跳过"
        ;;
    *)
        echo "  - 保留 PyMuPDF"
        ;;
esac
echo ""

echo "========================================"
echo "  卸载完成"
echo "========================================"
echo ""
echo "  重新安装新版:"
echo "    tar xzf docscanner_kit_v3.7.5.tar.gz"
echo "    cd docscanner_kit_v3.7.5"
echo "    sudo bash install_docscanner.sh"
echo ""
