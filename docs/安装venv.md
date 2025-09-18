1.95.67.233:22

/zzsn/AICoreDirector









要解决 `uv venv .venv` 解压 Python 安装包失败的问题，同时启用镜像加速下载，请按照以下完整步骤操作：

### 1. 清除损坏的缓存（关键第一步）
```bash
# 清除所有 UV 缓存
uv clean

# 手动删除残留文件
rm -rf /root/.local/share/uv/python/cpython-3.13.6-*
```



第一次：

### 2. 配置镜像源并设置环境变量

```bash
# 设置镜像源环境变量
export UV_PYTHON_DOWNLOAD_MIRROR="https://mirrors.aliyun.com/indygreg/python-build-standalone/20250807/"

# 或者使用清华镜像源
export UV_PYTHON_DOWNLOAD_MIRROR="https://mirrors.tuna.tsinghua.edu.cn/indygreg/python-build-standalone/20250807/"

# 启用 UV 调试模式
export RUST_LOG=debug
```

### 3. 创建虚拟环境（自动使用镜像）
```bash
uv venv .venv \
    --python 3.13.6 \
    --cache-dir /tmp/uv-cache 2>&1 | tee uv-install.log
```

### 4. 手动镜像方案（如果自动镜像失败）
```bash
# 手动下载安装包
MIRROR="https://mirrors.tuna.tsinghua.edu.cn/indygreg/python-build-standalone/20250807"
FILENAME="cpython-3.13.6-20250807-x86_64-unknown-linux-gnu-install_only_stripped.tar.gz"

wget "${MIRROR}/${FILENAME}" -P /root/.local/share/uv/python/

# 验证文件完整性
echo "Expected SHA256: $(curl -sL ${MIRROR}/SHASUMS256.txt | grep ${FILENAME})"
sha256sum "/root/.local/share/uv/python/${FILENAME}"

# 手动创建环境
uv venv .venv --python 3.13.6
```

### 5. 使用本地 HTTP 服务器（局域网传输）
```bash
# 在另一台机器启动服务（含安装包）
python3 -m http.server 8000

# 在目标机器执行
export UV_PYTHON_DOWNLOAD_MIRROR="http://<local_ip>:8000/"
uv venv .venv
```

### 6. 永久配置镜像源
```bash
# 创建 UV 配置文件
mkdir -p /etc/uv/
cat << EOF > /etc/uv/config.toml
[install]
download-mirror = "https://mirrors.aliyun.com/indygreg/python-build-standalone/20250807/"

[upgrade]
download-mirror = "https://mirrors.aliyun.com/indygreg/python-build-standalone/20250807/"
EOF

# 设置环境变量指向配置
export UV_CONFIG_FILE=/etc/uv/config.toml
```

### 7. 验证安装成功
```bash
source .venv/bin/activate
python -c "import sys; print(f'Python {sys.version}')"
uv pip list
```

### 备选方案：使用系统 Python
```bash
# 查找可用系统 Python
which python3.13 || which python3.12 || which python3

# 使用系统解释器创建环境
uv venv --python $(which python3.13) .venv
```

### 故障排查命令：
```bash
# 检查磁盘空间
df -h /root

# 检查文件权限
ls -la /root/.local/share/uv/python/

# 查看解压错误详情
grep -A 10 'failed to unpack' uv-install.log

# 测试压缩包完整性
tar -tzvf /root/.local/share/uv/python/cpython-3.13.6-*.tar.gz | head
```

### 国内推荐镜像源列表：
| 镜像名称 | URL                                                          |
| -------- | ------------------------------------------------------------ |
| 阿里云   | `https://mirrors.aliyun.com/indygreg/python-build-standalone/20250807/` |
| 清华     | `https://mirrors.tuna.tsinghua.edu.cn/indygreg/python-build-standalone/20250807/` |
| 华为云   | `https://mirrors.huaweicloud.com/indygreg/python-build-standalone/20250807/` |
| 腾讯云   | `https://mirrors.cloud.tencent.com/indygreg/python-build-standalone/20250807/` |

> 💡 **专业提示**：如果持续失败，尝试使用更稳定的 Python 版本：
> ```bash
> uv venv --python 3.12.4 .venv
> ```