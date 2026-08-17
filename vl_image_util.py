import os
import json
import base64
from io import BytesIO
from PIL import Image, ImageOps

IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp")


def list_subdirs_recursive(directory: str) -> list[str]:
    """Return the root directory and every subdirectory beneath it (sorted)."""
    if not os.path.isdir(directory):
        return []
    root = os.path.normpath(os.path.abspath(directory))
    out = [root]
    for dirpath, dirnames, _ in os.walk(root):
        for name in dirnames:
            out.append(os.path.join(dirpath, name))
    return sorted(set(out))


def list_image_paths(directory: str) -> list[str]:
    """Recursively collect image file paths under directory (sorted)."""
    if not os.path.isdir(directory):
        return []
    root = os.path.normpath(os.path.abspath(directory))
    out: list[str] = []
    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            if name.lower().endswith(IMAGE_EXTS):
                out.append(os.path.join(dirpath, name))
    out.sort()
    return out


def apply_exif_orientation(image: Image.Image) -> Image.Image:
    try:
        return ImageOps.exif_transpose(image)
    except Exception:
        return image


def load_thumbnail_pil(path: str, thumb_size: tuple[int, int] = (200, 200)) -> Image.Image:
    """Open image, EXIF orientation, fit inside thumb_size, RGBA. Fallback when QImageReader fails."""
    with Image.open(path) as img:
        img.load()
        img = apply_exif_orientation(img)
        thumb = img.copy()
    thumb.thumbnail(thumb_size, Image.LANCZOS)
    if thumb.mode != "RGBA":
        thumb = thumb.convert("RGBA")
    return thumb

def _format_size(bytes_val):
    """将字节转换为 KB, MB, GB 等可读格式"""
    if bytes_val == 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    val = float(bytes_val)
    while val >= 1024 and i < len(units) - 1:
        val /= 1024
        i += 1
    return f"{val:.2f} {units[i]}"

# 压缩后 JPEG 二进制上限（供 API 传输）；base64 体积约为该值的 4/3
_MAX_IMAGE_BYTES = 200 * 1024


def _jpeg_under_size_cap(rgb: Image.Image, max_bytes: int) -> tuple[bytes, int, int]:
    """将 RGB 图像缩放并 JPEG 编码，使输出字节数不超过 max_bytes。"""
    w0, h0 = rgb.size
    scale = 1.0
    qualities = (90, 85, 80, 75, 70, 65, 60, 55, 50, 45, 40, 35, 30, 25, 20, 15, 10)

    while scale >= 0.02:
        w = max(1, int(round(w0 * scale)))
        h = max(1, int(round(h0 * scale)))
        cur = rgb.resize((w, h), Image.LANCZOS) if (w, h) != (w0, h0) else rgb

        for q in qualities:
            buf = BytesIO()
            cur.save(buf, format="JPEG", quality=q, optimize=True)
            data = buf.getvalue()
            if len(data) <= max_bytes:
                return data, w, h

        scale *= 0.75

    tiny = rgb.resize((max(1, w0 // 64), max(1, h0 // 64)), Image.LANCZOS)
    buf = BytesIO()
    tiny.save(buf, format="JPEG", quality=10, optimize=True)
    data = buf.getvalue()
    return data, tiny.size[0], tiny.size[1]

def get_image_data(path):
    """读取图片，压缩为 JPEG 且体积不超过约 43KB，再返回 base64（供 Ollama user.images）。"""
    try:
        if not os.path.exists(path):
            return json.dumps({"error": f"文件不存在: {path}"}, ensure_ascii=False)

        with Image.open(path) as img:
            orig_w, orig_h = img.size
            orig_format = img.format or "UNKNOWN"
            rgb = img.convert("RGB")

        jpeg_bytes, out_w, out_h = _jpeg_under_size_cap(rgb, _MAX_IMAGE_BYTES)
        encoded_string = base64.b64encode(jpeg_bytes).decode("utf-8")

        payload = {
            "ok": True,
            "path": path,
            "metadata": {
                "path": path,
                "format": "JPEG",
                "width": out_w,
                "height": out_h,
                "mode": "RGB",
                "compressed_bytes": len(jpeg_bytes),
                "max_bytes": _MAX_IMAGE_BYTES,
                "original_width": orig_w,
                "original_height": orig_h,
                "original_format": orig_format,
                # "base64": encoded_string,
            },
            "base64": encoded_string,
        }
        return json.dumps(payload, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"读取文件或解析图片失败: {str(e)}"}, ensure_ascii=False)

def rotate_image(self, image):
        try:
            exif = image._getexif()
            if exif:
                orientation = exif.get(0x0112)
                if orientation == 3:
                    image = image.rotate(180, expand=True)
                elif orientation == 6:
                    image = image.rotate(270, expand=True)
                elif orientation == 8:
                    image = image.rotate(90, expand=True)
        except (AttributeError, KeyError, IndexError):
            pass
        return image