#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理模块
统一管理所有配置，避免硬编码
"""

import json
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class NetworkConfig:
    """网络配置"""
    timeout: int = 30
    max_retries: int = 3
    verify_ssl: bool = False
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    proxy: Optional[str] = None


@dataclass
class CaptchaConfig:
    """验证码配置"""
    resize_width: int = 150
    resize_height: int = 50
    ocr_config: str = "--oem 3 --psm 8"
    char_whitelist: str = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    use_gaussian_blur: bool = True
    use_morphology: bool = True
    kernel_size: int = 2
    max_retries: int = 5


@dataclass
class SystemConfig:
    """系统指纹配置"""
    name: str
    patterns: List[Dict[str, str]]
    login_endpoint: str
    method: str = "POST"
    content_type: str = "application/json"
    username_field: str = "username"
    password_field: str = "password"
    password_encryption: str = "none"
    headers: Dict[str, str] = None
    success_indicators: List[Dict[str, Any]] = None
    failure_indicators: List[Dict[str, Any]] = None

    def __post_init__(self):
        if self.headers is None:
            self.headers = {}
        if self.success_indicators is None:
            self.success_indicators = []
        if self.failure_indicators is None:
            self.failure_indicators = []


@dataclass
class ScanConfig:
    """扫描配置"""
    delay_between_requests: float = 0.5
    max_workers: int = 5
    retry_on_error: int = 1
    save_progress: bool = True
    auto_resume: bool = True
    progress_file: str = "scan_progress.json"


@dataclass
class SecurityConfig:
    """安全配置"""
    max_requests_per_minute: int = 60
    enable_rate_limit: bool = True
    log_sensitive_data: bool = False
    mask_password_in_logs: bool = True
    allowed_url_patterns: List[str] = None

    def __post_init__(self):
        if self.allowed_url_patterns is None:
            self.allowed_url_patterns = []


@dataclass
class AppConfig:
    """应用总配置"""
    network: NetworkConfig
    captcha: CaptchaConfig
    scan: ScanConfig
    security: SecurityConfig
    systems: Dict[str, SystemConfig]

    @classmethod
    def from_file(cls, config_path: str) -> 'AppConfig':
        """从JSON文件加载配置"""
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return cls(
            network=NetworkConfig(**data.get('network', {})),
            captcha=CaptchaConfig(**data.get('captcha', {})),
            scan=ScanConfig(**data.get('scan', {})),
            security=SecurityConfig(**data.get('security', {})),
            systems={
                sys_id: SystemConfig(**sys_data)
                for sys_id, sys_data in data.get('systems', {}).items()
            }
        )

    def to_file(self, config_path: str):
        """保存配置到JSON文件"""
        data = {
            'network': asdict(self.network),
            'captcha': asdict(self.captcha),
            'scan': asdict(self.scan),
            'security': asdict(self.security),
            'systems': {
                sys_id: asdict(sys_config)
                for sys_id, sys_config in self.systems.items()
            }
        }
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


class ConfigManager:
    """配置管理器"""
    
    DEFAULT_CONFIG = {
        "network": {
            "timeout": 30,
            "max_retries": 3,
            "verify_ssl": False,
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "proxy": None
        },
        "captcha": {
            "resize_width": 150,
            "resize_height": 50,
            "ocr_config": "--oem 3 --psm 8",
            "char_whitelist": "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
            "use_gaussian_blur": True,
            "use_morphology": True,
            "kernel_size": 2,
            "max_retries": 5
        },
        "scan": {
            "delay_between_requests": 0.5,
            "max_workers": 5,
            "retry_on_error": 1,
            "save_progress": True,
            "auto_resume": True,
            "progress_file": "scan_progress.json"
        },
        "security": {
            "max_requests_per_minute": 60,
            "enable_rate_limit": True,
            "log_sensitive_data": False,
            "mask_password_in_logs": True,
            "allowed_url_patterns": []
        },
        "systems": {
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
                    {"type": "body_contains", "value": "欢迎"},
                    {"type": "body_contains", "value": "dashboard"}
                ],
                "failure_indicators": [
                    {"type": "body_contains", "value": "验证码错误"},
                    {"type": "body_contains", "value": "用户名或密码"}
                ]
            },
            "httpbin": {
                "name": "HTTPBin测试服务",
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
                    {"type": "status_code", "value": 200}
                ],
                "failure_indicators": []
            },
            "generic": {
                "name": "通用登录系统",
                "patterns": [],
                "login_endpoint": "/login",
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
                "failure_indicators": [
                    {"type": "body_contains", "value": "error"},
                    {"type": "body_contains", "value": "failed"},
                    {"type": "status_code", "value": 401}
                ]
            }
        }
    }

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置管理器

        Args:
            config_path: 配置文件路径，如果为None则使用默认配置
        """
        self.config_path = config_path
        self.config: Optional[AppConfig] = None
        
        if config_path and os.path.exists(config_path):
            self.load(config_path)
        else:
            self.config = AppConfig(
                network=NetworkConfig(**self.DEFAULT_CONFIG['network']),
                captcha=CaptchaConfig(**self.DEFAULT_CONFIG['captcha']),
                scan=ScanConfig(**self.DEFAULT_CONFIG['scan']),
                security=SecurityConfig(**self.DEFAULT_CONFIG['security']),
                systems={
                    sys_id: SystemConfig(**sys_data)
                    for sys_id, sys_data in self.DEFAULT_CONFIG['systems'].items()
                }
            )

    def load(self, config_path: str):
        """加载配置文件"""
        self.config_path = config_path
        self.config = AppConfig.from_file(config_path)

    def save(self, config_path: Optional[str] = None):
        """保存配置文件"""
        path = config_path or self.config_path
        if path and self.config:
            self.config.to_file(path)

    def get_system_config(self, url: str) -> SystemConfig:
        """
        根据URL获取系统配置

        Args:
            url: 目标URL

        Returns:
            匹配的系统配置，如果没有匹配则返回通用配置
        """
        url_lower = url.lower()
        
        for sys_id, sys_config in self.config.systems.items():
            if sys_id == "generic":
                continue
            
            patterns = sys_config.patterns
            match_count = 0
            
            for pattern in patterns:
                p_type = pattern.get('type')
                p_value = pattern.get('value', '').lower()
                
                if p_type == 'url_contains':
                    if p_value in url_lower:
                        match_count += 1
            
            # 匹配超过一半的模式则认为识别成功
            if patterns and match_count >= len(patterns) / 2:
                return sys_config
        
        # 返回通用配置
        return self.config.systems.get('generic', SystemConfig(
            name="通用",
            patterns=[],
            login_endpoint="/login",
            method="POST",
            content_type="application/json"
        ))

    def update_network_config(self, **kwargs):
        """更新网络配置"""
        for key, value in kwargs.items():
            if hasattr(self.config.network, key):
                setattr(self.config.network, key, value)

    def update_scan_config(self, **kwargs):
        """更新扫描配置"""
        for key, value in kwargs.items():
            if hasattr(self.config.scan, key):
                setattr(self.config.scan, key, value)

    def add_custom_system(self, sys_id: str, system_config: SystemConfig):
        """添加自定义系统配置"""
        self.config.systems[sys_id] = system_config


# 全局配置管理器实例
_global_config_manager: Optional[ConfigManager] = None


def get_config_manager(config_path: Optional[str] = None) -> ConfigManager:
    """获取全局配置管理器实例"""
    global _global_config_manager
    
    if _global_config_manager is None:
        _global_config_manager = ConfigManager(config_path)
    
    return _global_config_manager


def reset_config_manager():
    """重置全局配置管理器"""
    global _global_config_manager
    _global_config_manager = None


if __name__ == "__main__":
    # 测试代码
    config_manager = ConfigManager()
    
    # 打印默认配置
    print("默认配置:")
    print(json.dumps(config_manager.DEFAULT_CONFIG, indent=2, ensure_ascii=False))
    
    # 测试系统配置匹配
    print("\n系统配置匹配测试:")
    test_urls = [
        "http://crmzzapp.shanyingintl.com:8718/api/user/login",
        "https://tms-tms.shanyingintl.com:8090/shanyingtms/a/login",
        "https://httpbin.org/post",
        "https://example.com/login"
    ]
    
    for url in test_urls:
        sys_config = config_manager.get_system_config(url)
        print(f"  {url}")
        print(f"    -> {sys_config.name} ({sys_config.login_endpoint})")