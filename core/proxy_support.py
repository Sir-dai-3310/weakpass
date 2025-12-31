#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代理支持模块
支持HTTP/HTTPS/SOCKS5代理
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
import random
import json
from pathlib import Path


class ProxyType(Enum):
    """代理类型"""
    HTTP = "http"
    HTTPS = "https"
    SOCKS5 = "socks5"


@dataclass
class ProxyInfo:
    """代理信息"""
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    proxy_type: ProxyType = ProxyType.HTTP
    
    def is_authenticated(self) -> bool:
        """是否需要认证"""
        return bool(self.username and self.password)
    
    def to_url(self) -> str:
        """转换为代理URL"""
        if self.is_authenticated():
            return f"{self.proxy_type.value}://{self.username}:{self.password}@{self.host}:{self.port}"
        else:
            return f"{self.proxy_type.value}://{self.host}:{self.port}"
    
    def to_dict(self) -> Dict[str, str]:
        """转换为代理字典（用于requests/aiohttp）"""
        url = self.to_url()
        if self.proxy_type == ProxyType.SOCKS5:
            return {
                'http': url,
                'https': url
            }
        else:
            return {
                'http': url,
                'https': url
            }


@dataclass
class ProxyPool:
    """代理池"""
    proxies: List[ProxyInfo] = field(default_factory=list)
    enabled: bool = False
    max_failures: int = 3
    rotation_strategy: str = "round_robin"  # round_robin, random, least_used
    
    def __post_init__(self):
        # 跟踪每个代理的失败次数
        self.failures: Dict[int, int] = {}
        self.current_index: int = 0
    
    def add_proxy(self, proxy: ProxyInfo):
        """添加代理"""
        self.proxies.append(proxy)
        self.failures[len(self.proxies) - 1] = 0
    
    def get_proxy(self) -> Optional[ProxyInfo]:
        """获取下一个可用代理"""
        if not self.enabled or not self.proxies:
            return None
        
        # 过滤掉失败的代理
        available = [
            (idx, proxy) for idx, proxy in enumerate(self.proxies)
            if self.failures.get(idx, 0) < self.max_failures
        ]
        
        if not available:
            # 所有代理都失败了，重置
            self.reset_failures()
            available = [(idx, proxy) for idx, proxy in enumerate(self.proxies)]
        
        if not available:
            return None
        
        # 根据策略选择代理
        if self.rotation_strategy == "random":
            idx, proxy = random.choice(available)
        elif self.rotation_strategy == "least_used":
            idx, proxy = min(available, key=lambda x: self.failures.get(x[0], 0))
        else:  # round_robin
            idx, proxy = available[self.current_index % len(available)]
            self.current_index += 1
        
        return proxy
    
    def mark_failure(self, proxy: ProxyInfo):
        """标记代理失败"""
        for idx, p in enumerate(self.proxies):
            if p.host == proxy.host and p.port == proxy.port:
                self.failures[idx] = self.failures.get(idx, 0) + 1
                break
    
    def mark_success(self, proxy: ProxyInfo):
        """标记代理成功"""
        for idx, p in enumerate(self.proxies):
            if p.host == proxy.host and p.port == proxy.port:
                self.failures[idx] = 0
                break
    
    def reset_failures(self):
        """重置失败计数"""
        self.failures = {idx: 0 for idx in range(len(self.proxies))}
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'total_proxies': len(self.proxies),
            'available_proxies': sum(1 for f in self.failures.values() if f < self.max_failures),
            'failed_proxies': sum(1 for f in self.failures.values() if f >= self.max_failures),
            'failures': self.failures.copy()
        }


class ProxyManager:
    """代理管理器"""
    
    def __init__(self):
        self.proxy_pool = ProxyPool()
        self.config_file: Optional[Path] = None
    
    def load_from_file(self, filepath: str) -> bool:
        """
        从文件加载代理配置
        
        Args:
            filepath: 配置文件路径
            
        Returns:
            是否成功
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.config_file = Path(filepath)
            
            # 加载代理池配置
            if 'proxy_pool' in data:
                pool_config = data['proxy_pool']
                self.proxy_pool.enabled = pool_config.get('enabled', False)
                self.proxy_pool.max_failures = pool_config.get('max_failures', 3)
                self.proxy_pool.rotation_strategy = pool_config.get('rotation_strategy', 'round_robin')
                
                # 加载代理列表
                for proxy_data in pool_config.get('proxies', []):
                    proxy_type = ProxyType(proxy_data.get('type', 'http'))
                    proxy = ProxyInfo(
                        host=proxy_data['host'],
                        port=proxy_data['port'],
                        username=proxy_data.get('username'),
                        password=proxy_data.get('password'),
                        proxy_type=proxy_type
                    )
                    self.proxy_pool.add_proxy(proxy)
            
            return True
            
        except Exception as e:
            print(f"加载代理配置失败: {e}")
            return False
    
    def save_to_file(self, filepath: str) -> bool:
        """
        保存代理配置到文件
        
        Args:
            filepath: 配置文件路径
            
        Returns:
            是否成功
        """
        try:
            data = {
                'proxy_pool': {
                    'enabled': self.proxy_pool.enabled,
                    'max_failures': self.proxy_pool.max_failures,
                    'rotation_strategy': self.proxy_pool.rotation_strategy,
                    'proxies': [
                        {
                            'host': p.host,
                            'port': p.port,
                            'username': p.username,
                            'password': p.password,
                            'type': p.proxy_type.value
                        }
                        for p in self.proxy_pool.proxies
                    ]
                }
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            self.config_file = Path(filepath)
            return True
            
        except Exception as e:
            print(f"保存代理配置失败: {e}")
            return False
    
    def add_proxy(
        self,
        host: str,
        port: int,
        username: Optional[str] = None,
        password: Optional[str] = None,
        proxy_type: ProxyType = ProxyType.HTTP
    ):
        """添加代理"""
        proxy = ProxyInfo(
            host=host,
            port=port,
            username=username,
            password=password,
            proxy_type=proxy_type
        )
        self.proxy_pool.add_proxy(proxy)
    
    def enable_proxy(self):
        """启用代理"""
        self.proxy_pool.enabled = True
    
    def disable_proxy(self):
        """禁用代理"""
        self.proxy_pool.enabled = False
    
    def get_next_proxy(self) -> Optional[ProxyInfo]:
        """获取下一个代理"""
        return self.proxy_pool.get_proxy()
    
    def report_result(self, proxy: Optional[ProxyInfo], success: bool):
        """报告代理结果"""
        if proxy:
            if success:
                self.proxy_pool.mark_success(proxy)
            else:
                self.proxy_pool.mark_failure(proxy)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = self.proxy_pool.get_stats()
        stats['enabled'] = self.proxy_pool.enabled
        return stats


# 便捷函数
def create_proxy_from_string(proxy_str: str) -> ProxyInfo:
    """
    从字符串创建代理
    
    Args:
        proxy_str: 代理字符串，如 "http://user:pass@host:port"
        
    Returns:
        ProxyInfo对象
    """
    # 解析协议
    if '://' in proxy_str:
        protocol, rest = proxy_str.split('://', 1)
        proxy_type = ProxyType(protocol.lower())
    else:
        rest = proxy_str
        proxy_type = ProxyType.HTTP
    
    # 解析认证信息
    auth = None
    if '@' in rest:
        auth, rest = rest.rsplit('@', 1)
    
    # 解析主机和端口
    if ':' in rest:
        host, port = rest.rsplit(':', 1)
        port = int(port)
    else:
        host = rest
        port = 8080
    
    # 解析用户名和密码
    username = None
    password = None
    if auth and ':' in auth:
        username, password = auth.split(':', 1)
    elif auth:
        username = auth
    
    return ProxyInfo(
        host=host,
        port=port,
        username=username,
        password=password,
        proxy_type=proxy_type
    )


def create_proxy_pool_from_list(proxy_list: List[str]) -> ProxyPool:
    """
    从代理列表创建代理池
    
    Args:
        proxy_list: 代理字符串列表
        
    Returns:
        ProxyPool对象
    """
    pool = ProxyPool()
    pool.enabled = True
    
    for proxy_str in proxy_list:
        proxy = create_proxy_from_string(proxy_str)
        pool.add_proxy(proxy)
    
    return pool


if __name__ == "__main__":
    # 测试代码
    print("测试代理支持...")
    
    # 创建代理管理器
    manager = ProxyManager()
    
    # 添加代理
    manager.add_proxy("127.0.0.1", 7890, proxy_type=ProxyType.HTTP)
    manager.add_proxy("127.0.0.1", 1080, proxy_type=ProxyType.SOCKS5)
    manager.enable_proxy()
    
    # 获取代理
    proxy = manager.get_next_proxy()
    if proxy:
        print(f"获取代理: {proxy.to_url()}")
    
    # 从字符串创建代理
    proxy_str = "http://user:pass@proxy.example.com:8080"
    proxy = create_proxy_from_string(proxy_str)
    print(f"从字符串创建: {proxy.to_url()}")
    
    # 从列表创建代理池
    proxy_list = [
        "http://proxy1.example.com:8080",
        "http://proxy2.example.com:8080",
        "socks5://proxy3.example.com:1080"
    ]
    pool = create_proxy_pool_from_list(proxy_list)
    print(f"代理池大小: {len(pool.proxies)}")
    
    # 获取统计
    stats = manager.get_stats()
    print(f"统计信息: {stats}")