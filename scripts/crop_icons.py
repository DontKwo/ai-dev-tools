"""Crop and export dual-brand repository logos (`assets/logo.png`) and icons (`assets/icon.png`, `.ico`)."""

from __future__ import annotations

import argparse
import shutil
import sys
from collections import deque
from pathlib import Path
from typing import Any

ANDROID_MIPMAP_SIZES: dict[str, int] = {
    "mipmap-mdpi": 48,
    "mipmap-hdpi": 72,
    "mipmap-xhdpi": 96,
    "mipmap-xxhdpi": 144,
    "mipmap-xxxhdpi": 192,
}

ICO_SIZES: list[tuple[int, int]] = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]

REPO_BRAND_SPECS: dict[str, dict[str, Any]] = {
    "ai-dev-tools": {
        "logo": "AI_Dev_Tools.png",
        "mode": "crop_box",
        "box": (16, 18, 253, 249),
        "bg": (28, 37, 46, 255),
    },
    "AutoSpanish": {
        "logo": "AutoSpanish Flashcard Logo.png",
        "icon_source": "Spanish Flashcard Spark Icon.png",
        "mode": "flood_dark_corners",
        "android_res": "app/src/main/res",
    },
    "formulaflash": {
        "logo": "formula-flash-logo.png",
        "icon_source": "formula-flash-icon-1024.png",
        "mode": "square_direct",
        "public_dir": "apps/app/public",
        "android_res": "apps/app/android/app/src/main/res",
    },
    "OpenRecipeBook": {
        "repo_logo": "logo.png",
        "mode": "crop_tile",
        "box": (182, 113, 844, 658),
        "tile_size": 700,
        "bg": (251, 246, 227, 255),
        "radius_ratio": 0.18,
        "public_dir": "public",
        "android_res": "android/app/src/main/res",
    },
    "RocketCFD": {
        "logo": "RocketCFD.png",
        "mode": "crop_box",
        "box": (19, 21, 253, 252),
        "bg": (28, 37, 46, 255),
    },
    "RocketSizer": {
        "logo": "RocketSizer.png",
        "mode": "crop_box",
        "box": (16, 19, 251, 251),
        "bg": (28, 37, 46, 255),
        "extra_icon_dirs": ["src-tauri/assets"],
    },
    "sane-windows": {
        "logo": "Sane_Windows.png",
        "mode": "crop_box",
        "box": (17, 21, 247, 252),
        "bg": (28, 37, 46, 255),
    },
    "time-is-money-sim": {
        "logo": "Time Is Money Sim Logo.png",
        "mode": "crop_tile",
        "box": (389, 196, 947, 675),
        "tile_size": 640,
        "bg": (5, 14, 26, 255),
        "radius_ratio": 0.18,
    },
}


def _import_pillow() -> tuple[Any, Any]:
    from PIL import Image, ImageDraw  # noqa: 13

    return Image, ImageDraw


def _apply_rounded_mask(image_rgba: Any, radius_ratio: float = 0.18) -> Any:
    image_cls, draw_cls = _import_pillow()
    side = image_rgba.size[0]
    mask = image_cls.new("L", (side, side), 0)
    radius_px = int(side * radius_ratio)
    draw_ctx = draw_cls.Draw(mask)
    draw_ctx.rounded_rectangle([(0, 0), (side - 1, side - 1)], radius=radius_px, fill=255)
    alpha = image_rgba.getchannel("A")
    combined_mask = mask.point(lambda val: val)
    for row_idx in range(side):
        for col_idx in range(side):
            alpha_val = alpha.getpixel((col_idx, row_idx))
            mask_val = combined_mask.getpixel((col_idx, row_idx))
            if alpha_val < mask_val:
                combined_mask.putpixel((col_idx, row_idx), alpha_val)
    out = image_rgba.copy()
    out.putalpha(combined_mask)
    return out


def _fit_on_square_tile(cropped_rgba: Any, tile_size: int, bg_rgba: tuple[int, int, int, int], radius_ratio: float) -> Any:
    image_cls, _ = _import_pillow()
    max_inner = int(tile_size * 0.84)
    scale = min(max_inner / max(cropped_rgba.width, 1), max_inner / max(cropped_rgba.height, 1))
    resized_w = max(1, int(round(cropped_rgba.width * scale)))
    resized_h = max(1, int(round(cropped_rgba.height * scale)))
    resized = cropped_rgba.resize((resized_w, resized_h), image_cls.Resampling.LANCZOS)
    canvas = image_cls.new("RGBA", (tile_size, tile_size), bg_rgba)
    offset_x = (tile_size - resized_w) // 2
    offset_y = (tile_size - resized_h) // 2
    canvas.paste(resized, (offset_x, offset_y), resized)
    return _apply_rounded_mask(canvas, radius_ratio=radius_ratio)


def _strip_outer_dark_corners(image_rgba: Any, threshold: int = 24) -> Any:
    width_px, height_px = image_rgba.size
    pixels = image_rgba.load()
    visited = bytearray(width_px * height_px)
    queue: deque[tuple[int, int]] = deque()
    for start_x, start_y in [(0, 0), (width_px - 1, 0), (0, height_px - 1), (width_px - 1, height_px - 1)]:
        queue.append((start_x, start_y))
        visited[start_y * width_px + start_x] = 1

    while queue:
        cur_x, cur_y = queue.popleft()
        red_ch, green_ch, blue_ch, _ = pixels[cur_x, cur_y]
        if red_ch <= threshold and green_ch <= threshold and blue_ch <= threshold:
            pixels[cur_x, cur_y] = (red_ch, green_ch, blue_ch, 0)
            for step_x, step_y in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                next_x = cur_x + step_x
                next_y = cur_y + step_y
                if 0 <= next_x < width_px and 0 <= next_y < height_px:
                    flat_idx = next_y * width_px + next_x
                    if not visited[flat_idx]:
                        visited[flat_idx] = 1
                        queue.append((next_x, next_y))
    return image_rgba


def _remove_light_margin_from_tile(cropped_rgba: Any) -> Any:
    width_px, height_px = cropped_rgba.size
    pixels = cropped_rgba.load()
    visited = bytearray(width_px * height_px)
    queue: deque[tuple[int, int]] = deque()
    for edge_x in range(width_px):
        queue.append((edge_x, 0))
        queue.append((edge_x, height_px - 1))
        visited[edge_x] = 1
        visited[(height_px - 1) * width_px + edge_x] = 1
    for edge_y in range(1, height_px - 1):
        queue.append((0, edge_y))
        queue.append((width_px - 1, edge_y))
        visited[edge_y * width_px] = 1
        visited[edge_y * width_px + (width_px - 1)] = 1

    while queue:
        cur_x, cur_y = queue.popleft()
        red_ch, green_ch, blue_ch, _ = pixels[cur_x, cur_y]
        if red_ch >= 225 and green_ch >= 225 and blue_ch >= 225:
            pixels[cur_x, cur_y] = (red_ch, green_ch, blue_ch, 0)
            for step_x, step_y in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                next_x = cur_x + step_x
                next_y = cur_y + step_y
                if 0 <= next_x < width_px and 0 <= next_y < height_px:
                    flat_idx = next_y * width_px + next_x
                    if not visited[flat_idx]:
                        visited[flat_idx] = 1
                        queue.append((next_x, next_y))
    return cropped_rgba


def build_square_icon(spec: dict[str, Any], logos_dir: Path, repo_dir: Path) -> Any:
    """Create a 512x512 RGBA square emblem icon from the configured source image."""
    image_cls, _ = _import_pillow()
    if "icon_source" in spec:
        source_path = logos_dir / str(spec["icon_source"])
    elif "logo" in spec:
        source_path = logos_dir / str(spec["logo"])
    else:
        source_path = repo_dir / str(spec["repo_logo"])

    src_image = image_cls.open(source_path).convert("RGBA")
    mode = str(spec["mode"])

    if mode == "square_direct":
        icon_512 = src_image.resize((512, 512), image_cls.Resampling.LANCZOS)
        return icon_512

    if mode == "flood_dark_corners":
        cleaned = _strip_outer_dark_corners(src_image)
        return cleaned.resize((512, 512), image_cls.Resampling.LANCZOS)

    if mode == "crop_box":
        crop_box = tuple(int(coord_px) for coord_px in spec["box"])
        cropped = src_image.crop(crop_box)
        square = cropped.resize((512, 512), image_cls.Resampling.LANCZOS)
        return _apply_rounded_mask(square, radius_ratio=0.18)

    crop_box = tuple(int(coord_px) for coord_px in spec["box"])
    cropped = src_image.crop(crop_box)
    bg_rgba = tuple(int(channel_val) for channel_val in spec["bg"])
    tile_size = int(spec["tile_size"])
    radius_ratio = float(spec.get("radius_ratio", 0.18))
    tiled = _fit_on_square_tile(cropped, tile_size, (bg_rgba[0], bg_rgba[1], bg_rgba[2], bg_rgba[3]), radius_ratio)
    return tiled.resize((512, 512), image_cls.Resampling.LANCZOS)


def apply_repo_branding(repo_name: str, repo_dir: Path, logos_dir: Path) -> list[Path]:
    """Copy full wordmark banner and generate cropped text-free icons for one repository."""
    if repo_name not in REPO_BRAND_SPECS:
        return []
    image_cls, _ = _import_pillow()
    spec = REPO_BRAND_SPECS[repo_name]
    assets_dir = repo_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    written_files: list[Path] = []

    if "logo" in spec:
        src_logo = logos_dir / str(spec["logo"])
    else:
        src_logo = repo_dir / str(spec["repo_logo"])
    dest_logo = assets_dir / "logo.png"
    if src_logo.is_file() and src_logo.resolve() != dest_logo.resolve():
        shutil.copy2(src_logo, dest_logo)
        written_files.append(dest_logo)

    icon_512 = build_square_icon(spec, logos_dir, repo_dir)
    icon_png = assets_dir / "icon.png"
    icon_ico = assets_dir / "icon.ico"
    icon_512.save(icon_png, format="PNG")
    icon_512.save(icon_ico, format="ICO", sizes=ICO_SIZES)
    written_files.extend([icon_png, icon_ico])

    for extra_rel in spec.get("extra_icon_dirs", []):
        extra_dir = repo_dir / str(extra_rel)
        if extra_dir.is_dir():
            extra_png = extra_dir / "icon.png"
            extra_ico = extra_dir / "icon.ico"
            icon_512.save(extra_png, format="PNG")
            icon_512.save(extra_ico, format="ICO", sizes=ICO_SIZES)
            written_files.extend([extra_png, extra_ico])

    if "public_dir" in spec:
        pub_dir = repo_dir / str(spec["public_dir"])
        if pub_dir.is_dir():
            for size_px, filename in [(192, "icon-192.png"), (512, "icon-512.png"), (32, "icon-32.png"), (16, "icon-16.png")]:
                out_file = pub_dir / filename
                icon_512.resize((size_px, size_px), image_cls.Resampling.LANCZOS).save(out_file, format="PNG")
                written_files.append(out_file)
            fav_ico = pub_dir / "favicon.ico"
            if fav_ico.exists():
                icon_512.save(fav_ico, format="ICO", sizes=[(16, 16), (32, 32), (48, 48)])
                written_files.append(fav_ico)
            fav_png = pub_dir / "favicon.png"
            icon_512.resize((64, 64), image_cls.Resampling.LANCZOS).save(fav_png, format="PNG")
            written_files.append(fav_png)

    if "android_res" in spec:
        res_dir = repo_dir / str(spec["android_res"])
        if res_dir.is_dir():
            fg_dir = res_dir / "drawable"
            fg_dir.mkdir(parents=True, exist_ok=True)
            fg_path = fg_dir / "ic_launcher_foreground.png"
            icon_512.resize((432, 432), image_cls.Resampling.LANCZOS).save(fg_path, format="PNG")
            written_files.append(fg_path)
            for mipmap_name, size_px in ANDROID_MIPMAP_SIZES.items():
                mip_dir = res_dir / mipmap_name
                mip_dir.mkdir(parents=True, exist_ok=True)
                resized = icon_512.resize((size_px, size_px), image_cls.Resampling.LANCZOS)
                for target_name in ("ic_launcher.png", "ic_launcher_round.png"):
                    out_mip = mip_dir / target_name
                    resized.save(out_mip, format="PNG")
                    written_files.append(out_mip)

    return written_files


def main() -> int:
    parser = argparse.ArgumentParser(description="Crop and install dual-brand logos and icons for repositories.")
    parser.add_argument("--projects-dir", type=Path, default=Path(__file__).resolve().parent.parent.parent)
    parser.add_argument("--logos-dir", type=Path, default=Path(__file__).resolve().parent.parent.parent.parent / "Downloads" / "logos")
    parser.add_argument("--repo", action="append", default=[], help="Target repository folder name (repeatable)")
    parser.add_argument("--all", action="store_true", help="Process all configured repositories found under projects-dir")
    args = parser.parse_args()

    targets = list(REPO_BRAND_SPECS.keys()) if args.all else args.repo
    if not targets:
        parser.print_help()
        return 1

    for repo_name in targets:
        repo_path = args.projects_dir / repo_name
        if not repo_path.is_dir():
            print(f"[SKIP] Missing directory: {repo_path}")  # noqa: 25
            continue
        outputs = apply_repo_branding(repo_name, repo_path, args.logos_dir)
        print(f"[OK] {repo_name}: generated {len(outputs)} asset file(s)")  # noqa: 25
    return 0


if __name__ == "__main__":
    sys.exit(main())
