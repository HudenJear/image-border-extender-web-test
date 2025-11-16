import requests
from PIL import Image
import io
import json

hostip='http://192.168.50.195:5001/'
net_test=False
# net_test=True



def test_image_upload():
    # API地址（假设Flask运行在本地8000端口）
    url = 'https://1339895887-1a3bm8xhpt.ap-guangzhou.tencentscf.com/product_service/api/image_upload' if net_test else hostip+'/api/image_upload'
    print(f"Testing api on {url}")
    
    # 准备图片文件
    image_path = r'./P1032386.jpg'  
    
    # 准备文件和参数
    with open(image_path, 'rb') as f:
      # image_data = f.read()
      files = {
          'image': ('test.jpg', f, 'image/jpeg'),
      }
      data = {
            # must be strings for form fields
            'infor_params': json.dumps({
                'use_info_option': True,         # important
                'text': ' \n\n ',
                'logo_file': 'logos/hassel.jpg',
                'suppli_info': ''
            }),
            'control_params': json.dumps({
                'use_control_option': True,      # important
                'max_length': 1200,
                'add_black_border': True,
                'extend_to_square': False,
                'filter': 'vivid'          # e.g. black_white | vivid | retro | film | none
            }),
            }
      
      # 发送请求
      response = requests.post(url, files=files,data=data)
      
      print("Status Code:", response.status_code)
      
      # 如果是图片响应
      if response.headers.get('content-type', '').startswith('image/'):
          # 保存返回的图片
          with open('processed_image.jpg', 'wb') as f:
              f.write(response.content)
          # print(response.content,"图片已保存为 processed_image.jpg")
          
          # 可以用PIL打开查看图片信息
          img = Image.open(io.BytesIO(response.content))
          print("图片大小:", img.size)
          print("图片格式:", img.format)
      elif  response.status_code == 200 and response.json().get('code') == 0:
          result = response.json()
          # print(result)
          print("处理后的图片URL:", result['data']['image_url'])
          print("处理信息:", result['data']['res_info'])
          image_response = requests.get(result['data']['image_url'])
          with open('downloaded_image.jpg', 'wb') as f:
              # print(image_response.content)
              f.write(image_response.content)
          print("图片已保存为 downloaded_image.jpg")
      else:
          # 如果是错误响应
          try:
              print("Response:", response.json())
          except:
              print("Raw Response:", response.text)

def test_numbers():
    url = hostip+'/api/factorial' if not net_test else 'https://1339895887-1a3bm8xhpt.ap-guangzhou.tencentscf.com/product_service/api/factorial'
    print(f"Testing api on {url}")
    headers = {
        'content-type': 'application/json'
    }

    body = {
        'number': 10
    }
    response = requests.post(url, json=body, headers=headers)
    print(response.json())

def test_static():
    url = hostip+'/api/debug_static' if not net_test else 'https://1339895887-1a3bm8xhpt.ap-guangzhou.tencentscf.com/product_service/api/debug_static'
    print(f"Testing api on {url}")

    response = requests.get(url)
    print(response.text)


if __name__ == "__main__":
    test_numbers()
    test_image_upload()
    test_static()
    
