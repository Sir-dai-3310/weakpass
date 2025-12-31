# WeakPass - 弱口令验证工具

> **⚠️ 安全警告**: 本工具仅用于**授权的安全审计、渗透测试、安全研究和学习**目的。未经授权使用本工具测试任何系统都是非法的。

## 简介

WeakPass 是一个用于检测弱口令的安全工具，帮助安全研究人员和系统管理员识别和修复密码安全漏洞。

### 主要特性

- 🔐 **单个验证**: 快速验证单个目标的登录凭据
- 📊 **批量验证**: 支持从 CSV/Excel 导入目标进行批量验证
- 🤖 **异步处理**: 支持异步并发验证，提高效率
- 🔍 **验证码识别**: 可选的自动验证码识别功能
- 📈 **进度跟踪**: 实时显示验证进度和统计信息
- 💾 **结果导出**: 支持导出验证结果为 CSV 格式
- ⚙️ **可配置**: 灵活的配置选项

## 安装

### 环境要求

- Python 3.8+
- tkinter (Python GUI 库，通常随 Python 一起安装)

### 安装依赖

```bash
pip install -r requirements.txt
```

### 可选依赖（验证码识别）

```bash
pip install Pillow pytesseract opencv-python numpy easyocr
```

注意：pytesseract 需要额外安装 Tesseract OCR 程序。

## 使用方法

### 启动图形界面

```bash
python run.py
```

### 单个验证

1. 在"单个验证"选项卡中输入目标 URL
2. 输入用户名和密码
3. 点击"开始验证"按钮
4. 查看验证结果

### 批量验证

1. 在"批量验证"选项卡中点击"导入CSV"或"导入Excel"
2. 选择包含目标信息的文件
3. 点击"开始批量验证"
4. 等待验证完成
5. 点击"导出结果"保存验证结果

### 文件格式

CSV 文件格式示例：

```csv
URL,用户名,密码
https://example.com/login,admin,password123
https://test.com/login,test,testpass
```

## 配置

配置文件 `config.json` 包含以下设置：

- **网络设置**: 超时时间、重试次数、用户代理
- **验证码设置**: OCR 配置、预处理选项
- **登录设置**: 成功/失败关键词、字段名称
- **UI 设置**: 日志、字体、主题
- **高级设置**: 调试模式、代理、自定义请求头

## 作为库使用

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

# 执行验证
result = await verifier.verify_async(target)

if result.success:
    print("验证成功!")
else:
    print(f"验证失败: {result.message}")
```

## 项目结构

```
@weakpass/
├── __init__.py          # 包初始化文件
├── core/                # 核心模块
│   ├── __init__.py
│   ├── unified_verifier.py      # 统一验证器
│   ├── enhanced_verifier.py     # 增强验证器
│   ├── login_verifier.py        # 登录验证器
│   ├── captcha_recognizer.py    # 验证码识别
│   ├── batch_importer.py        # 批量导入
│   ├── enhanced_batch_importer.py
│   ├── config_manager.py        # 配置管理
│   ├── async_verifier.py        # 异步验证
│   ├── progress_manager.py      # 进度管理
│   ├── proxy_support.py         # 代理支持
│   ├── simple_config.py         # 简单配置
│   └── wizard.py                # 向导
├── main_app.py          # 主界面
├── run.py               # 启动脚本
├── config.json          # 配置文件
├── requirements.txt     # 依赖列表
└── README.md            # 说明文档
```

## 安全声明

本工具仅用于以下合法用途：

- ✅ 授权的安全审计和渗透测试
- ✅ 系统管理员维护自己的系统
- ✅ 安全研究和学习
- ✅ 密码策略验证

**禁止用于**：

- ❌ 未经授权访问任何系统
- ❌ 攻击或破坏任何系统
- ❌ 任何非法活动

使用本工具即表示您同意遵守当地法律法规，并对您的行为负责。

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

## 免责声明

开发者不对本工具的滥用或误用负责。使用者应确保在合法授权范围内使用本工具。

## 联系方式

如有问题或建议，请通过 GitHub Issues 联系。