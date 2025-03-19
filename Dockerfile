# 二开推荐阅读[如何提高项目构建效率](https://developers.weixin.qq.com/miniprogram/dev/wxcloudrun/src/scene/build/speed.html)
# 选择基础镜像。如需更换，请到[dockerhub官方仓库](https://hub.docker.com/_/python?tab=tags)自行选择后替换。
# 已知alpine镜像与pytorch有兼容性问题会导致构建失败，如需使用pytorch请务必按需更换基础镜像。
FROM ubuntu:20.04

# 容器默认时区为UTC，如需使用上海时间请启用以下时区设置命令

# 使用 HTTPS 协议访问容器云调用证书安装


RUN sed -i 's/archive.ubuntu.com/mirrors.aliyun.com/g' /etc/apt/sources.list \
&& sed -i 's/security.ubuntu.com/mirrors.aliyun.com/g' /etc/apt/sources.list 

RUN apt-get update && apt-get install -y ca-certificates

RUN apt-get install -y python3 python3-pip 

# 拷贝当前项目到/app目录下（.dockerignore中文件除外）
COPY . /app

# 设定当前的工作目录
WORKDIR /app

# 安装gcc新版本
RUN apt-get install -y make automake gcc g++ subversion python3-dev
RUN apt-get install -y libc-dev
RUN apt-get install -y build-essential

# 安装依赖到指定的/install文件夹
# 选用国内镜像源以提高下载速度
# 设置pip阿里镜像
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple \
&& pip config set global.trusted-host mirrors.aliyun.com \
&& pip install --upgrade pip

RUN pip install --user -r requirements.txt

# 暴露端口。
# 此处端口必须与「服务设置」-「流水线」以及「手动上传代码包」部署时填写的端口一致，否则会部署失败。
EXPOSE 80

# 执行启动命令
# 写多行独立的CMD命令是错误写法！只有最后一行CMD命令会被执行，之前的都会被忽略，导致业务报错。
CMD ["python3", "run.py", "0.0.0.0", "80"]

