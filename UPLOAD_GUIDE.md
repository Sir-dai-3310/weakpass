# WeakPass 上传到代码仓库指南

## 目录结构

```
@weakpass/
├── __init__.py              # 包初始化文件
├── setup.py                 # Python 包安装配置
├── MANIFEST.in              # 打包清单
├── README.md                # 项目说明文档
├── LICENSE                  # MIT 许可证
├── QUICKSTART.md            # 快速开始指南
├── requirements.txt         # Python 依赖列表
├── config_template.json     # 配置文件模板
├── config.json              # 配置文件（会被 .gitignore 忽略）
├── run.py                   # 启动脚本
├── main_app.py              # 主界面程序
├── passwords.example.txt    # 示例密码列表
├── usernames.example.txt    # 示例用户名列表
├── .gitignore               # Git 忽略规则
├── core/                    # 核心模块目录
│   ├── __init__.py
│   ├── unified_verifier.py
│   ├── enhanced_verifier.py
│   ├── login_verifier.py
│   ├── async_verifier.py
│   ├── captcha_recognizer.py
│   ├── batch_importer.py
│   ├── enhanced_batch_importer.py
│   ├── config_manager.py
│   ├── progress_manager.py
│   ├── proxy_support.py
│   ├── simple_config.py
│   └── wizard.py
└── __pycache__/             # Python 缓存（会被 .gitignore 忽略）
```

## 上传步骤

### 1. 初始化 Git 仓库（如果还没有）

```bash
cd @weakpass
git init
```

### 2. 添加所有文件到 Git

```bash
git add .
```

### 3. 查看将要提交的文件

```bash
git status
```

### 4. 提交更改

```bash
git commit -m "Initial commit: WeakPass v1.0.0"
```

### 5. 创建 GitHub 仓库

1. 访问 [GitHub](https://github.com) 并登录
2. 点击右上角的 "+" 按钮
3. 选择 "New repository"
4. 填写仓库信息：
   - Repository name: `weakpass`
   - Description: `弱口令验证工具 - 用于安全审计和学习`
   - 选择 Public 或 Private
   - 不要勾选 "Initialize this repository with a README"
5. 点击 "Create repository"

### 6. 关联远程仓库

```bash
git remote add origin https://github.com/yourusername/weakpass.git
```

### 7. 推送到 GitHub

```bash
git branch -M main
git push -u origin main
```

## 发布到 PyPI（可选）

如果想让其他人可以通过 `pip install weakpass` 安装：

### 1. 构建包

```bash
pip install build twine
python -m build
```

### 2. 测试包（可选）

```bash
pip install twine
twine check dist/*
```

### 3. 上传到 PyPI

```bash
twine upload dist/*
```

注意：需要注册 PyPI 账号并配置 API token。

## 使用说明

### 克隆仓库

```bash
git clone https://github.com/yourusername/weakpass.git
cd weakpass
```

### 安装

```bash
pip install -r requirements.txt
```

### 运行

```bash
python run.py
```

### 作为包安装

```bash
pip install .
```

然后可以在任何地方使用：

```python
from weakpass import UnifiedVerifier, TargetInfo
```

## 注意事项

1. **敏感文件**: `config.json`、`passwords.txt`、`usernames.txt` 已被 `.gitignore` 忽略，不会上传
2. **Python 缓存**: `__pycache__/` 目录已被忽略
3. **日志文件**: `*.log` 文件已被忽略
4. **结果文件**: `*_results_*.csv` 文件已被忽略

## 版本管理

更新版本号时，需要修改以下文件：

1. `__init__.py` 中的 `__version__`
2. `setup.py` 中的 `version`
3. `config_template.json` 中的 `app.version`

然后提交并打标签：

```bash
git add .
git commit -m "Bump version to 1.1.0"
git tag v1.1.0
git push origin main --tags
```

## 维护建议

1. **定期更新依赖**: 检查并更新 `requirements.txt` 中的依赖版本
2. **安全审计**: 定期检查代码中的安全问题
3. **文档更新**: 保持 README 和文档的更新
4. **Issue 跟踪**: 及时处理 GitHub Issues
5. **Pull Request**: 审查并合并社区贡献

## 许可证

本项目使用 MIT 许可证，详见 [LICENSE](LICENSE) 文件。

## 贡献

欢迎贡献！请查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解如何参与贡献。

## 联系方式

如有问题，请通过 GitHub Issues 联系。