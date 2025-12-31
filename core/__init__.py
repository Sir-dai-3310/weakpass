#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
弱口令验证工具核心模块
"""

# 导入统一验证器（推荐使用）
from .unified_verifier import (
    UnifiedVerifier,
    VerifyMode,
    LoginResult,
    LoginStatus,
    TargetInfo,
    verify_single_sync,
    verify_single_async,
    verify_batch_sync_quick,
    verify_batch_async_quick
)

# 保留旧版验证器用于向后兼容
try:
    from .enhanced_verifier import (
        EnhancedLoginVerifier as LoginVerifier,
        FormInfo
    )
except ImportError:
    from .login_verifier import (
        LoginVerifier,
        FormInfo
    )

from .captcha_recognizer import (
    CaptchaRecognizer,
    CaptchaResult
)

from .batch_importer import (
    BatchImporter,
    ImportResult,
    ImportFormat,
    get_supported_formats
)

from .enhanced_batch_importer import EnhancedBatchImporter

from .config_manager import (
    ConfigManager,
    get_config_manager
)

__all__ = [
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

__version__ = '2.0.0'