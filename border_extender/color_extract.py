from PIL import Image
import numpy as np
from sklearn.cluster import KMeans


def extract_main_colors(image, num_colors=3):
    # 打开图像并转换为RGB模式

    # 缩小图像尺寸
    image = image.resize((256, 256))

    # 将图像转换为numpy数组
    image_np = np.array(image)

    # 将图像数据重塑为二维数组
    pixels = image_np.reshape(-1, 3)

    # 使用KMeans聚类算法提取主要颜色+1 用于筛除不那么重要的主要颜色
    kmeans = KMeans(n_clusters=num_colors+1, max_iter=10000000, n_init=1)
    kmeans.fit(pixels)

    # 获取聚类中心（主要颜色）
    main_colors = kmeans.cluster_centers_.astype(int)
    sort_ind=main_colors.sum(axis=1).argsort()[::-1]
    # np.argsort
    main_colors=main_colors[sort_ind]
    # print(main_colors[:-1])
    


    return main_colors[:-1]


def plot_colors(colors):
    # 创建一个空白图像用于显示颜色
    color_image = np.zeros((20, 200, 3), dtype=int)

    # 计算每个颜色块的宽度
    block_width = color_image.shape[1] // len(colors)

    for i, color in enumerate(colors):
        color_image[:, i * block_width:(i + 1) * block_width] = color
    Image.fromarray(color_image.astype('uint8'))
    return color_image
    # plt.imshow(color_image)
    # plt.axis('off')
    # plt.show()


# 使用示例
if __name__=='__main__':
    image_path = "imgtoprocess/hassel_CF60/1547-09.JPG"
    img=Image.open(image_path).convert('RGB')
    main_colors = extract_main_colors(img, num_colors=4)
    plot_colors(main_colors)

    print("主要颜色:", main_colors)
