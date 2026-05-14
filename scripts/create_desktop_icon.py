from __future__ import annotations

import struct
import zlib
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = PROJECT_ROOT / "assets"
ICON_PATH = ASSETS_DIR / "desktop-icon.ico"
PREVIEW_PATH = ASSETS_DIR / "desktop-icon.png"
SMALL_PREVIEW_PATH = ASSETS_DIR / "desktop-icon-small-preview.png"
ICON_SIZES = (16, 24, 32, 48, 64, 128, 256)

Color = tuple[int, int, int, int]


def main() -> int:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    write_png(PREVIEW_PATH, render_icon(256))
    rendered_icons = {size: render_icon(size) for size in ICON_SIZES}
    write_png(SMALL_PREVIEW_PATH, render_small_preview(rendered_icons))
    write_ico(ICON_PATH, rendered_icons)
    print(f"[ok] Icon written to {ICON_PATH}")
    print(f"[ok] Preview written to {PREVIEW_PATH}")
    print(f"[ok] Small-size preview written to {SMALL_PREVIEW_PATH}")
    return 0


def render_icon(size: int) -> tuple[int, int, list[Color]]:
    if size <= 48:
        return render_small_icon(size)

    scale = 4
    canvas_size = size * scale
    canvas = [(0, 0, 0, 0)] * (canvas_size * canvas_size)

    def px(value: float) -> int:
        return round(value * canvas_size)

    fill_rounded_rect(
        canvas,
        canvas_size,
        px(0.06),
        px(0.06),
        px(0.94),
        px(0.94),
        px(0.19),
        (31, 111, 84, 255),
        (38, 92, 142, 255),
    )
    fill_rounded_rect(
        canvas,
        canvas_size,
        px(0.17),
        px(0.19),
        px(0.71),
        px(0.78),
        px(0.055),
        (43, 84, 128, 130),
    )
    fill_rounded_rect(
        canvas,
        canvas_size,
        px(0.23),
        px(0.16),
        px(0.80),
        px(0.73),
        px(0.06),
        (230, 241, 235, 255),
    )
    fill_rounded_rect(
        canvas,
        canvas_size,
        px(0.18),
        px(0.22),
        px(0.74),
        px(0.82),
        px(0.06),
        (255, 254, 247, 255),
    )
    fill_rect(canvas, canvas_size, px(0.61), px(0.22), px(0.70), px(0.82), (222, 159, 68, 255))
    fill_rect(canvas, canvas_size, px(0.28), px(0.35), px(0.57), px(0.39), (143, 159, 150, 255))
    fill_rect(canvas, canvas_size, px(0.28), px(0.46), px(0.55), px(0.50), (143, 159, 150, 255))

    draw_letter_e(canvas, canvas_size, px(0.27), px(0.58), px(0.13), px(0.18), (24, 63, 82, 255))
    draw_letter_n(canvas, canvas_size, px(0.43), px(0.58), px(0.16), px(0.18), (24, 63, 82, 255))

    return downsample(canvas, canvas_size, size, scale)


def render_small_icon(size: int) -> tuple[int, int, list[Color]]:
    scale = 6
    canvas_size = size * scale
    canvas = [(0, 0, 0, 0)] * (canvas_size * canvas_size)

    def px(value: float) -> int:
        return round(value * canvas_size)

    fill_rounded_rect(
        canvas,
        canvas_size,
        px(0.02),
        px(0.02),
        px(0.98),
        px(0.98),
        px(0.22),
        (31, 111, 84, 255),
        (38, 92, 142, 255),
    )
    fill_rounded_rect(
        canvas,
        canvas_size,
        px(0.15),
        px(0.17),
        px(0.84),
        px(0.84),
        px(0.09),
        (255, 254, 247, 255),
    )
    fill_rect(
        canvas,
        canvas_size,
        px(0.68),
        px(0.17),
        px(0.82),
        px(0.84),
        (222, 159, 68, 255),
    )
    draw_letter_e(
        canvas,
        canvas_size,
        px(0.24),
        px(0.45),
        px(0.18),
        px(0.24),
        (24, 63, 82, 255),
    )
    draw_letter_n(
        canvas,
        canvas_size,
        px(0.46),
        px(0.45),
        px(0.19),
        px(0.24),
        (24, 63, 82, 255),
    )
    return downsample(canvas, canvas_size, size, scale)


def draw_letter_e(
    canvas: list[Color],
    size: int,
    x: int,
    y: int,
    width: int,
    height: int,
    color: Color,
) -> None:
    stroke = max(1, round(width * 0.24))
    fill_rect(canvas, size, x, y, x + stroke, y + height, color)
    fill_rect(canvas, size, x, y, x + width, y + stroke, color)
    fill_rect(canvas, size, x, y + height // 2 - stroke // 2, x + int(width * 0.86), y + height // 2 + stroke // 2, color)
    fill_rect(canvas, size, x, y + height - stroke, x + width, y + height, color)


def draw_letter_n(
    canvas: list[Color],
    size: int,
    x: int,
    y: int,
    width: int,
    height: int,
    color: Color,
) -> None:
    stroke = max(1, round(width * 0.2))
    fill_rect(canvas, size, x, y, x + stroke, y + height, color)
    fill_rect(canvas, size, x + width - stroke, y, x + width, y + height, color)
    for offset in range(-stroke // 2, stroke // 2 + 1):
        draw_line(canvas, size, x + stroke, y + offset, x + width - stroke, y + height + offset, stroke, color)


def fill_rect(
    canvas: list[Color],
    size: int,
    left: int,
    top: int,
    right: int,
    bottom: int,
    color: Color,
) -> None:
    clipped_left = max(0, left)
    clipped_top = max(0, top)
    clipped_right = min(size, right)
    clipped_bottom = min(size, bottom)
    for y in range(clipped_top, clipped_bottom):
        row_offset = y * size
        for x in range(clipped_left, clipped_right):
            canvas[row_offset + x] = blend(color, canvas[row_offset + x])


def fill_rounded_rect(
    canvas: list[Color],
    size: int,
    left: int,
    top: int,
    right: int,
    bottom: int,
    radius: int,
    color_top: Color,
    color_bottom: Color | None = None,
) -> None:
    if color_bottom is None:
        color_bottom = color_top
    height = max(1, bottom - top)
    for y in range(max(0, top), min(size, bottom)):
        ratio = (y - top) / height
        color = mix(color_top, color_bottom, ratio)
        row_offset = y * size
        for x in range(max(0, left), min(size, right)):
            if point_in_rounded_rect(x, y, left, top, right, bottom, radius):
                canvas[row_offset + x] = blend(color, canvas[row_offset + x])


def point_in_rounded_rect(
    x: int,
    y: int,
    left: int,
    top: int,
    right: int,
    bottom: int,
    radius: int,
) -> bool:
    if left + radius <= x < right - radius:
        return True
    if top + radius <= y < bottom - radius:
        return True
    center_x = left + radius if x < left + radius else right - radius - 1
    center_y = top + radius if y < top + radius else bottom - radius - 1
    return (x - center_x) ** 2 + (y - center_y) ** 2 <= radius**2


def draw_line(
    canvas: list[Color],
    size: int,
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    stroke: int,
    color: Color,
) -> None:
    dx = x2 - x1
    dy = y2 - y1
    steps = max(abs(dx), abs(dy), 1)
    radius = max(1, stroke // 2)
    for index in range(steps + 1):
        x = round(x1 + dx * index / steps)
        y = round(y1 + dy * index / steps)
        fill_rect(canvas, size, x - radius, y - radius, x + radius + 1, y + radius + 1, color)


def blend(source: Color, destination: Color) -> Color:
    source_alpha = source[3] / 255
    destination_alpha = destination[3] / 255
    output_alpha = source_alpha + destination_alpha * (1 - source_alpha)
    if output_alpha <= 0:
        return (0, 0, 0, 0)
    channels = []
    for index in range(3):
        value = (
            source[index] * source_alpha
            + destination[index] * destination_alpha * (1 - source_alpha)
        ) / output_alpha
        channels.append(round(value))
    return (channels[0], channels[1], channels[2], round(output_alpha * 255))


def mix(first: Color, second: Color, ratio: float) -> Color:
    return tuple(
        round(first[index] + (second[index] - first[index]) * ratio)
        for index in range(4)
    )


def downsample(
    canvas: list[Color],
    canvas_size: int,
    target_size: int,
    scale: int,
) -> tuple[int, int, list[Color]]:
    pixels: list[Color] = []
    for y in range(target_size):
        for x in range(target_size):
            totals = [0, 0, 0, 0]
            for sample_y in range(scale):
                for sample_x in range(scale):
                    source_x = x * scale + sample_x
                    source_y = y * scale + sample_y
                    pixel = canvas[source_y * canvas_size + source_x]
                    for channel in range(4):
                        totals[channel] += pixel[channel]
            samples = scale * scale
            pixels.append(tuple(round(value / samples) for value in totals))
    return target_size, target_size, pixels


def render_small_preview(
    images: dict[int, tuple[int, int, list[Color]]],
) -> tuple[int, int, list[Color]]:
    preview_size = 256
    canvas = [(245, 247, 242, 255)] * (preview_size * preview_size)
    placements = [
        (16, 18, 16, 88),
        (24, 88, 24, 72),
        (32, 164, 32, 56),
        (48, 28, 48, 172),
        (64, 132, 64, 150),
    ]
    for source_size, x, display_size, y in placements:
        source_image = images[source_size]
        scaled_image = scale_nearest(source_image, display_size)
        paste_image(canvas, preview_size, scaled_image, x, y)
    return preview_size, preview_size, canvas


def scale_nearest(
    image: tuple[int, int, list[Color]],
    target_size: int,
) -> tuple[int, int, list[Color]]:
    width, height, pixels = image
    scaled_pixels: list[Color] = []
    for y in range(target_size):
        source_y = min(height - 1, y * height // target_size)
        for x in range(target_size):
            source_x = min(width - 1, x * width // target_size)
            scaled_pixels.append(pixels[source_y * width + source_x])
    return target_size, target_size, scaled_pixels


def paste_image(
    canvas: list[Color],
    canvas_size: int,
    image: tuple[int, int, list[Color]],
    left: int,
    top: int,
) -> None:
    width, height, pixels = image
    for y in range(height):
        target_y = top + y
        if target_y < 0 or target_y >= canvas_size:
            continue
        for x in range(width):
            target_x = left + x
            if target_x < 0 or target_x >= canvas_size:
                continue
            canvas[target_y * canvas_size + target_x] = blend(
                pixels[y * width + x],
                canvas[target_y * canvas_size + target_x],
            )


def write_png(path: Path, image: tuple[int, int, list[Color]]) -> None:
    width, height, pixels = image
    raw_rows = bytearray()
    for y in range(height):
        raw_rows.append(0)
        for x in range(width):
            raw_rows.extend(pixels[y * width + x])

    def chunk(kind: bytes, payload: bytes) -> bytes:
        return (
            struct.pack(">I", len(payload))
            + kind
            + payload
            + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
        )

    png_bytes = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(bytes(raw_rows), 9))
        + chunk(b"IEND", b"")
    )
    path.write_bytes(png_bytes)


def write_ico(path: Path, images: dict[int, tuple[int, int, list[Color]]]) -> None:
    entries = []
    payloads = []
    offset = 6 + len(images) * 16
    for size in sorted(images):
        image = images[size]
        payload = build_ico_bitmap_payload(image)
        entries.append((size, len(payload), offset))
        payloads.append(payload)
        offset += len(payload)

    output = bytearray(struct.pack("<HHH", 0, 1, len(entries)))
    for size, payload_size, payload_offset in entries:
        dimension = 0 if size >= 256 else size
        output.extend(
            struct.pack(
                "<BBBBHHII",
                dimension,
                dimension,
                0,
                0,
                1,
                32,
                payload_size,
                payload_offset,
            )
        )
    for payload in payloads:
        output.extend(payload)
    path.write_bytes(bytes(output))


def build_ico_bitmap_payload(image: tuple[int, int, list[Color]]) -> bytes:
    width, height, pixels = image
    header = struct.pack(
        "<IIIHHIIIIII",
        40,
        width,
        height * 2,
        1,
        32,
        0,
        width * height * 4,
        0,
        0,
        0,
        0,
    )
    bitmap = bytearray()
    for y in reversed(range(height)):
        for x in range(width):
            red, green, blue, alpha = pixels[y * width + x]
            bitmap.extend((blue, green, red, alpha))

    mask_stride = ((width + 31) // 32) * 4
    mask = bytes(mask_stride * height)
    return header + bytes(bitmap) + mask


if __name__ == "__main__":
    raise SystemExit(main())
