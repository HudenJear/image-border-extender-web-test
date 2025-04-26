from datetime import datetime
from flask import render_template, request, send_file, url_for
from run import app
from wxcloudrun.dao import delete_counterbyid, query_counterbyid, insert_counter, update_counterbyid
from wxcloudrun.model import Counters
from wxcloudrun.response import make_succ_empty_response, make_succ_response, make_err_response
from PIL import Image,ImageDraw,ImageFont,ImageOps
from PIL.ExifTags import TAGS
import piexif
import  os,glob,io
import numpy as np
import json
from .add_bd import rotate_image_90_no_crop, process_one_image
import logging
import requests
from io import BytesIO
from PIL import Image
from .add_bd import rotate_image_90_no_crop  # 假设rotate_image_90_no_crop是用于旋转图片的函数

import uuid
from datetime import datetime

# 微信云开发认证信息
app_id = 'your_app_id'
app_secret = 'your_app_secret'
env_id = 'your_env_id'  # 例如 'test-123456'

# 腾讯云认证信息
secret_id = 'your_secret_id'
secret_key = 'your_secret_key'
region = 'your_region'  # 例如 'ap-guangzhou'
bucket_name = 'your_bucket_name-123456789'  # 例如 'example-123456789'

logging.basicConfig(
    format='[%(asctime)s] %(message)s',
    level=logging.INFO,
    handlers=[logging.StreamHandler()]  # 输出到控制台
)

# 确保 tempimage 目录存在
temp_image_dir = 'temp_images'

# @app.route('/static/<path:filename>')
# def static_files(filename):
#     """
#     :return: 返回index页面

#     """
#     return render_template('index.html')

@app.route('/debug_static', methods=['GET'])
def debug_static():
    static_path = app.static_folder
    return make_succ_response(static_path)
    # return f"Static folder: {static_path}"


@app.route('/')
def index():
    """
    :return: 返回index页面
    """
    return render_template('index.html')


@app.route('/api/count', methods=['POST'])
def count():
    """
    :return:计数结果/清除结果
    """

    # 获取请求体参数
    params = request.get_json()

    # 检查action参数
    if 'action' not in params:
        return make_err_response('缺少action参数')

    # 按照不同的action的值，进行不同的操作
    action = params['action']

    # 执行自增操作
    if action == 'inc':
        counter = query_counterbyid(1)
        if counter is None:
            counter = Counters()
            counter.id = 1
            counter.count = 1
            counter.created_at = datetime.now()
            counter.updated_at = datetime.now()
            insert_counter(counter)
        else:
            counter.id = 1
            counter.count += 1
            counter.updated_at = datetime.now()
            update_counterbyid(counter)
        return make_succ_response(counter.count)

    # 执行清0操作
    elif action == 'clear':
        delete_counterbyid(1)
        return make_succ_empty_response()

    # action参数错误
    else:
        return make_err_response('action参数错误')


@app.route('/api/count', methods=['GET'])
def get_count():
    """
    :return: 计数的值
    """
    counter = Counters.query.filter(Counters.id == 1).first()
    return make_succ_response(0) if counter is None else make_succ_response(counter.count)

@app.route('/api/factorial', methods=['POST'])
def factorial():
    """
    计算阶乘的API
    :return: 阶乘计算结果
    """
    # 获取请求体参数
    params = request.get_json()

    # 检查number参数
    if 'number' not in params:
        return make_err_response('缺少number参数')

    number = params['number']
    
    # 检查参数类型和范围
    if not isinstance(number, int):
        return make_err_response('参数必须是整数')
    if number < 0:
        return make_err_response('参数不能为负数')
    if number > 10:  # 设置一个上限以防止计算过大的数
        return make_err_response('参数过大')

    # 计算阶乘
    result = 1
    for i in range(1, number + 1+1):
        result *= i

    return make_succ_response(result)




@app.route('/api/image_process', methods=['POST'])
def image_process():
    """
    处理一张图片
    :return: 处理后的图片URL
    """
    # 获取请求体参数
    os.makedirs('static/' + temp_image_dir, exist_ok=True)

    data_param = request.get_json()
    logging.log(logging.INFO, data_param)
    # 检查img参数
    if 'image_file' not in data_param:
        return make_err_response('没有收到图片URL')
    else:
        image_url = data_param['image_file']
        try:
            # 下载图片
            response = requests.get(image_url)
            response.raise_for_status()
            img = Image.open(BytesIO(response.content))

            # 处理图片（旋转90度）
            img = rotate_image_90_no_crop(img)

            # 生成唯一的文件名
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            random_code = uuid.uuid4().hex[:8]  # 取前8位随机码
            unique_filename = f"{timestamp}_{random_code}.jpg"
            temp_image_path = os.path.join('static', temp_image_dir, unique_filename)

            # 保存处理后的图片到本地临时目录
            img.save(temp_image_path)

            # 构建图片的URL
            processed_image_url = url_for('static', filename=os.path.join(temp_image_dir, unique_filename))

            # 返回图片URL
            return make_succ_response({
                'image_url': processed_image_url,
                'res_info': {
                    'info': '图片处理成功',
                }
            })
        

        except Exception as e:
            logging.log(logging.ERROR, f'图片处理失败: {e}')
            return make_err_response(f'图片处理失败: {e}')
