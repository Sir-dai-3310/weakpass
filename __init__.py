#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WeakPass - 弱口令验证工具
用于安全研究和学习的弱密码检测工具
"""

__version__ = "1.0.0"
__author__ = "Sir-dai-3310"
__license__ = "MIT"
__description__ = "弱口令验证工具 - 用于安全审计和学习"

# 导入核心模块
from .core import (
    # 统一验证器（推荐）
    UnifiedVerifier,
    VerifyMode,
    LoginResult,
    LoginStatus,
    TargetInfo,
    verify_single_sync,
    verify_single_async,
    verify_batch_sync_quick,
    verify_batch_async_quick,
    # 旧版验证器（向后兼容）
    LoginVerifier,
    FormInfo,
    # 验证码识别
    CaptchaRecognizer,
    CaptchaResult,
    # 批量导入
    BatchImporter,
    EnhancedBatchImporter,
    ImportResult,
    ImportFormat,
    get_supported_formats,
    # 配置管理
    ConfigManager,
    get_config_manager,
)

__all__ = [
    '__version__',
    '__author__',
    '__license__',
    '__description__',
    # 统一验证器（推荐）
    'UnifiedVerifier',
    'VerifyMode',
    'LoginResult',
    'LoginStatus',
    'TargetInfo',
    'verify_single_sync',
    'verify_single_async',
    'verify_batch_sync_quick',
    'verify_batch_async_quick',
    # 旧版验证器（向后兼容）
    'LoginVerifier',
    'FormInfo',
    # 验证码识别
    'CaptchaRecognizer',
    'CaptchaResult',
    # 批量导入
    'BatchImporter',
    'EnhancedBatchImporter',
    'ImportResult',
    'ImportFormat',
    'get_supported_formats',
    # 配置管理
    'ConfigManager',
    'get_config_manager',
]

# 兼容性导入 - 保持向后兼容
try:
    from .core import *
except ImportError:
    pass