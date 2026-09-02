#!/bin/bash
# 简易扫描仪安装脚本 v2.2
# 全架构通用 (x86_64 / ARM64 / LoongArch64)

if [ "$EUID" -ne 0 ]; then
    echo "请使用 sudo 运行: sudo bash install_docscanner.sh"
    exit 1
fi

# 获取脚本所在目录 (解决 sudo 改变工作目录的问题)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

APP_DIR="/opt/docscanner"
BIN_PATH="/usr/local/bin/docscanner"
DESKTOP_PATH="/usr/share/applications/docscanner.desktop"
ICON_PATH="/usr/share/icons/hicolor/256x256/apps/docscanner.png"
ICON_PATH_64="/usr/share/icons/hicolor/64x64/apps/docscanner.png"
ICON_PATH_48="/usr/share/icons/hicolor/48x48/apps/docscanner.png"

echo "========================================"
echo "  简易扫描仪 v2.3 安装程序"
echo "========================================"
echo ""

# 1. 安装依赖
echo "[1/6] 安装依赖..."
apt-get update -qq 2>/dev/null
apt-get install -y -qq python3 python3-tk python3-pil python3-pil.imagetk sane-utils 2>/dev/null
pip3 install Pillow --break-system-packages -q 2>/dev/null
echo "  依赖安装完成"
echo ""

# 2. 创建应用目录
echo "[2/6] 创建应用目录..."
mkdir -p "$APP_DIR"
cp "$SCRIPT_DIR/docscanner.py" "$APP_DIR/docscanner.py"
chmod +x "$APP_DIR/docscanner.py"
echo "  应用已复制到 $APP_DIR"
echo ""

# 3. 安装应用图标
echo "[3/6] 安装应用图标..."
ICON_SOURCE=""
# 优先用打包的 256x256 PNG
if [ -f "$SCRIPT_DIR/docscanner_icon_256.png" ]; then
    ICON_SOURCE="$SCRIPT_DIR/docscanner_icon_256.png"
elif [ -f "$SCRIPT_DIR/../docscanner_icon_256.png" ]; then
    ICON_SOURCE="$SCRIPT_DIR/../docscanner_icon_256.png"
fi

if [ -n "$ICON_SOURCE" ] && [ -f "$ICON_SOURCE" ]; then
    # 安装 256x256
    mkdir -p "$(dirname "$ICON_PATH")"
    cp "$ICON_SOURCE" "$ICON_PATH"
    chmod 644 "$ICON_PATH"
    # 生成 64x64 和 48x48
    python3 -c "
from PIL import Image
img = Image.open('$ICON_SOURCE')
for size, path in [(64, '$ICON_PATH_64'), (48, '$ICON_PATH_48')]:
    img2 = img.resize((size, size), Image.Resampling.LANCZOS)
    import os; os.makedirs(os.path.dirname(path), exist_ok=True)
    img2.save(path, 'PNG')
print('icons installed')
" 2>/dev/null
    # 复制到应用目录
    cp "$ICON_SOURCE" "$APP_DIR/icon.png"
    echo "  AI 图标已安装 (256/64/48px): $ICON_PATH"
else
    echo "  [警告] 未找到图标文件, 用 PIL 生成..."
    python3 -c "
from PIL import Image, ImageDraw
import os
C_PRIMARY = '#2563eb'
C_SUCCESS = '#16a34a'
for size, path in [(256, '$ICON_PATH'), (64, '$ICON_PATH_64'), (48, '$ICON_PATH_48')]:
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    s = size
    draw.rounded_rectangle([s//30, s//30, s-s//30, s-s//30], radius=s//6, fill=C_PRIMARY)
    draw.rounded_rectangle([s//4, s//5, s-s//4, 2*s//5], radius=s//16, fill='#e0e7ff')
    draw.rectangle([3*s//10, 7*s//20, s-3*s//10, 2*s//5+s//20], fill=C_PRIMARY)
    draw.rounded_rectangle([s//4, s//2, s-s//4, 4*s//5], radius=s//16, fill='#dbeafe')
    draw.rectangle([7*s//20, 11*s//20, s-7*s//20, 3*s//4], fill='white')
    for y in [3*s//5, 5*s//8, 11*s//16]:
        draw.rectangle([2*s//5, y, s-2*s//5, y+max(1,s//64)], fill='#93c5fd')
    draw.ellipse([s-5*s//32, s//8, s-s//16, 3*s//32+s//8], fill=C_SUCCESS)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path, 'PNG')
print('fallback icons generated')
" 2>/dev/null || echo "  [警告] 图标生成失败"
fi

# 强制更新图标缓存
gtk-update-icon-cache -f /usr/share/icons/hicolor 2>/dev/null
update-desktop-database 2>/dev/null
echo ""

# 4. 创建启动脚本
echo "[4/6] 创建启动脚本..."
cat > "$BIN_PATH" << 'EOF'
#!/bin/bash
exec python3 /opt/docscanner/docscanner.py "$@"
EOF
chmod +x "$BIN_PATH"
echo "  启动脚本已创建: $BIN_PATH"
echo ""

# 5. 创建桌面快捷方式
echo "[5/6] 创建桌面快捷方式..."
cat > "$DESKTOP_PATH" << EOF
[Desktop Entry]
Name=简易扫描仪
Name[zh_CN]=简易扫描仪
Comment=手动双面扫描PDF
Comment[zh_CN]=手动双面扫描PDF
Exec=$BIN_PATH
Terminal=false
Type=Application
Categories=Graphics;Scanning;Office;
Icon=/usr/share/icons/hicolor/256x256/apps/docscanner.png
Keywords=scanner;scan;pdf;document;
EOF
chmod 644 "$DESKTOP_PATH"

# 复制到桌面 (先删除旧的)
for desktop_dir in /home/*/.桌面 /home/*/Desktop /home/*/桌面; do
    if [ -d "$desktop_dir" ]; then
        rm -f "$desktop_dir/docscanner.desktop" 2>/dev/null
        cp "$DESKTOP_PATH" "$desktop_dir/docscanner.desktop"
        chmod 755 "$desktop_dir/docscanner.desktop"
        chown $(stat -c %U "$desktop_dir" 2>/dev/null):$(stat -c %G "$desktop_dir" 2>/dev/null) "$desktop_dir/docscanner.desktop" 2>/dev/null
        echo "  已复制到桌面: $desktop_dir"
    fi
done

# 再次更新缓存
gtk-update-icon-cache -f /usr/share/icons/hicolor 2>/dev/null
echo ""

# 6. 验证
echo "[6/6] 验证安装..."
if python3 -c "import tkinter; from PIL import Image, ImageTk; print('OK')" 2>/dev/null; then
    echo "  ✓ Python 依赖正常"
else
    echo "  ⚠ Python 依赖缺失，请运行: sudo apt install python3-pil python3-pil.imagetk"
fi

if command -v scanimage &>/dev/null; then
    echo "  ✓ scanimage 已安装"
else
    echo "  ⚠ scanimage 未安装，请运行: sudo apt install sane-utils"
fi

if [ -x "$BIN_PATH" ]; then
    echo "  ✓ 启动脚本已就绪"
fi

if [ -f "$DESKTOP_PATH" ]; then
    echo "  ✓ 桌面快捷方式已创建"
fi

if [ -f "$ICON_PATH" ]; then
    echo "  ✓ 应用图标已安装"
fi

echo ""
echo "========================================"
echo "  安装完成！"
echo "========================================"
echo ""
echo "  启动方式:"
echo "    命令行: docscanner"
echo "    桌面: 双击「简易扫描仪」图标"
echo ""
echo "  使用前请确保:"
echo "    1. 扫描仪已开启并连接"
echo "    2. scanimage -L 能检测到扫描仪"
echo "    3. 手动设备栏可填: lenovo3:net1;dev0"
echo ""
