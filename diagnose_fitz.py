#!/usr/bin/env python3
"""
诊断 fitz 各种 PDF 嵌入路径的真实体积和内部压缩方式。
用于排查 "PDF 保存后体积过大" 的问题。
"""
import io
import os
import tempfile
import fitz
from PIL import Image, ImageDraw


def _new_page(doc, w_pt, h_pt):
    for name in ("new_page", "newPage"):
        if hasattr(doc, name):
            fn = getattr(doc, name)
            for call in (
                lambda: fn(width=w_pt, height=h_pt),
                lambda: fn(-1, w_pt, h_pt),
            ):
                try:
                    return call()
                except Exception:
                    pass
    raise RuntimeError("无法创建 PDF 页面")


def _insert_image(page, **kwargs):
    for name in ("insert_image", "insertImage"):
        if hasattr(page, name):
            fn = getattr(page, name)
            try:
                fn(page.rect, **kwargs)
                return True
            except Exception as e:
                return e
    return RuntimeError("没有 insert_image 方法")


def _compress_name(doc, page_num=0):
    """查看 PDF 内第一个图像对象的 Filters"""
    try:
        page = doc.load_page(page_num)
        imglist = page.get_images(full=True)
        if not imglist:
            return "无图像"
        xref = imglist[0][0]
        # 兼容老版 fitz：可能没有 get_object
        obj = doc.get_object(xref) if hasattr(doc, "get_object") else None
        if obj is None:
            return "未知"
        filters = obj.get("Filter")
        if filters is None:
            return "无压缩"
        if isinstance(filters, list):
            return "/".join(str(f) for f in filters)
        return str(filters)
    except Exception as e:
        return f"检测失败:{e}"


def _test_path(doc, page_w_pt, page_h_pt, img, label, mode, quality=85, subsampling=1):
    page = _new_page(doc, page_w_pt, page_h_pt)
    err = None
    try:
        if mode == "raw_pixmap":
            cs = getattr(fitz, "csRGB", None)
            if cs is None:
                cs = fitz.Colorspace(getattr(fitz, "CS_RGB", 3))
            raw = img.tobytes("raw", "RGB")
            try:
                pix = fitz.Pixmap(cs, img.width, img.height, raw, False)
            except Exception:
                pix = fitz.Pixmap(cs, img.width, img.height)
                pix.samples = raw
            err = _insert_image(page, pixmap=pix)
        elif mode == "jpeg_file":
            buf = io.BytesIO()
            img.save(buf, "JPEG", quality=quality, subsampling=subsampling, optimize=True)
            tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
            tmp.write(buf.getvalue())
            tmp.close()
            try:
                err = _insert_image(page, filename=tmp.name)
            finally:
                os.unlink(tmp.name)
        elif mode == "png_file":
            buf = io.BytesIO()
            img.save(buf, "PNG", optimize=True)
            tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            tmp.write(buf.getvalue())
            tmp.close()
            try:
                err = _insert_image(page, filename=tmp.name)
            finally:
                os.unlink(tmp.name)
        elif mode == "jpeg_stream":
            buf = io.BytesIO()
            img.save(buf, "JPEG", quality=quality, subsampling=subsampling, optimize=True)
            data = buf.getvalue()
            err = _insert_image(page, stream=data)
        elif mode == "png_stream":
            buf = io.BytesIO()
            img.save(buf, "PNG", optimize=True)
            data = buf.getvalue()
            err = _insert_image(page, stream=data)
        else:
            err = RuntimeError(f"未知模式 {mode}")
    except Exception as e:
        err = e

    if isinstance(err, Exception):
        return None, f"✗ {label}: {type(err).__name__}: {err}"

    tmp_pdf = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    tmp_pdf.close()
    doc.save(tmp_pdf.name, deflate=True, garbage=4)
    size_kb = os.path.getsize(tmp_pdf.name) // 1024
    doc2 = fitz.open(tmp_pdf.name)
    comp = _compress_name(doc2)
    doc2.close()
    os.unlink(tmp_pdf.name)
    return size_kb, f"✓ {label}: {size_kb:>6} KB   内部: {comp}"


def _make_image(w, h, kind="photo"):
    """生成测试图：photo=伪照片, text=黑白文字"""
    img = Image.new("RGB", (w, h), "white")
    draw = ImageDraw.Draw(img)
    if kind == "photo":
        # 彩色渐变/噪声，模拟照片
        for y in range(0, h, 4):
            for x in range(0, w, 4):
                r = (x * 255 // w) ^ (y // 3)
                g = (y * 255 // h) ^ (x // 5)
                b = ((x + y) * 128 // (w + h)) % 255
                draw.rectangle([x, y, x + 4, y + 4], fill=(r, g, b))
    else:
        # 文字：画很多行黑线/黑块模拟文字（避免默认字体不支持中文）
        for i in range(60):
            y = 80 + i * 55
            # 每行不同长度的黑条，模拟真实文字行
            line_w = w - 160 - (i % 5) * 80
            draw.rectangle([80, y, 80 + line_w, y + 18], fill="black")
        # 一个方框模拟图片/表格
        draw.rectangle([80, 3000, w - 80, 3400], outline="black", width=4)
    return img


def main():
    print(f"fitz: {fitz.version[0] if hasattr(fitz, 'version') else '?'}")
    print("")

    # A4 300DPI
    page_w_pt, page_h_pt = 595.28, 841.89
    target_w = int(210 / 25.4 * 300)
    target_h = int(297 / 25.4 * 300)
    print(f"测试页面: A4 300DPI = {target_w}x{target_h} 像素")
    print("")

    modes = [
        ("raw_pixmap+deflate=T", "raw_pixmap"),
        ("PNG_file+deflate=T", "png_file"),
        ("JPEG_file+deflate=T", "jpeg_file"),
        ("JPEG_stream+deflate=T", "jpeg_stream"),
        ("PNG_stream+deflate=T", "png_stream"),
    ]

    for scene, kind in [("彩色图文", "photo"), ("纯文字", "text")]:
        print(f"=== {scene} ===")
        img = _make_image(target_w, target_h, kind)
        for label, mode in modes:
            doc = fitz.open()
            size_kb, msg = _test_path(doc, page_w_pt, page_h_pt, img, label, mode)
            print(f"  {msg}")
            doc.close()
        print("")


if __name__ == "__main__":
    main()
