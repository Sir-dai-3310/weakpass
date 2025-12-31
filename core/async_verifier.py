#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
异步登录验证器
支持并发验证，提高扫描效率
"""

import asyncio
import aiohttp
import hashlib
import base64
import time
import re
import json
import chardet
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from urllib.parse import urljoin, urlparse
from datetime import datetime

from .config_manager import ConfigManager, SystemConfig, NetworkConfig, get_config_manager


class LoginStatus(Enum):
    """登录状态枚举"""
    SUCCESS = "登录成功"
    PASSWORD_ERROR = "密码错误"
    USERNAME_ERROR = "用户名错误"
    CAPTCHA_ERROR = "验证码错误"
    CAPTCHA_REQUIRED = "需要验证码"
    CONNECTION_ERROR = "连接错误"
    TIMEOUT_ERROR = "超时错误"
    UNKNOWN_ERROR = "未知错误"


@dataclass
class LoginResult:
    """登录结果"""
    status: LoginStatus
    success: bool
    message: str
    response_time: float
    url: str
    final_url: str
    page_changed: bool
    details: Optional[Dict[str, Any]] = field(default=None)
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


@dataclass
class TargetInfo:
    """目标信息"""
    url: str
    username: str
    password: str
    extra: Optional[Dict[str, str]] = field(default=None)
    index: int = 0

    def is_valid(self) -> bool:
        """检查目标是否有效"""
        return bool(self.url and self.username and self.password)


class AsyncLoginVerifier:
    """异步登录验证器"""

    def __init__(
        self,
        config_manager: Optional[ConfigManager] = None,
        max_concurrent: int = 5,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None
    ):
        """
        初始化异步验证器

        Args:
            config_manager: 配置管理器
            max_concurrent: 最大并发数
            progress_callback: 进度回调函数 (current, total)
            log_callback: 日志回调函数
        """
        self.config_manager = config_manager or get_config_manager()
        self.max_concurrent = max_concurrent
        self.progress_callback = progress_callback
        self.log_callback = log_callback
        
        # 会话
        self.session: Optional[aiohttp.ClientSession] = None
        
        # 统计
        self.stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'errors': 0
        }

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()

    async def start(self):
        """启动会话"""
        network_config = self.config_manager.config.network
        
        connector = aiohttp.TCPConnector(
            limit=self.max_concurrent,
            ssl=network_config.verify_ssl,
            force_close=False
        )
        
        timeout = aiohttp.ClientTimeout(total=network_config.timeout)
        
        headers = {
            'User-Agent': network_config.user_agent,
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate'
        }
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers=headers
        )

    async def close(self):
        """关闭会话"""
        if self.session:
            await self.session.close()
            self.session = None

    def _log(self, message: str, level: str = "INFO"):
        """记录日志"""
        if self.log_callback:
            self.log_callback(f"[{level}] {message}")

    async def _get_response_text(self, response: aiohttp.ClientResponse) -> str:
        """
        获取响应文本内容，自动处理编码问题

        Args:
            response: 响应对象

        Returns:
            解码后的文本内容
        """
        try:
            # 尝试直接获取文本
            return await response.text()
        except UnicodeDecodeError:
            # 如果UTF-8解码失败，尝试其他编码
            try:
                # 获取原始字节
                content_bytes = await response.read()
                
                # 尝试从Content-Type头获取编码
                content_type = response.headers.get('Content-Type', '')
                charset = None
                if 'charset=' in content_type:
                    charset = content_type.split('charset=')[-1].strip()
                
                # 如果有指定的编码，尝试使用
                if charset:
                    try:
                        return content_bytes.decode(charset)
                    except (UnicodeDecodeError, LookupError):
                        pass
                
                # 使用chardet检测编码
                detected = chardet.detect(content_bytes)
                if detected and detected.get('confidence', 0) > 0.5:
                    detected_encoding = detected.get('encoding')
                    if detected_encoding:
                        try:
                            return content_bytes.decode(detected_encoding)
                        except (UnicodeDecodeError, LookupError):
                            pass
                
                # 尝试常见中文编码
                common_encodings = ['gbk', 'gb2312', 'gb18030', 'big5']
                for encoding in common_encodings:
                    try:
                        return content_bytes.decode(encoding)
                    except (UnicodeDecodeError, LookupError):
                        continue
                
                # 最后尝试ISO-8859-1（不会失败）
                return content_bytes.decode('iso-8859-1', errors='replace')
                
            except Exception as e:
                # 如果所有方法都失败，返回错误信息
                return f"<编码错误: {str(e)[:50]}>"

    def _encrypt_password(self, password: str, method: str) -> str:
        """
        根据方法加密密码

        Args:
            password: 原始密码
            method: 加密方法

        Returns:
            加密后的密码
        """
        if method == 'none' or method is None:
            return password
        elif method == 'md5':
            return hashlib.md5(password.encode()).hexdigest()
        elif method == 'md5_upper':
            return hashlib.md5(password.encode()).hexdigest().upper()
        elif method == 'sha1':
            return hashlib.sha1(password.encode()).hexdigest()
        elif method == 'sha256':
            return hashlib.sha256(password.encode()).hexdigest()
        elif method == 'base64':
            return base64.b64encode(password.encode()).decode()
        elif method == 'md5_base64':
            md5_hash = hashlib.md5(password.encode()).hexdigest()
            return base64.b64encode(md5_hash.encode()).decode()
        else:
            return password

    def _build_request_body(
        self,
        username: str,
        password: str,
        sys_config: SystemConfig
    ) -> Dict[str, Any]:
        """
        构建请求体

        Args:
            username: 用户名
            password: 密码
            sys_config: 系统配置

        Returns:
            请求体字典
        """
        encrypted_pwd = self._encrypt_password(password, sys_config.password_encryption)
        
        if sys_config.content_type == 'application/json':
            return {
                sys_config.username_field: username,
                sys_config.password_field: encrypted_pwd
            }
        else:
            # 表单格式
            return {
                sys_config.username_field: username,
                sys_config.password_field: encrypted_pwd
            }

    def _check_response(
        self,
        response: aiohttp.ClientResponse,
        content: str,
        sys_config: SystemConfig
    ) -> Tuple[bool, str]:
        """
        检查响应是否成功

        Args:
            response: 响应对象
            content: 响应内容
            sys_config: 系统配置

        Returns:
            (是否成功, 消息)
        """
        # 首先检查失败指标
        for indicator in sys_config.failure_indicators:
            ind_type = indicator.get('type')
            ind_value = indicator.get('value')
            
            if ind_type == 'body_contains':
                if ind_value in content:
                    try:
                        data = json.loads(content)
                        if isinstance(data, dict) and 'Message' in data:
                            return False, data['Message']
                    except:
                        pass
                    return False, f"包含失败标识: {ind_value}"
            elif ind_type == 'status_code':
                if response.status == ind_value:
                    return False, f"HTTP状态码: {ind_value}"
        
        # 检查成功指标
        success_count = 0
        for indicator in sys_config.success_indicators:
            ind_type = indicator.get('type')
            ind_value = indicator.get('value')
            
            if ind_type == 'status_code':
                if response.status == ind_value:
                    success_count += 1
            elif ind_type == 'body_length_gt':
                if len(content) > ind_value:
                    success_count += 1
            elif ind_type == 'body_contains':
                if ind_value in content:
                    success_count += 1
            elif ind_type == 'body_not_contains':
                if ind_value not in content:
                    success_count += 1
        
        # 至少满足一半的成功指标
        if success_count >= max(1, len(sys_config.success_indicators) // 2 + 1):
            return True, "登录成功"
        
        return False, "未知响应"

    async def verify_login(
        self,
        target: TargetInfo
    ) -> LoginResult:
        """
        验证单个目标

        Args:
            target: 目标信息

        Returns:
            登录结果
        """
        start_time = time.time()
        
        try:
            # 获取系统配置
            sys_config = self.config_manager.get_system_config(target.url)
            
            # 解析URL
            parsed = urlparse(target.url)
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            
            # 确定登录端点
            if parsed.path and parsed.path != '/':
                endpoint = parsed.path
            else:
                endpoint = sys_config.login_endpoint
            
            full_url = urljoin(base_url, endpoint)
            
            # 构建请求
            method = sys_config.method.upper()
            headers = sys_config.headers.copy()
            
            # 根据Content-Type设置headers
            if sys_config.content_type == 'application/json':
                headers['Content-Type'] = 'application/json'
            
            # 构建请求体
            body = self._build_request_body(target.username, target.password, sys_config)
            
            # 发送请求
            if method == 'POST':
                if sys_config.content_type == 'application/json':
                    async with self.session.post(
                        full_url,
                        json=body,
                        headers=headers
                    ) as response:
                        content = await self._get_response_text(response)
                        elapsed = time.time() - start_time
                        success, message = self._check_response(response, content, sys_config)

                        return LoginResult(
                            status=LoginStatus.SUCCESS if success else LoginStatus.PASSWORD_ERROR,
                            success=success,
                            message=message,
                            response_time=elapsed,
                            url=target.url,
                            final_url=str(response.url),
                            page_changed=str(response.url) != target.url,
                            details={
                                'system_type': sys_config.name,
                                'status_code': response.status,
                                'content_length': len(content)
                            }
                        )
                else:
                    async with self.session.post(
                        full_url,
                        data=body,
                        headers=headers
                    ) as response:
                        content = await self._get_response_text(response)
                        elapsed = time.time() - start_time
                        success, message = self._check_response(response, content, sys_config)

                        return LoginResult(
                            status=LoginStatus.SUCCESS if success else LoginStatus.PASSWORD_ERROR,
                            success=success,
                            message=message,
                            response_time=elapsed,
                            url=target.url,
                            final_url=str(response.url),
                            page_changed=str(response.url) != target.url,
                            details={
                                'system_type': sys_config.name,
                                'status_code': response.status,
                                'content_length': len(content)
                            }
                        )
            else:
                async with self.session.get(
                    full_url,
                    params=body,
                    headers=headers
                ) as response:
                    content = await self._get_response_text(response)
                    elapsed = time.time() - start_time
                    success, message = self._check_response(response, content, sys_config)

                    return LoginResult(
                        status=LoginStatus.SUCCESS if success else LoginStatus.PASSWORD_ERROR,
                        success=success,
                        message=message,
                        response_time=elapsed,
                        url=target.url,
                        final_url=str(response.url),
                        page_changed=str(response.url) != target.url,
                        details={
                            'system_type': sys_config.name,
                            'status_code': response.status,
                            'content_length': len(content)
                        }
                    )
                    
        except asyncio.TimeoutError:
            elapsed = time.time() - start_time
            return LoginResult(
                status=LoginStatus.TIMEOUT_ERROR,
                success=False,
                message="请求超时",
                response_time=elapsed,
                url=target.url,
                final_url=target.url,
                page_changed=False
            )
        except aiohttp.ClientError as e:
            elapsed = time.time() - start_time
            return LoginResult(
                status=LoginStatus.CONNECTION_ERROR,
                success=False,
                message=f"连接错误: {str(e)[:50]}",
                response_time=elapsed,
                url=target.url,
                final_url=target.url,
                page_changed=False
            )
        except Exception as e:
            elapsed = time.time() - start_time
            return LoginResult(
                status=LoginStatus.UNKNOWN_ERROR,
                success=False,
                message=f"未知错误: {str(e)[:50]}",
                response_time=elapsed,
                url=target.url,
                final_url=target.url,
                page_changed=False
            )

    async def verify_batch(
        self,
        targets: List[TargetInfo],
        delay: float = 0.5
    ) -> List[LoginResult]:
        """
        批量验证目标

        Args:
            targets: 目标列表
            delay: 请求间隔（秒）

        Returns:
            结果列表
        """
        if not self.session:
            await self.start()
        
        total = len(targets)
        results: List[LoginResult] = []
        
        # 创建信号量控制并发
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def verify_with_limit(target: TargetInfo) -> LoginResult:
            """带并发限制的验证"""
            async with semaphore:
                result = await self.verify_login(target)
                
                # 更新统计
                self.stats['total'] += 1
                if result.success:
                    self.stats['success'] += 1
                elif result.status in [LoginStatus.CONNECTION_ERROR, LoginStatus.TIMEOUT_ERROR, LoginStatus.UNKNOWN_ERROR]:
                    self.stats['errors'] += 1
                else:
                    self.stats['failed'] += 1
                
                # 回调
                if self.progress_callback:
                    self.progress_callback(self.stats['total'], total)
                
                # 日志
                if self.log_callback:
                    status_icon = "✓" if result.success else "✗"
                    self._log(f"{status_icon} {target.url} - {target.username}:{target.password} - {result.message} ({result.response_time:.2f}s)")
                
                # 延迟
                if delay > 0:
                    await asyncio.sleep(delay)
                
                return result
        
        # 并发执行
        tasks = [verify_with_limit(target) for target in targets]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                target = targets[i]
                valid_results.append(LoginResult(
                    status=LoginStatus.UNKNOWN_ERROR,
                    success=False,
                    message=f"任务异常: {str(result)[:50]}",
                    response_time=0,
                    url=target.url,
                    final_url=target.url,
                    page_changed=False
                ))
            else:
                valid_results.append(result)
        
        return valid_results

    def get_stats(self) -> Dict[str, int]:
        """获取统计信息"""
        return self.stats.copy()

    def reset_stats(self):
        """重置统计信息"""
        self.stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'errors': 0
        }


# 便捷函数
async def verify_single(
    url: str,
    username: str,
    password: str,
    config_manager: Optional[ConfigManager] = None
) -> LoginResult:
    """
    快速验证单个目标

    Args:
        url: 目标URL
        username: 用户名
        password: 密码
        config_manager: 配置管理器

    Returns:
        登录结果
    """
    target = TargetInfo(url=url, username=username, password=password)
    
    async with AsyncLoginVerifier(config_manager) as verifier:
        return await verifier.verify_login(target)


async def verify_batch_async(
    targets: List[TargetInfo],
    max_concurrent: int = 5,
    delay: float = 0.5,
    config_manager: Optional[ConfigManager] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None,
    log_callback: Optional[Callable[[str], None]] = None
) -> List[LoginResult]:
    """
    快速批量验证

    Args:
        targets: 目标列表
        max_concurrent: 最大并发数
        delay: 请求间隔
        config_manager: 配置管理器
        progress_callback: 进度回调
        log_callback: 日志回调

    Returns:
        结果列表
    """
    async with AsyncLoginVerifier(
        config_manager=config_manager,
        max_concurrent=max_concurrent,
        progress_callback=progress_callback,
        log_callback=log_callback
    ) as verifier:
        return await verifier.verify_batch(targets, delay)


if __name__ == "__main__":
    # 测试代码
    async def test():
        print("测试异步验证器...")
        
        # 测试单个验证
        result = await verify_single(
            "https://httpbin.org/post",
            "testuser",
            "testpass"
        )
        print(f"单个验证结果: {result.success} - {result.message}")
        
        # 测试批量验证
        targets = [
            TargetInfo(
                url="https://httpbin.org/post",
                username=f"user{i}",
                password=f"pass{i}",
                index=i
            )
            for i in range(1, 4)
        ]
        
        def progress(current, total):
            print(f"进度: {current}/{total} ({current*100//total}%)")
        
        def log(msg):
            print(msg)
        
        results = await verify_batch_async(
            targets,
            max_concurrent=3,
            delay=0.1,
            progress_callback=progress,
            log_callback=log
        )
        
        print(f"\n批量验证完成:")
        for r in results:
            print(f"  {r.url} - {r.success} - {r.message}")
    
    asyncio.run(test())