#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一验证器模块
整合同步和异步验证功能，提供统一的接口
"""

import asyncio
import aiohttp
import requests
import hashlib
import base64
import time
import re
import json
import chardet
from typing import Dict, List, Optional, Tuple, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from urllib.parse import urljoin, urlparse
from datetime import datetime

from .config_manager import ConfigManager, SystemConfig, get_config_manager
from .simple_config import SimpleConfigManager, SimpleSystemConfig, get_simple_config_manager


class VerifyMode(Enum):
    """验证模式"""
    SYNC = "sync"       # 同步模式
    ASYNC = "async"     # 异步模式


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


class UnifiedVerifier:
    """
    统一验证器
    支持同步和异步两种验证模式
    """

    def __init__(
        self,
        config_manager: Optional[Union[ConfigManager, SimpleConfigManager]] = None,
        mode: VerifyMode = VerifyMode.ASYNC,
        max_concurrent: int = 5,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None,
        use_simple_config: bool = True
    ):
        """
        初始化统一验证器

        Args:
            config_manager: 配置管理器
            mode: 验证模式（同步/异步）
            max_concurrent: 最大并发数（异步模式）
            progress_callback: 进度回调函数 (current, total)
            log_callback: 日志回调函数
            use_simple_config: 是否使用简化配置管理器
        """
        if use_simple_config:
            self.config_manager = config_manager or get_simple_config_manager()
        else:
            self.config_manager = config_manager or get_config_manager()

        self.mode = mode
        self.max_concurrent = max_concurrent
        self.progress_callback = progress_callback
        self.log_callback = log_callback

        # 异步会话
        self._async_session: Optional[aiohttp.ClientSession] = None

        # 统计
        self.stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'errors': 0
        }

    def __enter__(self):
        """同步上下文管理器入口"""
        if self.mode == VerifyMode.ASYNC:
            raise RuntimeError("异步模式请使用 async with")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """同步上下文管理器出口"""
        pass

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self._start_async_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self._close_async_session()

    async def _start_async_session(self):
        """启动异步会话"""
        if self._async_session is None:
            # 获取网络配置（兼容两种配置管理器）
            if isinstance(self.config_manager, SimpleConfigManager):
                # SimpleConfigManager
                network_config = self.config_manager
            else:
                # ConfigManager
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

            self._async_session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers=headers
            )

    async def _close_async_session(self):
        """关闭异步会话"""
        if self._async_session:
            await self._async_session.close()
            self._async_session = None

    def _log(self, message: str, level: str = "INFO"):
        """记录日志"""
        if self.log_callback:
            self.log_callback(f"[{level}] {message}")

    def _encrypt_password(self, password: str, method: str) -> str:
        """根据方法加密密码"""
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
        """构建请求体"""
        encrypted_pwd = self._encrypt_password(password, sys_config.password_encryption)

        return {
            sys_config.username_field: username,
            sys_config.password_field: encrypted_pwd
        }

    def _check_response(
        self,
        status_code: int,
        content: str,
        sys_config: SystemConfig
    ) -> Tuple[bool, str]:
        """检查响应是否成功"""
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
                if status_code == ind_value:
                    return False, f"HTTP状态码: {ind_value}"

        # 检查成功指标
        success_count = 0
        for indicator in sys_config.success_indicators:
            ind_type = indicator.get('type')
            ind_value = indicator.get('value')

            if ind_type == 'status_code':
                if status_code == ind_value:
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

    # ==================== 同步验证方法 ====================

    def _verify_sync(self, target: TargetInfo) -> LoginResult:
        """同步验证单个目标"""
        start_time = time.time()

        try:
            sys_config = self.config_manager.get_system_config(target.url)

            # 获取网络配置（兼容两种配置管理器）
            if isinstance(self.config_manager, SimpleConfigManager):
                # SimpleConfigManager
                network_config = self.config_manager
            else:
                # ConfigManager
                network_config = self.config_manager.config.network

            parsed = urlparse(target.url)
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            endpoint = parsed.path if parsed.path and parsed.path != '/' else sys_config.login_endpoint
            full_url = urljoin(base_url, endpoint)

            method = sys_config.method.upper()
            headers = sys_config.headers.copy()
            headers['User-Agent'] = network_config.user_agent

            body = self._build_request_body(target.username, target.password, sys_config)

            # 获取超时和SSL配置
            timeout = getattr(network_config, 'timeout', 30)
            verify_ssl = getattr(network_config, 'verify_ssl', False)

            # 发送请求
            if method == 'POST':
                if sys_config.content_type == 'application/json':
                    response = requests.post(
                        full_url,
                        json=body,
                        headers=headers,
                        timeout=timeout,
                        verify=verify_ssl
                    )
                else:
                    response = requests.post(
                        full_url,
                        data=body,
                        headers=headers,
                        timeout=timeout,
                        verify=verify_ssl
                    )
            else:
                response = requests.get(
                    full_url,
                    params=body,
                    headers=headers,
                    timeout=timeout,
                    verify=verify_ssl
                )

            # 处理编码
            try:
                content = response.text
            except UnicodeDecodeError:
                content_bytes = response.content
                detected = chardet.detect(content_bytes)
                if detected and detected.get('confidence', 0) > 0.5:
                    content = content_bytes.decode(detected.get('encoding', 'utf-8'))
                else:
                    content = content_bytes.decode('gbk', errors='replace')

            elapsed = time.time() - start_time
            success, message = self._check_response(response.status_code, content, sys_config)

            return LoginResult(
                status=LoginStatus.SUCCESS if success else LoginStatus.PASSWORD_ERROR,
                success=success,
                message=message,
                response_time=elapsed,
                url=target.url,
                final_url=response.url,
                page_changed=response.url != target.url,
                details={
                    'system_type': sys_config.name,
                    'status_code': response.status_code,
                    'content_length': len(content)
                }
            )

        except requests.exceptions.Timeout:
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
        except requests.exceptions.RequestException as e:
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

    def verify_batch_sync(
        self,
        targets: List[TargetInfo],
        delay: float = 0.5
    ) -> List[LoginResult]:
        """批量验证（同步模式）"""
        results = []
        total = len(targets)

        for i, target in enumerate(targets, 1):
            result = self._verify_sync(target)

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
                self.progress_callback(i, total)

            # 日志
            if self.log_callback:
                status_icon = "[OK]" if result.success else "[FAIL]"
                self._log(f"{status_icon} {target.url} - {target.username}:{target.password} - {result.message} ({result.response_time:.2f}s)")

            # 延迟
            if delay > 0 and i < total:
                time.sleep(delay)

            results.append(result)

        return results

    # ==================== 异步验证方法 ====================

    async def _get_response_text(self, response: aiohttp.ClientResponse) -> str:
        """获取响应文本内容，自动处理编码问题"""
        try:
            return await response.text()
        except UnicodeDecodeError:
            try:
                content_bytes = await response.read()
                content_type = response.headers.get('Content-Type', '')
                charset = None
                if 'charset=' in content_type:
                    charset = content_type.split('charset=')[-1].strip()

                if charset:
                    try:
                        return content_bytes.decode(charset)
                    except (UnicodeDecodeError, LookupError):
                        pass

                detected = chardet.detect(content_bytes)
                if detected and detected.get('confidence', 0) > 0.5:
                    detected_encoding = detected.get('encoding')
                    if detected_encoding:
                        try:
                            return content_bytes.decode(detected_encoding)
                        except (UnicodeDecodeError, LookupError):
                            pass

                common_encodings = ['gbk', 'gb2312', 'gb18030', 'big5']
                for encoding in common_encodings:
                    try:
                        return content_bytes.decode(encoding)
                    except (UnicodeDecodeError, LookupError):
                        continue

                return content_bytes.decode('iso-8859-1', errors='replace')

            except Exception as e:
                return f"<编码错误: {str(e)[:50]}>"

    async def _verify_async(self, target: TargetInfo) -> LoginResult:
        """异步验证单个目标"""
        start_time = time.time()

        try:
            sys_config = self.config_manager.get_system_config(target.url)

            parsed = urlparse(target.url)
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            endpoint = parsed.path if parsed.path and parsed.path != '/' else sys_config.login_endpoint
            full_url = urljoin(base_url, endpoint)

            method = sys_config.method.upper()
            headers = sys_config.headers.copy()

            if sys_config.content_type == 'application/json':
                headers['Content-Type'] = 'application/json'

            body = self._build_request_body(target.username, target.password, sys_config)

            # 发送请求
            if method == 'POST':
                if sys_config.content_type == 'application/json':
                    async with self._async_session.post(full_url, json=body, headers=headers) as response:
                        content = await self._get_response_text(response)
                        elapsed = time.time() - start_time
                        success, message = self._check_response(response.status, content, sys_config)

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
                    async with self._async_session.post(full_url, data=body, headers=headers) as response:
                        content = await self._get_response_text(response)
                        elapsed = time.time() - start_time
                        success, message = self._check_response(response.status, content, sys_config)

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
                async with self._async_session.get(full_url, params=body, headers=headers) as response:
                    content = await self._get_response_text(response)
                    elapsed = time.time() - start_time
                    success, message = self._check_response(response.status, content, sys_config)

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

    async def verify_batch_async(
        self,
        targets: List[TargetInfo],
        delay: float = 0.5
    ) -> List[LoginResult]:
        """批量验证（异步模式）"""
        if self._async_session is None:
            await self._start_async_session()

        total = len(targets)
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def verify_with_limit(target: TargetInfo) -> LoginResult:
            """带并发限制的验证"""
            async with semaphore:
                result = await self._verify_async(target)

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
                    status_icon = "[OK]" if result.success else "[FAIL]"
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

    # ==================== 统一接口 ====================

    def verify(self, target: TargetInfo) -> LoginResult:
        """
        验证单个目标（自动选择模式）

        Args:
            target: 目标信息

        Returns:
            登录结果
        """
        if self.mode == VerifyMode.ASYNC:
            raise RuntimeError("异步模式请使用 verify_async 或 async with")
        return self._verify_sync(target)

    def verify_batch(
        self,
        targets: List[TargetInfo],
        delay: float = 0.5
    ) -> Union[List[LoginResult], asyncio.coroutine]:
        """
        批量验证（自动选择模式）

        Args:
            targets: 目标列表
            delay: 请求间隔（秒）

        Returns:
            结果列表
        """
        if self.mode == VerifyMode.ASYNC:
            return self.verify_batch_async(targets, delay)
        else:
            return self.verify_batch_sync(targets, delay)

    async def verify_async(self, target: TargetInfo) -> LoginResult:
        """
        异步验证单个目标

        Args:
            target: 目标信息

        Returns:
            登录结果
        """
        if self._async_session is None:
            await self._start_async_session()
        return await self._verify_async(target)

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
def verify_single_sync(
    url: str,
    username: str,
    password: str,
    config_manager: Optional[ConfigManager] = None
) -> LoginResult:
    """快速同步验证单个目标"""
    target = TargetInfo(url=url, username=username, password=password)
    verifier = UnifiedVerifier(config_manager, mode=VerifyMode.SYNC)
    return verifier.verify(target)


async def verify_single_async(
    url: str,
    username: str,
    password: str,
    config_manager: Optional[ConfigManager] = None
) -> LoginResult:
    """快速异步验证单个目标"""
    target = TargetInfo(url=url, username=username, password=password)
    async with UnifiedVerifier(config_manager, mode=VerifyMode.ASYNC) as verifier:
        return await verifier.verify_async(target)


def verify_batch_sync_quick(
    targets: List[TargetInfo],
    config_manager: Optional[ConfigManager] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None,
    log_callback: Optional[Callable[[str], None]] = None
) -> List[LoginResult]:
    """快速同步批量验证"""
    verifier = UnifiedVerifier(
        config_manager,
        mode=VerifyMode.SYNC,
        progress_callback=progress_callback,
        log_callback=log_callback
    )
    return verifier.verify_batch(targets)


async def verify_batch_async_quick(
    targets: List[TargetInfo],
    max_concurrent: int = 5,
    delay: float = 0.5,
    config_manager: Optional[ConfigManager] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None,
    log_callback: Optional[Callable[[str], None]] = None
) -> List[LoginResult]:
    """快速异步批量验证"""
    async with UnifiedVerifier(
        config_manager,
        mode=VerifyMode.ASYNC,
        max_concurrent=max_concurrent,
        progress_callback=progress_callback,
        log_callback=log_callback
    ) as verifier:
        return await verifier.verify_batch(targets, delay)