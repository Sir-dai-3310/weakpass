# GitHub 上传说明

本文件夹包含了上传到GitHub所需的所有文件。

## 📦 包含的文件

| 文件 | 说明 |
|------|------|
| `README.md` | 项目说明文档（通俗易懂，适合所有人阅读） |
| `LICENSE` | MIT开源协议 |
| `.gitignore` | Git忽略规则 |
| `requirements.txt` | Python依赖列表 |
| `passwords.txt.example` | 密码字典示例文件 |
| `usernames.txt.example` | 用户名字典示例文件 |

## 🚀 上传步骤

### 步骤1：初始化Git仓库

在项目根目录（`weakpass-弱口令验证工具`）下执行：

```bash
git init
```

### 步骤2：复制GitHub文件

将 `github` 文件夹中的以下文件复制到项目根目录：

- `README.md`
- `LICENSE`
- `.gitignore`
- `requirements.txt`
- `passwords.txt.example`
- `usernames.txt.example`

### 步骤3：创建GitHub仓库

1. 访问 https://github.com/new
2. 创建新仓库，命名为 `weakpass-scanner`（或你喜欢的名称）
3. 选择 Public 或 Private
4. **不要**勾选 "Initialize this repository with a README"

### 步骤4：添加文件并提交

```bash
# 添加所有文件到Git
git add .

# 提交
git commit -m "Initial commit: 弱口令验证工具 v1.0"

# 添加远程仓库
git remote add origin https://github.com/你的用户名/weakpass-scanner.git

# 推送到GitHub
git branch -M main
git push -u origin main
```

### 步骤5：验证上传

访问你的GitHub仓库，确认以下文件已上传：

- ✅ `README.md`
- ✅ `LICENSE`
- ✅ `.gitignore`
- ✅ `requirements.txt`
- ✅ `passwords.txt.example`
- ✅ `usernames.txt.example`
- ✅ `core/` 文件夹
- ✅ `launcher.py`
- ✅ `main_app.py`
- ✅ `cli_verify.py`
- ✅ `weakpass_scanner_gui.py`
- ✅ `run.py`
- ✅ `config.json`
- ✅ `config_template.json`
- ✅ `示例目标.csv`
- ✅ `安装依赖.bat`
- ✅ `启动.bat`
- ✅ `启动图形界面.bat`
- ✅ `快速验证示例.bat`

## 📝 注意事项

### 已忽略的文件（不会上传）

根据 `.gitignore` 配置，以下文件**不会**被上传到GitHub：

- `logs/` - 日志文件夹
- `results/` - 测试结果文件夹
- `outputs/` - 输出文件文件夹
- `__pycache__/` - Python缓存
- `*.png`, `*.jpg` - 截图文件
- `*.html` - HTML分析文件
- `*_results_*.csv` - 测试结果文件
- `*_log_*.txt` - 日志文件
- `*_report_*.md` - 报告文件
- `passwords.txt` - 密码字典（敏感信息）
- `usernames.txt` - 用户名字典（敏感信息）

### 敏感信息保护

为了保护隐私和安全，以下文件被忽略：

- `passwords.txt` - 包含密码列表
- `usernames.txt` - 包含用户名列表
- 测试结果文件 - 可能包含真实的账号密码

项目提供 `.example` 示例文件：
- `passwords.txt.example` - 密码字典示例
- `usernames.txt.example` - 用户名字典示例

**下载者使用指南：**
- 需要将 `.example` 文件重命名为实际文件名
- 根据实际需求编辑字典内容
- 仅用于授权的安全测试

如果需要分享自定义字典文件，请：
1. 使用示例数据替代真实数据
2. 在 `.gitignore` 中移除对应行
3. 重新提交

## 🎯 上传后的操作

### 1. 设置仓库描述

在GitHub仓库页面点击 "Settings" → "General"，设置：

- **Description**: 弱口令验证工具 - 帮助安全测试人员发现系统中的弱密码漏洞
- **Topics**: security, password-scanner, pentesting, vulnerability-assessment

### 2. 添加Star和Watch

- 点击 ⭐ Star 收藏仓库
- 点击 👁️ Watch 关注更新

### 3. 分享仓库

复制仓库链接分享给其他人：
```
https://github.com/你的用户名/weakpass-scanner
```

## 🔧 常见问题

### Q: 如何更新代码到GitHub？

```bash
# 添加修改的文件
git add .

# 提交修改
git commit -m "更新说明"

# 推送到GitHub
git push
```

### Q: 如何克隆仓库到其他电脑？

```bash
git clone https://github.com/你的用户名/weakpass-scanner.git
cd weakpass-scanner
pip install -r requirements.txt
```

### Q: 如何创建Release版本？

1. 访问 GitHub 仓库页面
2. 点击 "Releases" → "Create a new release"
3. 填写版本号（如 v1.0.0）
4. 添加发布说明
5. 点击 "Publish release"

## 📞 需要帮助？

如有问题，请查看：
- [Git 官方文档](https://git-scm.com/doc)
- [GitHub 官方文档](https://docs.github.com/)