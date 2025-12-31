# API 参考文档

## 目录

- [核心模块](#核心模块)
  - [AsyncLoginVerifier](#asyncloginverifier)
  - [EnhancedBatchImporter](#enhancedbatchimporter)
  - [ProgressManager](#progressmanager)
  - [ProxyManager](#proxymanager)
- [数据模型](#数据模型)
  - [TargetInfo](#targetinfo)
  - [LoginResult](#loginresult)
  - [ScanSession](#scansession)
- [使用示例](#使用示例)

---

## 核心模块

### AsyncLoginVerifier

异步登录验证器，支持并发验证。

#### 初始化

```python
from core.async_verifier import AsyncLoginVerifier, TargetInfo

verifier = AsyncLoginVerifier(
    config_manager=None,      # ConfigManager对象
    max_concurrent=5,         # 最大并发数
    progress_callback=None,   # 进度回调函数
    log_callback=None          # 日志回调函数
)
```

#### 方法

##### verify_login(target: TargetInfo) -> LoginResult

验证单个目标。

**参数:**
- `target`: 目标信息对象

**返回:**
- `LoginResult`: 登录结果

**示例:**
```python
target = TargetInfo(
    url="https://example.com/login",
    username="admin",
    password="password123"
)

result = await verifier.verify_login(target)
if result.success:
    print(f"登录成功: {result.message}")
else:
    print(f"登录失败: {result.message}")
```

##### verify_batch(targets: List[TargetInfo], delay: float = 0.5) -> List[LoginResult]

批量验证目标。

**参数:**
- `targets`: 目标列表
- `delay`: 请求间隔（秒）

**返回:**
- `List[LoginResult]`: 结果列表

**示例:**
```python
targets = [
    TargetInfo(url=f"https://example{i}.com/login", username="admin", password=f"pass{i}")
    for i in range(1, 11)
]

def progress(current, total):
    print(f"进度: {current}/{total}")

results = await verifier.verify_batch(targets, delay=0.5, progress_callback=progress)
```

##### start() / close()

启动/关闭会话。

**示例:**
```python
await verifier.start()
# ... 使用验证器
await verifier.close()
```

##### get_stats() -> Dict[str, int]

获取统计信息。

**返回:**
```python
{
    'total': 10,
    'success': 3,
    'failed': 5,
    'errors': 2
}
```

##### reset_stats()

重置统计信息。

---

### EnhancedBatchImporter

增强版批量导入器，支持多种文件格式。

#### 初始化

```python
from core.enhanced_batch_importer import EnhancedBatchImporter

importer = EnhancedBatchImporter()
```

#### 方法

##### import_file(filepath: str) -> ImportResult

导入文件（自动检测格式）。

**参数:**
- `filepath`: 文件路径

**返回:**
- `ImportResult`: 导入结果

**示例:**
```python
result = importer.import_file("targets.csv")
if result.success:
    print(f"导入成功: {result.valid_count} 条记录")
    for target in result.targets:
        print(f"  {target.url} - {target.username}")
else:
    print(f"导入失败: {result.errors[0]}")
```

##### import_csv(filepath: str, encoding: Optional[str] = None) -> ImportResult

导入CSV文件。

##### import_excel(filepath: str) -> ImportResult

导入Excel文件。

##### import_json(filepath: str) -> ImportResult

导入JSON文件。

##### export_template(filepath: str, format: ImportFormat, sample_count: int = 3) -> bool

导出模板文件。

**参数:**
- `filepath`: 文件路径
- `format`: 文件格式
- `sample_count`: 示例数量

**示例:**
```python
importer.export_template("template.csv", ImportFormat.CSV, sample_count=5)
```

---

### ProgressManager

进度管理器，支持进度保存/恢复。

#### 初始化

```python
from core.progress_manager import ProgressManager

manager = ProgressManager(save_dir="sessions")
```

#### 方法

##### create_session(targets: List[TargetInfo], config: Optional[Dict] = None) -> ScanSession

创建新会话。

**示例:**
```python
session = manager.create_session(targets, config={'max_concurrent': 5})
```

##### save_session(session: Optional[ScanSession] = None) -> bool

保存会话。

##### load_session(session_id: str) -> Optional[ScanSession]

加载会话。

##### list_sessions() -> List[Dict[str, Any]]

列出所有会话。

**返回:**
```python
[
    {
        'session_id': 'scan_20250101_120000_abc123',
        'created_at': '2025-01-01 12:00:00',
        'total_targets': 100,
        'completed_targets': 50,
        'completion_rate': 0.5,
        'stats': {...}
    },
    ...
]
```

##### export_results(session_id: str, output_file: str, format: str = "csv") -> bool

导出结果。

**参数:**
- `session_id`: 会话ID
- `output_file`: 输出文件路径
- `format`: 格式（csv/json）

---

### ProxyManager

代理管理器，支持代理池和轮换策略。

#### 初始化

```python
from core.proxy_support import ProxyManager, ProxyType

manager = ProxyManager()
```

#### 方法

##### add_proxy(host: str, port: int, username: Optional[str] = None, password: Optional[str] = None, proxy_type: ProxyType = ProxyType.HTTP)

添加代理。

**示例:**
```python
manager.add_proxy("127.0.0.1", 7890, proxy_type=ProxyType.HTTP)
manager.add_proxy("proxy.example.com", 1080, "user", "pass", ProxyType.SOCKS5)
```

##### enable_proxy() / disable_proxy()

启用/禁用代理。

##### get_next_proxy() -> Optional[ProxyInfo]

获取下一个可用代理。

##### report_result(proxy: Optional[ProxyInfo], success: bool)

报告代理结果（成功/失败）。

##### load_from_file(filepath: str) -> bool

从文件加载代理配置。

##### save_to_file(filepath: str) -> bool

保存代理配置到文件。

---

## 数据模型

### TargetInfo

目标信息数据类。

```python
@dataclass
class TargetInfo:
    url: str                          # 目标URL
    username: str                     # 用户名
    password: str                     # 密码
    extra: Optional[Dict[str, str]]   # 额外信息
    index: int = 0                    # 索引
    source_file: Optional[str] = None # 来源文件
    
    def is_valid(self) -> bool        # 检查是否有效
    def to_dict() -> Dict[str, Any]   # 转换为字典
```

### LoginResult

登录结果数据类。

```python
@dataclass
class LoginResult:
    status: LoginStatus               # 登录状态
    success: bool                     # 是否成功
    message: str                      # 消息
    response_time: float              # 响应时间
    url: str                          # 原始URL
    final_url: str                    # 最终URL
    page_changed: bool                # 页面是否变化
    details: Optional[Dict[str, Any]] # 详细信息
    timestamp: str                    # 时间戳
```

### ScanSession

扫描会话数据类。

```python
@dataclass
class ScanSession:
    session_id: str                   # 会话ID
    created_at: str                   # 创建时间
    updated_at: str                   # 更新时间
    targets: List[TargetInfo]         # 目标列表
    completed_indices: List[int]      # 已完成索引
    results: List[LoginResult]        # 结果列表
    config: Dict[str, Any]            # 配置
    stats: Dict[str, int]             # 统计
    
    def get_progress() -> Tuple[int, int]           # 获取进度
    def get_completion_rate() -> float              # 获取完成率
    def is_completed() -> bool                      # 是否完成
    def get_remaining_targets() -> List[TargetInfo] # 获取剩余目标
    def add_result(index: int, result: LoginResult) # 添加结果
    def to_dict() -> Dict[str, Any]                 # 转换为字典
```

---

## 使用示例

### 示例1：单个验证

```python
import asyncio
from core.async_verifier import verify_single

async def main():
    result = await verify_single(
        "https://httpbin.org/post",
        "testuser",
        "testpass"
    )
    print(f"结果: {result.success} - {result.message}")

asyncio.run(main())
```

### 示例2：批量验证

```python
import asyncio
from core.async_verifier import verify_batch_async, TargetInfo

async def main():
    targets = [
        TargetInfo(url="https://example1.com/login", username="admin", password="pass1"),
        TargetInfo(url="https://example2.com/login", username="admin", password="pass2"),
    ]
    
    def progress(current, total):
        print(f"进度: {current}/{total}")
    
    results = await verify_batch_async(
        targets,
        max_concurrent=3,
        delay=0.5,
        progress_callback=progress
    )
    
    for result in results:
        print(f"{result.url}: {result.success}")

asyncio.run(main())
```

### 示例3：断点续扫

```python
import asyncio
from core.progress_manager import ProgressManager
from core.async_verifier import AsyncLoginVerifier, TargetInfo

async def main():
    manager = ProgressManager()
    
    # 尝试加载之前的会话
    session = manager.load_session("scan_20250101_120000_abc123")
    
    if not session:
        # 创建新会话
        targets = [TargetInfo(url=f"https://example{i}.com/login", username="admin", password=f"pass{i}") for i in range(1, 101)]
        session = manager.create_session(targets)
    
    # 获取剩余目标
    remaining = session.get_remaining_targets()
    
    # 继续验证
    async with AsyncLoginVerifier() as verifier:
        for target in remaining:
            result = await verifier.verify_login(target)
            session.add_result(target.index, result)
            
            # 定期保存进度
            if len(session.completed_indices) % 10 == 0:
                manager.save_session(session)
    
    # 保存最终结果
    manager.save_session(session)
    manager.export_results(session.session_id, "results.csv")

asyncio.run(main())
```

### 示例4：使用代理

```python
import asyncio
from core.proxy_support import ProxyManager, ProxyType
from core.async_verifier import verify_batch_async, TargetInfo

async def main():
    # 配置代理
    proxy_manager = ProxyManager()
    proxy_manager.add_proxy("127.0.0.1", 7890, proxy_type=ProxyType.HTTP)
    proxy_manager.enable_proxy()
    
    # 创建目标
    targets = [TargetInfo(url="https://example.com/login", username="admin", password="password")]
    
    # 验证（需要集成代理支持到AsyncLoginVerifier）
    results = await verify_batch_async(targets)
    
    for result in results:
        proxy_manager.report_result(None, result.success)
    
    # 查看代理统计
    stats = proxy_manager.get_stats()
    print(f"代理统计: {stats}")

asyncio.run(main())
```

---

## 错误处理

所有方法都包含适当的错误处理。建议使用try-except捕获异常：

```python
try:
    result = await verifier.verify_login(target)
except Exception as e:
    print(f"验证失败: {e}")
```

---

## 最佳实践

1. **使用异步上下文管理器**
```python
async with AsyncLoginVerifier() as verifier:
    results = await verifier.verify_batch(targets)
```

2. **定期保存进度**
```python
if len(session.completed_indices) % 10 == 0:
    manager.save_session(session)
```

3. **设置合理的并发数**
```python
verifier = AsyncLoginVerifier(max_concurrent=5)  # 不要太高
```

4. **添加请求延迟**
```python
results = await verifier.verify_batch(targets, delay=0.5)  # 避免被封
```

5. **使用代理池**
```python
proxy_manager.add_proxy("proxy1.example.com", 8080)
proxy_manager.add_proxy("proxy2.example.com", 8080)
```

---

## 更多信息

- [开发者指南](DEVELOPER_GUIDE.md)
- [故障排查指南](TROUBLESHOOTING.md)
- [使用说明](../使用说明.md)