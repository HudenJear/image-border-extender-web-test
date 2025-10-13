from datetime import datetime
from flask import render_template, request, send_file, url_for, after_this_request
from wxcloudrun.dao import delete_counterbyid, query_counterbyid, insert_counter, update_counterbyid
from wxcloudrun.model import Counters
from wxcloudrun.response import make_succ_empty_response, make_succ_response, make_err_response
from PIL import Image,ImageDraw,ImageFont,ImageOps
from PIL.ExifTags import TAGS
import piexif
import  os,glob,io
import numpy as np
import json
import uuid
from .add_bd import rotate_image_90_no_crop, process_one_image, apply_filter, AVAILABLE_FORMAT_KEYS as AVAILABLE_FORMAT_KEYS
import logging
from run import app

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

@app.route('/api/debug_static')
def debug_static():
    static_path = app.static_folder
    return f"Static folder: {static_path}"


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


@app.route('/api/image_upload', methods=['POST'])
def image_upload():
    """
    上传一张图片
    :return: 图片url
    """
    # 获取请求体参数
    # 确保 tempimage 目录存在
    # os.makedirs('wxcloudrun/static/'+temp_image_dir, exist_ok=True)
    os.makedirs(os.path.join(app.static_folder, temp_image_dir), exist_ok=True)

    # params = request.get_json()
    logging.info(request.files)
    logging.info(request.form)
    # control_
    #     infor_
    # print(request)
    files = request.files
    # 检查img参数
    if 'image' not in files:
        return make_err_response('没有收到图片')
    elif files['image'].filename == '':
            return make_err_response('没有收到图片')
    else:
        img_file = files['image']
        # logging.info(img_file.stream)
        try:
            # Log original upload size (bytes)
            original_size_bytes = getattr(img_file, 'content_length', None)
            if not original_size_bytes:
                try:
                    cur_pos = img_file.stream.tell()
                    img_file.stream.seek(0, os.SEEK_END)
                    original_size_bytes = img_file.stream.tell()
                    img_file.stream.seek(cur_pos)
                except Exception:
                    original_size_bytes = None
            logging.info(f"Original upload size: {original_size_bytes} bytes")

            img_file.stream.seek(0)
            img = Image.open(img_file.stream).convert('RGB')
        except Exception as e:
            logging.info(e)
            return make_err_response(f'图片加载失败: {e}')
        try:
            #set default control parameters
            add_black_border = True
            max_length = 2400
            extend_to_square=False
            # default filter key
            filter_key = 'none'
            # default filter strength
            filter_strength = 0.5
            # default format key
            format_key = 'basic1'
            if 'control_params' in request.form:
                params = json.loads(request.form.get('control_params', '{}'))
                use_control_option=params.get('use_control_option') if params.get('use_control_option') else False
                if use_control_option:
                  logging.info('收到控制参数，使用控制参数覆盖默认设定')
                  add_black_border = params.get('add_black_border') if params.get('add_black_border') else False
                  max_length = params.get('max_length') if params.get('max_length') else 2400
                  extend_to_square=params.get('extend_to_square') if params.get('extend_to_square') else False
                  # parse filter key from control params
                  filter_key = str(params.get('filter', 'none')).strip().lower()
                  # parse filter strength from control params, default 0.5
                  try:
                      fs = float(params.get('filter_strength', 0.5))
                  except Exception:
                      fs = 0.5
                  # clamp to [0,1]
                  filter_strength = max(0.0, min(1.0, fs))
                  # parse format key from control params
                  fmt = params.get('format')
                  if isinstance(fmt, str):
                      candidate = fmt.strip()
                      if candidate in AVAILABLE_FORMAT_KEYS:
                          format_key = candidate
                else:
                  logging.info('不使用控制参数')
            else:
                logging.info('未收到控制参数，不使用控制参数')

            #set default information
            text=' \n\n '
            logo_file='logos/hassel.jpg'
            suppli_info=' '
            if 'infor_params' in request.form:
              params = json.loads(request.form.get('infor_params', '{}'))
              use_info_option=params.get('use_info_option') if params.get('use_info_option') else False
              if use_info_option:
                res_info='收到处理选项,开始默认处理模式'
                logging.info(res_info)
                suppli_info = params.get('suppli_info') if params.get('suppli_info') else ' '
                text = params.get('text') if params.get('text') else ' \n\n '
                logo_file = params.get('logo_file') if params.get('logo_file') else 'logos/hassel.jpg'
              # img=process_one_image(img,text,logo_file,suppli_info,max_length,add_black_border)
              else:
                  res_info='不使用信息参数'
                  logging.info(res_info)
                  text=''
                  logo_file=''
                  suppli_info=''

            else:
              res_info='没有收到处理选项,使用EXIF信息overwrite识别结果'
              logging.info(res_info)
              text=''
              logo_file=''
              suppli_info=''
              
        except Exception as e:
            logging.info(e)

            return make_err_response(f'信息处理失败: {e}')
        # apply filter
        try:
            img=apply_filter(img,filter_key, strength=filter_strength)
            logging.info(f'apply filter: {filter_key} successful.')
        except Exception as e:
          logging.info(f'apply filter: {filter_key} failed: {e}')
        # apply border and text
        try:
            img=process_one_image(img,text,logo_file,suppli_info,format=format_key,max_length=max_length,add_black_border=add_black_border,square=extend_to_square)
            # 微信小程序无法接收二进制文件流，这是因为uploadfile和request.files之间的区别导致的，这个问题时微信自己的api限制，并不是本程序的问题
            # # 返回处理后的图片(图片流)
        except Exception as e:
          return make_err_response(f'图片处理失败: {e}')
        
        try:
            # 生成唯一的文件名
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            random_code = uuid.uuid4().hex[:8]
            filename = f'processed_{timestamp}_{random_code}.jpg'
            filepath = os.path.join(app.static_folder, temp_image_dir, filename)
            img.save(filepath, 'JPEG', quality=80)
            image_url = url_for('static', filename=f"{temp_image_dir}/{filename}", _external=True)
            

            return make_succ_response({
            'image_url': image_url,
            'res_info': res_info
            })

        except Exception as e:
          return make_err_response(f'图片保存失败: {e}')

@app.route('/api/image_download', methods=['POST'])
def image_download():
    """
    下载处理好的图片
    :return: 图片二进制流
    """
    # 获取请求体参数
    params = request.get_json()

    # 检查img_url参数
    if 'img_url' not in params:
        return make_err_response('缺少img_url参数')

    img_url = params['img_url']

    # Extract the filename from the URL (Assuming the URL ends with '/filename.jpg')
    filename = img_url.split('/')[-1]

    # Construct the local file path
    filepath = os.path.join(app.static_folder, temp_image_dir, filename)
    logging.info(filepath)

    # Check if the file exists
    if not os.path.isfile(filepath):
        return make_err_response('文件不存在')

    # @after_this_request
    # def remove_file(response):
    #     try:
    #         os.remove(filepath)
    #         logging.info(f"Deleted file after download: {filepath}")
    #     except Exception as e:
    #         logging.error(f"删除文件失败: {e}")
    #     return response

    # Send the file as a binary stream and trigger deletion after response
    return send_file(filepath, mimetype='image/jpeg', as_attachment=True, download_name=filename)

        

    
