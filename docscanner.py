#!/usr/bin/env python3
"""
简易扫描仪 - Simple Scanner v3.6.0
支持手动双面扫描、ADF批量扫描，输出PDF
deb包: LoongArch64 | 脚本安装: 全架构通用
作者: frozenzero123
GitHub: https://github.com/frozenzero123/docscanner
"""

import os
import sys
import io
import json
import glob
import base64
import subprocess
import threading
import socket
import tempfile
import time
from pathlib import Path
from datetime import datetime
from urllib.request import urlopen
from PIL import Image, ImageDraw
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

try:
    from PIL import ImageTk
    HAS_IMAGETK = True
except ImportError:
    HAS_IMAGETK = False

VERSION = "3.6.0"
APP_NAME = "简易扫描仪"
CONFIG_DIR = Path.home() / ".config" / "docscanner"
CONFIG_FILE = CONFIG_DIR / "settings.json"

PAPER_SIZES = {
    "A4": (210, 297),
    "A3": (297, 420),
    "Letter": (216, 279),
    "Legal": (216, 356),
}

RESOLUTIONS = ["100", "150", "200", "300", "600"]
COLOR_MODES = ["Color", "Gray", "Lineart"]
SCAN_SOURCES = [
    ("ADF 输稿器", "ADF"),
    ("平板", "Flatbed"),
]

# 兼容新旧 Pillow 版本
try:
    LANCZOS = Image.Resampling.LANCZOS
except AttributeError:
    LANCZOS = Image.LANCZOS

# ── 配色 ──
C_BG        = "#f0f2f5"
C_CARD      = "#ffffff"
C_PRIMARY   = "#2563eb"
C_PRIMARY_H = "#1d4ed8"
C_PRIMARY_L = "#dbeafe"
C_SUCCESS   = "#16a34a"
C_DANGER    = "#dc2626"
C_WARN      = "#d97706"
C_TEXT      = "#1e293b"
C_TEXT_SEC  = "#64748b"
C_BORDER    = "#e2e8f0"
C_FRONT_BG  = "#eff6ff"
C_BACK_BG   = "#fef2f2"
C_FRONT_BD  = "#3b82f6"
C_BACK_BD   = "#ef4444"
C_PLACEHOLDER = "#cbd5e1"

# AI 生成的应用图标 (64x64 PNG, base64)
ICON_B64 = "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"


def load_app_icon():
    """加载应用图标: 优先 AI 生成的, 回退到 PIL 绘制的"""
    # 方式1: 从安装路径加载 256x256 PNG
    icon_paths = [
        "/usr/share/icons/hicolor/256x256/apps/docscanner.png",
        "/opt/docscanner/icon.png",
    ]
    for path in icon_paths:
        try:
            img = Image.open(path)
            if HAS_IMAGETK:
                return ImageTk.PhotoImage(img)
            else:
                fd, tmp = tempfile.mkstemp(suffix=".ppm")
                img.save(tmp, "PPM")
                os.close(fd)
                photo = tk.PhotoImage(file=tmp)
                os.unlink(tmp)
                return photo
        except:
            pass
    # 方式2: 从 base64 加载
    try:
        img = Image.open(io.BytesIO(base64.b64decode(ICON_B64)))
        if HAS_IMAGETK:
            return ImageTk.PhotoImage(img)
        else:
            fd, tmp = tempfile.mkstemp(suffix=".ppm")
            img.save(tmp, "PPM")
            os.close(fd)
            photo = tk.PhotoImage(file=tmp)
            os.unlink(tmp)
            return photo
    except:
        pass
    # 方式3: PIL 绘制
    try:
        size = 64
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle([2, 2, size-2, size-2], radius=14, fill=C_PRIMARY)
        draw.rounded_rectangle([14, 12, size-14, 28], radius=4, fill=C_PRIMARY_L)
        draw.rectangle([18, 22, size-18, 25], fill=C_PRIMARY)
        draw.rounded_rectangle([14, 32, size-14, 52], radius=4, fill="#dbeafe")
        draw.rectangle([22, 36, size-22, 50], fill="white")
        for y in [40, 44, 48]:
            draw.rectangle([25, y, size-25, y+1], fill="#93c5fd")
        draw.ellipse([size-20, 15, size-14, 21], fill=C_SUCCESS)
        if HAS_IMAGETK:
            return ImageTk.PhotoImage(img)
        else:
            fd, tmp = tempfile.mkstemp(suffix=".ppm")
            img.save(tmp, "PPM")
            os.close(fd)
            photo = tk.PhotoImage(file=tmp)
            os.unlink(tmp)
            return photo
    except:
        return None


class SaveDialog(tk.Toplevel):
    """自定义保存对话框"""
    def __init__(self, parent, page_count, default_name):
        super().__init__(parent)
        self.title("保存文件")
        self.geometry("520x400")
        self.resizable(False, False)
        self.configure(bg=C_BG)
        self.transient(parent)
        self.grab_set()
        self.result = None

        # 标题
        header = tk.Frame(self, bg=C_PRIMARY, height=50)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="保存扫描文档", font=("", 14, "bold"),
                 bg=C_PRIMARY, fg="white").pack(side="left", padx=15, pady=8)

        # 内容
        body = tk.Frame(self, bg=C_CARD, padx=20, pady=16)
        body.pack(fill="both", expand=True)

        # 文件名
        tk.Label(body, text="文件名", font=("", 10, "bold"),
                 bg=C_CARD, fg=C_TEXT).grid(row=0, column=0, sticky="w", pady=(0, 4))
        self.name_var = tk.StringVar(value=default_name)
        name_entry = ttk.Entry(body, textvariable=self.name_var, font=("", 11), width=40)
        name_entry.grid(row=1, column=0, columnspan=3, sticky="we", pady=(0, 12))
        name_entry.focus_set()
        name_entry.select_range(0, "end")

        # 保存位置
        tk.Label(body, text="保存位置", font=("", 10, "bold"),
                 bg=C_CARD, fg=C_TEXT).grid(row=2, column=0, sticky="w", pady=(0, 4))
        self.dir_var = tk.StringVar(value=str(Path.home() / "桌面"))
        dir_entry = ttk.Entry(body, textvariable=self.dir_var, font=("", 10), width=35)
        dir_entry.grid(row=3, column=0, columnspan=2, sticky="we", padx=(0, 6))
        ttk.Button(body, text="浏览...", command=self._browse).grid(row=3, column=2, padx=(6, 0))

        # 格式
        tk.Label(body, text="输出格式", font=("", 10, "bold"),
                 bg=C_CARD, fg=C_TEXT).grid(row=4, column=0, sticky="w", pady=(12, 4))
        self.fmt_var = tk.StringVar(value="PDF")
        fmt_frame = tk.Frame(body, bg=C_CARD)
        fmt_frame.grid(row=5, column=0, columnspan=3, sticky="w")
        for fmt in ["PDF", "PNG 图片", "JPEG 图片"]:
            rb = tk.Radiobutton(fmt_frame, text=fmt, value=fmt, variable=self.fmt_var,
                                bg=C_CARD, fg=C_TEXT, activebackground=C_CARD,
                                selectcolor=C_CARD, font=("", 10))
            rb.pack(side="left", padx=(0, 20))

        # 信息
        info = tk.Frame(body, bg=C_PRIMARY_L, padx=12, pady=8)
        info.grid(row=6, column=0, columnspan=3, sticky="we", pady=(14, 0))
        tk.Label(info, text=f"  共 {page_count} 页  |  正面 + 背面自动交替合并",
                 font=("", 9), bg=C_PRIMARY_L, fg=C_PRIMARY).pack()

        body.columnconfigure(0, weight=1)

        # 底部按钮
        btn_bar = tk.Frame(self, bg=C_BG, padx=20, pady=10)
        btn_bar.pack(fill="x", side="bottom")
        ttk.Button(btn_bar, text="取消", command=self._cancel,
                  style="Custom.TButton").pack(side="right", padx=(6, 0))
        ttk.Button(btn_bar, text="保存", command=self._save,
                  style="Success.TButton").pack(side="right")

        self.bind("<Return>", lambda e: self._save())
        self.bind("<Escape>", lambda e: self._cancel())

    def _browse(self):
        d = filedialog.askdirectory(title="选择保存位置", initialdir=self.dir_var.get())
        if d:
            self.dir_var.set(d)

    def _save(self):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showwarning("提示", "请输入文件名", parent=self)
            return
        d = self.dir_var.get().strip()
        if not os.path.isdir(d):
            try:
                os.makedirs(d, exist_ok=True)
            except:
                messagebox.showerror("错误", f"无法创建目录: {d}", parent=self)
                return
        fmt = self.fmt_var.get()
        if fmt == "PDF":
            ext = ".pdf"
        elif fmt == "PNG 图片":
            ext = ""
        else:
            ext = ""
        if not name.endswith(ext) and ext:
            name = name + ext
        self.result = (os.path.join(d, name), fmt)
        self.destroy()

    def _cancel(self):
        self.result = None
        self.destroy()


class ThumbnailItem:
    """单个缩略图项"""
    def __init__(self, parent, image, page_num, side, rotate_cb, delete_cb, index, root):
        self.image = image
        self.page_num = page_num
        self.side = side
        self.index = index
        self.rotate_cb = rotate_cb
        self.delete_cb = delete_cb
        self._photo = None
        self.root = root

        bg = C_FRONT_BG if side == "front" else C_BACK_BG
        border = C_FRONT_BD if side == "front" else C_BACK_BD

        self.frame = tk.Frame(parent, bg=C_CARD, bd=0, highlightthickness=2,
                              highlightbackground=border, highlightcolor=border)

        inner = tk.Frame(self.frame, bg=C_CARD, padx=6, pady=4)
        inner.pack(fill="both", expand=True)

        tk.Label(inner, text=f"第 {page_num} 页", font=("", 9, "bold"),
                 bg=C_CARD, fg=C_TEXT).pack()

        thumb = image.copy()
        thumb.thumbnail((130, 180), LANCZOS)
        self._set_photo(thumb)
        self.img_label = tk.Label(inner, bg=C_CARD)
        self.img_label.pack(pady=3)
        self._update_label()

        side_text = "正面" if side == "front" else "背面"
        tag_color = C_FRONT_BD if side == "front" else C_BACK_BD
        tk.Label(inner, text=side_text, font=("", 8), bg=bg, fg=tag_color,
                 padx=8, pady=1).pack()

        btn_frame = tk.Frame(inner, bg=C_CARD)
        btn_frame.pack(pady=2)
        ttk.Button(btn_frame, text="旋转", command=self._on_rotate,
                   style="Small.TButton", width=4).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="删除", command=self._on_delete,
                   style="Danger.TButton", width=4).pack(side="left", padx=2)

    def _set_photo(self, thumb):
        if HAS_IMAGETK:
            self._photo = ImageTk.PhotoImage(thumb)
        else:
            fd, tmp = tempfile.mkstemp(suffix=".ppm")
            thumb.save(tmp, "PPM")
            os.close(fd)
            self._photo = tk.PhotoImage(file=tmp)
            os.unlink(tmp)

    def _update_label(self):
        if self._photo:
            self.img_label.config(image=self._photo)
            self.img_label.image = self._photo

    def _on_rotate(self):
        self.rotate_cb(self.index, self.side)

    def _on_delete(self):
        self.delete_cb(self.index, self.side)

    def update_image(self, image):
        self.image = image
        thumb = image.copy()
        thumb.thumbnail((130, 180), LANCZOS)
        self._set_photo(thumb)
        self._update_label()

    def destroy(self):
        self.frame.destroy()


class ScannerApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"{APP_NAME}  v{VERSION}")
        self.root.geometry("1180x820")
        self.root.minsize(950, 640)
        self.root.configure(bg=C_BG)

        # 应用图标
        self._icon_photo = load_app_icon()
        if self._icon_photo:
            try:
                self.root.iconphoto(True, self._icon_photo)
            except:
                pass

        self.front_pages = []
        self.back_pages = []
        self.scanning = False
        self.scanners = []
        self._settings = {}

        self._load_settings()
        self._setup_styles()
        self._build_ui()
        self._refresh_thumbnails("front")
        self._refresh_thumbnails("back")
        self._refresh_scanners()

    def _load_settings(self):
        """从配置文件加载上次设置"""
        try:
            with open(CONFIG_FILE, "r") as f:
                self._settings = json.load(f)
        except:
            self._settings = {}

    def _save_settings(self):
        """保存当前设置"""
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            data = {
                "resolution": self.res_var.get(),
                "color_mode": self.color_var.get(),
                "paper_size": self.paper_var.get(),
                "scan_source": self.source_var.get(),
                "manual_device": self.manual_device_var.get(),
                "back_order": self.back_order_var.get(),
            }
            with open(CONFIG_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except:
            pass

    def _setup_styles(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except:
            pass

        style.configure(".", font=("", 10), background=C_BG, foreground=C_TEXT)

        style.configure("Primary.TButton", font=("", 10, "bold"),
                        foreground="white", background=C_PRIMARY,
                        borderwidth=0, focusthickness=0, padding=(12, 6))
        style.map("Primary.TButton",
                  background=[("active", C_PRIMARY_H), ("disabled", "#94a3b8")])

        style.configure("Front.TButton", font=("", 11, "bold"),
                        foreground="white", background=C_FRONT_BD,
                        borderwidth=0, focusthickness=0, padding=(16, 8))
        style.map("Front.TButton",
                  background=[("active", "#2563eb"), ("disabled", "#94a3b8")])

        style.configure("Back.TButton", font=("", 11, "bold"),
                        foreground="white", background=C_BACK_BD,
                        borderwidth=0, focusthickness=0, padding=(16, 8))
        style.map("Back.TButton",
                  background=[("active", "#b91c1c"), ("disabled", "#94a3b8")])

        style.configure("Stop.TButton", font=("", 11, "bold"),
                        foreground="white", background=C_DANGER,
                        borderwidth=0, focusthickness=0, padding=(16, 8))
        style.map("Stop.TButton",
                  background=[("active", "#991b1b"), ("disabled", "#94a3b8")])

        style.configure("Success.TButton", font=("", 10, "bold"),
                        foreground="white", background=C_SUCCESS,
                        borderwidth=0, focusthickness=0, padding=(12, 6))
        style.map("Success.TButton",
                  background=[("active", "#15803d"), ("disabled", "#94a3b8")])

        style.configure("Danger.TButton", font=("", 9),
                        foreground=C_DANGER, background=C_CARD,
                        borderwidth=1, focusthickness=0, padding=(8, 3))
        style.map("Danger.TButton",
                  background=[("active", "#fee2e2")])

        style.configure("Small.TButton", font=("", 9),
                        foreground=C_TEXT_SEC, background=C_CARD,
                        borderwidth=1, focusthickness=0, padding=(8, 3))
        style.map("Small.TButton",
                  background=[("active", "#e2e8f0")])

        style.configure("Custom.TButton", font=("", 10),
                        foreground=C_TEXT, background=C_CARD,
                        borderwidth=1, focusthickness=0, padding=(12, 6))
        style.map("Custom.TButton",
                  background=[("active", "#e2e8f0")])

        style.configure("Card.TFrame", background=C_CARD)
        style.configure("Bg.TFrame", background=C_BG)
        style.configure("Custom.TEntry", padding=(6, 4))

        # 下拉框样式 — 白底蓝边
        style.configure("TCombobox",
                        fieldbackground=C_CARD,
                        background=C_PRIMARY,
                        foreground=C_TEXT,
                        borderwidth=1,
                        relief="solid",
                        padding=(6, 4),
                        arrowcolor="white",
                        darkcolor=C_BORDER,
                        lightcolor=C_BORDER)
        style.map("TCombobox",
                  fieldbackground=[("readonly", C_CARD)],
                  foreground=[("readonly", C_TEXT)],
                  background=[("active", C_PRIMARY_H)],
                  bordercolor=[("focus", C_PRIMARY)])
        # 下拉箭头按钮
        style.configure("TCombobox.Dropdown.Button",
                        background=C_PRIMARY,
                        foreground="white",
                        borderwidth=0,
                        arrowcolor="white")
        style.map("TCombobox.Dropdown.Button",
                  background=[("active", C_PRIMARY_H)])

    def _build_ui(self):
        # 菜单
        menubar = tk.Menu(self.root, bg=C_CARD, fg=C_TEXT, activebackground=C_PRIMARY,
                          activeforeground="white", bd=0)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0, bg=C_CARD, fg=C_TEXT,
                            activebackground=C_PRIMARY, activeforeground="white")
        file_menu.add_command(label="保存为 PDF", command=self._save_pdf, accelerator="Ctrl+S")
        file_menu.add_command(label="保存为图片", command=self._save_images)
        file_menu.add_command(label="导入图片", command=self._import_images)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit, accelerator="Ctrl+Q")
        menubar.add_cascade(label="文件", menu=file_menu)

        help_menu = tk.Menu(menubar, tearoff=0, bg=C_CARD, fg=C_TEXT,
                            activebackground=C_PRIMARY, activeforeground="white")
        help_menu.add_command(label="使用说明", command=self._show_help)
        help_menu.add_command(label="关于", command=self._show_about)
        menubar.add_cascade(label="帮助", menu=help_menu)

        self.root.bind("<Control-s>", lambda e: self._save_pdf())
        self.root.bind("<Control-q>", lambda e: self.root.quit())
        self.root.bind("<F5>", lambda e: self._scan_page("front"))

        outer = ttk.Frame(self.root, style="Bg.TFrame")
        outer.pack(fill="both", expand=True)

        main = tk.Frame(outer, bg=C_BG, padx=16, pady=12)
        main.pack(fill="both", expand=True)

        # ── 标题栏 ──
        header = tk.Frame(main, bg=C_BG)
        header.pack(fill="x", pady=(0, 14))

        tk.Label(header, text=APP_NAME, font=("", 18, "bold"),
                 bg=C_BG, fg=C_TEXT).pack(side="left")
        badge = tk.Frame(header, bg=C_PRIMARY_L, padx=8, pady=2)
        badge.pack(side="left", padx=10, pady=(8, 0))
        tk.Label(badge, text=f"v{VERSION}", font=("", 8, "bold"),
                 bg=C_PRIMARY_L, fg=C_PRIMARY).pack()
        tk.Label(header, text="手动双面扫描  |  SANE / eSCL",
                 font=("", 9), bg=C_BG, fg=C_TEXT_SEC).pack(side="left", pady=(10, 0))

        # ── 设置卡片 ──
        settings_card = self._make_card(main)
        settings_card.pack(fill="x", pady=(0, 10))
        settings_inner = tk.Frame(settings_card, bg=C_CARD, padx=16, pady=12)
        settings_inner.pack(fill="x")

        tk.Label(settings_inner, text="扫描设置", font=("", 11, "bold"),
                 bg=C_CARD, fg=C_PRIMARY).grid(row=0, column=0, columnspan=10, sticky="w", pady=(0, 8))

        # 第一行: 扫描仪
        r1 = tk.Frame(settings_inner, bg=C_CARD)
        r1.grid(row=1, column=0, columnspan=10, sticky="we", pady=2)
        r1.columnconfigure(1, weight=1)

        tk.Label(r1, text="扫描仪", font=("", 9), bg=C_CARD, fg=C_TEXT_SEC,
                 width=8).grid(row=0, column=0, sticky="e", padx=(0, 4))
        self.scanner_var = tk.StringVar()
        self.scanner_combo = ttk.Combobox(r1, textvariable=self.scanner_var)
        self.scanner_combo.grid(row=0, column=1, sticky="we", padx=4)
        ttk.Button(r1, text="刷新", command=self._refresh_scanners,
                   style="Custom.TButton").grid(row=0, column=2, padx=3)
        ttk.Button(r1, text="eSCL", command=self._discover_escl,
                   style="Custom.TButton").grid(row=0, column=3, padx=3)

        # 第二行: 手动设备
        r2 = tk.Frame(settings_inner, bg=C_CARD)
        r2.grid(row=2, column=0, columnspan=10, sticky="we", pady=2)
        r2.columnconfigure(1, weight=1)

        tk.Label(r2, text="手动设备", font=("", 9), bg=C_CARD, fg=C_TEXT_SEC,
                 width=8).grid(row=0, column=0, sticky="e", padx=(0, 4))
        self.manual_device_var = tk.StringVar(value=self._settings.get("manual_device", ""))
        manual_entry = ttk.Entry(r2, textvariable=self.manual_device_var)
        manual_entry.grid(row=0, column=1, sticky="we", padx=4)
        manual_entry.bind("<Return>", lambda e: self._use_manual_device())
        ttk.Button(r2, text="使用", command=self._use_manual_device,
                   style="Primary.TButton").grid(row=0, column=2, padx=4)
        tk.Label(r2, text="填入设备名后点「使用」", font=("", 8), bg=C_CARD, fg=C_TEXT_SEC).grid(row=0, column=3, sticky="w", padx=4)

        # 第三行: 参数
        r3 = tk.Frame(settings_inner, bg=C_CARD)
        r3.grid(row=3, column=0, columnspan=10, sticky="we", pady=2)

        tk.Label(r3, text="分辨率", font=("", 9), bg=C_CARD, fg=C_TEXT_SEC).grid(row=0, column=0, sticky="e", padx=(0, 4))
        self.res_var = tk.StringVar(value=self._settings.get("resolution", "300"))
        ttk.Combobox(r3, textvariable=self.res_var, values=RESOLUTIONS, width=5,
                     state="readonly").grid(row=0, column=1, padx=4)
        tk.Label(r3, text="DPI", font=("", 8), bg=C_CARD, fg=C_TEXT_SEC).grid(row=0, column=2)

        tk.Label(r3, text="颜色", font=("", 9), bg=C_CARD, fg=C_TEXT_SEC).grid(row=0, column=3, sticky="e", padx=(14, 4))
        self.color_var = tk.StringVar(value=self._settings.get("color_mode", "Color"))
        ttk.Combobox(r3, textvariable=self.color_var, values=COLOR_MODES, width=7,
                     state="readonly").grid(row=0, column=4, padx=4)

        tk.Label(r3, text="纸张", font=("", 9), bg=C_CARD, fg=C_TEXT_SEC).grid(row=0, column=5, sticky="e", padx=(14, 4))
        self.paper_var = tk.StringVar(value=self._settings.get("paper_size", "A4"))
        ttk.Combobox(r3, textvariable=self.paper_var, values=list(PAPER_SIZES.keys()),
                     width=7, state="readonly").grid(row=0, column=6, padx=4)

        tk.Label(r3, text="来源", font=("", 9), bg=C_CARD, fg=C_TEXT_SEC).grid(row=0, column=7, sticky="e", padx=(14, 4))
        self.source_var = tk.StringVar(value=self._settings.get("scan_source", "平板"))
        ttk.Combobox(r3, textvariable=self.source_var,
                     values=[s[0] for s in SCAN_SOURCES], width=10,
                     state="readonly").grid(row=0, column=8, padx=4)

        tk.Label(r3, text="背面页序", font=("", 9), bg=C_CARD, fg=C_TEXT_SEC).grid(row=0, column=9, sticky="e", padx=(14, 4))
        self.back_order_var = tk.StringVar(value=self._settings.get("back_order", "倒序"))
        back_order_cb = ttk.Combobox(r3, textvariable=self.back_order_var,
                     values=["倒序", "正序"], width=6,
                     state="readonly")
        back_order_cb.grid(row=0, column=10, padx=4)
        back_order_cb.bind("<<ComboboxSelected>>", lambda e: self._on_back_order_changed())

        # ── 操作按钮 ──
        btn_card = self._make_card(main)
        btn_card.pack(fill="x", pady=(0, 10))
        btn_inner = tk.Frame(btn_card, bg=C_CARD, padx=16, pady=10)
        btn_inner.pack(fill="x")

        self.scan_front_btn = ttk.Button(btn_inner, text="扫描正面",
                                        command=lambda: self._scan_page("front"),
                                        style="Front.TButton")
        self.scan_front_btn.pack(side="left", padx=4)

        self.scan_back_btn = ttk.Button(btn_inner, text="扫描背面",
                                       command=lambda: self._scan_page("back"),
                                       style="Back.TButton")
        self.scan_back_btn.pack(side="left", padx=4)

        # 停止扫描按钮 (ADF多页时显示)
        self.stop_btn = ttk.Button(btn_inner, text="停止扫描",
                                   command=self._stop_scanning,
                                   style="Stop.TButton")
        # 默认隐藏, 扫描时显示

        tk.Frame(btn_inner, width=2, bg=C_BORDER).pack(side="left", fill="y", padx=10)

        ttk.Button(btn_inner, text="保存 PDF", command=self._save_pdf,
                   style="Success.TButton").pack(side="left", padx=4)
        ttk.Button(btn_inner, text="保存图片", command=self._save_images,
                   style="Custom.TButton").pack(side="left", padx=4)
        ttk.Button(btn_inner, text="导入图片", command=self._import_images,
                   style="Custom.TButton").pack(side="left", padx=4)
        ttk.Button(btn_inner, text="清空", command=self._clear_all,
                   style="Danger.TButton").pack(side="left", padx=4)

        tk.Frame(btn_inner, width=2, bg=C_BORDER).pack(side="left", fill="y", padx=10)
        ttk.Button(btn_inner, text="说明", command=self._show_help,
                   style="Custom.TButton").pack(side="left", padx=4)

        # ── 缩略图区 ──
        thumb_container = tk.Frame(main, bg=C_BG)
        thumb_container.pack(fill="both", expand=True, pady=(0, 8))
        thumb_container.columnconfigure(0, weight=1)
        thumb_container.columnconfigure(1, weight=1)

        # 正面
        front_card, _ = self._make_side_card(thumb_container, "正面页", "第 1, 3, 5, 7... 页",
                                           C_FRONT_BD, C_FRONT_BG)
        front_card.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        self.front_wrapper = tk.Frame(front_card, bg=C_FRONT_BG)
        self.front_wrapper.pack(fill="both", expand=True, padx=4, pady=4)

        # Canvas + 水平滚动条 — 支持多页横向滚动
        self.front_canvas = tk.Canvas(self.front_wrapper, bg=C_FRONT_BG,
                                       highlightthickness=0, bd=0, height=340)
        front_scroll = ttk.Scrollbar(self.front_wrapper, orient="horizontal",
                                      command=self.front_canvas.xview)
        self.front_canvas.configure(xscrollcommand=front_scroll.set)
        self.front_canvas.pack(side="top", fill="both", expand=True)
        front_scroll.pack(side="bottom", fill="x")
        self.front_inner = tk.Frame(self.front_canvas, bg=C_FRONT_BG)
        self.front_canvas_window = self.front_canvas.create_window(
            (0, 0), window=self.front_inner, anchor="nw")
        # 内部 Frame 高度跟 Canvas 高度
        self.front_canvas.bind("<Configure>",
            lambda e: self.front_canvas.itemconfig(
                self.front_canvas_window, height=e.height))
        # scrollregion 跟随内容变化
        self.front_inner.bind("<Configure>",
            lambda e: self.front_canvas.configure(
                scrollregion=self.front_canvas.bbox("all")))
        # 鼠标滚轮横向滚动
        self.front_canvas.bind("<Enter>",
            lambda e: self._bind_wheel(self.front_canvas))
        self.front_canvas.bind("<Leave>",
            lambda e: self._unbind_wheel())
        self.front_thumbs = []

        # 背面
        back_card, self.back_subtitle_label = self._make_side_card(thumb_container, "背面页", "倒序合并 (翻转整叠)",
                                   C_BACK_BD, C_BACK_BG)
        back_card.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        self.back_wrapper = tk.Frame(back_card, bg=C_BACK_BG)
        self.back_wrapper.pack(fill="both", expand=True, padx=4, pady=4)

        self.back_canvas = tk.Canvas(self.back_wrapper, bg=C_BACK_BG,
                                      highlightthickness=0, bd=0, height=340)
        back_scroll = ttk.Scrollbar(self.back_wrapper, orient="horizontal",
                                     command=self.back_canvas.xview)
        self.back_canvas.configure(xscrollcommand=back_scroll.set)
        self.back_canvas.pack(side="top", fill="both", expand=True)
        back_scroll.pack(side="bottom", fill="x")
        self.back_inner = tk.Frame(self.back_canvas, bg=C_BACK_BG)
        self.back_canvas_window = self.back_canvas.create_window(
            (0, 0), window=self.back_inner, anchor="nw")
        self.back_canvas.bind("<Configure>",
            lambda e: self.back_canvas.itemconfig(
                self.back_canvas_window, height=e.height))
        self.back_inner.bind("<Configure>",
            lambda e: self.back_canvas.configure(
                scrollregion=self.back_canvas.bbox("all")))
        self.back_canvas.bind("<Enter>",
            lambda e: self._bind_wheel(self.back_canvas))
        self.back_canvas.bind("<Leave>",
            lambda e: self._unbind_wheel())
        self.back_thumbs = []

        # 进度条
        self.progress = ttk.Progressbar(main, mode="indeterminate")

        # 状态栏
        status_frame = tk.Frame(main, bg=C_CARD, bd=0, highlightthickness=1,
                                highlightbackground=C_BORDER, highlightcolor=C_BORDER)
        status_frame.pack(fill="x")
        self.status_var = tk.StringVar(value="就绪 — 请放置文档后点击「扫描正面」")
        self.status_label = tk.Label(status_frame, textvariable=self.status_var,
                                     font=("", 9), bg=C_CARD, fg=C_TEXT_SEC,
                                     anchor="w", padx=12, pady=6)
        self.status_label.pack(fill="x")

    def _make_card(self, parent):
        return tk.Frame(parent, bg=C_CARD, bd=0, highlightthickness=1,
                        highlightbackground=C_BORDER, highlightcolor=C_BORDER)

    def _make_side_card(self, parent, title, subtitle, border_color, bg_color):
        card = tk.Frame(parent, bg=C_CARD, bd=0, highlightthickness=2,
                        highlightbackground=border_color, highlightcolor=border_color)
        header = tk.Frame(card, bg=border_color)
        header.pack(fill="x")
        tk.Label(header, text=f"  {title}", font=("", 10, "bold"),
                 bg=border_color, fg="white", pady=4).pack(side="left", padx=4)
        sub_label = tk.Label(header, text=f"{subtitle}  ", font=("", 8),
                 bg=border_color, fg="#e0e7ff")
        sub_label.pack(side="right", padx=4)
        return card, sub_label

    def _set_status(self, text, color=None):
        self.status_var.set(text)
        self.status_label.config(fg=color or C_TEXT_SEC)

    def _refresh_scanners(self):
        self._set_status("正在检测扫描仪...")
        self.root.update()
        try:
            result = subprocess.run(["scanimage", "-L"], capture_output=True, text=True, timeout=45)
            scanners = []
            output = result.stdout + result.stderr
            for line in output.split("\n"):
                bt = line.find("`")
                if bt < 0:
                    continue
                sq = line.find("'", bt + 1)
                if sq < 0:
                    continue
                device = line[bt+1:sq]
                if not device:
                    continue
                rest = line[sq+1:].strip()
                if rest.lower().startswith("is a "):
                    desc = rest[6:].strip()
                else:
                    desc = rest
                scanners.append((device, f"{device} - {desc}"))
            self.scanners = scanners
            self.scanner_combo["values"] = [s[1] for s in scanners]
            if scanners:
                self.scanner_var.set(scanners[0][1])
                self._set_status(f"检测到 {len(scanners)} 个扫描仪: {scanners[0][0]}", C_SUCCESS)
            else:
                self.scanner_var.set("")
                self._set_status("SANE 未检测到扫描仪，点击「eSCL」搜索，或在手动设备栏填入: lenovo3:net1;dev0", C_WARN)
        except FileNotFoundError:
            self._set_status("未安装 scanimage，请运行: sudo apt install sane-utils", C_DANGER)
        except subprocess.TimeoutExpired:
            self._set_status("检测超时，请在「手动设备」栏填入: lenovo3:net1;dev0", C_WARN)
        except Exception as e:
            self._set_status(f"检测失败: {e}", C_DANGER)

    def _discover_escl(self):
        self._set_status("正在搜索网络扫描仪 (eSCL)...")
        self.root.update()
        self.progress.pack(fill="x", pady=(4, 0))
        self.progress.start()

        def do_discover():
            found = []
            try:
                result = subprocess.run(
                    ["avahi-browse", "-r", "-t", "_uscan._tcp"],
                    capture_output=True, text=True, timeout=10
                )
                lines = result.stdout.split("\n")
                ip = None
                port = 80
                for line in lines:
                    if "=" in line and "address" in line.lower():
                        parts = line.split("=")
                        if len(parts) >= 2:
                            ip = parts[1].strip().split("[")[0].strip()
                    if "port" in line.lower() and "=" in line:
                        parts = line.split("=")
                        if len(parts) >= 2:
                            try:
                                port = int(parts[1].strip().split()[0])
                            except:
                                pass
                if ip:
                    device = f"escl:http://{ip}:{port}"
                    found.append((device, f"eSCL 网络扫描仪 ({ip}:{port})"))
            except:
                pass

            if not found:
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    s.connect(("8.8.8.8", 80))
                    my_ip = s.getsockname()[0]
                    s.close()
                    subnet = ".".join(my_ip.split(".")[:3])
                    self.root.after(0, lambda: self._set_status(f"正在扫描 {subnet}.1-254 ..."))
                    for i in range(1, 255):
                        ip = f"{subnet}.{i}"
                        for port in [80, 8080, 9100]:
                            try:
                                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                                sock.settimeout(0.3)
                                result = sock.connect_ex((ip, port))
                                sock.close()
                                if result == 0 and port in [80, 8080]:
                                    device = f"escl:http://{ip}:{port}"
                                    try:
                                        r = urlopen(f"http://{ip}:{port}/eSCL/ScannerStatus", timeout=1)
                                        if r.status == 200:
                                            found.append((device, f"eSCL 网络扫描仪 ({ip}:{port})"))
                                            break
                                    except:
                                        found.append((device, f"网络设备 ({ip}:{port})"))
                                        break
                            except:
                                pass
                except:
                    pass
            self.root.after(0, lambda: self._on_escl_discovered(found))

        thread = threading.Thread(target=do_discover, daemon=True)
        thread.start()

    def _on_escl_discovered(self, found):
        self.progress.stop()
        self.progress.pack_forget()
        if found:
            existing = set(d for d, _ in self.scanners)
            for device, desc in found:
                if device not in existing:
                    self.scanners.append((device, desc))
                    existing.add(device)
            self.scanner_combo["values"] = [s[1] for s in self.scanners]
            if self.scanners:
                self.scanner_var.set(self.scanners[-1][1])
            self._set_status(f"共检测到 {len(self.scanners)} 个扫描仪", C_SUCCESS)
        else:
            self._set_status("未找到 eSCL 扫描仪。请在「手动设备」栏填入: lenovo3:net1;dev0", C_WARN)

    def _use_manual_device(self):
        """确认使用手动输入的设备名"""
        device = self.manual_device_var.get().strip()
        if not device:
            messagebox.showwarning("提示", "请先在输入框中填写设备名\n\n示例: lenovo3:net1;dev0")
            return
        self._save_settings()
        # 添加到扫描仪列表
        existing = set(d for d, _ in self.scanners)
        if device not in existing:
            self.scanners.append((device, f"{device} (手动)"))
            existing.add(device)
            self.scanner_combo["values"] = [s[1] for s in self.scanners]
        # 选中
        for d, desc in self.scanners:
            if d == device:
                self.scanner_var.set(desc)
                break
        self._set_status(f"已切换到设备: {device}", C_SUCCESS)

    def _get_scanner_device(self):
        manual = self.manual_device_var.get().strip()
        if manual:
            return manual
        selected = self.scanner_var.get()
        for device, desc in self.scanners:
            if desc == selected:
                return device
        return None

    def _scan_page(self, side):
        if self.scanning:
            return
        self._save_settings()
        device = self._get_scanner_device()
        if not device:
            messagebox.showwarning("提示",
                "请先选择扫描仪或在「手动设备」栏填写设备名\n\n"
                "示例:\n"
                "  lenovo3:net1;dev0\n"
                "  escl:http://192.168.0.169:80")
            return

        self.scanning = True
        self._stop_scan = False
        self.scan_front_btn.config(state="disabled")
        self.scan_back_btn.config(state="disabled")

        # 判断是否 ADF 模式, 显示停止按钮
        source_name = self.source_var.get()
        source_val = None
        for name, val in SCAN_SOURCES:
            if name == source_name:
                source_val = val
                break
        if source_val and "ADF" in source_val.upper():
            self.stop_btn.pack(side="left", padx=4)

        side_text = "正面" if side == "front" else "背面"
        self._set_status(f"正在扫描{side_text}... 请稍候", C_PRIMARY)
        self.progress.pack(fill="x", pady=(4, 0))
        self.progress.start()

        def do_scan():
            try:
                paper = self.paper_var.get()
                paper_dims = PAPER_SIZES.get(paper)
                source_name = self.source_var.get()
                source_val = None
                for name, val in SCAN_SOURCES:
                    if name == source_name:
                        source_val = val
                        break

                option_sets = []
                full = ["--resolution", self.res_var.get(), "--mode", self.color_var.get()]
                if source_val:
                    full.extend(["--source", source_val])
                if paper_dims:
                    w, h = paper_dims
                    full.extend(["-x", str(w), "-y", str(h)])
                option_sets.append(("完整", full))

                no_mode = ["--resolution", self.res_var.get()]
                if source_val:
                    no_mode.extend(["--source", source_val])
                if paper_dims:
                    no_mode.extend(["-x", str(w), "-y", str(h)])
                option_sets.append(("无mode", no_mode))

                no_res = []
                if source_val:
                    no_res.extend(["--source", source_val])
                if paper_dims:
                    no_res.extend(["-x", str(w), "-y", str(h)])
                option_sets.append(("无mode+res", no_res))

                no_src = []
                if paper_dims:
                    no_src.extend(["-x", str(w), "-y", str(h)])
                option_sets.append(("无mode+res+source", no_src))

                option_sets.append(("仅默认", []))

                is_adf = source_val and "ADF" in source_val.upper()
                used_label = ""
                last_error = ""
                page_count = 0
                max_pages = 200

                if is_adf:
                    # ── ADF 多页批量扫描 (优先用 --batch 模式) ──
                    tmpdir = tempfile.mkdtemp(prefix="docscan_")
                    batch_pattern = os.path.join(tmpdir, "page_%04d.pnm")

                    self.root.after(0, lambda: self._set_status(
                        f"正在批量扫描{side_text}... (ADF进稿器, --batch模式)", C_PRIMARY))

                    batch_ok = False
                    for label, opts in option_sets:
                        if self._stop_scan:
                            break
                        # 清理旧文件
                        for old in glob.glob(os.path.join(tmpdir, "page_*.pnm")):
                            try:
                                os.unlink(old)
                            except:
                                pass
                        cmd = ["scanimage", "-d", device, "--format", "pnm",
                               "--batch=" + batch_pattern, "--batch-count=200"] + opts
                        try:
                            result = subprocess.run(cmd, capture_output=True, timeout=600)
                            page_files = sorted(glob.glob(os.path.join(tmpdir, "page_*.pnm")))
                            if page_files:
                                used_label = label
                                batch_ok = True
                                break
                            last_error = result.stderr.decode("utf-8", errors="replace").strip()
                            stderr_lower = last_error.lower()
                            if any(k in stderr_lower for k in ["failed", "invalid", "unknown", "not support"]):
                                continue
                            else:
                                break
                        except subprocess.TimeoutExpired:
                            last_error = "批量扫描超时(600秒)"
                            continue

                    if batch_ok:
                        # ── 读取 --batch 生成的文件 ──
                        page_files = sorted(glob.glob(os.path.join(tmpdir, "page_*.pnm")))
                        for pf in page_files:
                            if self._stop_scan:
                                break
                            try:
                                img = Image.open(pf)
                                # 不跳过空白页，全部保留，用户可在预览中手动删除
                                if side == "front":
                                    self.front_pages.append(img)
                                else:
                                    self.back_pages.append(img)
                                page_count += 1
                                self.root.after(0, lambda: self._refresh_thumbnails(side))
                                self.root.after(0, lambda n=page_count: self._set_status(
                                    f"已扫描{side_text} {n} 页...", C_PRIMARY))
                            except Exception:
                                continue
                            finally:
                                try:
                                    os.unlink(pf)
                                except:
                                    pass
                    else:
                        # ── 回退: 循环扫描 + 长延迟 ──
                        self.root.after(0, lambda: self._set_status(
                            f"正在循环扫描{side_text}... (ADF进稿器, 回退模式)", C_PRIMARY))

                        while page_count < max_pages and not self._stop_scan:
                            self.root.after(0, lambda n=page_count+1: self._set_status(
                                f"正在扫描{side_text}第 {n} 页... (ADF进稿器)", C_PRIMARY))

                            result = None
                            for label, opts in option_sets:
                                if self._stop_scan:
                                    break
                                cmd = ["scanimage", "-d", device, "--format", "pnm"] + opts
                                try:
                                    result = subprocess.run(cmd, capture_output=True, timeout=180)
                                    if result.returncode == 0 and result.stdout:
                                        if not used_label:
                                            used_label = label
                                        break
                                    last_error = result.stderr.decode("utf-8", errors="replace").strip()
                                    stderr_lower = last_error.lower()
                                    if any(k in stderr_lower for k in [
                                        "no document", "feeder", "no paper",
                                        "empty", "out of"
                                    ]):
                                        result = None
                                        break
                                    if any(k in stderr_lower for k in ["failed", "invalid", "unknown"]):
                                        continue
                                    else:
                                        break
                                except subprocess.TimeoutExpired:
                                    last_error = "扫描超时(180秒)"
                                    continue

                            if self._stop_scan:
                                break
                            if not result or result.returncode != 0 or not result.stdout:
                                break

                            img = Image.open(io.BytesIO(result.stdout))
                            # 不跳过空白页，全部保留，用户可在预览中手动删除
                            if side == "front":
                                self.front_pages.append(img)
                            else:
                                self.back_pages.append(img)
                            page_count += 1
                            self.root.after(0, lambda: self._refresh_thumbnails(side))
                            self.root.after(0, lambda n=page_count: self._set_status(
                                f"已扫描{side_text} {n} 页, 继续扫描...", C_PRIMARY))
                            # 等 3 秒让进稿器送纸
                            time.sleep(3)

                    try:
                        os.rmdir(tmpdir)
                    except:
                        pass

                    if page_count == 0:
                        raise Exception(
                            f"扫描失败: {last_error}" if last_error
                            else "ADF为空，请放入文档后重试")

                    total = len(self.front_pages) + len(self.back_pages)
                    self.root.after(0, lambda: self._set_status(
                        f"扫描完成 [{used_label}] — 正面 {len(self.front_pages)} 页, "
                        f"背面 {len(self.back_pages)} 页, 共 {total} 页", C_SUCCESS))

                else:
                    # ── 平板单页扫描 ──
                    result = None
                    for label, opts in option_sets:
                        cmd = ["scanimage", "-d", device, "--format", "pnm"] + opts
                        self.root.after(0, lambda l=label: self._set_status(
                            f"正在扫描{side_text}... [{l}] (可能需要10-60秒)", C_PRIMARY))
                        try:
                            result = subprocess.run(cmd, capture_output=True, timeout=180)
                            if result.returncode == 0 and result.stdout:
                                used_label = label
                                break
                            last_error = result.stderr.decode("utf-8", errors="replace").strip()
                            stderr_lower = last_error.lower()
                            if any(k in stderr_lower for k in ["failed", "invalid", "unknown"]):
                                continue
                            else:
                                break
                        except subprocess.TimeoutExpired:
                            last_error = "扫描超时(180秒)"
                            continue

                    if not result or result.returncode != 0 or not result.stdout:
                        raise Exception(
                            f"扫描失败: {last_error}" if last_error else "扫描失败: 未知错误")

                    img = Image.open(io.BytesIO(result.stdout))
                    if side == "front":
                        self.front_pages.append(img)
                    else:
                        self.back_pages.append(img)

                    self.root.after(0, lambda: self._refresh_thumbnails(side))
                    total = len(self.front_pages) + len(self.back_pages)
                    self.root.after(0, lambda: self._set_status(
                        f"扫描完成 [{used_label}] — 正面 {len(self.front_pages)} 页, "
                        f"背面 {len(self.back_pages)} 页, 共 {total} 页", C_SUCCESS))

            except subprocess.TimeoutExpired:
                self.root.after(0, lambda: messagebox.showerror("超时", "扫描超时(180秒)，请重试"))
                self.root.after(0, lambda: self._set_status("扫描超时", C_DANGER))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("扫描错误", str(e)))
                self.root.after(0, lambda: self._set_status(f"扫描失败: {e}", C_DANGER))
            finally:
                self.root.after(0, self._scan_done)

        thread = threading.Thread(target=do_scan, daemon=True)
        thread.start()

    def _stop_scanning(self):
        """用户点击停止扫描"""
        self._stop_scan = True
        self._set_status("正在停止扫描...", C_DANGER)

    def _scan_done(self):
        self.scanning = False
        self._stop_scan = False
        self.scan_front_btn.config(state="normal")
        self.scan_back_btn.config(state="normal")
        self.stop_btn.pack_forget()
        self.progress.stop()
        self.progress.pack_forget()

    def _is_blank_image(self, img):
        """检测图片是否为空白页 (ADF空了之后可能返回空白图)"""
        try:
            # 缩小图片加速检测
            small = img.copy()
            small.thumbnail((100, 140), LANCZOS)
            # 转灰度
            gray = small.convert("L")
            # 统计像素值
            pixels = list(gray.getdata())
            total = len(pixels)
            white = sum(1 for p in pixels if p > 240)
            # 98% 以上白色 = 空白页
            return (white / total) > 0.98
        except Exception:
            return False

    def _bind_wheel(self, canvas):
        """绑定鼠标滚轮横向滚动"""
        self._wheel_canvas = canvas
        canvas.bind_all("<Button-4>", self._on_wheel)
        canvas.bind_all("<Button-5>", self._on_wheel)

    def _unbind_wheel(self):
        """解绑鼠标滚轮"""
        if hasattr(self, '_wheel_canvas'):
            self._wheel_canvas.unbind_all("<Button-4>")
            self._wheel_canvas.unbind_all("<Button-5>")
            del self._wheel_canvas

    def _on_wheel(self, event):
        """鼠标滚轮 → 横向滚动"""
        if hasattr(self, '_wheel_canvas'):
            if event.num == 4:
                self._wheel_canvas.xview_scroll(-3, "units")
            elif event.num == 5:
                self._wheel_canvas.xview_scroll(3, "units")

    def _is_blank_image(self, img):
        """检测图片是否为空白页（超过98%白色像素）"""
        try:
            gray = img.convert("L")
            small = gray.resize((100, 140))
            pixels = list(small.getdata())
            white_count = sum(1 for p in pixels if p > 240)
            return white_count / len(pixels) > 0.98
        except:
            return False

    def _refresh_thumbnails(self, side):
        """刷新缩略图 — 清空容器所有子控件后重建, 最可靠方式"""
        if side == "front":
            container = self.front_inner
            pages = self.front_pages
            bg = C_FRONT_BG
            bd_color = C_FRONT_BD
            side_text = "正面"
            side_color = C_PRIMARY
        else:
            container = self.back_inner
            pages = self.back_pages
            bg = C_BACK_BG
            bd_color = C_BACK_BD
            side_text = "背面"
            side_color = C_BACK_BD

        # 1. 清空容器内所有子控件 (包括旧的空状态标签和缩略图)
        for child in container.winfo_children():
            child.destroy()

        # 2. 没有页面 → 显示空状态
        if not pages:
            empty = tk.Label(container,
                             text="暂无扫描\n\n点击「扫描%s」开始\n或「导入图片」加载已有文件" % side_text,
                             font=("", 11), bg=bg, fg=C_PLACEHOLDER,
                             justify="center", width=40, height=15)
            empty.pack(pady=60)
            return

        # 3. 有页面 → 逐个创建缩略图
        for i, img in enumerate(pages):
            if side == "front":
                page_num = (i + 1) * 2 - 1
            else:
                total_back = len(pages)
                if self.back_order_var.get() == "倒序":
                    page_num = (total_back - i) * 2
                else:
                    page_num = (i + 1) * 2

            # 缩略图卡片
            card = tk.Frame(container, bg=C_CARD, bd=0,
                            highlightthickness=2,
                            highlightbackground=bd_color,
                            highlightcolor=bd_color)
            card.pack(side="left", padx=5, pady=5)

            # 页码
            tk.Label(card, text=f"第 {page_num} 页", font=("", 9, "bold"),
                     bg=C_CARD, fg=C_TEXT).pack(pady=(4, 2))

            # 缩略图图片 — 四级降级确保显示
            thumb = img.copy()
            thumb.thumbnail((130, 180), LANCZOS)
            img_shown = False
            # 方式0: ImageTk.PhotoImage (PIL 原生, 质量最好)
            if HAS_IMAGETK:
                try:
                    photo = ImageTk.PhotoImage(thumb)
                    img_label = tk.Label(card, image=photo, bg=C_CARD)
                    img_label.image = photo
                    img_label.pack(pady=2)
                    img_shown = True
                except Exception:
                    pass
            # 方式1: base64 PNG data (最自包含)
            if not img_shown:
                try:
                    buf = io.BytesIO()
                    thumb.convert("RGB").save(buf, format="PNG")
                    b64 = base64.b64encode(buf.getvalue())
                    photo = tk.PhotoImage(data=b64, format="png")
                    img_label = tk.Label(card, image=photo, bg=C_CARD,
                                          width=130, height=180)
                    img_label.image = photo
                    img_label.pack(pady=2)
                    img_shown = True
                except Exception as e1:
                    pass
            # 方式2: GIF 文件 (Tk 原生支持)
            if not img_shown:
                try:
                    thumb_p = thumb.convert("P", palette=Image.ADAPTIVE, colors=256)
                    fd, tmp = tempfile.mkstemp(suffix=".gif")
                    thumb_p.save(tmp, "GIF")
                    os.close(fd)
                    photo = tk.PhotoImage(file=tmp)
                    os.unlink(tmp)
                    img_label = tk.Label(card, image=photo, bg=C_CARD,
                                          width=130, height=180)
                    img_label.image = photo
                    img_label.pack(pady=2)
                    img_shown = True
                except Exception as e2:
                    pass
            # 方式3: 都失败 → 显示错误
            if not img_shown:
                tk.Label(card, text="[图片无法显示]",
                         bg=C_CARD, fg="red", font=("", 9),
                         width=18, height=8).pack(pady=2)
            # 调试: 图片尺寸
            tk.Label(card, text=f"{img.size[0]}x{img.size[1]} {img.mode}",
                     font=("", 7), bg=C_CARD, fg=C_TEXT_SEC).pack()

            # 正面/背面标签
            tk.Label(card, text=side_text, font=("", 8),
                     bg=C_CARD, fg=side_color).pack()

            # 旋转/删除按钮
            btn_frame = tk.Frame(card, bg=C_CARD)
            btn_frame.pack(pady=2)
            ttk.Button(btn_frame, text="旋转", width=5,
                       command=lambda idx=i, s=side: self._rotate_page(idx, s)
                       ).pack(side="left", padx=2)
            ttk.Button(btn_frame, text="查看", width=5,
                       command=lambda img_ref=img, idx=i, s=side: self._view_image(img_ref)
                       ).pack(side="left", padx=2)
            ttk.Button(btn_frame, text="删除", width=5,
                       command=lambda idx=i, s=side: self._delete_page(idx, s)
                       ).pack(side="left", padx=2)

    def _view_image(self, img):
        """用系统默认图片查看器打开原图"""
        try:
            fd, tmp = tempfile.mkstemp(suffix=".png")
            img.save(tmp, "PNG")
            os.close(fd)
            subprocess.Popen(["xdg-open", tmp])
            self._set_status(f"已打开原图 {img.size[0]}x{img.size[1]}")
        except Exception as e:
            messagebox.showerror("错误", f"无法打开图片: {e}")

    def _rotate_page(self, index, side):
        if side == "front":
            self.front_pages[index] = self.front_pages[index].rotate(-90, expand=True)
            self._refresh_thumbnails("front")
        else:
            self.back_pages[index] = self.back_pages[index].rotate(-90, expand=True)
            self._refresh_thumbnails("back")
        self._set_status(f"已旋转第 {index + 1} 页")

    def _delete_page(self, index, side):
        if side == "front":
            del self.front_pages[index]
            self._refresh_thumbnails("front")
        else:
            del self.back_pages[index]
            self._refresh_thumbnails("back")
        total = len(self.front_pages) + len(self.back_pages)
        self._set_status(f"已删除 — 正面 {len(self.front_pages)} 页, 背面 {len(self.back_pages)} 页, 共 {total} 页", C_WARN)

    def _get_merged_pages(self):
        pages = []
        backs = list(self.back_pages)
        if self.back_order_var.get() == "倒序":
            backs.reverse()
        for i in range(max(len(self.front_pages), len(backs))):
            if i < len(self.front_pages):
                pages.append(self.front_pages[i])
            if i < len(backs):
                pages.append(backs[i])
        return pages

    def _on_back_order_changed(self):
        """背面页序切换时更新副标题和缩略图页码"""
        order = self.back_order_var.get()
        if order == "倒序":
            self.back_subtitle_label.config(text="倒序合并 (翻转整叠)  ")
        else:
            self.back_subtitle_label.config(text="正序合并 (逐张翻页)  ")
        self._refresh_thumbnails("back")

    def _save_pdf(self):
        pages = self._get_merged_pages()
        if not pages:
            messagebox.showwarning("提示", "没有扫描的页面，请先扫描")
            return
        default_name = f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        dialog = SaveDialog(self.root, len(pages), default_name)
        self.root.wait_window(dialog)
        if not dialog.result:
            return
        filepath, fmt = dialog.result
        try:
            self._set_status(f"正在保存 {fmt} ({len(pages)} 页)...", C_PRIMARY)
            self.root.update()
            if fmt == "PDF":
                rgb_pages = []
                for img in pages:
                    if img.mode != "RGB":
                        img = img.convert("RGB")
                    rgb_pages.append(img)
                rgb_pages[0].save(filepath, "PDF", save_all=True, append_images=rgb_pages[1:])
            elif fmt == "PNG 图片":
                prefix = os.path.splitext(filepath)[0]
                for i, img in enumerate(pages):
                    img.save(f"{prefix}_page_{i+1:03d}.png", "PNG")
            else:  # JPEG
                prefix = os.path.splitext(filepath)[0]
                for i, img in enumerate(pages):
                    if img.mode == "RGBA":
                        img = img.convert("RGB")
                    img.save(f"{prefix}_page_{i+1:03d}.jpg", "JPEG", quality=90)
            self._set_status(f"已保存: {filepath} ({len(pages)} 页)", C_SUCCESS)
            messagebox.showinfo("成功", f"已保存 {len(pages)} 页到:\n{filepath}")
        except Exception as e:
            messagebox.showerror("保存失败", str(e))
            self._set_status(f"保存失败: {e}", C_DANGER)

    def _save_images(self):
        pages = self._get_merged_pages()
        if not pages:
            messagebox.showwarning("提示", "没有扫描的页面")
            return
        dirname = filedialog.askdirectory(title="选择保存目录", initialdir=str(Path.home() / "桌面"))
        if not dirname:
            return
        try:
            prefix = f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            for i, img in enumerate(pages):
                filepath = os.path.join(dirname, f"{prefix}_page_{i+1:03d}.png")
                img.save(filepath, "PNG")
            self._set_status(f"已保存 {len(pages)} 张图片到: {dirname}", C_SUCCESS)
            messagebox.showinfo("成功", f"已保存 {len(pages)} 张图片到:\n{dirname}")
        except Exception as e:
            messagebox.showerror("保存失败", str(e))
            self._set_status(f"保存失败: {e}", C_DANGER)

    def _import_images(self):
        files = filedialog.askopenfilenames(
            title="选择图片文件",
            filetypes=[("图片文件", "*.png *.jpg *.jpeg *.tif *.tiff *.bmp *.pnm")],
            initialdir=str(Path.home() / "桌面"))
        if not files:
            return
        for f in files:
            try:
                img = Image.open(f)
                self.front_pages.append(img)
            except Exception as e:
                messagebox.showerror("导入失败", f"无法读取 {f}:\n{e}")
        self._refresh_thumbnails("front")
        total = len(self.front_pages) + len(self.back_pages)
        self._set_status(f"已导入 {len(files)} 张图片 — 共 {total} 页")

    def _clear_all(self):
        if not self.front_pages and not self.back_pages:
            return
        if messagebox.askyesno("确认", "确定要清空所有扫描的页面吗？"):
            self.front_pages.clear()
            self.back_pages.clear()
            self._refresh_thumbnails("front")
            self._refresh_thumbnails("back")
            self._set_status("已清空所有页面", C_WARN)

    def _show_help(self):
        help_text = """使用说明

1. 扫描仪检测
   - 点击「刷新」检测 SANE 扫描仪
   - 点击「eSCL」搜索网络扫描仪 (AirPrint)
   - 或在「手动设备」栏直接填写设备名:
     lenovo3:net1;dev0
     escl:http://192.168.0.169:80

2. 扫描来源
   - 自动: 不指定来源，用驱动默认值
   - ADF 输稿器: 自动进纸，适合多页文档
   - 平板: 手动放在玻璃上，一页一页扫

3. 手动双面扫描流程
   1) 扫描所有奇数页(1,3,5...) -> 扫描正面
   2) 翻转文档，扫描所有偶数页(2,4,6...) -> 扫描背面
   3) 点击「保存 PDF」自动交替合并

   背面页序说明:
   - 倒序(默认): 适合翻转整叠纸张
     先扫3张正面(1,3,5), 整叠翻转后扫背面
     背面出来的顺序是6,4,2, 程序自动倒序后合并
   - 正序: 适合逐张翻页
     每张纸先扫正面再翻面扫背面, 背面顺序与正面一致

4. 单面扫描
   只用「扫描正面」扫描所有页面，然后「保存 PDF」

5. ADF 批量扫描
   来源选「ADF 输稿器」放入多页文档，点「扫描正面」
   程序连续扫描全部页面（含空白页），扫完后可在预览中手动删除空白页

6. 快捷键
   F5: 扫描正面 | Ctrl+S: 保存 PDF | Ctrl+Q: 退出

7. 每页可单独旋转或删除

8. 自动适配
   程序会自动适配扫描仪支持的参数
   如果某个参数不被支持会自动去掉重试
"""
        messagebox.showinfo("使用说明", help_text)

    def _show_about(self):
        messagebox.showinfo("关于",
            f"{APP_NAME}  v{VERSION}\n\n"
            "支持手动双面扫描、ADF批量扫描，输出 PDF\n"
            "支持 SANE / eSCL (AirPrint) 协议\n"
            "deb包: LoongArch64 | 脚本安装: 全架构通用\n\n"
            "作者: frozenzero123\n"
            "GitHub: https://github.com/frozenzero123/docscanner\n\n"
            "Python3 + tkinter + Pillow + SANE\n\n"
            "本软件由 Trae AI 指令辅助生成")


def main():
    root = tk.Tk()
    app = ScannerApp(root)
    root.protocol("WM_DELETE_WINDOW", lambda: (app._save_settings(), root.destroy()))
    root.mainloop()


if __name__ == "__main__":
    main()
