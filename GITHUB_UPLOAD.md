# GitHub 上传指南

## ✅ Git 仓库已准备完成

`weakpass/` 目录已经初始化为 Git 仓库，并创建了初始提交。

## 📊 当前状态

- **分支**: main
- **提交**: 1 个初始提交
- **文件**: 36 个文件已暂存
- **代码行数**: 13,726 行

## 🚀 上传到 GitHub 的步骤

### 步骤 1: 在 GitHub 创建新仓库

1. 访问 [GitHub](https://github.com) 并登录
2. 点击右上角的 `+` 按钮
3. 选择 `New repository`
4. 填写仓库信息：
   - **Repository name**: `weakpass`
   - **Description**: `弱口令验证工具 - 用于安全审计和学习`
   - **Public/Private**: 根据需要选择
   - **不要勾选** "Initialize this repository with a README"
   - **不要勾选** "Add .gitignore"
   - **不要勾选** "Choose a license"
5. 点击 `Create repository`

### 步骤 2: 关联远程仓库

在 `weakpass/` 目录中运行以下命令：

```bash
# 你的 GitHub 用户名: Sir-dai-3310
git remote add origin https://github.com/Sir-dai-3310/weakpass.git
```

或者使用 SSH（如果已配置）：

```bash
git remote add origin git@github.com:Sir-dai-3310/weakpass.git
```

### 步骤 3: 推送到 GitHub

```bash
git push -u origin main
```

如果遇到错误，可能需要强制推送：

```bash
git push -u origin main --force
```

### 步骤 4: 验证上传

1. 访问你的 GitHub 仓库页面
2. 确认所有文件都已上传
3. 检查 README.md 是否正确显示

## 📝 完整命令汇总

```bash
# 1. 进入 weakpass 目录（如果还没进入）
cd E:\iflow_run\渗透工具\weakpass-弱口令验证工具\weakpass

# 2. 关联远程仓库
git remote add origin https://github.com/Sir-dai-3310/weakpass.git

# 3. 推送到 GitHub
git push -u origin main
```

## 🔧 常见问题

### 问题 1: 认证失败

如果遇到认证错误，需要配置 GitHub 访问令牌：

1. 访问 GitHub Settings -> Developer settings -> Personal access tokens
2. 生成新的 token，选择 `repo` 权限
3. 使用 token 作为密码进行推送

或者配置 SSH 密钥：

```bash
ssh-keygen -t ed25519 -C "your_email@example.com"
# 然后将公钥添加到 GitHub SSH keys
```

### 问题 2: 分支名称冲突

如果 GitHub 仓库已初始化为 master 分支：

```bash
git push -u origin master
# 或者
git push -u origin main:master
```

### 问题 3: 远程仓库已存在文件

如果远程仓库已有文件，需要先拉取：

```bash
git pull origin main --allow-unrelated-histories
git push -u origin main
```

## 📦 后续操作

上传成功后，你可以：

1. **编辑仓库描述**：在 GitHub 页面编辑仓库信息
2. **添加 Topics**：添加标签如 `security`, `password`, `auditing`
3. **启用 GitHub Pages**：如果需要托管文档
4. **设置分支保护**：保护 main 分支
5. **添加贡献指南**：创建 CONTRIBUTING.md

## 🎯 仓库 URL 示例

上传成功后，你的仓库 URL 将是：

```
https://github.com/Sir-dai-3310/weakpass
```

## 📋 检查清单

上传前请确认：

- [x] Git 仓库已初始化
- [x] 所有文件已添加
- [x] 初始提交已创建
- [x] 分支已重命名为 main
- [ ] GitHub 仓库已创建
- [ ] 远程仓库已关联
- [ ] 代码已推送成功

## 🚀 一键推送命令

将以下命令中的 `YOUR_USERNAME` 替换为你的 GitHub 用户名，然后一次性执行：

```bash
cd E:\iflow_run\渗透工具\weakpass-弱口令验证工具\weakpass
git remote add origin https://github.com/Sir-dai-3310/weakpass.git
git push -u origin main
```

## 📞 获取帮助

如果遇到问题：

1. 查看 [GitHub 文档](https://docs.github.com)
2. 搜索相关错误信息
3. 在 GitHub Issues 中提问

---

**准备好了吗？现在就可以上传到 GitHub 了！** 🎉