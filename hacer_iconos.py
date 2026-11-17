from pathlib import Path

from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "assets" / "juan_icon.png"
OUTPUT = ROOT / "docs"
BACKGROUND = (18, 61, 83, 255)


def resize_contained(image: Image.Image, size: int) -> Image.Image:
    return ImageOps.contain(image, (size, size), Image.Resampling.LANCZOS)


def main() -> None:
    if not SOURCE.is_file():
        raise FileNotFoundError(f"No se encontró el icono fuente: {SOURCE}")

    OUTPUT.mkdir(exist_ok=True)
    source = Image.open(SOURCE).convert("RGBA")

    for size in (192, 512):
        icon = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        resized = resize_contained(source, size)
        icon.alpha_composite(resized, ((size - resized.width) // 2, (size - resized.height) // 2))
        icon.save(OUTPUT / f"icon-{size}.png", optimize=True)

    maskable = Image.new("RGBA", (512, 512), BACKGROUND)
    resized_maskable = resize_contained(source, 512 - 2 * 64)
    maskable.alpha_composite(
        resized_maskable,
        ((512 - resized_maskable.width) // 2, (512 - resized_maskable.height) // 2),
    )
    maskable.save(OUTPUT / "icon-maskable-512.png", optimize=True)

    apple_icon = Image.new("RGBA", (180, 180), BACKGROUND)
    resized_apple = resize_contained(source, 180)
    apple_icon.alpha_composite(
        resized_apple,
        ((180 - resized_apple.width) // 2, (180 - resized_apple.height) // 2),
    )
    apple_icon.convert("RGB").save(OUTPUT / "apple-touch-icon.png", optimize=True)


if __name__ == "__main__":
    main()
