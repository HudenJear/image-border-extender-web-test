"""
本地批量图片处理脚本
使用argparse传参，统一使用wxcloudrun.effects.formats中的process_one_image函数
"""
import argparse
import os
import glob
from PIL import Image
import sys

# 使用统一的导入方式（与add_bd.py保持一致）
from wxcloudrun.effects.formats import (
    process_one_image as _effects_process_one_image,
    AVAILABLE_FORMAT_KEYS,
)


# 相机和镜头配置字典
text_dict = {
    'hassel_CF60': ["Hasselblad 500CM Type.1990s\n\nCarl Zeiss CF 60mm F3.5", 'logos/hassel.jpg'],
    'hassel_CF150': ["Hasselblad 500CM Type.1990s\n\nCarl Zeiss CF 150mm F4", 'logos/hassel.jpg'],
    'olym_50': ["Olympus OM-30\n\nG.Zuiko Auto-S 50mm F1.4", 'logos/Olympus.jpg'],
    'olym_dc35': ["Olympus 35DC\n\nF.Zuiko Auto 40mm F1.7", 'logos/Olympus.jpg'],
    'olym_135': ["Olympus OM-30\n\nZuiko MC Auto-T 135mm F2.8", 'logos/Olympus.jpg'],
    'olym_2848': ["Olympus OM-30\n\nZuiko S Auto-Zoom 28-48mm F4", 'logos/Olympus.jpg'],
    'mamiya_six': ["Mamiya-Six Type.K-1953\n\nOlympus D.Zuiko F.C. 75mm F3.5 Sekorsha", 'logos/mamiya.jpg'],
    'minolta': ["Minolta Hi-Matic E \n\nRokkor-QF 40mm F1.7", 'logos/Minolta.jpg'],
    'auto_detect': ['', ''],
    'infinity_nikki': ['Miracle Continent 奇迹大陆\n\nPhotogragher: Fay', 'logos/infinity-nikki.jpg'],
    'Bronica': ['Zenza Bronica ETR-S \n\nZenzanon MC 75mm F2.8', "logos/bronica.jpg"],
    'Rollei': ['Rolleiflex Twin lens 3.5A \n\nCarl Zeiss Opton T* 75mm F3.5', "logos/Rollei.jpg"],
    'canon_EOS85': ['Canon EOS 7 \n\n Canon EF 85mm f/1.2L II USM', 'logos/canon.jpg'],
    'canon_EOS40': ['Canon EOS 7 \n\n Canon EF 40mm f/2.8 STM', 'logos/canon.jpg'],
    'pentax645_80160': ['Pentax 645N II \n\n Pentax smc FA 645 80-160mm f/4.5', 'logos/pentax.jpg'],
    'pentax645_4585': ['Pentax 645N II \n\n Pentax smc FA 645 45-85mm f/4.5', 'logos/pentax.jpg'],
    'pentax645_75': ['Pentax 645N II \n\n Pentax smc FA 645 75mm f/2.8', 'logos/pentax.jpg'],
    'yashica124g': ['Yashica-MAT 124G \n\n Yashinon 80mm F3.5', 'logos/yashica.jpg'],
    'leica_VM40': ['Leica M4 film camera \n\n Voigtländer VM 40mm F1.4 Nokton MC', 'logos/Leicalogo.jpg'],
    'leica_M35': ['Leica M4 film camera \n\n Leica Summicron-M 35mm f1:2', 'logos/Leicalogo.jpg'],
}

logo_dict = {
    'hassel_CF60': 'logos/hassel.jpg',
    'hassel_CF150': 'logos/hassel.jpg',
    'olym_50': 'logos/Olympus.jpg',
    'olym_dc35': 'logos/Olympus.jpg',
    'olym_135': 'logos/Olympus.jpg',
    'olym_2848': 'logos/Olympus.jpg',
    'mamiya_six': 'logos/mamiya.jpg',
    'minolta': 'logos/Minolta.jpg',
    'SONY': 'logos/Sony-Alpha-Logo.png',
    'Panasonic': 'logos/LumixS.jpg',
    'Canon': "logos/canon-r-logo.jpg",
    'OLYMPUS IMAGING CORP.  ': "logos/Olympus-new.png",
    'OLYMPUS CORPORATION': "logos/Olympus-new.png",
    'NIKON CORPORATION': "logos/Olympus-new.png",
    'FUJIFILM': "logos/fujifilm.jpg",
    'Bronica': "logos/bronica.jpg",
    'Rollei': "logos/Rollei.jpg",
    'canon_EOS85': 'logos/canon.jpg',
    'canon_EOS40': 'logos/canon.jpg',
    'pentax645_80160': 'logos/pentax.jpg',
    'pentax645_4585': 'logos/pentax.jpg',
    'pentax645_75': 'logos/pentax.jpg',
    'yashica124g': 'logos/yashica.jpg',
    'leica_VM40': 'logos/Leicalogo.jpg',
    'leica_M35': 'logos/Leicalogo.jpg',
}


def process_one_image(img_input, text, logo_file, *args, format='basic3', suppli_info='', 
                      max_length=2400, add_black_border=True, film_name='',square=False):
    """委托给effects.formats.process_one_image"""
    return _effects_process_one_image(
        img_input, text, logo_file, *args,
        format=format, suppli_info=suppli_info,
        max_length=max_length, add_black_border=add_black_border,
        square=square,
        film_name=film_name,
    )


def initializing_directories(src, tgt):
    """初始化源目录和目标目录，以及相机文件夹"""
    if not os.path.exists(tgt):
        os.mkdir(tgt)
    if not os.path.exists(src):
        os.mkdir(src)
    for dir_name in list(text_dict.keys()):
        dir_path = os.path.join(src, dir_name)
        if not os.path.exists(dir_path):
            os.mkdir(dir_path)


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='批量处理图片，添加边框、Logo和文字信息',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
# film_logs={
#   'FujiFilm Acros 100 II 135':  'films/Acros100ii-135_.jpg',
#   'FujiFilm C200 135':  'films/FujiC200-new-135.jpg',
#   'FujiFilm C400 135':  'films/FujiC400-new-135.jpg',
#   'FujiFilm Pro Provia 100f 120':  'films/Fujifilm_RDP_III_120.jpg',
#   'FujiFilm Pro Provia 100f 135':  'films/Fujifilm_RDP_III_135.jpg',
#   'FujiFilm Pro Velvia 100 120':  'films/Velvia100-120.jpg',
#   'FujiFilm Pro Velvia 100 135':  'films/Velvia100-135.jpg',
#   'FujiFilm Pro Velvia 50 120':  'films/Velvia_50-120.jpg',
#   'FujiFilm Pro Velvia 50 135':  'films/Velvia_50-135.jpg',
#   'Kodak Ektachrome 100 Daylight 120':  'films/kodak-film-ektachrome-100-120.webp',
#   'Kodak Ektachrome 100 Daylight 135':  'films/kodak-film-ektachrome-100-135.webp',
#   'Kodak Gold 200 Daylight 120':  'films/kodak-gold-200-120.jpg',
#   'Kodak T-Max 400 135':  'films/kodak-tmax-400-135.jpg',
#   'Kodak T-Max 400 120':  'films/kodak-tmax400-120.jpg',
#   'Kodak Tri-X 400 135':  'films/kodak-tri-x-400-135.jpg',
# }

    # 必需参数
    parser.add_argument('--src', type=str, 
                        default=r'F:\Image-border-extender本地图片目录\imgtoprocess',
                        help='源图片目录路径')
    parser.add_argument('--tgt', type=str,
                        default=r'F:\Image-border-extender本地图片目录\imgdone',
                        help='目标输出目录路径')
    
    # 图片处理参数
    parser.add_argument('--max-length', type=int, default=2400,
                        help='输出图片的最大边长')
    parser.add_argument('--format', type=str, default='basic1',
                        choices=list(AVAILABLE_FORMAT_KEYS),
                        help='图片格式样式')
    parser.add_argument('--square', action='store_true',
                        help='输出正方形图片')
    parser.add_argument('--add-black-border', type=bool, default=False,
                        help='是否添加黑色边框')
    parser.add_argument('--film-name', type=str, default='FujiFilm Pro Provia 100f 120',
                        help='胶卷名称')
    
    # 补充信息
    parser.add_argument('--suppli-info', type=str, default='',
                        help='补充信息文字（如胶卷型号等）默认跟随film-name')
    
    # 调试选项
    parser.add_argument('--verbose', action='store_true',
                        help='显示详细处理信息')
    
    return parser.parse_args()


def process_images(src, tgt, format='basic3', suppli_info='', max_length=2400, 
                   add_black_border=True, square=False, film_name='',verbose=False):
    """批量处理图片的主逻辑"""
    initializing_directories(src, tgt)
    
    dir_list = os.listdir(src)
    for dir_name in dir_list:
        dir_path = os.path.join(src, dir_name)
        
        # 只处理在text_dict中定义的目录
        if os.path.isdir(dir_path) and dir_name in text_dict:
            text_line, logo_path = text_dict[dir_name]
            
            # 收集所有图片文件
            img_all = []
            for suf in ['png', 'jpeg', 'jpg', 'PNG', 'tif', 'JPG', 'JPEG']:
                img_all.extend(glob.glob(os.path.join(dir_path, "*." + suf)))
            
            if not img_all:
                if verbose:
                    print(f'目录 {dir_name} 中没有图片文件')
                continue
            
            print(f'\n处理目录: {dir_name}')
            print(f'找到 {len(img_all)} 张图片需要处理')
            
            # 逐个处理图片
            for indx, img_path in enumerate(img_all):
                try:
                    if verbose:
                        print(f'\n正在处理: {os.path.basename(img_path)}')
                    else:
                        print(f"\r处理进度 {indx+1}/{len(img_all)}...", end='', flush=True)
                    
                    # 读取图片
                    img = Image.open(img_path).convert('RGB')
                    
                    # 调用统一的process_one_image函数
                    processed_img = process_one_image(
                        img, 
                        text_line, 
                        logo_path,
                        format=format,
                        suppli_info=suppli_info,
                        max_length=max_length,
                        add_black_border=add_black_border,
                        square=square,
                        film_name=film_name,
                    )
                    
                    # 保存处理后的图片
                    base_name = os.path.splitext(os.path.basename(img_path))[0]
                    save_path = os.path.join(tgt, f"{base_name}_{dir_name}_{format}.jpg")
                    processed_img.save(save_path, quality=95)
                    
                    if verbose:
                        print(f'已保存: {save_path}')
                        
                except Exception as e:
                    print(f'\n处理失败: {img_path}')
                    print(f'错误信息: {str(e)}')
            
            print(f'\n目录 {dir_name} 处理完成!')


def main():
    """主函数"""
    args = parse_arguments()
    
    print('=' * 60)
    print('图片批量处理工具 (Local2Run)')
    print('=' * 60)
    print(f'源目录: {args.src}')
    print(f'目标目录: {args.tgt}')
    print(f'最大边长: {args.max_length}')
    print(f'格式样式: {args.format}')
    if args.suppli_info != '':
      suppli_info=args.suppli_info
      print(f'补充信息: {args.suppli_info}')
      print(f'胶卷型号: {args.film_name}')
    else:
      suppli_info=args.film_name
      print(f'补充信息: {args.film_name}')
    print(f'正方形输出: {args.square}')
    print(f'添加黑边: {args.add_black_border}')
    print('=' * 60)
    
    process_images(
        src=args.src,
        tgt=args.tgt,
        format=args.format,
        suppli_info=suppli_info,
        max_length=args.max_length,
        add_black_border=args.add_black_border,
        square=args.square,
        verbose=args.verbose,
        film_name=args.film_name,
    )
    
    print('\n所有处理完成！')


if __name__ == '__main__':
    main()
