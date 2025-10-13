from PIL import Image,ImageDraw,ImageFont,ImageOps
from PIL import ImageEnhance
from PIL.ExifTags import TAGS
import piexif
import numpy as np
import logging

# from .localrun import text_dict, logo_dict
from .color_extract import extract_main_colors

logging.basicConfig(
    format='[%(asctime)s] %(message)s',
    level=logging.INFO,
    handlers=[logging.StreamHandler()]  # 输出到控制台
)

using_font=r'fonts/LXGWBright-Italic.ttf'

# suppli_info="Kodak Vision3 5219 500T 120"
# suppli_info="Kodak Vision3 5207 250T 120"
# suppli_info="Kodak EktarChrome 5294 100D 135"
suppli_info="FUJICHROME Velvia 100 Daylight 120"
# suppli_info="FUJICHROME Provia 100f Daylight 120"
# suppli_info=None



text_dict={
    'hassel_CF60':["Hasselblad 500CM Type.1990s\n\nCarl Zeiss CF 60mm F3.5",'logos/hassel.jpg'],
    'hassel_CF150': ["Hasselblad 500CM Type.1990s\n\nCarl Zeiss CF 150mm F4", 'logos/hassel.jpg'],
    'olym_50': ["Olympus OM-30\n\nG.Zuiko Auto-S 50mm F1.4", 'logos/Olympus.jpg'],
    'olym_135': ["Olympus OM-30\n\nZuiko MC Auto-T 135mm F2.8", 'logos/Olympus.jpg'],
    'olym_2848': ["Olympus OM-30\n\nZuiko S Auto-Zoom 28-48mm F4", 'logos/Olympus.jpg'],
    'mamiya_six': ["Mamiya-Six Type.K-1953\n\nOlympus D.Zuiko F.C. 75mm F3.5 Sekorsha", 'logos/mamiya.jpg'],
    'minolta': ["Minolta Hi-Matic E \n\nRokkor-QF 40mm F1.7", 'logos/Minolta.jpg'],
    'auto_detect':['',''],
    'infinity_nikki': ['Miracle Continent 奇迹大陆\n\nPhotogragher: Fay','logos/infinity-nikki.jpg'],
    'Bronica': ['Zenza Bronica ETR-S \n\nZenzanon MC 75mm F2.8', "logos/bronica.jpg"],
    'Rollei': ['Rolleiflex Twin lens 3.5A \n\nCarl Zeiss Opton T* 75mm F3.5', "logos/Rollei.jpg"],
    'canon_EOS85': ['Canon EOS 7 \n\n Canon EF 85mm f/1.2L II USM','logos/canon.jpg'],
    'canon_EOS40': ['Canon EOS 7 \n\n Canon EF 40mm f/2.8 STM','logos/canon.jpg'],
    'pentax645_80160': ['Pentax 645N II \n\n Pentax smc FA 645 80-160mm f/4.5','logos/pentax.jpg'],
    'pentax645_75': ['Pentax 645N II \n\n Pentax smc FA 645 75mm f/2.8','logos/pentax.jpg'],
    'yashica124g': ['Yashica-MAT 124G \n\n Yashinon 80mm F3.5','logos/yashica.jpg'],
    



}
logo_dict={
'hassel_CF60':'logos/hassel.jpg',
    'hassel_CF150': 'logos/hassel.jpg',
    'olym_50':'logos/Olympus.jpg',
    'olym_135': 'logos/Olympus.jpg',
    'olym_2848': 'logos/Olympus.jpg',
    'mamiya_six': 'logos/mamiya.jpg',
    'minolta':'logos/Minolta.jpg',
    'SONY':'logos/Sony-Alpha-Logo.png',
    'Panasonic': 'logos/LumixS.jpg',
    'Canon': "logos/canon-r-logo.jpg",
    'OLYMPUS IMAGING CORP.  ': "logos/Olympus-new.png",
    'OLYMPUS CORPORATION': "logos/Olympus-new.png",
    'NIKON CORPORATION': "logos/Olympus-new.png",
    'FUJIFILM': "logos/fujifilm.jpg",
    'Bronica': "logos/bronica.jpg",
    'Rollei': "logos/Rollei.jpg",
    'canon_EOS85': 'logos/canon.jpg',
    'canon_EOS40':  'logos/canon.jpg',
    'pentax645_80160': 'logos/pentax.jpg',
    'pentax645_75': 'logos/pentax.jpg',
    'yashica124g': 'logos/yashica.jpg',
    'Leica': 'logos/Leicalogo.jpg',

}
# def initializing_directories():
#     if not os.path.exists(tgt):
#         os.mkdir(tgt)
#     if not os.path.exists(src):
#         os.mkdir(src)
#     for dir_name in list(text_dict.keys()):
#         if not os.path.exists(os.path.join(src,dir_name)):
#             os.mkdir(os.path.join(src,dir_name))
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


def process_one_image(img_input, text, logo_file, *args, format='basic3', suppli_info='', max_length=2400, add_black_border=True, square=False):
    """Delegate to effects.formats.process_one_image"""
    return _effects_process_one_image(
        img_input, text, logo_file, *args,
        format=format, suppli_info=suppli_info,
        max_length=max_length, add_black_border=add_black_border,
        square=square,
    )


if __name__=='__main__':
    img_path=r'F:\Image-border-extender\imgtoprocess\auto_detect\_4080535.jpg'
    img=Image.open(img_path)
    text_line,logo_path=' \n\n ','logos/hassel.jpg'
    process_res = process_one_image(img,text=text_line,logo_file=logo_path)
    process_res.show()
