"""
批量分割图片：
- 竖图（高 > 宽）：纵向均分为 3 份
- 横图（宽 > 高）：横向均分为 6 份
- 分割后沿切缝两侧检测黑边并裁除
输出保存到源目录下的 processed 子文件夹
"""
import argparse
from pathlib import Path

import numpy as np
from PIL import Image

IMAGE_SUFFIXES = {'.jpg', '.jpeg', '.png', '.tif', '.tiff', '.webp', '.bmp', '.gif'}


def collect_images(folder: Path) -> list[Path]:
    return sorted(
        p for p in folder.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES
    )


def _edge_is_black(line: np.ndarray, threshold: int, dark_ratio: float) -> bool:
    """一行/列中足够比例的像素为暗色则视为黑边。"""
    return float(np.mean(np.max(line, axis=-1) <= threshold)) >= dark_ratio


def trim_black_edges(
    img: Image.Image,
    *,
    top: bool = True,
    bottom: bool = True,
    left: bool = True,
    right: bool = True,
    threshold: int = 30,
    dark_ratio: float = 0.98,
) -> Image.Image:
    """从指定边缘向内扫描并裁除连续黑边。"""
    arr = np.array(img)
    height, width = arr.shape[:2]
    crop_top, crop_bottom = 0, height
    crop_left, crop_right = 0, width

    if top:
        while crop_top < crop_bottom and _edge_is_black(arr[crop_top], threshold, dark_ratio):
            crop_top += 1
    if bottom:
        while crop_bottom > crop_top and _edge_is_black(arr[crop_bottom - 1], threshold, dark_ratio):
            crop_bottom -= 1
    if left:
        while crop_left < crop_right and _edge_is_black(arr[:, crop_left], threshold, dark_ratio):
            crop_left += 1
    if right:
        while crop_right > crop_left and _edge_is_black(arr[:, crop_right - 1], threshold, dark_ratio):
            crop_right -= 1

    if crop_top >= crop_bottom or crop_left >= crop_right:
        return img
    if (crop_top, crop_bottom, crop_left, crop_right) == (0, height, 0, width):
        return img
    return img.crop((crop_left, crop_top, crop_right, crop_bottom))


def split_vertical(
    img: Image.Image,
    parts: int = 3,
    *,
    trim_black: bool = True,
    threshold: int = 30,
    dark_ratio: float = 0.98,
) -> list[Image.Image]:
    width, height = img.size
    step = height // parts
    result = []
    for i in range(parts):
        top = i * step
        bottom = height if i == parts - 1 else (i + 1) * step
        tile = img.crop((0, top, width, bottom))
        if trim_black:
            tile = trim_black_edges(
                tile,
                top=True,
                bottom=True,
                left=True,
                right=True,
                threshold=threshold,
                dark_ratio=dark_ratio,
            )
        result.append(tile)
    return result


def split_horizontal(
    img: Image.Image,
    parts: int = 6,
    *,
    trim_black: bool = True,
    threshold: int = 30,
    dark_ratio: float = 0.98,
) -> list[Image.Image]:
    width, height = img.size
    step = width // parts
    result = []
    for i in range(parts):
        left = i * step
        right = width if i == parts - 1 else (i + 1) * step
        tile = img.crop((left, 0, right, height))
        if trim_black:
            tile = trim_black_edges(
                tile,
                top=True,
                bottom=True,
                left=True,
                right=True,
                threshold=threshold,
                dark_ratio=dark_ratio,
            )
        result.append(tile)
    return result


def process_folder(
    src: Path,
    verbose: bool = False,
    trim_black: bool = True,
    threshold: int = 20,
    dark_ratio: float = 0.95,
) -> tuple[int, int, int]:
    out_dir = src / 'processed'
    out_dir.mkdir(exist_ok=True)

    images = collect_images(src)
    if not images:
        print(f'目录中没有找到图片: {src}')
        return 0, 0, 0

    processed = 0
    skipped = 0
    failed = 0

    for img_path in images:
        try:
            with Image.open(img_path) as img:
                img = img.convert('RGB')
                width, height = img.size

                if height > width:
                    tiles = split_vertical(
                        img, 3,
                        trim_black=trim_black,
                        threshold=threshold,
                        dark_ratio=dark_ratio,
                    )
                    split_desc = '纵向 3 份'
                elif width > height:
                    tiles = split_horizontal(
                        img, 6,
                        trim_black=trim_black,
                        threshold=threshold,
                        dark_ratio=dark_ratio,
                    )
                    split_desc = '横向 6 份'
                else:
                    skipped += 1
                    if verbose:
                        print(f'跳过（正方形）: {img_path.name}')
                    continue

                stem = img_path.stem
                for idx, tile in enumerate(tiles, start=1):
                    save_path = out_dir / f'{stem}_part{idx}.jpg'
                    tile.save(save_path, quality=95)

                processed += 1
                if verbose:
                    print(f'{img_path.name} -> {split_desc} -> {len(tiles)} 张')
                else:
                    print(f'已处理: {img_path.name} ({split_desc})')

        except Exception as exc:
            failed += 1
            print(f'处理失败: {img_path.name} - {exc}')

    return processed, skipped, failed


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='按纵横比分割文件夹内所有图片，结果保存到 processed 子目录',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        'folder',
        type=str,
        nargs='?',
        default=r'E:\Photos\FILMs\2026-春节\118',
        help='待处理图片所在文件夹',
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='显示详细处理信息',
    )
    parser.add_argument(
        '--no-trim-black',
        action='store_true',
        help='禁用切缝黑边裁除',
    )
    parser.add_argument(
        '--black-threshold',
        type=int,
        default=20,
        help='判定黑边的 RGB 上限（0-255）',
    )
    parser.add_argument(
        '--black-ratio',
        type=float,
        default=0.985,
        help='一行/列中暗色像素占比达到此值则视为黑边',
    )
    return parser.parse_args()


def main():
    args = parse_arguments()
    src = Path(args.folder).resolve()

    if not src.is_dir():
        print(f'错误: 目录不存在: {src}')
        raise SystemExit(1)

    print('=' * 60)
    print('图片分割工具')
    print('=' * 60)
    print(f'源目录: {src}')
    print(f'输出目录: {src / "processed"}')
    print(f'黑边裁除: {"关闭" if args.no_trim_black else "开启"}')
    if not args.no_trim_black:
        print(f'黑边阈值: RGB<={args.black_threshold}, 占比>={args.black_ratio:.0%}')
    print('=' * 60)

    processed, skipped, failed = process_folder(
        src,
        verbose=args.verbose,
        trim_black=not args.no_trim_black,
        threshold=args.black_threshold,
        dark_ratio=args.black_ratio,
    )

    print('-' * 60)
    print(f'完成: 处理 {processed} 张, 跳过 {skipped} 张, 失败 {failed} 张')
    print(f'输出位置: {src / "processed"}')


if __name__ == '__main__':
    main()
