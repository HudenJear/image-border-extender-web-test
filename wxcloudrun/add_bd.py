from PIL import Image,ImageDraw,ImageFont,ImageOps
from PIL.ExifTags import TAGS
import piexif
import numpy as np
import logging

from .localrun import text_dict, logo_dict
from .color_extract import extract_main_colors

logging.basicConfig(
    format='[%(asctime)s] %(message)s',
    level=logging.INFO,
    handlers=[logging.StreamHandler()]  # 输出到控制台
)

using_font=r'fonts\LXGWBright-Italic.ttf'

# suppli_info="Kodak Vision3 5219 500T 120"
# suppli_info="Kodak Vision3 5207 250T 120"
# suppli_info="Kodak EktarChrome 5294 100D 135"
suppli_info="FUJICHROME Velvia 100 Daylight 120"
# suppli_info="FUJICHROME Provia 100f Daylight 120"
# suppli_info=None


# text_dict={
#     'hassel_CF60':["Hasselblad 500CM Type.1990s\n\nCarl Zeiss CF 60mm F3,5",'logos/hassel.jpg'],
#     'hassel_CF150': ["Hasselblad 500CM Type.1990s\n\nCarl Zeiss CF 150mm F4", 'logos/hassel.jpg'],
#     'olym_50': ["Olympus OM-30\n\nG.Zuiko Auto-S 50mm F1,4", 'logos/Olympus.jpg'],
#     'olym_135': ["Olympus OM-30\n\nZuiko MC Auto-T 135mm F2,8", 'logos/Olympus.jpg'],
#     'olym_2848': ["Olympus OM-30\n\nZuiko S Auto-Zoom 28-48mm F4", 'logos/Olympus.jpg'],
#     'mamiya_six': ["Mamiya-Six Type.K-1953\n\nOlympus D.Zuiko F.C. 75mm F3.5 Sekorsha", 'logos/mamiya.jpg'],
#     'minolta': ["Minolta Hi-Matic E \n\nRokkor-QF 40mm F1,7", 'logos/Minolta.jpg'],
#     'auto_detect':['',''],
#     'infinity_nikki': ['Miracle Continent\n\n Photogragher: Fay','logos/infinity-nikki.jpg'],

# }
# logo_dict={
# 'hassel_CF60':'logos/hassel.jpg',
#     'hassel_CF150': 'logos/hassel.jpg',
#     'olym_50':'logos/Olympus.jpg',
#     'olym_135': 'logos/Olympus.jpg',
#     'olym_2848': 'logos/Olympus.jpg',
#     'mamiya_six': 'logos/mamiya.jpg',
#     'minolta':'logos/Minolta.jpg',
#     'SONY':'logos/Sony-Alpha-Logo.png',
#     'Panasonic': 'logos/Panasonic-Lumix-Logo.jpg',
#     'Canon': "logos/canon-r-logo.jpg",
#     'OLYMPUS IMAGING CORP.  ': "logos/Olympus-new.png",
#     'OLYMPUS CORPORATION': "logos/Olympus-new.png",
#     'NIKON CORPORATION': "logos/Olympus-new.png",
#     'FUJIFILM': "logos/Olympus-new.png",

# }

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


def process_one_image(img_input,text,logo_file,suppli_info='',max_length=2400,add_black_border=True,square=False):
    update_tgt_size(max_length,add_black_border)
    img = img_input
    suppli_line=suppli_info
    # logging.log("图片加载成功，开始处理")
    # if the image is auto-detected, the exif will be extracted
    if text=='':
        
        # exif=img.info['exif']
        exif_data = img.getexif()
        camera_mk=None
        camera_m=None
        if exif_data:
            for tag, value in exif_data.items():
                tag_name = TAGS.get(tag, tag)
                # print(f"{tag_name}: {value}")
                if tag_name=="Make":
                    camera_mk=value
                elif tag_name=='Model':
                    camera_m=value

        if camera_mk and camera_m:
            text = camera_mk + ' '+ camera_m+'\n\n'
            logo_file=logo_dict[camera_mk]
            try:
                exif_dict = piexif.load(img.info['exif'])
                # print(exif_dict['Exif'].keys())
                # for element in dir(piexif.ExifIFD):
                #     # 排除内置属性和方法
                #     if not element.startswith('__'):
                #         value = getattr(piexif.ExifIFD, element)
                #         if value in exif_dict['Exif'].keys():
                #             print(f"{element}: {value}")
                #             # print(f"{element}: {value}: {exif_dict['Exif'][value]}")
                focal_length = exif_dict['Exif'][piexif.ExifIFD.FocalLength]
                # print(focal_length)
                F_value=exif_dict['Exif'][piexif.ExifIFD.FNumber]
                # print(F_value)
                ISO_value=exif_dict['Exif'][piexif.ExifIFD.ISOSpeedRatings]
                ss_value=exif_dict['Exif'][piexif.ExifIFD.ExposureTime]
                # ss_text='S: '+str(ss_value[0])+"/"+str(ss_value[1])+'s' if ss_value[0]/ss_value[1] <1 else 'S: '+str(ss_value[0])+'s'
                ss_value=int(ss_value[1])/int(ss_value[0])
                ss_text='S: '+'1'+"/"+str(int(ss_value))+'s' if ss_value >1 else 'S: '+str(int(1/ss_value))+'s'

                # print(str(exif_dict['Exif'][piexif.ExifIFD.LensModel]))
                text=text+exif_dict['Exif'][piexif.ExifIFD.LensModel].decode('utf-8')
                # camera_m=exif_data['Make']
                # suppli_line='Focal: '+str(int(focal_length[0]/focal_length[1]))+'mm    '+'A: F'+str(F_value[0]/F_value[1]).replace('.',',')+'    '+'ISO: '+str(ISO_value)+'    '+ss_text
                suppli_line='Focal: '+str(int(focal_length[0]/focal_length[1]))+'mm    '+'A: F'+str(F_value[0]/F_value[1])+'    '+'ISO: '+str(ISO_value)+'    '+ss_text



                # print(text)
                # print(logo_file)
                # print(suppli_line)

            except:
                print(f"Exif detected broken for one image in the auto detect dictionary")


        else:
            print(f"No exif detected for one image in the auto detect dictionary")
            return
    # print(img.height,img.width)


    # 计算要将原始图片粘贴到白色背景图上的位置,rotate or not
    rota=True if img.width < img.height * 0.95 else False

    if rota:
        img=rotate_image_90_no_crop(img,reverse=True)
    #     ht,wh=img.width, img.height
    #     print("Flipped!")
    # else:
    wh,ht  = img.width, img.height
    # print(img.height, img.width)
    # 计算新的图像尺寸
    new_width = tgt_size
    new_height = int(ht * new_width / wh)
    # 重新缩放原始图片
    img = img.resize((new_width, new_height))
    # left = int((tgt_size * (1 - ratio)) // 2)

    # calculate bg size
    background = Image.new('RGB', (tgt_size+2*border_size+2*exterior, new_height+2*border_size+3*exterior+infor_area), (255, 255, 255))
    # add border 1
    img= ImageOps.expand(img, border=border_size, fill=border_color)

    # 将原始图片粘贴到白色背景图上
    background.paste(img, (exterior, exterior))


    # add logo
    logo_img = Image.open(logo_file).convert('RGB')
    logo_height = infor_area * 0.8
    logo_img=logo_img.resize((int(logo_img.width*logo_height/logo_img.height),int(logo_height)))
    background.paste(logo_img,(int(tgt_size+2*border_size+exterior-logo_img.width*logo_height/logo_img.height),int(new_height+2*border_size+2*exterior)))
    draw = ImageDraw.Draw(background)

    # add text 1 the camera
    font = ImageFont.truetype(using_font, font_size)
    posi = (int(exterior*1.01), 2 * exterior + new_height + 2*border_size)
    text_1=text.split('\n\n')[0].strip('\0')
    draw.text(posi, text_1, fill=(0, 0, 0), font=font)
    bold_offset = 1 # make it bold
    for offset in [(0, 0), (bold_offset, 0), (0, bold_offset), (bold_offset, bold_offset)]:
        draw.text((posi[0] + offset[0], posi[1] + offset[1]), text_1, font=font, fill=(0, 0, 0))

    # add text 2 the lens
    font = ImageFont.truetype(using_font, int(font_size*0.9))
    posi = (int(exterior*1.01), 2 * exterior + new_height + 2 * border_size+1.6*font_size)
    text_2 = text.split('\n\n')[1].strip('\0')
    draw.text(posi, text_2, fill=(0, 0, 0), font=font)
    # text2 = "\nShot in Somewhere on the earth."

    # add main_color
    main_c=extract_main_colors(img,num_colors=4)
    color_image = np.zeros((int(0.8* font_size), int(15*font_size), 3), dtype=int)
    block_width = color_image.shape[1] // len(main_c) +1
    for i, color in enumerate(main_c):
        color_image[:, i * block_width:(i + 1) * block_width] = color
    color_pad=Image.fromarray(color_image.astype('uint8'))
    posi_mc=(int(exterior*1.01), int(2 * exterior + new_height + 2 * border_size+3.0*font_size))
    background.paste(color_pad,posi_mc)

    # add supplementary_line in the last line
    if suppli_line:
        font = ImageFont.truetype(using_font, int(font_size * 0.8))
        posi = (int(exterior*1.01), 2 * exterior + new_height + 2 * border_size + 4.2 * font_size)
        draw.text(posi, suppli_line.strip('\0'), fill=(80, 80, 80), font=font)

    # rotate back and save
    if rota:
        background=rotate_image_90_no_crop(background,reverse=False)
    # dir_p=os.path.split(os.path.split(img_path)[0])[1]
    # sav_path=os.path.join(tgt, os.path.splitext(os.path.split(img_path)[1])[0] +'_'+dir_p+ f".jpg")
    # 保存最终结果os.path.join(tgt, os.path.splitext(os.path.split(img_path)[1])[0] + f".jpg")

    if square:
        # 创建正方形背景
        w, h = background.size
        square_size = max(w, h)
        square_bg = Image.new('RGB', (square_size, square_size), (255, 255, 255))
        # 计算粘贴位置
        paste_x = (square_size - w) // 2
        paste_y = (square_size - h) // 2
        square_bg.paste(background, (paste_x, paste_y))
        background = square_bg

    return background


if __name__=='__main__':
    img_path=r'F:\Image-border-extender\imgtoprocess\auto_detect\_4080535.jpg' 
    img=Image.open(img_path)
    text_line,logo_path=' \n\n ','logos/hassel.jpg'
    process_res = process_one_image(img,text=text_line,logo_file=logo_path)
    process_res.show()
