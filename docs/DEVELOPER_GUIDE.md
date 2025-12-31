# 开发者指南

## 目录

- [项目结构](#项目结构)
- [开发环境搭建](#开发环境搭建)
- [代码规范](#代码规范)
- [模块说明](#模块说明)
- [扩展开发](#扩展开发)
- [测试指南](#测试指南)
- [贡献指南](#贡献指南)

---

## 项目结构

```
weakpass-弱口令验证工具/
├── core/                          # 核心模块
│   ├── __init__.py               # 包初始化
│   ├── async_verifier.py         # 异步验证器（新增）
│   ├── enhanced_batch_importer.py # 增强批量导入器（新增）
│   ├── progress_manager.py       # 进度管理器（新增）
│   ├── proxy_support.py          # 代理支持（新增）
│   ├── wizard.py                 # 使用向导（新增）
│   ├── config_manager.py         # 配置管理器（新增）
│   ├── login_verifier.py         # 原始验证器
│   ├── enhanced_verifier.py      # 增强验证器
│   ├── specialized_verifier.py   # 专用验证器
│   ├── captcha_recognizer.py     # 验证码识别
│   └── batch_importer.py         # 批量导入器（旧版）
├── docs/                          # 文档
│   ├── API_REFERENCE.md          # API参考
│   ├── DEVELOPER_GUIDE.md        # 开发者指南
│   └── TROUBLESHOOTING.md        # 故障排查
├── main_app.py                    # 主界面
├── launcher.py                    # 启动器
├── cli_verify.py                  # 命令行工具
├── requirements.txt               # 依赖列表
├── config.json                    # 配置文件
└── 使用说明.md                    # 用户手册
```

---

## 开发环境搭建

### 1. 克隆项目

```bash
git clone <repository-url>
cd weakpass-弱口令验证工具
```

### 2. 创建虚拟环境（推荐）

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 安装开发依赖

```bash
pip install pytest pytest-asyncio pytest-cov black flake8 mypy
```

### 5. 运行测试

```bash
pytest tests/
```

---

## 代码规范

### Python版本

- Python 3.8+

### 代码风格

遵循 PEP 8 规范：

```bash
# 代码格式化
black .

# 代码检查
flake8 .

# 类型检查
mypy core/
```

### 命名规范

- **类名**: PascalCase (如 `AsyncLoginVerifier`)
- **函数名**: snake_case (如 `verify_login`)
- **常量**: UPPER_SNAKE_CASE (如 `MAX_CONCURRENT`)
- **私有方法**: _snake_case (如 `_check_dependencies`)

### 类型注解

所有公共函数和方法必须添加类型注解：

```python
def verify_login(
    self,
    target: TargetInfo
) -> LoginResult:
    """验证单个目标"""
    pass
```

### 文档字符串

使用 Google 风格的文档字符串：

```python
def verify_login(self, target: TargetInfo) -> LoginResult:
    """验证单个目标
    
    Args:
        target: 目标信息对象
        
    Returns:
        LoginResult: 登录结果
        
    Raises:
        ValueError: 当目标信息无效时
        
    Example:
        >>> target = TargetInfo(url="...", username="admin", password="pass")
        >>> result = await verifier.verify_login(target)
    """
    pass
```

---

## 模块说明

### async_verifier.py

异步验证器，支持并发验证。

**核心类:**
- `AsyncLoginVerifier`: 异步验证器主类
- `LoginStatus`: 登录状态枚举
- `LoginResult`: 登录结果数据类
- `TargetInfo`: 目标信息数据类

**使用场景:**
- 批量验证
- 高性能扫描
- 需要进度反馈的场景

### enhanced_batch_importer.py

增强版批量导入器。

**核心类:**
- `EnhancedBatchImporter`: 批量导入器
- `ImportFormat`: 导入格式枚举
- `ImportResult`: 导入结果数据类

**支持格式:**
- CSV
- Excel (xlsx/xls)
- TSV
- TXT
- JSON

### progress_manager.py

进度管理器，支持断点续扫。

**核心类:**
- `ProgressManager`: 进度管理器
- `ScanSession`: 扫描会话

**功能:**
- 保存/恢复进度
- 导出结果
- 会话管理

### proxy_support.py

代理支持模块。

**核心类:**
- `ProxyManager`: 代理管理器
- `ProxyPool`: 代理池
- `ProxyInfo`: 代理信息

**功能:**
- HTTP/HTTPS/SOCKS5代理
- 代理轮换
- 失败重试

### wizard.py

使用向导模块。

**核心类:**
- `SetupWizard`: 设置向导

**功能:**
- 依赖检查
- 模板下载
- 快速开始

---

## 扩展开发

### 添加新的验证规则

1. 在 `config_manager.py` 中添加新的系统配置：

```python
SYSTEM_CONFIGS = {
    'my_system': {
        'name': '我的系统',
        'patterns': [...],
        'config': {
            'login_endpoint': '/api/login',
            'method': 'POST',
            ...
        }
    }
}
```

2. 在 `async_verifier.py` 中添加特殊处理逻辑：

```python
async def verify_login(self, target: TargetInfo) -> LoginResult:
    sys_config = self.config_manager.get_system_config(target.url)
    
    # 特殊处理
    if sys_config.name == '我的系统':
        return self._verify_my_system(target)
    
    # 通用处理
    return await self._verify_generic(target)
```

### 添加新的导入格式

在 `enhanced_batch_importer.py` 中添加：

```python
class ImportFormat(Enum):
    CSV = "csv"
    EXCEL = "excel"
    MY_FORMAT = "my_format"  # 新格式

class EnhancedBatchImporter:
    def import_my_format(self, filepath: str) -> ImportResult:
        """导入自定义格式"""
        # 实现导入逻辑
        pass
```

### 添加新的验证码识别引擎

在 `captcha_recognizer.py` 中添加：

```python
class CaptchaRecognizer:
    def __init__(self):
        # 初始化新引擎
        self.my_ocr = MyOCR()
    
    def _my_ocr_recognize(self, image_data: bytes) -> CaptchaResult:
        """使用新引擎识别"""
        # 实现识别逻辑
        pass
```

---

## 测试指南

### 单元测试

```python
# tests/test_async_verifier.py
import pytest
from core.async_verifier import AsyncLoginVerifier, TargetInfo, LoginStatus

@pytest.mark.asyncio
async def test_verify_single():
    verifier = AsyncLoginVerifier()
    target = TargetInfo(
        url="https://httpbin.org/post",
        username="test",
        password="test"
    )
    
    result = await verifier.verify_login(target)
    assert result is not None
    assert isinstance(result.success, bool)

@pytest.mark.asyncio
async def test_verify_batch():
    verifier = AsyncLoginVerifier()
    targets = [
        TargetInfo(url=f"https://httpbin.org/post", username=f"user{i}", password=f"pass{i}")
        for i in range(3)
    ]
    
    results = await verifier.verify_batch(targets)
    assert len(results) == 3
```

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_async_verifier.py

# 生成覆盖率报告
pytest --cov=core --cov-report=html
```

### 集成测试

```python
# tests/integration/test_full_workflow.py
import pytest
from core.enhanced_batch_importer import EnhancedBatchImporter
from core.async_verifier import AsyncLoginVerifier, TargetInfo
from core.progress_manager import ProgressManager

@pytest.mark.asyncio
async def test_full_workflow():
    # 1. 导入目标
    importer = EnhancedBatchImporter()
    result = importer.import_csv("test_targets.csv")
    assert result.success
    
    # 2. 创建会话
    manager = ProgressManager()
    session = manager.create_session(result.targets)
    
    # 3. 验证
    async with AsyncLoginVerifier() as verifier:
        for target in session.get_remaining_targets():
            r = await verifier.verify_login(target)
            session.add_result(target.index, r)
    
    # 4. 保存结果
    manager.save_session(session)
    manager.export_results(session.session_id, "test_results.csv")
    
    # 5. 验证结果
    assert session.is_completed()
```

---

## 贡献指南

### 提交代码

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

### 提交信息格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Type:**
- `feat`: 新功能
- `fix`: 修复bug
- `docs`: 文档更新
- `style`: 代码格式（不影响功能）
- `refactor`: 重构
- `test`: 添加测试
- `chore`: 构建过程或辅助工具变动

**示例:**
```
feat(async-verifier): 添加代理支持

- 实现ProxyManager类
- 支持HTTP/HTTPS/SOCKS5代理
- 添加代理轮换策略

Closes #123
```

### 代码审查清单

- [ ] 代码符合 PEP 8 规范
- [ ] 添加了类型注解
- [ ] 添加了文档字符串
- [ ] 添加了单元测试
- [ ] 测试通过
- [ ] 更新了相关文档

---

## 常见问题

### Q: 如何调试异步代码？

A: 使用 `pytest-asyncio` 和 `asyncio.run()`:

```python
import asyncio

async def debug():
    # 调试代码
    pass

asyncio.run(debug())
```

### Q: 如何处理大量目标？

A: 使用分批处理和进度保存:

```python
BATCH_SIZE = 100

for i in range(0, len(targets), BATCH_SIZE):
    batch = targets[i:i+BATCH_SIZE]
    results = await verifier.verify_batch(batch)
    manager.save_session(session)
```

### Q: 如何添加新的系统指纹？

A: 在 `config_manager.py` 中添加配置:

```python
SYSTEM_CONFIGS = {
    'new_system': {
        'name': '新系统',
        'patterns': [
            {'type': 'url_contains', 'value': 'my-system'}
        ],
        'config': {
            'login_endpoint': '/api/auth',
            ...
        }
    }
}
```

---

## 更多资源

- [API参考](API_REFERENCE.md)
- [故障排查](TROUBLESHOOTING.md)
- [Python异步编程指南](https://docs.python.org/3/library/asyncio.html)
- [PEP 8 风格指南](https://www.python.org/dev/peps/pep-0008/)