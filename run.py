# 创建应用实例
import sys
from wxcloudrun import app

# # local test
# if len(sys.argv) < 3:
#     sys.argv = [sys.argv[0], '0.0.0.0', '5001']


# 启动Flask Web服务
if __name__ == '__main__':
    app.run(host='0.0.0.0', port='5001')
