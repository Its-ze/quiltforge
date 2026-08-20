from pathlib import Path
import shutil

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "quiltforge" / "resources" / "brand-art.png"
ICON = ROOT / "src" / "quiltforge" / "resources" / "quiltforge.ico"
SITE_ASSETS = ROOT / "site" / "assets"


def main() -> None:
    SITE_ASSETS.mkdir(parents=True, exist_ok=True)
    with Image.open(SOURCE) as source:
        image = source.convert("RGBA")
        image.save(ICON, format="ICO", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    shutil.copy2(SOURCE, SITE_ASSETS / "quiltforge-mark.png")
    preview = ROOT / "build" / "quiltforge-editor.png"
    if preview.exists():
        shutil.copy2(preview, SITE_ASSETS / "quiltforge-app.png")
    print(f"Created {ICON}")


if __name__ == "__main__":
    main()

