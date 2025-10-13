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


# -----------------------------
# Filters: helpers and registry
# -----------------------------
def _clamp01(x: float) -> float:
    return 0.0 if x < 0 else 1.0 if x > 1 else x

def _scale_factor(base_at_half: float, strength: float) -> float:
    """
    将强度映射为乘法因子。
    - strength ∈ [0,1]
    - strength=0.5 => 返回 base_at_half (当前实现的强度)
    - strength=1.0 => 相对中性值(1.0)的效果幅度翻倍，即: 1 + (base_at_half-1)*2
    - strength=0.0 => 中性值 1.0
    对于小于0或大于1的输入，进行截断。
    """
    s = _clamp01(strength)
    k = s / 0.5 if s > 0 else 0.0  # 映射: 0->0, 0.5->1, 1.0->2
    return 1.0 + (base_at_half - 1.0) * k

def _filter_none(img: Image.Image, strength: float) -> Image.Image:
    # 无处理，忽略强度
    return img

def _filter_black_white(img: Image.Image, strength: float) -> Image.Image:
    # 在 s<=0.5 时：原图与灰度之间插值；s=0.5 等效当前：完全灰度
    # 在 s>0.5 时：完全灰度，并按强度增加对比度
    gray = ImageOps.grayscale(img).convert('RGB')
    s = _clamp01(strength)
    if s < 0.5:
        a = s / 0.5  # 0..1
        # 从原图逐步过渡到灰度
        out = Image.blend(img, gray, a)
        return out
    else:
        out = gray
        # s=0.5 时对比度因子=1.0，s=1.0 时增加少量对比度
        extra = (s - 0.5) / 0.5  # 0..1
        contrast_factor = 1.0 + 0.2 * extra
        out = ImageEnhance.Contrast(out).enhance(contrast_factor)
        return out

def _filter_vivid(img: Image.Image, strength: float) -> Image.Image:
    # 基准(在 s=0.5 时)：Color=1.5, Contrast=1.2, Brightness=1.03
    color_f = _scale_factor(1.5, strength)
    contrast_f = _scale_factor(1.2, strength)
    bright_f = _scale_factor(1.03, strength)
    img_c = ImageEnhance.Color(img).enhance(color_f)
    img_ct = ImageEnhance.Contrast(img_c).enhance(contrast_f)
    img_b = ImageEnhance.Brightness(img_ct).enhance(bright_f)
    return img_b

def _filter_retro(img: Image.Image, strength: float) -> Image.Image:
    # s<=0.5: 原图与(当前 sepia 效果)之间插值，s=0.5 等效当前
    # s>0.5: 在 sepia 基础上增加少量暖色与色彩强化
    arr = np.array(img, dtype=np.float32)
    r = arr[:, :, 0]
    g = arr[:, :, 1]
    b = arr[:, :, 2]
    tr = 0.393 * r + 0.769 * g + 0.189 * b
    tg = 0.349 * r + 0.686 * g + 0.168 * b
    tb = 0.272 * r + 0.534 * g + 0.131 * b
    sepia = np.stack([tr, tg, tb], axis=-1)
    sepia = np.clip(sepia, 0, 255).astype('uint8')
    out = Image.fromarray(sepia, mode='RGB')
    out = ImageEnhance.Contrast(out).enhance(0.95)
    out = ImageEnhance.Color(out).enhance(1.05)

    s = _clamp01(strength)
    if s < 0.5:
        a = s / 0.5  # 0..1
        return Image.blend(img, out, a)
    else:
        extra = (s - 0.5) / 0.5  # 0..1
        # 叠加暖色微调与色彩增强，放大当前效果
        warm = Image.new('RGB', out.size, (255, 235, 200))
        out2 = Image.blend(out, warm, 0.08 * extra)
        out2 = ImageEnhance.Color(out2).enhance(1.0 + 0.1 * extra)
        out2 = ImageEnhance.Contrast(out2).enhance(1.0 + 0.05 * extra)
        return out2

def _filter_film(img: Image.Image, strength: float) -> Image.Image:
    # 基准(在 s=0.5 时)：noise_sigma=6.0, contrast=0.98, tint_alpha=0.04
    s = _clamp01(strength)
    k = s / 0.5 if s > 0 else 0.0  # 0..2
    sigma = 6.0 * k
    contrast_f = 1.0 + (0.98 - 1.0) * k  # 1 - 0.02*k
    tint_alpha = 0.04 * k

    if sigma > 0:
        arr = np.array(img, dtype=np.int16)
        h, w, _ = arr.shape
        noise = np.random.normal(loc=0.0, scale=sigma, size=(h, w, 1))
        noise = np.repeat(noise, 3, axis=2)
        arr = arr + noise
        arr = np.clip(arr, 0, 255).astype('uint8')
        out = Image.fromarray(arr, mode='RGB')
    else:
        out = img

    out = ImageEnhance.Contrast(out).enhance(contrast_f)
    if tint_alpha > 0:
        tint = Image.new('RGB', out.size, (220, 235, 225))
        out = Image.blend(out, tint, alpha=tint_alpha)
    return out

# 过滤器字典：key -> 处理函数
FILTER_HANDLERS = {
    'none': _filter_none,
    'black_white': _filter_black_white,
    'vivid': _filter_vivid,
    'retro': _filter_retro,
    'film': _filter_film,
}

# 可用过滤器key集合，便于外部检查或文档展示
AVAILABLE_FILTER_KEYS = set(FILTER_HANDLERS.keys())


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


def apply_filter(img_input, filter_key: str, strength: float = 0.5):
    """
    根据给定的过滤器关键字对图片进行滤镜处理。
    支持的 filter_key:
    - 'black_white': 黑白
    - 'vivid': 增强色彩与对比度
    - 'retro': 复古(棕褐色/褪色)
    - 'film': 胶片感(轻微颗粒+柔和对比)
    - 'none' 或未知: 不处理

    参数:
    - strength: 0~1 浮点数。0.5 等同于当前实现强度；1.0 为当前强度的 2 倍；0 为无效果。

    返回处理后的 PIL.Image.Image
    """
    if img_input is None:
        return img_input

    key = (filter_key or 'none').strip().lower()
    img = img_input.convert('RGB')

    try:
        handler = FILTER_HANDLERS.get(key, FILTER_HANDLERS['none'])
        return handler(img, strength)
    except Exception:
        # 任意异常都回退为原图，避免中断流程
        raise ValueError("apply_filter failed")


def _format_basic1(img, text, logo_file, suppli_info='', *, square=False):
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
            logo_file = logo_dict[camera_mk]
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
        img = rotate_image_90_no_crop(img, reverse=True)

    wh, ht = img.width, img.height
    new_width = tgt_size
    new_height = int(ht * new_width / wh)
    img = img.resize((new_width, new_height))

    # calculate bg size
    background = Image.new('RGB', (tgt_size + 2 * border_size + 2 * exterior, new_height + 2 * border_size + 3 * exterior + infor_area), (255, 255, 255))
    # add border 1
    img = ImageOps.expand(img, border=border_size, fill=border_color)

    # 将原始图片粘贴到白色背景图上
    background.paste(img, (exterior, exterior))

    # add logo
    logo_img = Image.open(logo_file).convert('RGB')
    logo_height = infor_area * 0.8
    logo_img = logo_img.resize((int(logo_img.width * logo_height / logo_img.height), int(logo_height)))
    background.paste(logo_img, (int(tgt_size + 2 * border_size + exterior - logo_img.width * logo_height / logo_img.height), int(new_height + 2 * border_size + 2 * exterior)))
    draw = ImageDraw.Draw(background)

    # add text 1 the camera
    font = ImageFont.truetype(using_font, font_size)
    posi = (int(exterior * 1.01), 2 * exterior + new_height + 2 * border_size)
    text_1 = text.split('\n\n')[0].strip('\0')
    draw.text(posi, text_1, fill=(0, 0, 0), font=font)
    bold_offset = 1  # make it bold
    for offset in [(0, 0), (bold_offset, 0), (0, bold_offset), (bold_offset, bold_offset)]:
        draw.text((posi[0] + offset[0], posi[1] + offset[1]), text_1, font=font, fill=(0, 0, 0))

    # add text 2 the lens
    font = ImageFont.truetype(using_font, int(font_size * 0.9))
    posi = (int(exterior * 1.01), 2 * exterior + new_height + 2 * border_size + 1.6 * font_size)
    text_2 = text.split('\n\n')[1].strip('\0')
    draw.text(posi, text_2, fill=(0, 0, 0), font=font)

    # add main_color
    main_c = extract_main_colors(img, num_colors=4)
    color_image = np.zeros((int(0.8 * font_size), int(15 * font_size), 3), dtype=int)
    block_width = color_image.shape[1] // len(main_c) + 1
    for i, color in enumerate(main_c):
        color_image[:, i * block_width:(i + 1) * block_width] = color
    color_pad = Image.fromarray(color_image.astype('uint8'))
    posi_mc = (int(exterior * 1.01), int(2 * exterior + new_height + 2 * border_size + 3.0 * font_size))
    background.paste(color_pad, posi_mc)

    # add supplementary_line in the last line
    if suppli_line:
        font = ImageFont.truetype(using_font, int(font_size * 0.8))
        posi = (int(exterior * 1.01), 2 * exterior + new_height + 2 * border_size + 4.2 * font_size)
        draw.text(posi, suppli_line.strip('\0'), fill=(80, 80, 80), font=font)

    # rotate back and save
    if rota:
        background = rotate_image_90_no_crop(background, reverse=False)

    if square:
        # 创建正方形背景
        w, h = background.size
        square_size = max(w, h)
        square_bg = Image.new('RGB', (square_size, square_size), (255, 255, 255))
        paste_x = (square_size - w) // 2
        paste_y = (square_size - h) // 2
        square_bg.paste(background, (paste_x, paste_y))
        background = square_bg

    return background

# 注册格式处理器
FORMAT_HANDLERS = {
    'basic1': _format_basic1,
}

AVAILABLE_FORMAT_KEYS = set(FORMAT_HANDLERS.keys())

def process_one_image(img_input, text, logo_file, *args, format='basic1', suppli_info='', max_length=2400, add_black_border=True, square=False):
    """
    处理图片外边框和信息排版，支持多种格式，通过 format key 分发。

    兼容旧调用：如果第三个位置参数传入的是 suppli_info（而不是已知的 format key），则按旧逻辑处理。
    """
    # 兼容旧的第4个位置参数
    if args:
        candidate = args[0]
        if isinstance(candidate, str) and candidate in AVAILABLE_FORMAT_KEYS:
            format = candidate
        else:
            suppli_info = candidate

    # 应用控制参数
    update_tgt_size(max_length, add_black_border)
    img = img_input

    handler = FORMAT_HANDLERS.get(format)
    if handler is None:
        raise ValueError('format not recognized')
    return handler(img, text, logo_file, suppli_info=suppli_info, square=square)


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


def process_one_image(img_input, text, logo_file, *args, format='basic1', suppli_info='', max_length=2400, add_black_border=True, square=False):
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
