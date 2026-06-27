from PIL import Image,ImageDraw,ImageFont,ImageOps
from PIL import ImageEnhance
from PIL.ExifTags import TAGS
import piexif
import numpy as np
import logging

from .color_extract import extract_main_colors

logging.basicConfig(
    format='[%(asctime)s] %(message)s',
    level=logging.INFO,
    handlers=[logging.StreamHandler()]  # 输出到控制台
)

using_font=r'fonts/LXGWBright-Italic.ttf'

tgt_size=2400
border_size=int(0.01*tgt_size)
border_color='black'
exterior=int(0.03*tgt_size)
infor_area=int(0.12*tgt_size)
font_size=int(infor_area*0.2)
cc_name='Credit Name'

def update_tgt_size(max_length,add_black_border=True):
    global border_size,border_color,exterior,infor_area,font_size,tgt_size
    tgt_size=max_length
    border_size=int(0.01*tgt_size) if add_black_border else int(0.0001*tgt_size)
    border_color='black'
    exterior=int(0.03*tgt_size)
    infor_area=int(0.12*tgt_size)
    font_size=int(infor_area*0.2)


def rotate_image_90_no_crop(image_data,reverse=False):
    # 打开图像
    image=image_data
    width, height = image.size

    # 创建一个新的背景图像，尺寸为原图像的对角线长度
    new_size = int((width ** 2 + height ** 2) ** 0.5)
    new_image = Image.new("RGB", (new_size, new_size), (0, 0,0))

    # 将原图像粘贴到背景图像的中心
    new_image.paste(image, ((new_size - width) // 2, (new_size - height) // 2))

    # 旋转图像90度
    if not reverse:
        rotated_image = new_image.rotate(90, expand=True)
    else:
        rotated_image = new_image.rotate(270, expand=True)

    # 裁剪掉多余的透明部分
    bbox = rotated_image.getbbox()
    cropped_image = rotated_image.crop(bbox)

    return cropped_image


# -----------------------------
# Delegation to effects package
# -----------------------------
from .effects.filters import (
    apply_filter as _effects_apply_filter,
    AVAILABLE_FILTER_KEYS as AVAILABLE_FILTER_KEYS,
    FILTER_HANDLERS as FILTER_HANDLERS,
)
from .effects.formats import (
    process_one_image as _effects_process_one_image,
    AVAILABLE_FORMAT_KEYS as AVAILABLE_FORMAT_KEYS,
    FORMAT_HANDLERS as FORMAT_HANDLERS,
)

def apply_filter(img_input, filter_key: str, strength: float = 0.5):
    """Delegate to effects.filters.apply_filter"""
    return _effects_apply_filter(img_input, filter_key, strength)


def process_one_image(img_input, text, logo_file, *args, format='basic3', suppli_info='', max_length=2400, add_black_border=True, square=False, film_file='', film_name=''):
    """Delegate to effects.formats.process_one_image"""
    film_logo_file = film_file or film_name
    return _effects_process_one_image(
        img_input, text, logo_file, *args,
        format=format, suppli_info=suppli_info,
        max_length=max_length, add_black_border=add_black_border,
        square=square,
        film_file=film_logo_file,
    )


if __name__=='__main__':
    img_path=r'F:\Image-border-extender\imgtoprocess\auto_detect\_4080535.jpg'
    img=Image.open(img_path)
    text_line,logo_path=' \n\n ','logos/hassel.jpg'
    process_res = process_one_image(img,text=text_line,logo_file=logo_path)
    process_res.show()
