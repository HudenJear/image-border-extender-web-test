from datetime import datetime
from flask import render_template, request, send_file
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
    for i in range(1, number + 1):
        result *= i

    return make_succ_response(result)


@app.route('/api/image_process', methods=['POST'])
def image_process():
    """
    处理一张图片
    :return: 处理后的图片
    """
    # 获取请求体参数

    # params = request.get_json()
    files = request.files
    # 检查img参数
    if 'image' not in files:
        return make_err_response('没有收到图片')
    elif files['image'].filename == '':
            return make_err_response('没有收到图片')
    else:
        img_file = files['image']
        try:
            img = Image.open(img_file.stream).convert('RGB')
            if 'control_params' in files:
                params = json.loads(request.files['control_params'].read())
                add_black_border = params.get('add_black_border') if params.get('add_black_border') else False
                max_length = params.get('max_length') if params.get('max_length') else 2400
            else:
                add_black_border = True
                max_length = 2400

            if 'infor_params' in files:

              res_info='收到处理选项,开始默认处理模式'
              params = json.loads(request.files['infor_params'].read())
              
              suppli_info = params.get('suppli_info') if params.get('suppli_info') else ' '
              
              text = params.get('text') if params.get('text') else ' \n\n '
              logo_file = params.get('logo_file') if params.get('logo_file') else 'logos/hassel.jpg'
              img=process_one_image(img,text,logo_file,suppli_info,max_length,add_black_border)

            else:
              res_info='没有收到处理选项,使用EXIF信息overwrite识别结果'
              img=process_one_image(img,text='',logo_file='',max_length=max_length,add_black_border=add_black_border)


            img_io = io.BytesIO()
            img.save(img_io, 'JPEG', quality=80)
            img_io.seek(0)
            return send_file(img_io,mimetype='image/jpeg',as_attachment=True,download_name='processed.jpg')

            # return make_succ_response(image_info)
        except Exception as e:
          return make_err_response(f'图片处理失败: {e}')
        

    
