import os
from PIL import Image

from wxcloudrun.add_bd import apply_filter, AVAILABLE_FILTER_KEYS as FILTER_KEYS
from wxcloudrun.add_bd import process_one_image, AVAILABLE_FORMAT_KEYS as FORMAT_KEYS
from wxcloudrun.effects.filter_utils import apply_pylut


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


def generate_logo_thumbnails(logos_dir='logos', out_dir='img_thumbnail'):
    """Generate thumbnails for all images in logos directory.
    Max dimension: 100px, saved to logos/logos-thumbnails
    """
    thumbnails_dir = os.path.join(out_dir, logos_dir+'-thumbnails')
    ensure_dir(thumbnails_dir)
    
    if not os.path.exists(logos_dir):
        print(f"Logos directory not found: {logos_dir}")
        return
    
    # Supported image extensions
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp'}
    
    for filename in os.listdir(logos_dir):
        file_path = os.path.join(logos_dir, filename)
        
        # Skip if not a file or not an image
        if not os.path.isfile(file_path):
            continue
        
        _, ext = os.path.splitext(filename)
        if ext.lower() not in image_extensions:
            continue
        
        try:
            with Image.open(file_path) as img:
                # Convert to RGB to handle various formats
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Generate thumbnail with max dimension of 100px
                thumbnail = make_width_thumbnail(img, 100)
                
                # Save thumbnail with same base name
                thumb_filename = os.path.splitext(filename)[0] + '.jpg'
                thumb_path = os.path.join(thumbnails_dir, thumb_filename)
                thumbnail.save(thumb_path, format='JPEG', quality=92)
                print(f"Generated thumbnail: {thumb_path}")
        except Exception as e:
            print(f"Failed to process {filename}: {e}")


def main():
    # Generate logo thumbnails first
    out_dir = './wxcloudrun/static/img_thumbnail'

    print("\n=== Generating logo thumbnails ===")
    generate_logo_thumbnails('logos', out_dir)
    generate_logo_thumbnails("films", out_dir)
    
    print("\n=== Generating filter and format thumbnails ===")
    image_path = os.path.join('.', 'P_1016535.jpg')
    ensure_dir(out_dir)

    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Input image not found: {image_path}")

    filters_thumb_dir = os.path.join(out_dir, 'filters-thumbnail')
    ensure_dir(filters_thumb_dir)

    pylut_filters_thumb_dir = os.path.join(out_dir, 'pylutfilters-thumbnail')
    ensure_dir(pylut_filters_thumb_dir)

    # Deterministic order for output files
    filter_keys = sorted(FILTER_KEYS)

    for key in filter_keys:
        try:
            with Image.open(image_path) as img:
                img = img.convert('RGB')
                # strength default = 0.5 (baseline)
                thumb = make_width_thumbnail(img, 200)
                processed = apply_filter(thumb, key, strength=0.5)
                out_path = os.path.join(filters_thumb_dir, f"filter_{key}.jpg")
                processed.save(out_path, format='JPEG', quality=92)
                print(f"Saved: {out_path}")

                # if key.startswith('lut') and len(key) == 5 and key[3:].isdigit():
                #     cube_name = f"Titanium_Cinematic_{key[3:]}.cube"
                #     processed2 = apply_pylut(thumb, 0.5, f"cubes/{cube_name}")
                #     out_path2 = os.path.join(pylut_filters_thumb_dir, f"filter_{key}.jpg")
                #     processed2.save(out_path2, format='JPEG', quality=92)
                #     print(f"Saved: {out_path2}")
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

    img_list=['P_1016535.JPG','P1032386.jpg','P_0162552.jpg','P_0162490.jpg',]

    logo_path = pick_logo()
    text_default = 'Camera Type: Panasonic DC-S5MII\n\nLens information: Leica Summilux 50mm f/1.4'
    film_path = os.path.join('films', 'Fujifilm_RDP_III_120.jpg')

    for idx, fmt in enumerate(sorted(FORMAT_KEYS)):
        try:
            current_image_path = os.path.join('.', img_list[idx % len(img_list)])
            with Image.open(current_image_path) as img:
                img = img.convert('RGB')
                processed = process_one_image(
                    img_input=img,
                    text=text_default,
                    logo_file=logo_path,
                    format=fmt,
                    suppli_info='Supplimentary information: you can type your film here',
                    max_length=2400,
                    add_black_border=True,
                    square=False,
                    film_file=film_path,
                )
                thumb = make_width_thumbnail(processed, 600)
                out_path = os.path.join(out_dir, f"format_{fmt}.jpg")
                thumb.save(out_path, format='JPEG', quality=92)
                print(f"Saved: {out_path}")
        except Exception as e:
            print(f"Failed on format '{fmt}': {e}")


if __name__ == '__main__':
    main()
