#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化配置管理模块
提供简洁的配置管理，减少配置层级
"""

import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SimpleSystemConfig:
    """系统指纹配置"""
    name: str
    patterns: List[Dict[str, str]]
    login_endpoint: str
    method: str = "POST"
    content_type: str = "application/json"
    username_field: str = "username"
    password_field: str = "password"
    password_encryption: str = "none"
    headers: Dict[str, str] = field(default_factory=dict)
    success_indicators: List[Dict[str, Any]] = field(default_factory=list)
    failure_indicators: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class SimpleConfig:
    """简化配置"""
    # 网络配置
    timeout: int = 30
    max_concurrent: int = 5
    verify_ssl: bool = False
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

    # 扫描配置
    delay_between_requests: float = 0.5
    auto_resume: bool = True

    # 系统配置
    systems: Dict[str, SimpleSystemConfig] = field(default_factory=dict)

    def __post_init__(self):
        """初始化后处理，确保systems字典中的值是SimpleSystemConfig对象"""
        converted_systems = {}
        for sys_id, sys_config in self.systems.items():
            if isinstance(sys_config, dict):
                converted_systems[sys_id] = SimpleSystemConfig(**sys_config)
            else:
                converted_systems[sys_id] = sys_config
        self.systems = converted_systems

    @classmethod
    def from_file(cls, config_path: str) -> 'SimpleConfig':
        """从JSON文件加载配置"""
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        systems = {}
        for sys_id, sys_data in data.get('systems', {}).items():
            systems[sys_id] = SimpleSystemConfig(**sys_data)

        return cls(
            timeout=data.get('timeout', 30),
            max_concurrent=data.get('max_concurrent', 5),
            verify_ssl=data.get('verify_ssl', False),
            user_agent=data.get('user_agent', "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"),
            delay_between_requests=data.get('delay_between_requests', 0.5),
            auto_resume=data.get('auto_resume', True),
            systems=systems
        )

    def to_file(self, config_path: str):
        """保存配置到JSON文件"""
        data = {
            'timeout': self.timeout,
            'max_concurrent': self.max_concurrent,
            'verify_ssl': self.verify_ssl,
            'user_agent': self.user_agent,
            'delay_between_requests': self.delay_between_requests,
            'auto_resume': self.auto_resume,
            'systems': {
                sys_id: {
                    'name': sys_config.name,
                    'patterns': sys_config.patterns,
                    'login_endpoint': sys_config.login_endpoint,
                    'method': sys_config.method,
                    'content_type': sys_config.content_type,
                    'username_field': sys_config.username_field,
                    'password_field': sys_config.password_field,
                    'password_encryption': sys_config.password_encryption,
                    'headers': sys_config.headers,
                    'success_indicators': sys_config.success_indicators,
                    'failure_indicators': sys_config.failure_indicators
                }
                for sys_id, sys_config in self.systems.items()
            }
        }

        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


class SimpleConfigManager:
    """简化配置管理器"""

    DEFAULT_SYSTEMS = {
        "httpbin": {
            "name": "HTTPBin测试",
            "patterns": [
                {"type": "url_contains", "value": "httpbin.org"}
            ],
            "login_endpoint": "/post",
            "method": "POST",
            "content_type": "application/json",
            "username_field": "username",
            "password_field": "password",
            "password_encryption": "none",
            "headers": {},
            "success_indicators": [
                {"type": "status_code", "value": 200},
                {"type": "body_length_gt", "value": 50}
            ],
            "failure_indicators": []
        },
        "shanying_crm": {
            "name": "山鹰CRM系统",
            "patterns": [
                {"type": "url_contains", "value": "shanyingintl"},
                {"type": "url_contains", "value": "crmzzapp"}
            ],
            "login_endpoint": "/api/user/login",
            "method": "POST",
            "content_type": "application/json",
            "username_field": "UserName",
            "password_field": "UserPwd",
            "password_encryption": "none",
            "headers": {
                "X-Source": "4",
                "Accept": "application/json, text/plain, */*"
            },
            "success_indicators": [
                {"type": "status_code", "value": 200},
                {"type": "body_length_gt", "value": 100},
                {"type": "body_not_contains", "value": "Message"}
            ],
            "failure_indicators": [
                {"type": "body_contains", "value": "Message"}
            ]
        },
        "shanying_tms": {
            "name": "山鹰TMS系统",
            "patterns": [
                {"type": "url_contains", "value": "shanyingtms"}
            ],
            "login_endpoint": "/shanyingtms/a/login",
            "method": "POST",
            "content_type": "application/x-www-form-urlencoded",
            "username_field": "username",
            "password_field": "password",
            "password_encryption": "none",
            "headers": {},
            "success_indicators": [
                {"type": "status_code", "value": 200},
                {"type": "body_length_gt", "value": 100}
            ],
            "failure_indicators": []
        },
        "generic": {
            "name": "通用系统",
            "patterns": [],
            "login_endpoint": "/login",
            "method": "POST",
            "content_type": "application/x-www-form-urlencoded",
            "username_field": "username",
            "password_field": "password",
            "password_encryption": "none",
            "headers": {},
            "success_indicators": [
                {"type": "status_code", "value": 200}
            ],
            "failure_indicators": []
        }
    }

    DEFAULT_CONFIG = {
        "timeout": 30,
        "max_concurrent": 5,
        "verify_ssl": False,
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "delay_between_requests": 0.5,
        "auto_resume": True,
        "systems": DEFAULT_SYSTEMS
    }

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置管理器

        Args:
            config_path: 配置文件路径，如果为None则使用默认配置
        """
        if config_path and Path(config_path).exists():
            self.config = SimpleConfig.from_file(config_path)
        else:
            # 转换DEFAULT_CONFIG中的systems字典为SimpleSystemConfig对象
            systems = {}
            for sys_id, sys_data in self.DEFAULT_SYSTEMS.items():
                systems[sys_id] = SimpleSystemConfig(**sys_data)

            self.config = SimpleConfig(
                timeout=self.DEFAULT_CONFIG['timeout'],
                max_concurrent=self.DEFAULT_CONFIG['max_concurrent'],
                verify_ssl=self.DEFAULT_CONFIG['verify_ssl'],
                user_agent=self.DEFAULT_CONFIG['user_agent'],
                delay_between_requests=self.DEFAULT_CONFIG['delay_between_requests'],
                auto_resume=self.DEFAULT_CONFIG['auto_resume'],
                systems=systems
            )

    def get_system_config(self, url: str) -> SimpleSystemConfig:
        """
        根据URL获取系统配置

        Args:
            url: 目标URL

        Returns:
            系统配置
        """
        # 遍历所有系统配置，查找匹配的
        for sys_id, sys_config in self.config.systems.items():
            for pattern in sys_config.patterns:
                pattern_type = pattern.get('type')
                pattern_value = pattern.get('value')

                if pattern_type == 'url_contains':
                    if pattern_value in url:
                        return sys_config

        # 如果没有匹配的，返回通用配置
        return self.config.systems.get('generic', self.config.systems.get('httpbin'))

    def save_config(self, config_path: str):
        """保存配置到文件"""
        self.config.to_file(config_path)

    @property
    def timeout(self) -> int:
        return self.config.timeout

    @property
    def max_concurrent(self) -> int:
        return self.config.max_concurrent

    @property
    def verify_ssl(self) -> bool:
        return self.config.verify_ssl

    @property
    def user_agent(self) -> str:
        return self.config.user_agent

    @property
    def delay_between_requests(self) -> float:
        return self.config.delay_between_requests


# 全局配置管理器实例
_global_config_manager: Optional[SimpleConfigManager] = None


def get_simple_config_manager(config_path: Optional[str] = None) -> SimpleConfigManager:
    """
    获取全局配置管理器实例

    Args:
        config_path: 配置文件路径

    Returns:
        配置管理器实例
    """
    global _global_config_manager
    if _global_config_manager is None:
        _global_config_manager = SimpleConfigManager(config_path)
    return _global_config_manager


def reset_config_manager():
    """重置全局配置管理器"""
    global _global_config_manager
    _global_config_manager = None