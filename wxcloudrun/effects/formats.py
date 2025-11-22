from typing import Dict, Callable
from PIL import Image, ImageDraw, ImageFont, ImageOps
import numpy as np
import piexif
import os
from PIL.ExifTags import TAGS

# Import shared sizing, style and utils from core module to avoid duplication
from wxcloudrun import add_bd as core
from wxcloudrun.color_extract import extract_main_colors

__all__ = [
    'process_one_image',
    'FORMAT_HANDLERS',
    'AVAILABLE_FORMAT_KEYS',
]

film_logs={
  
  'FujiFilm C200 135':  'films/FujiC200-new-135.jpg',
  'FujiFilm C400 135':  'films/FujiC400-new-135.jpg',
  'FujiFilm Pro Provia 100f 120':  'films/Fujifilm_RDP_III_120.jpg',
  'FujiFilm Pro Provia 100f 135':  'films/Fujifilm_RDP_III_135.jpg',
  'FujiFilm Pro Velvia 100 120':  'films/Velvia100-120.jpg',
  'FujiFilm Pro Velvia 100 135':  'films/Velvia100-135.jpg',
  'FujiFilm Pro Velvia 50 120':  'films/Velvia_50-120.jpg',
  'FujiFilm Pro Velvia 50 135':  'films/Velvia_50-135.jpg',
  'FujiFilm Acros 100 II 135':  'films/Acros100ii-135_.jpg',

  'Kodak Ektachrome 100 Daylight 120':  'films/kodak-film-ektachrome-100-120.webp',
  'Kodak Ektachrome 100 Daylight 135':  'films/kodak-film-ektachrome-100-135.jpg',

  'Kodak Gold 200 Daylight 120':  'films/kodak-gold-200-120.jpg',
  'Kodak Gold 200 Daylight 135':  'films/kodak-gold200-135.webp',
  'Kodak ColorPlus 200 135':       'films/kodak-cp200-135.jpg',
  'Kodak Ultramax 400 135':        'films/kodak-ultramax400-135.jpg',

  'Kodak T-Max 400 135':  'films/kodak-tmax-400-135.jpg',
  'Kodak T-Max 400 120':  'films/kodak-tmax400-120.jpg',
  'Kodak Tri-X 400 135':  'films/kodak-tri-x-400-135.jpg',

  
  'Kodak Ektachrome 100D 7294':       'films/Ektachrome-100D-7294-190529-HR-1.jpg',
  'Kodak Vision3 50D 5203':           'films/VISION3-50D-Cans_round_022018_white-5.jpg',
  'Kodak Vision3 200T 5213':          'films/VISION-200T-filmcans_022018_white-4.jpg',
  'Kodak Vision3 250D 5207':          'films/VISION3-250D_5207_LARGE-filmcans_-35mm-1000ft-COLORS-3300x3300-1.jpg',
  'Kodak Vision3 500T 5219':     'films/VISION3_5219_7219_filmcans_022018_white-2.jpg',
  'Kodak Eastman Double-X 5222': 'films/EASTMAN-DOUBLE-X-5222-7222_180801-3-1.jpg',

  'Lucky Color 200 120':  'films/lucky C200 120.jpg',
  'Lucky Color 200 135':  'films/lucky C200 135.jpg',
  'Lucky SHD 100 120':    'films/lucky SHD100 120.jpg',
  'Lucky SHD 100 135':    'films/lucky SHD100 135.jpg',
  'Lucky SHD 400 120':    'films/lucky SHD400 1230.jpg',
  'Lucky SHD 400 135':    'films/lucky SHD400 135.jpg',

}


def _format_basic1(img: Image.Image, text: str, logo_file: str, suppli_info: str = '', *, square: bool = False, film_name: str = '', **kwargs) -> Image.Image:
    suppli_line = suppli_info
    # 自动读取 EXIF 信息
    if text == '':
        exif_data = img.getexif()
        camera_mk = None
        camera_m = None
        if exif_data:
            for tag, value in exif_data.items():
                tag_name = TAGS.get(tag, tag)
                if tag_name == "Make":
                    camera_mk = value
                elif tag_name == 'Model':
                    camera_m = value

        if camera_mk and camera_m:
            text = camera_mk + ' ' + camera_m + '\n\n'
            logo_file = core.logo_dict[camera_mk]
            try:
                exif_dict = piexif.load(img.info['exif'])
                focal_length = exif_dict['Exif'][piexif.ExifIFD.FocalLength]
                F_value = exif_dict['Exif'][piexif.ExifIFD.FNumber]
                ISO_value = exif_dict['Exif'][piexif.ExifIFD.ISOSpeedRatings]
                ss_value = exif_dict['Exif'][piexif.ExifIFD.ExposureTime]
                ss_value = int(ss_value[1]) / int(ss_value[0])
                ss_text = 'S: ' + '1' + "/" + str(int(ss_value)) + 's' if ss_value > 1 else 'S: ' + str(int(1 / ss_value)) + 's'
                text = text + exif_dict['Exif'][piexif.ExifIFD.LensModel].decode('utf-8')
                suppli_line = 'Focal: ' + str(int(focal_length[0] / focal_length[1])) + 'mm    ' + 'A: F' + str(F_value[0] / F_value[1]) + '    ' + 'ISO: ' + str(ISO_value) + '    ' + ss_text
            except Exception:
                print(f"Exif detected broken for one image in the auto detect dictionary")
        else:
            print(f"No exif detected for one image in the auto detect dictionary")
            return img

    # 计算要将原始图片粘贴到白色背景图上的位置, rotate or not
    rota = True if img.width < img.height * 0.95 else False
    if rota:
        img = core.rotate_image_90_no_crop(img, reverse=True)

    wh, ht = img.width, img.height
    new_width = core.tgt_size
    new_height = int(ht * new_width / wh)
    img = img.resize((new_width, new_height))

    # calculate bg size
    background = Image.new('RGB', (core.tgt_size + 2 * core.border_size + 2 * core.exterior, new_height + 2 * core.border_size + 3 * core.exterior + core.infor_area), (255, 255, 255))
    # add border 1
    img = ImageOps.expand(img, border=core.border_size, fill=core.border_color)

    # 将原始图片粘贴到白色背景图上
    background.paste(img, (core.exterior, core.exterior))

    # add logo
    if film_name!='':
      # 获取film logo路径
      film_logo_path = film_logs.get(film_name, '')
      if film_logo_path and os.path.exists(film_logo_path):
        # 打开两个logo
        film_logo_img = Image.open(film_logo_path).convert('RGB')
        camera_logo_img = Image.open(logo_file).convert('RGB')
        
        # 统一高度，以原有logo的高度标准
        logo_height = core.infor_area * 0.8
        
        # 调整两个logo尺寸
        camera_logo_width = int(camera_logo_img.width * logo_height / camera_logo_img.height)
        camera_logo_img = camera_logo_img.resize((camera_logo_width, int(logo_height)))
        
        film_logo_width = int(film_logo_img.width * logo_height / film_logo_img.height)
        film_logo_img = film_logo_img.resize((film_logo_width, int(logo_height)))
        
        # 计算位置：原有logo在右边的位置
        camera_logo_x = int(core.tgt_size + 2 * core.border_size + core.exterior - camera_logo_width)
        logo_y = int(new_height + 2 * core.border_size + 2 * core.exterior)
        
        # film logo在左边，间距为core.exterior
        film_logo_x = camera_logo_x - core.exterior - film_logo_width
        
        # 粘贴两个logo
        background.paste(film_logo_img, (film_logo_x, logo_y))
        background.paste(camera_logo_img, (camera_logo_x, logo_y))
        
        draw = ImageDraw.Draw(background)
      else:
        # 如果film logo不存在，退回到只显示原有logo
        logo_img = Image.open(logo_file).convert('RGB')
        logo_height = core.infor_area * 0.8
        logo_img = logo_img.resize((int(logo_img.width * logo_height / logo_img.height), int(logo_height)))
        background.paste(logo_img, (int(core.tgt_size + 2 * core.border_size + core.exterior - logo_img.width * logo_height / logo_img.height), int(new_height + 2 * core.border_size + 2 * core.exterior)))
        draw = ImageDraw.Draw(background)
    else:
      # logo_file=logo_file
      logo_img = Image.open(logo_file).convert('RGB')
      logo_height = core.infor_area * 0.8
      logo_img = logo_img.resize((int(logo_img.width * logo_height / logo_img.height), int(logo_height)))
      background.paste(logo_img, (int(core.tgt_size + 2 * core.border_size + core.exterior - logo_img.width * logo_height / logo_img.height), int(new_height + 2 * core.border_size + 2 * core.exterior)))
      draw = ImageDraw.Draw(background)

    # add text 1 the camera
    font = ImageFont.truetype(core.using_font, core.font_size)
    posi = (int(core.exterior * 1.01), 2 * core.exterior + new_height + 2 * core.border_size)
    text_1 = text.split('\n\n')[0].strip('\0')
    draw.text(posi, text_1, fill=(0, 0, 0), font=font)
    bold_offset = 1
    for offset in [(0, 0), (bold_offset, 0), (0, bold_offset), (bold_offset, bold_offset)]:
        draw.text((posi[0] + offset[0], posi[1] + offset[1]), text_1, font=font, fill=(0, 0, 0))

    # add text 2 the lens
    font = ImageFont.truetype(core.using_font, int(core.font_size * 0.9))
    posi = (int(core.exterior * 1.01), 2 * core.exterior + new_height + 2 * core.border_size + 1.6 * core.font_size)
    text_2 = text.split('\n\n')[1].strip('\0')
    draw.text(posi, text_2, fill=(0, 0, 0), font=font)

    # add main_color
    main_c = extract_main_colors(img, num_colors=4)
    color_image = np.zeros((int(0.8 * core.font_size), int(15 * core.font_size), 3), dtype=int)
    block_width = color_image.shape[1] // len(main_c) + 1
    for i, color in enumerate(main_c):
        color_image[:, i * block_width:(i + 1) * block_width] = color
    color_pad = Image.fromarray(color_image.astype('uint8'))
    posi_mc = (int(core.exterior * 1.01), int(2 * core.exterior + new_height + 2 * core.border_size + 3.0 * core.font_size))
    background.paste(color_pad, posi_mc)

    # add supplementary_line in the last line
    if suppli_line:
        font = ImageFont.truetype(core.using_font, int(core.font_size * 0.8))
        posi = (int(core.exterior * 1.01), 2 * core.exterior + new_height + 2 * core.border_size + 4.2 * core.font_size)
        draw.text(posi, suppli_line.strip('\0'), fill=(80, 80, 80), font=font)

    # rotate back and save
    if rota:
        background = core.rotate_image_90_no_crop(background, reverse=False)

    if square:
        w, h = background.size
        square_size = max(w, h)
        square_bg = Image.new('RGB', (square_size, square_size), (255, 255, 255))
        paste_x = (square_size - w) // 2
        paste_y = (square_size - h) // 2
        square_bg.paste(background, (paste_x, paste_y))
        background = square_bg

    return background

def _format_basic2(img, text, logo_file, suppli_info='', *, square=False, film_name:str = '', **kwargs):
    """
    Format with all elements centered vertically:
    - Logo (top)
    - Image (center)
    - Main colors
    - Text (camera + lens)
    - Supplementary info (bottom)
    """
    suppli_line = suppli_info
    text_1, text_2 = (text.split('\n\n') + ['', ''])[:2]  # Ensure we have at least 2 elements
    text_1 = text_1.strip('\0')
    text_2 = text_2.strip('\0')
    
    # Handle image rotation
    # rota = img.width < img.height * 0.95
    # if rota:
    #     img = core.rotate_image_90_no_crop(img, reverse=True)
    
    # Resize image
    wh, ht = img.width, img.height
    new_width = core.tgt_size
    new_height = int(ht * new_width / wh)
    img = img.resize((new_width, new_height))
    
    # Calculate total height needed
    logo_height = core.infor_area * 0.6
    color_swatch_h = int(0.8 * core.font_size)
    text1_h = core.font_size
    text2_h = int(core.font_size * 0.9)
    suppli_h = int(core.font_size * 0.8) if suppli_line else 0
    
    # Calculate spacing
    spacing = core.exterior // 2
    max_text_h = max(text1_h, text2_h)
    total_h = (logo_height + spacing * 3 + (new_height + 2 * core.border_size) + spacing * 2 + 
              color_swatch_h + spacing * 2 + 
              max_text_h + spacing * 2 + 
              suppli_h)
    # Create background
    bg_width = core.tgt_size + 2 * core.border_size + 2 * core.exterior
    background = Image.new('RGB', (bg_width, int(total_h + 2 * core.exterior)), (255, 255, 255))
    draw = ImageDraw.Draw(background)
    
    # Add logo (centered)
    if film_name != '' and film_logs.get(film_name, '') and os.path.exists(film_logs.get(film_name, '')):
        # 双logo模式：film logo + camera logo
        film_logo_path = film_logs.get(film_name, '')
        film_logo_img = Image.open(film_logo_path).convert('RGB')
        camera_logo_img = Image.open(logo_file).convert('RGB')
        
        # 调整两个logo尺寸到相同高度
        camera_logo_width = int(camera_logo_img.width * logo_height / camera_logo_img.height)
        camera_logo_img = camera_logo_img.resize((camera_logo_width, int(logo_height)))
        
        film_logo_width = int(film_logo_img.width * logo_height / film_logo_img.height)
        film_logo_img = film_logo_img.resize((film_logo_width, int(logo_height)))
        
        # 计算两个logo的总宽度（包括间距）
        total_logos_width = film_logo_width + core.exterior + camera_logo_width
        
        # 计算起始位置使两个logo整体居中
        start_x = (bg_width - total_logos_width) // 2
        
        # 粘贴film logo（左）和camera logo（右）
        background.paste(film_logo_img, (start_x, core.exterior))
        background.paste(camera_logo_img, (start_x + film_logo_width + core.exterior, core.exterior))
    elif os.path.exists(logo_file):
        # 单logo模式
        logo_img = Image.open(logo_file).convert('RGB')
        logo_img = logo_img.resize((int(logo_img.width * logo_height / logo_img.height), int(logo_height)))
        logo_x = (bg_width - logo_img.width) // 2
        background.paste(logo_img, (logo_x, core.exterior))
    
    # Add image with border
    img_with_border = ImageOps.expand(img, border=core.border_size, fill=core.border_color)
    img_x = (bg_width - img_with_border.width) // 2
    img_y = int(core.exterior + logo_height + spacing * 2)
    background.paste(img_with_border, (img_x, img_y))
    
    # Add main colors
    main_c = extract_main_colors(img, num_colors=4)
    color_swatch_w = int(15 * core.font_size)
    color_image = np.zeros((color_swatch_h, color_swatch_w, 3), dtype=int)
    block_width = color_swatch_w // len(main_c) + 1
    for i, color in enumerate(main_c):
        color_image[:, i * block_width:(i + 1) * block_width] = color
    color_pad = Image.fromarray(color_image.astype('uint8'))
    color_x = (bg_width - color_swatch_w) // 2
    color_y = img_y + img_with_border.height + spacing * 2
    background.paste(color_pad, (color_x, color_y))
    
    # Add text (camera + lens)
    font = ImageFont.truetype(core.using_font, core.font_size)
    text_y = color_y + color_swatch_h + spacing * 2
    
    # Text 1 (camera)
    font_small = ImageFont.truetype(core.using_font, int(core.font_size * 0.9))
    w1 = draw.textlength(text_1, font=font)
    w2 = draw.textlength(text_2, font=font_small)
    gap = int(0.5 * core.font_size)
    combined_w = int(w1 + gap + w2)
    x_start = (bg_width - combined_w) // 2
    draw.text((x_start, text_y), text_1, fill=(0, 0, 0), font=font)
    
    # Text 2 (lens)
    draw.text((x_start + int(w1 + gap), text_y), text_2, fill=(0, 0, 0), font=font_small)
    
    # Add supplementary info
    if suppli_line:
        font_suppli = ImageFont.truetype(core.using_font, int(core.font_size * 0.8))
        suppli_x = (bg_width - draw.textlength(suppli_line, font=font_suppli)) // 2
        suppli_y = text_y + max_text_h + spacing
        draw.text((suppli_x, suppli_y), suppli_line, fill=(80, 80, 80), font=font_suppli)
    
    # Handle square output if needed
    if square:
        w, h = background.size
        square_size = max(w, h)
        square_bg = Image.new('RGB', (square_size, square_size), (255, 255, 255))
        paste_x = (square_size - w) // 2
        paste_y = (square_size - h) // 2
        square_bg.paste(background, (paste_x, paste_y))
        background = square_bg

    return background



def _format_basic3(img: Image.Image, text: str, logo_file: str, suppli_info: str = '', *, square: bool = False, film_name:str = '', **kwargs) -> Image.Image:
    """
    Layout:
    +----------------+ +------------+
    | LOGO           | |            |
    |                | |            |
    +----------------+ |            |
    |                | |            |
    | MAIN COLOR     | |   IMAGE    |
    |                | |            |
    +----------------+ |            |
    | TEXT1          | |            |
    | TEXT2          | |            |
    | SUPPLEMENTARY  | |            |
    +----------------+ +------------+
    """
    # Split text into parts
    text_parts = text.split('\n\n')
    text1 = text_parts[0].strip('\0') if len(text_parts) > 0 else ''
    text2 = text_parts[1].strip('\0') if len(text_parts) > 1 else ''
    
    # Handle image rotation and resizing
    # rota = img.width < img.height * 0.95
    # if rota:
    #     img = core.rotate_image_90_no_crop(img, reverse=True)
    
    # Calculate dimensions (right image target size)
    img_width = core.tgt_size
    img_ratio = img.height / img.width
    img_height = int(img_width * img_ratio)
    img_total_h = img_height + 2 * core.border_size
    
    # Dynamically determine left info panel width from text lengths
    inner_pad = core.exterior
    font1 = ImageFont.truetype(core.using_font, core.font_size)
    font2 = ImageFont.truetype(core.using_font, int(core.font_size * 0.9))
    font_suppli = ImageFont.truetype(core.using_font, int(core.font_size * 0.8)) if suppli_info else None
    _dummy_draw = ImageDraw.Draw(Image.new('RGB', (1, 1), (255, 255, 255)))
    desired_inner_w = 0
    desired_inner_w = max(desired_inner_w, int(_dummy_draw.textlength(text1, font=font1)))
    desired_inner_w = max(desired_inner_w, int(_dummy_draw.textlength(text2, font=font2)))
    # Wrap supplementary info against current desired_inner_w, then update desired_inner_w
    suppli_lines = []
    if suppli_info:
        words = suppli_info.split()
        line_buf = []
        for word in words:
            test_line = ' '.join(line_buf + [word])
            if _dummy_draw.textlength(test_line, font=font_suppli) <= desired_inner_w:
                line_buf.append(word)
            else:
                if line_buf:
                    suppli_lines.append(' '.join(line_buf))
                line_buf = [word]
        if line_buf:
            suppli_lines.append(' '.join(line_buf))
        for line in suppli_lines:
            desired_inner_w = max(desired_inner_w, int(_dummy_draw.textlength(line, font=font_suppli)))
    # Enforce a minimal inner width for a reasonable color swatch
    min_inner = int(12 * core.font_size)
    desired_inner_w = max(desired_inner_w, min_inner)
    left_panel_width = desired_inner_w + 2 * inner_pad
    
    # Calculate element heights
    # Dynamic logo block height based on half of content width
    content_w_for_logo = max(1, left_panel_width - 2 * inner_pad)
    logo_block_h = 0
    # 检查是否需要双logo模式
    if film_name != '' and film_logs.get(film_name, '') and os.path.exists(film_logs.get(film_name, '')) and os.path.exists(logo_file):
        try:
            # 双logo模式：宽度比例改为0.5，垂直堆叠
            logo_w_target = max(1, int(content_w_for_logo * 0.5))
            _camera_probe = Image.open(logo_file)
            _film_probe = Image.open(film_logs.get(film_name, ''))
            # 计算两个logo各自的高度（基于相同的目标宽度）
            _camera_ratio = _camera_probe.height / max(1, _camera_probe.width)
            _film_ratio = _film_probe.height / max(1, _film_probe.width)
            # 垂直堆叠：总高度 = camera_h + border_size + film_h
            camera_h = int(logo_w_target * _camera_ratio)
            film_h = int(logo_w_target * _film_ratio)
            logo_block_h = camera_h + core.border_size + film_h
            _camera_probe.close()
            _film_probe.close()
        except Exception:
            logo_block_h = 0
    elif os.path.exists(logo_file):
        try:
            # 单logo模式：宽度比例使用0.66
            logo_w_target = max(1, int(content_w_for_logo * 0.66))
            _logo_probe = Image.open(logo_file)
            _ratio = _logo_probe.height / max(1, _logo_probe.width)
            _logo_probe.close()
            logo_block_h = int(logo_w_target * _ratio)
        except Exception:
            logo_block_h = 0
    else:
        logo_w_target = max(1, int(content_w_for_logo * 0.66))
    color_swatch_h = int(0.8 * core.font_size)
    text1_h = core.font_size * 2  # Some extra space for text
    text2_h = int(core.font_size * 0.9) * 2
    suppli_h = int(core.font_size * 0.8) * 2 if suppli_info else 0
    spacing = core.exterior
    
    # Calculate total height needed for left panel
    left_panel_height = (logo_block_h + spacing * 2 + 
                        color_swatch_h + spacing * 2 + 
                        text1_h + spacing + 
                        text2_h + spacing + 
                        suppli_h)
    
    # Adjust image height to match left panel or keep original aspect (include border)
    if img_total_h < left_panel_height:
        img_y_offset = (left_panel_height - img_total_h) // 2
        total_height = left_panel_height
    else:
        img_y_offset = 0
        total_height = img_total_h
    
    # Create background with reduced horizontal outer padding (1*exterior each side)
    bg_width = left_panel_width + (img_width + 2 * core.border_size) + 2 * core.exterior
    bg_height = total_height + 2 * core.exterior
    background = Image.new('RGB', (bg_width, bg_height), (255, 255, 255))
    draw = ImageDraw.Draw(background)
    
    # # Draw dividing line
    # line_x = left_panel_width + core.exterior
    # draw.line([(line_x, 0), (line_x, bg_height)], fill=(200, 200, 200), width=1)
    # Compute vertical centering for the whole left block (logo + colors + text)
    suppli_line_h = int(core.font_size * 1.2)
    text_block_h = text1_h + spacing + text2_h
    if suppli_info:
        text_block_h += spacing + len(suppli_lines) * suppli_line_h
    left_block_h = logo_block_h + spacing * 2 + color_swatch_h + spacing * 2 + text_block_h
    current_y = core.exterior + max(0, (total_height - left_block_h) // 2)

    # Add logo
    if film_name != '' and film_logs.get(film_name, '') and os.path.exists(film_logs.get(film_name, '')) and os.path.exists(logo_file) and logo_block_h > 0:
        try:
            # 双logo模式：垂直排列，camera在上，film在下
            logo_w_target_dual = max(1, int(content_w_for_logo * 0.5))
            film_logo_path = film_logs.get(film_name, '')
            film_logo_img = Image.open(film_logo_path).convert('RGBA')
            camera_logo_img = Image.open(logo_file).convert('RGBA')
            
            # 调整两个logo到相同宽度
            camera_ratio = camera_logo_img.height / max(1, camera_logo_img.width)
            camera_h = max(1, int(logo_w_target_dual * camera_ratio))
            camera_logo_img = camera_logo_img.resize((logo_w_target_dual, camera_h))
            
            film_ratio = film_logo_img.height / max(1, film_logo_img.width)
            film_h = max(1, int(logo_w_target_dual * film_ratio*0.8))
            film_logo_img = film_logo_img.resize((int(logo_w_target_dual*0.8), film_h))
            
            # 在左侧面板中水平居中
            logo_x = (left_panel_width - logo_w_target_dual) // 2
            
            # 垂直排列：camera在上，film在下（间距border_size）
            camera_y = current_y
            film_y = current_y + camera_h + core.border_size
            
            # 粘贴两个logo
            background.paste(camera_logo_img, (int(logo_x), int(camera_y)), camera_logo_img if camera_logo_img.mode == 'RGBA' else None)
            background.paste(film_logo_img, (int(logo_x+logo_w_target_dual*0.1), int(film_y)), film_logo_img if film_logo_img.mode == 'RGBA' else None)
        except Exception as e:
            print(f"Error loading logos: {e}")
    elif os.path.exists(logo_file) and logo_block_h > 0:
        try:
            # 单logo模式
            logo_w_target_single = max(1, int(content_w_for_logo * 0.66))
            logo_img = Image.open(logo_file).convert('RGBA')
            logo_ratio = logo_img.height / max(1, logo_img.width)
            logo_w = logo_w_target_single
            logo_h = max(1, int(logo_w * logo_ratio))
            logo_img = logo_img.resize((logo_w, logo_h))
            logo_x = (left_panel_width - logo_w) // 2
            background.paste(logo_img, (int(logo_x), int(current_y)), logo_img if logo_img.mode == 'RGBA' else None)
        except Exception as e:
            print(f"Error loading logo: {e}")

    current_y += logo_block_h + spacing * 2

    # Add main colors sized to content width (left panel width minus inner padding on both sides)
    main_c = extract_main_colors(img, num_colors=4)
    content_w = left_panel_width - 2 * inner_pad
    color_swatch_w = content_w
    color_image = np.zeros((color_swatch_h, color_swatch_w, 3), dtype=int)
    block_width = max(1, color_swatch_w // max(1, len(main_c)))
    for i, color in enumerate(main_c):
        color_image[:, i * block_width:(i + 1) * block_width] = color
    color_pad = Image.fromarray(color_image.astype('uint8'))
    color_x = inner_pad
    background.paste(color_pad, (int(color_x), int(current_y)))

    current_y += color_swatch_h + spacing * 2

    # Add text centered within content width
    x1 = inner_pad + (content_w - draw.textlength(text1, font=font1)) // 2
    draw.text((int(x1), int(current_y)), text1, fill=(0, 0, 0), font=font1)

    cur_y = current_y + text1_h + spacing
    x2 = inner_pad + (content_w - draw.textlength(text2, font=font2)) // 2
    draw.text((int(x2), int(cur_y)), text2, fill=(80, 80, 80), font=font2)
    cur_y += text2_h

    if suppli_info:
        cur_y += spacing
        for line in suppli_lines:
            xs = inner_pad + (content_w - draw.textlength(line, font=font_suppli)) // 2
            draw.text((int(xs), int(cur_y)), line, fill=(120, 120, 120), font=font_suppli)
            cur_y += suppli_line_h
    
    # Add main image on the right
    img_resized = img.resize((img_width, img_height), Image.Resampling.LANCZOS)
    img_with_border = ImageOps.expand(img_resized, border=core.border_size, fill=core.border_color)
    img_x = left_panel_width + core.exterior
    img_y = core.exterior + img_y_offset
    background.paste(img_with_border, (img_x, img_y))
    
    # Handle square output if needed
    if square:
        square_size = max(background.size)
        square_bg = Image.new('RGB', (square_size, square_size), (255, 255, 255))
        paste_x = (square_size - background.width) // 2
        paste_y = (square_size - background.height) // 2
        square_bg.paste(background, (paste_x, paste_y))
        background = square_bg

    return background    

def _format_none(img: Image.Image, text: str, logo_file: str, suppli_info: str = '', *, square: bool = False, **kwargs) -> Image.Image:
    return img

FORMAT_HANDLERS: Dict[str, Callable[..., Image.Image]] = {
    'basic1': _format_basic1,
    'basic2': _format_basic2,
    'basic3': _format_basic3,
    'format_none': _format_none,
}

AVAILABLE_FORMAT_KEYS = set(FORMAT_HANDLERS.keys())

def process_one_image(img_input: Image.Image, text: str, logo_file: str, *args,
                      format: str = 'basic2', suppli_info: str = '', max_length: int = 2400,
                      add_black_border: bool = True, square: bool = False, film_name: str = '') -> Image.Image:
    """Dispatch to a registered format handler after applying layout sizing via core.update_tgt_size.
    Backward compatibility: extra positional arg treated as suppli_info unless it's a known format key.
    """
    # print("Process Params: ", "format: ", format, "suppli_info: ", suppli_info, "max_length: ", max_length, "add_black_border: ", add_black_border, "square: ", square, "film_name: ", film_name)
    if args:
        candidate = args[0]
        if isinstance(candidate, str) and candidate in AVAILABLE_FORMAT_KEYS:
            format = candidate
        else:
            suppli_info = candidate

    core.update_tgt_size(max_length, add_black_border)
    img = img_input

    handler = FORMAT_HANDLERS.get(format)
    if handler is None:
        raise ValueError('format not recognized')
    return handler(img, text, logo_file, suppli_info=suppli_info, square=square, film_name=film_name)
