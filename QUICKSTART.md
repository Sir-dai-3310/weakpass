# WeakPass 快速开始指南

## 快速安装

### 1. 克隆或下载项目

```bash
git clone https://github.com/yourusername/weakpass.git
cd weakpass
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 启动应用

```bash
python run.py
```

## 基本使用

### 单个验证

1. 启动应用后，在"单个验证"选项卡中：
   - 输入目标 URL（例如：`https://example.com/login`）
   - 输入用户名
   - 输入密码
2. 点击"开始验证"按钮
3. 查看验证结果

### 批量验证

1. 在"批量验证"选项卡中：
   - 点击"导出模板"获取 CSV 模板
   - 编辑模板，填入目标信息
   - 点击"导入CSV"选择文件
2. 点击"开始批量验证"
3. 等待验证完成
4. 点击"导出结果"保存结果

## CSV 文件格式

创建一个 CSV 文件，包含以下列：

```csv
URL,用户名,密码
https://example.com/login,admin,password123
https://test.com/login,test,testpass
https://demo.com/login,demo,demo123
```

## 配置

复制 `config_template.json` 为 `config.json` 并根据需要修改配置：

```bash
cp config_template.json config.json
```

主要配置项：

- `network.timeout`: 请求超时时间（秒）
- `network.max_retries`: 最大重试次数
- `captcha.enabled`: 是否启用验证码识别
- `advanced.max_concurrent_requests`: 最大并发请求数

## 可选功能

### 验证码识别

安装额外依赖：

```bash
pip install -r requirements.txt
pip install Pillow pytesseract opencv-python numpy easyocr
```

注意：pytesseract 需要安装 Tesseract OCR 程序。

### Excel 支持

安装额外依赖：

```bash
pip install pandas openpyxl xlrd
```

## 作为 Python 库使用

```python
from weakpass import UnifiedVerifier, TargetInfo, VerifyMode

# 创建验证器
verifier = UnifiedVerifier(mode=VerifyMode.ASYNC, max_concurrent=5)

# 创建目标
target = TargetInfo(
    url="https://example.com/login",
    username="admin",
    password="password123"
)

# 执行验证（异步）
import asyncio

async def verify():
    result = await verifier.verify_async(target)
    if result.success:
        print(f"验证成功: {result.message}")
    else:
        print(f"验证失败: {result.message}")

asyncio.run(verify())
```

## 常见问题

### 1. 导入错误

确保已安装所有依赖：

```bash
pip install -r requirements.txt
```

### 2. tkinter 错误

tkinter 通常随 Python 一起安装。如果遇到错误：

- **Windows**: 重新安装 Python，确保勾选 "tcl/tk and IDLE"
- **Linux**: `sudo apt-get install python3-tk`
- **macOS**: 重新安装 Python

### 3. 验证码识别不工作

确保已安装 Tesseract OCR：

- **Windows**: 下载并安装 [Tesseract-OCR](https://github.com/UB-Mannheim/tesseract/wiki)
- **Linux**: `sudo apt-get install tesseract-ocr`
- **macOS**: `brew install tesseract`

### 4. 连接超时

增加配置文件中的 `network.timeout` 值。

## 安全提醒

⚠️ **重要**：

- 仅用于授权的安全审计和渗透测试
- 未经授权使用是非法的
- 遵守当地法律法规
- 对您的行为负责

## 获取帮助

- 查看 [README.md](README.md) 获取更多信息
- 提交 [GitHub Issues](https://github.com/yourusername/weakpass/issues)

## 下一步

- 阅读 [API 文档](docs/API_REFERENCE.md)
- 查看 [开发者指南](docs/DEVELOPER_GUIDE.md)
- 浏览 [故障排除指南](docs/TROUBLESHOOTING.md)