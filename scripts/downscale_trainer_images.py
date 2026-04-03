from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageOps


TRAINER_DIR = Path("gym_app/static/trainer")
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg"}
MAX_EDGE = 1200
JPEG_QUALITY = 82


def iter_image_paths() -> list[Path]:
    return sorted(
        path
        for path in TRAINER_DIR.glob("*/*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    )


def resize_image(path: Path) -> tuple[int, int, int, int, int, int] | None:
    before_size = path.stat().st_size

    with Image.open(path) as image:
        image = ImageOps.exif_transpose(image)
        before_width, before_height = image.size
        largest_edge = max(before_width, before_height)

        if largest_edge <= MAX_EDGE:
            return None

        scale = MAX_EDGE / largest_edge
        resized = image.resize(
            (round(before_width * scale), round(before_height * scale)),
            Image.Resampling.LANCZOS,
        )

        if resized.mode not in ("RGB", "L"):
            resized = resized.convert("RGB")

        resized.save(path, optimize=True, quality=JPEG_QUALITY, progressive=True)

    after_size = path.stat().st_size
    after_width, after_height = resized.size
    return before_width, before_height, before_size, after_width, after_height, after_size


def main() -> None:
    updated = 0
    for path in iter_image_paths():
        result = resize_image(path)
        if result is None:
            continue

        before_width, before_height, before_size, after_width, after_height, after_size = result
        updated += 1
        print(
            f"{path}: "
            f"{before_width}x{before_height} ({before_size // 1024} KB) -> "
            f"{after_width}x{after_height} ({after_size // 1024} KB)"
        )

    print(f"Updated {updated} trainer images.")


if __name__ == "__main__":
    main()
