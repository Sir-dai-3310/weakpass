# 故障排查指南

## 目录

- [安装问题](#安装问题)
- [运行问题](#运行问题)
- [性能问题](#性能问题)
- [验证问题](#验证问题)
- [常见错误](#常见错误)
- [获取帮助](#获取帮助)

---

## 安装问题

### 问题1: pip安装失败

**症状:**
```
ERROR: Could not find a version that satisfies the requirement xxx
```

**解决方案:**

1. 升级pip:
```bash
python -m pip install --upgrade pip
```

2. 使用国内镜像源:
```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

3. 单独安装失败的包:
```bash
pip install <package-name> -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 问题2: 依赖冲突

**症状:**
```
ERROR: pip's dependency resolver does not currently take into account...
```

**解决方案:**

1. 创建虚拟环境:
```bash
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac
```

2. 重新安装依赖:
```bash
pip install -r requirements.txt --force-reinstall
```

### 问题3: Tesseract未安装

**症状:**
```
[!] 警告: pytesseract未安装，OCR功能将不可用
```

**解决方案:**

1. 下载Tesseract:
   - Windows: https://github.com/UB-Mannheim/tesseract/wiki
   - Linux: `sudo apt-get install tesseract-ocr`
   - Mac: `brew install tesseract`

2. 配置环境变量:
   - Windows: 添加安装路径到PATH
   - Linux/Mac: 通常自动配置

3. 验证安装:
```bash
tesseract --version
```

---

## 运行问题

### 问题1: 导入模块失败

**症状:**
```
ModuleNotFoundError: No module named 'core.xxx'
```

**解决方案:**

1. 检查Python路径:
```python
import sys
print(sys.path)
```

2. 确保在项目根目录运行:
```bash
cd weakpass-弱口令验证工具
python launcher.py
```

3. 检查`__init__.py`文件:
```bash
ls core/__init__.py
```

### 问题2: 编码错误

**症状:**
```
UnicodeDecodeError: 'utf-8' codec can't decode byte...
```

**解决方案:**

1. 检查文件编码:
```python
from core.enhanced_batch_importer import EnhancedBatchImporter

importer = EnhancedBatchImporter()
encoding = importer.detect_encoding("yourfile.csv")
print(f"检测到编码: {encoding}")
```

2. 转换文件编码:
```bash
# 使用iconv (Linux/Mac)
iconv -f GBK -t UTF-8 input.csv > output.csv

# 使用记事本另存为UTF-8 (Windows)
```

3. 在导入时指定编码:
```python
result = importer.import_csv("file.csv", encoding="gbk")
```

### 问题3: 权限错误

**症状:**
```
PermissionError: [Errno 13] Permission denied: 'xxx'
```

**解决方案:**

1. 检查文件权限:
```bash
# Linux/Mac
chmod +r file.csv

# Windows
# 右键 -> 属性 -> 安全 -> 编辑权限
```

2. 使用管理员权限运行:
```bash
# Windows
# 右键 -> 以管理员身份运行

# Linux/Mac
sudo python launcher.py
```

---

## 性能问题

### 问题1: 批量验证速度慢

**症状:**
- 验证100个目标需要很长时间
- CPU使用率低

**解决方案:**

1. 增加并发数:
```python
from core.async_verifier import AsyncLoginVerifier

verifier = AsyncLoginVerifier(max_concurrent=10)  # 默认是5
```

2. 减少请求延迟:
```python
results = await verifier.verify_batch(targets, delay=0.1)  # 默认是0.5秒
```

3. 使用异步验证器:
```python
# 使用 AsyncLoginVerifier 而不是同步的 LoginVerifier
from core.async_verifier import verify_batch_async
```

### 问题2: 内存占用过高

**症状:**
- 内存使用持续增长
- 程序崩溃

**解决方案:**

1. 分批处理:
```python
BATCH_SIZE = 50

for i in range(0, len(targets), BATCH_SIZE):
    batch = targets[i:i+BATCH_SIZE]
    results = await verifier.verify_batch(batch)
    # 保存结果
    # 清理内存
    del results
```

2. 定期保存进度:
```python
if len(session.completed_indices) % 50 == 0:
    manager.save_session(session)
```

### 问题3: 网络超时

**症状:**
```
TimeoutError: timeout
```

**解决方案:**

1. 增加超时时间:
```python
from core.config_manager import get_config_manager

config = get_config_manager()
config.config.network.timeout = 30  # 默认是10秒
```

2. 使用代理:
```python
from core.proxy_support import ProxyManager

proxy_manager = ProxyManager()
proxy_manager.add_proxy("proxy.example.com", 8080)
proxy_manager.enable_proxy()
```

---

## 验证问题

### 问题1: 登录状态判断不准确

**症状:**
- 明明失败却显示成功
- 明明成功却显示失败

**解决方案:**

1. 检查系统配置:
```python
from core.config_manager import get_config_manager

config = get_config_manager()
sys_config = config.get_system_config(url)
print(f"系统配置: {sys_config}")
```

2. 调整成功/失败指标:
```python
# 在 config.json 中修改
{
  "response": {
    "success_indicators": [
      {"type": "status_code", "value": 200},
      {"type": "body_contains", "value": "欢迎"}
    ],
    "failure_indicators": [
      {"type": "body_contains", "value": "错误"}
    ]
  }
}
```

3. 查看详细响应:
```python
result = await verifier.verify_login(target)
print(f"详情: {result.details}")
```

### 问题2: 验证码识别失败

**症状:**
- 验证码识别为空
- 识别结果不正确

**解决方案:**

1. 检查Tesseract安装:
```bash
tesseract --version
```

2. 测试识别功能:
```python
from core.captcha_recognizer import CaptchaRecognizer

recognizer = CaptchaRecognizer()
with open("captcha.png", "rb") as f:
    result = recognizer.recognize(f.read())
print(f"识别结果: {result.text} - {result.confidence}")
```

3. 尝试不同的识别引擎:
```python
# ddddocr (需要Python 3.10或更低)
# easyocr (推荐)
```

### 问题3: 字段识别错误

**症状:**
- 导入CSV时列名识别错误
- 数据错位

**解决方案:**

1. 检查CSV格式:
```python
import csv

with open("file.csv", 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    print(f"列名: {reader.fieldnames}")
```

2. 使用标准列名:
```
URL, 用户名, 密码
```

3. 手动指定列映射:
```python
# 在导入代码中添加
url_field = "url"  # 或其他标准名称
username_field = "username"
password_field = "password"
```

---

## 常见错误

### 错误1: AttributeError: 'NoneType' object has no attribute 'xxx'

**原因:** 对象为None

**解决方案:**
```python
# 添加空值检查
if result is not None:
    print(result.success)
else:
    print("结果为空")
```

### 错误2: ConnectionError: [Errno 11001] getaddrinfo failed

**原因:** DNS解析失败

**解决方案:**
1. 检查网络连接
2. 检查URL是否正确
3. 尝试使用IP地址

### 错误3: SSL: CERTIFICATE_VERIFY_FAILED

**原因:** SSL证书验证失败

**解决方案:**
```python
# 在配置中禁用SSL验证
from core.config_manager import get_config_manager

config = get_config_manager()
config.config.network.verify_ssl = False
```

### 错误4: RuntimeError: This event loop is already running

**原因:** 在已有事件循环中运行异步代码

**解决方案:**
```python
import nest_asyncio

nest_asyncio.apply()

# 或使用create_task
import asyncio

loop = asyncio.get_event_loop()
task = loop.create_task(verify_batch_async(targets))
```

---

## 调试技巧

### 1. 启用详细日志

```python
import logging

logging.basicConfig(level=logging.DEBUG)
```

### 2. 打印请求/响应

```python
# 在 async_verifier.py 中添加
async def verify_login(self, target: TargetInfo) -> LoginResult:
    # ...
    print(f"请求URL: {full_url}")
    print(f"请求体: {body}")
    print(f"响应状态: {response.status}")
    print(f"响应内容: {content[:200]}")
```

### 3. 使用断点调试

```python
# 在代码中添加断点
import pdb; pdb.set_trace()

# 或使用IDE的调试功能
```

### 4. 保存原始响应

```python
# 在配置中启用
{
  "advanced": {
    "save_raw_response": true
  }
}
```

---

## 获取帮助

### 1. 查看日志

```bash
# 查看日志文件
ls logs/

# 查看最新日志
tail -f logs/app_*.log
```

### 2. 运行测试

```bash
# 运行测试套件
pytest tests/ -v

# 运行特定测试
pytest tests/test_async_verifier.py::test_verify_single -v
```

### 3. 查看文档

- [API参考](API_REFERENCE.md)
- [开发者指南](DEVELOPER_GUIDE.md)
- [使用说明](../使用说明.md)

### 4. 提交问题

如果问题仍未解决，请：

1. 收集以下信息:
   - Python版本 (`python --version`)
   - 操作系统版本
   - 错误信息
   - 重现步骤

2. 在GitHub上提交Issue:
   - 描述问题
   - 提供日志文件
   - 提供最小复现代码

---

## 常用命令

### 检查环境

```bash
# Python版本
python --version

# 已安装包
pip list

# 依赖树
pip install pipdeptree
pipdeptree
```

### 清理缓存

```bash
# 清理pip缓存
pip cache purge

# 清理Python缓存
find . -type d -name __pycache__ -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
```

### 重置配置

```bash
# 备份配置
cp config.json config.json.backup

# 重置为默认配置
cp config_template.json config.json
```

---

## 性能优化建议

### 1. 使用异步验证器

```python
# 好的做法
from core.async_verifier import verify_batch_async
results = await verify_batch_async(targets, max_concurrent=10)

# 不好的做法
from core.login_verifier import LoginVerifier
verifier = LoginVerifier()
for target in targets:
    result = verifier.verify_login(target.url, target.username, target.password)
```

### 2. 合理设置并发数

```python
# 根据目标系统调整
# 一般网站: 3-5
# 内部系统: 10-20
# 高性能服务器: 20-50
```

### 3. 使用代理池

```python
# 分散请求压力
proxy_manager.add_proxy("proxy1.example.com", 8080)
proxy_manager.add_proxy("proxy2.example.com", 8080)
proxy_manager.add_proxy("proxy3.example.com", 8080)
```

### 4. 定期保存进度

```python
# 避免长时间运行后崩溃导致数据丢失
if len(session.completed_indices) % 50 == 0:
    manager.save_session(session)
```

---

## 更多资源

- [Python官方文档](https://docs.python.org/3/)
- [aiohttp文档](https://docs.aiohttp.org/)
- [requests文档](https://requests.readthedocs.io/)
- [项目GitHub](https://github.com/your-repo)