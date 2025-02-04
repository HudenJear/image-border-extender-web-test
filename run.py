# 创建应用实例
import sys
from wxcloudrun import app

# local test
# if len(sys.argv) < 3:
#     sys.argv = [sys.argv[0], '127.0.0.1', '8000']


# 启动Flask Web服务
if __name__ == '__main__':
    app.run(host=sys.argv[1], port=sys.argv[2])
