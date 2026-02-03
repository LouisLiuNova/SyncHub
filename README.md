# SyncHub - 局域网跨设备协作中心

SyncHub 是一个轻量级、自托管的剪贴板和文件共享工具。专为需要在多台机器（Windows, Mac, Linux）之间频繁共享文本和文件的开发者设计。

> [!IMPORTANT]
> 请勿在公网环境直接暴露端口，建议配合 Nginx 和 HTTPS 使用.

## ✨ 功能特性

- **📋 文本剪贴板**：带标签和时间戳的历史记录，一键复制。
- **📁 文件共享**：拖拽上传，实时列表更新，高速下载。
- **🔐 用户认证**：私有化部署，安全可靠。
- **⚡ 实时同步**：基于 WebSocket，多端操作毫秒级同步。
- **🐳 Docker 部署**：一键启动，数据持久化。

## 🛠️ 技术栈

- **Backend**: Python FastAPI, SQLite, SQLAlchemy
- **Frontend**: HTML5, Tailwind CSS, Alpine.js
- **Deployment**: Docker Compose

## 🚀 快速开始

### 前置要求
- 安装 [Docker](https://www.docker.com/) 和 [Docker Compose](https://docs.docker.com/compose/)。

### 部署步骤

1. **克隆或下载代码**
   确保目录结构如下：
   ```text
   synchub/
   ├── app/
   │   ├── __init__.py
   │   ├── main.py
   │   ├── auth.py
   │   ├── models.py
   │   ├── database.py
   │   ├── templates/index.html
   │   └── static/
   ├── Dockerfile
   ├── docker-compose.yml
   └── requirements.txt
    ```
2. 启动服务
    在项目根目录下运行：
    ```shell
    docker-compose up -d --build
    ```
3. 访问应用
    打开浏览器访问：`http://localhost:8000`.如果是局域网其他电脑访问，请使用服务器 IP，例如 `http://192.168.1.100:8000`

## 使用说明
1. 注册账户：首次进入点击登录框下方的“注册”按钮。
2. 共享文本：在“文本剪贴板”页签输入内容，支持添加标签（如：代码、链接）。
3. 共享文件：切换到“文件共享”，拖拽文件到上传区域。