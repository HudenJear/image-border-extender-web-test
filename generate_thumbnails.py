import os
from PIL import Image

from wxcloudrun.add_bd import apply_filter, AVAILABLE_FILTER_KEYS as FILTER_KEYS
from wxcloudrun.add_bd import process_one_image, AVAILABLE_FORMAT_KEYS as FORMAT_KEYS


def ensure_dir(path: str):
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


def make_width_thumbnail(img: Image.Image, width: int) -> Image.Image:
  
    if img.width == 0 or img.height == 0:
        return img
    if img.width< img.height:
        scale = width / float(img.width)
        new_w = max(1, int(round(img.width * scale)))
        new_h = max(1, int(round(img.height * scale)))
    else:
        scale = width / float(img.height)
        new_w = max(1, int(round(img.width * scale)))
        new_h = max(1, int(round(img.height * scale)))
    return img.resize((new_w, new_h), Image.LANCZOS)


def main():
    image_path = os.path.join('.', 'P_1016535.JPG')
    out_dir = os.path.join('.', 'img_thumbnail')
    ensure_dir(out_dir)

    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Input image not found: {image_path}")

    # Deterministic order for output files
    filter_keys = sorted(FILTER_KEYS)

    for key in filter_keys:
        try:
            with Image.open(image_path) as img:
                img = img.convert('RGB')
                # strength default = 0.5 (baseline)
                thumb = make_width_thumbnail(img,200)
                processed = apply_filter(thumb, key, strength=0.5)
                out_path = os.path.join(out_dir, f"filter_{key}.jpg")
                processed.save(out_path, format='JPEG', quality=92)
                print(f"Saved: {out_path}")
        except Exception as e:
            print(f"Failed on filter '{key}': {e}")

    # Generate thumbnails for all formats as <format>_format.jpg
    def pick_logo() -> str:
        # Try a few known logos; return first that exists, else ''
        candidates = [
            os.path.join('logos', 'hassel.jpg'),
            os.path.join('logos', 'fujifilm.jpg'),
            os.path.join('logos', 'Olympus.jpg'),
        ]
        for p in candidates:
            if os.path.exists(p):
                return p
        return ''

    logo_path = pick_logo()
    text_default = 'Camera Type\n\nLens information '

    for fmt in sorted(FORMAT_KEYS):
        try:
            with Image.open(image_path) as img:
                img = img.convert('RGB')
                processed = process_one_image(
                    img_input=img,
                    text=text_default,
                    logo_file=logo_path,
                    format=fmt,
                    suppli_info='Supplimentary information',
                    max_length=2000,
                    add_black_border=True,
                    square=False,
                )
                thumb = make_width_thumbnail(processed, 600)
                out_path = os.path.join(out_dir, f"format_{fmt}.jpg")
                thumb.save(out_path, format='JPEG', quality=92)
                print(f"Saved: {out_path}")
        except Exception as e:
            print(f"Failed on format '{fmt}': {e}")


if __name__ == '__main__':
    main()
