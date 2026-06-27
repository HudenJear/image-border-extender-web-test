# image-border-extender-web

![Python](https://img.shields.io/badge/python-3.10+-green)

基于 Flask 的图片边框扩展 Web 应用，支持在线上传处理与本地批量处理。项目采用 [uv](https://docs.astral.sh/uv/) 管理虚拟环境与依赖，部署方式为**服务器本地目录**运行，不依赖 Docker。

## 环境要求

- Python 3.10 及以上（推荐 3.12，见 `.python-version`）
- [uv](https://docs.astral.sh/uv/getting-started/installation/) 包管理器

## 安装

### 安装 uv

```powershell
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# 或使用 pip
pip install uv
```

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 安装项目依赖

将代码放到服务器目标目录后，在项目根目录执行：

```bash
uv sync
```

该命令会根据 `.python-version` 创建 `.venv`，并按 `uv.lock` 安装全部依赖。

## 运行

```bash
# 启动 Flask Web 服务（默认 0.0.0.0:5001）
uv run python run.py

# 本地批量图片处理
uv run python local2run.py --src <源目录> --tgt <输出目录>

# 生成滤镜/格式缩略图
uv run python generate_thumbnails.py
```

也可手动激活虚拟环境：

```powershell
# Windows
.\.venv\Scripts\Activate.ps1
python run.py
```

```bash
# macOS / Linux
source .venv/bin/activate
python run.py
```

## 服务器部署

1. 将项目目录同步到服务器（git clone、rsync 等）
2. 在服务器上安装 Python 3.10+ 与 uv
3. 进入项目目录执行 `uv sync`
4. 按需配置环境变量（见下方）
5. 使用进程管理器（systemd、supervisor 等）长期运行：

```bash
uv run python run.py
```

### 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `MYSQL_USERNAME` | 数据库用户名 | `root` |
| `MYSQL_PASSWORD` | 数据库密码 | `root` |
| `MYSQL_ADDRESS` | 数据库地址 | `127.0.0.1:3306` |

若使用 MySQL 相关功能，请确保数据库可访问并已创建对应表结构。

## 依赖管理

```bash
uv add <package>      # 添加依赖
uv remove <package>   # 移除依赖
uv lock               # 更新 lock 文件
uv sync               # 同步到当前环境
```

`pyproject.toml` 为依赖声明的唯一来源，`uv.lock` 锁定完整解析结果。

## 目录结构

```
.
├── pyproject.toml          项目依赖声明
├── uv.lock                 锁定的依赖解析结果
├── .python-version         Python 版本约定
├── config.py               项目配置（数据库等）
├── run.py                  Flask 服务入口
├── local2run.py            本地批量图片处理脚本
├── generate_thumbnails.py  缩略图生成工具
└── border_extender/          应用主包
    ├── __init__.py         Flask 应用初始化
    ├── views.py            路由与业务逻辑
    ├── add_bd.py           边框/滤镜处理核心
    ├── dao.py              数据库访问
    ├── model.py            数据模型
    ├── response.py         响应结构
    ├── effects/            滤镜与格式处理
    └── templates/          前端页面
```

## API 示例

服务默认监听 `http://0.0.0.0:5001`。

### `GET /api/count`

获取当前计数。

```bash
curl http://127.0.0.1:5001/api/count
```

### `POST /api/count`

更新计数（自增或清零）。

```bash
curl -X POST -H 'content-type: application/json' \
  -d '{"action": "inc"}' \
  http://127.0.0.1:5001/api/count
```

## License

[MIT](./LICENSE)
