
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
弱口令扫描器 GUI v3.0
增强版功能:
- 图形用户界面 (GUI)
- 独立的批量目标模式页面
- 智能URL解析（协议/域名/端口/路径）
- 目标系统类型自动检测
- 支持从CSV/TXT文件批量导入
- 配置文件支持
- 批量验证控制（暂停/继续/取消）
- 自动编码检测 (UTF-8/GBK/GB2312)
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import requests
import json
import time
import csv
import os
import hashlib
import base64
import threading
from datetime import datetime
from typing import List, Dict, Tuple, Optional
import re
from urllib.parse import urlparse, urljoin


def detect_encoding(file_path: str) -> str:
    """检测文件编码"""
    encodings = ['utf-8', 'gbk', 'gb2312', 'utf-16', 'latin-1']
    
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                f.read()
            return encoding
        except (UnicodeDecodeError, UnicodeError):
            continue
    
    return 'utf-8'  # 默认UTF-8


def normalize_column_name(name: str) -> str:
    """标准化列名，用于匹配"""
    name = name.lower().strip()
    # 移除BOM和特殊字符
    name = name.replace('\ufeff', '').replace('\u0000', '')
    return name


class URLParser:
    """智能URL解析器"""
    
    @staticmethod
    def parse(url: str) -> Dict:
        """
        解析URL，提取协议、域名、端口、路径
        返回: {'protocol': 'http', 'host': 'example.com', 'port': 8080, 'path': '/api/login', 'full_url': '...'}
        """
        result = {
            'protocol': 'http',
            'host': '',
            'port': 80,
            'path': '',
            'full_url': url
        }
        
        # 补全协议
        if not url.startswith(('http://', 'https://')):
            url = 'http://' + url
            result['full_url'] = url
        
        try:
            parsed = urlparse(url)
            result['protocol'] = parsed.scheme or 'http'
            result['host'] = parsed.hostname or ''
            
            # 端口
            if parsed.port:
                result['port'] = parsed.port
            elif result['protocol'] == 'https':
                result['port'] = 443
            else:
                result['port'] = 80
            
            # 路径
            result['path'] = parsed.path or '/'
            if parsed.query:
                result['path'] += '?' + parsed.query
                
        except Exception as e:
            print(f"URL解析错误: {e}")
        
        return result
    
    @staticmethod
    def get_base_url(url: str) -> str:
        """获取基础URL（协议+域名+端口）"""
        info = URLParser.parse(url)
        port_str = ''
        if info['port'] not in [80, 443]:
            port_str = f":{info['port']}"
        elif info['protocol'] == 'http' and info['port'] != 80:
            port_str = f":{info['port']}"
        elif info['protocol'] == 'https' and info['port'] != 443:
            port_str = f":{info['port']}"
        return f"{info['protocol']}://{info['host']}{port_str}"
    
    @staticmethod
    def get_endpoint(url: str) -> str:
        """获取登录接口路径"""
        info = URLParser.parse(url)
        return info['path'] if info['path'] else '/'


class SystemFingerprint:
    """目标系统指纹识别器"""
    
    # 系统指纹配置
    FINGERPRINTS = {
        'shanyingintl_crm': {
            'name': '山鹰CRM系统',
            'patterns': [
                {'type': 'url_contains', 'value': 'shanyingintl'},
                {'type': 'url_contains', 'value': 'crmzzapp'},
                {'type': 'path_contains', 'value': '/api/user/login'}
            ],
            'config': {
                'login_endpoint': '/api/user/login',
                'method': 'POST',
                'content_type': 'application/json',
                'username_field': 'UserName',
                'password_field': 'UserPwd',
                'password_encryption': 'none',
                'headers': {
                    'X-Source': '4',
                    'Accept': 'application/json, text/plain, */*'
                },
                'success_indicators': [
                    {'type': 'status_code', 'value': 200},
                    {'type': 'body_length_gt', 'value': 100},
                    {'type': 'body_not_contains', 'value': 'Message'}
                ],
                'failure_indicators': [
                    {'type': 'body_contains', 'value': 'Message'}
                ]
            }
        },
        'httpbin_test': {
            'name': 'HTTPBin测试服务',
            'patterns': [
                {'type': 'url_contains', 'value': 'httpbin.org'}
            ],
            'config': {
                'login_endpoint': '/post',
                'method': 'POST',
                'content_type': 'application/json',
                'username_field': 'username',
                'password_field': 'password',
                'password_encryption': 'none',
                'headers': {},
                'success_indicators': [
                    {'type': 'status_code', 'value': 200}
                ],
                'failure_indicators': []
            }
        },
        'generic_json': {
            'name': '通用JSON登录',
            'patterns': [],
            'config': {
                'login_endpoint': '/login',
                'method': 'POST',
                'content_type': 'application/json',
                'username_field': 'username',
                'password_field': 'password',
                'password_encryption': 'none',
                'headers': {},
                'success_indicators': [
                    {'type': 'status_code', 'value': 200},
                    {'type': 'body_length_gt', 'value': 50}
                ],
                'failure_indicators': [
                    {'type': 'body_contains', 'value': 'error'},
                    {'type': 'body_contains', 'value': 'failed'},
                    {'type': 'status_code', 'value': 401}
                ]
            }
        }
    }
    
    @classmethod
    def detect(cls, url: str) -> Tuple[str, str, Dict]:
        """
        检测目标系统类型
        返回: (系统ID, 系统名称, 配置)
        """
        url_lower = url.lower()
        parsed = URLParser.parse(url)
        
        for sys_id, sys_info in cls.FINGERPRINTS.items():
            if sys_id == 'generic_json':  # 跳过通用配置
                continue
            
            patterns = sys_info.get('patterns', [])
            match_count = 0
            
            for pattern in patterns:
                p_type = pattern.get('type')
                p_value = pattern.get('value', '').lower()
                
                if p_type == 'url_contains':
                    if p_value in url_lower:
                        match_count += 1
                elif p_type == 'path_contains':
                    if p_value in parsed['path'].lower():
                        match_count += 1
            
            # 匹配超过一半的模式则认为识别成功
            if patterns and match_count >= len(patterns) / 2:
                return sys_id, sys_info['name'], sys_info['config']
        
        # 返回通用配置
        generic = cls.FINGERPRINTS['generic_json']
        return 'generic_json', generic['name'], generic['config']


class WeakpassScannerCore:
    """核心扫描引擎 - 增强版"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.session = requests.Session()
        self.results = []
        self.stats = {'total': 0, 'success': 0, 'failed': 0, 'errors': 0}
        self.is_running = False
        self.is_paused = False
        self.stop_flag = False
        self._pause_event = threading.Event()
        self._pause_event.set()  # 默认不暂停
        
    def load_config(self, config_path: str) -> bool:
        """从JSON文件加载配置"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
            return True
        except Exception as e:
            print(f"加载配置错误: {e}")
            return False
    
    def encrypt_password(self, password: str, method: str) -> str:
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
    
    def build_request_body(self, username: str, password: str, sys_config: Dict = None) -> str:
        """从模板构建请求体"""
        if sys_config:
            username_field = sys_config.get('username_field', 'username')
            password_field = sys_config.get('password_field', 'password')
            encryption = sys_config.get('password_encryption', 'none')
        else:
            body_template = self.config.get('request', {}).get('body_template', {})
            encryption = self.config.get('request', {}).get('password_encryption', 'none')
            username_field = 'username'
            password_field = 'password'
            
            for key, value in body_template.items():
                if value == '${username}':
                    username_field = key
                elif value == '${password}':
                    password_field = key
        
        encrypted_pwd = self.encrypt_password(password, encryption)
        
        body = {
            username_field: username,
            password_field: encrypted_pwd
        }
        
        return json.dumps(body)
    
    def check_success(self, response, sys_config: Dict = None) -> Tuple[bool, str]:
        """根据配置检查登录是否成功"""
        if sys_config:
            success_indicators = sys_config.get('success_indicators', [])
            failure_indicators = sys_config.get('failure_indicators', [])
        else:
            success_indicators = self.config.get('response', {}).get('success_indicators', [])
            failure_indicators = self.config.get('response', {}).get('failure_indicators', [])
        
        # 首先检查失败指标
        for indicator in failure_indicators:
            ind_type = indicator.get('type')
            ind_value = indicator.get('value')
            
            if ind_type == 'body_contains':
                if ind_value in response.text:
                    try:
                        data = response.json()
                        if isinstance(data, dict) and 'Message' in data:
                            return False, data['Message']
                    except:
                        pass
                    return False, f"包含: {ind_value}"
            elif ind_type == 'status_code':
                if response.status_code == ind_value:
                    return False, f"HTTP {ind_value}"
        
        # 检查成功指标
        success_count = 0
        for indicator in success_indicators:
            ind_type = indicator.get('type')
            ind_value = indicator.get('value')
            
            if ind_type == 'status_code':
                if response.status_code == ind_value:
                    success_count += 1
            elif ind_type == 'body_length_gt':
                if len(response.text) > ind_value:
                    success_count += 1
            elif ind_type == 'body_contains':
                if ind_value in response.text:
                    success_count += 1
            elif ind_type == 'body_not_contains':
                if ind_value not in response.text:
                    success_count += 1
        
        if success_count >= len(success_indicators) // 2 + 1:
            return True, "登录成功"
        
        return False, "未知响应"
    
    def try_login_smart(self, url: str, username: str, password: str) -> Tuple[bool, str, float, str]:
        """
        智能登录尝试 - 自动识别系统类型
        返回: (是否成功, 消息, 响应时间, 系统类型)
        """
        start_time = time.time()
        
        try:
            # 自动检测系统类型
            sys_id, sys_name, sys_config = SystemFingerprint.detect(url)
            
            # 解析URL
            url_info = URLParser.parse(url)
            base_url = URLParser.get_base_url(url)
            
            # 确定登录接口
            # 优先使用URL中的路径，如果路径为空或是根路径，则使用系统配置的接口
            if url_info['path'] and url_info['path'] != '/':
                endpoint = url_info['path']
            else:
                endpoint = sys_config.get('login_endpoint', '/login')
            
            full_url = urljoin(base_url, endpoint)
            
            # 构建请求
            method = sys_config.get('method', 'POST').upper()
            content_type = sys_config.get('content_type', 'application/json')
            
            headers = {
                'Content-Type': content_type,
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            headers.update(sys_config.get('headers', {}))
            
            body = self.build_request_body(username, password, sys_config)
            timeout = self.config.get('scan_settings', {}).get('timeout', 10)
            
            if method == 'POST':
                response = self.session.post(full_url, headers=headers, data=body, timeout=timeout)
            else:
                response = self.session.get(full_url, headers=headers, timeout=timeout)
            
            elapsed = time.time() - start_time
            success, message = self.check_success(response, sys_config)
            
            return success, message, elapsed, sys_name
            
        except requests.exceptions.Timeout:
            return False, "超时", time.time() - start_time, "未知"
        except requests.exceptions.ConnectionError:
            return False, "连接错误", time.time() - start_time, "未知"
        except Exception as e:
            return False, f"错误: {str(e)[:30]}", time.time() - start_time, "未知"
    
    def pause(self):
        """暂停扫描"""
        self.is_paused = True
        self._pause_event.clear()
    
    def resume(self):
        """继续扫描"""
        self.is_paused = False
        self._pause_event.set()
    
    def stop(self):
        """停止扫描"""
        self.stop_flag = True
        self._pause_event.set()  # 确保不会卡在暂停状态
    
    def scan_batch_smart(self, targets: List[Dict], 
                         progress_callback=None, log_callback=None,
                         result_callback=None) -> List[Dict]:
        """
        智能批量目标扫描
        targets: [{'url': '...', 'username': '...', 'password': '...'}]
        """
        self.is_running = True
        self.is_paused = False
        self.stop_flag = False
        self._pause_event.set()
        self.results = []
        self.stats = {'total': 0, 'success': 0, 'failed': 0, 'errors': 0}
        
        delay = self.config.get('scan_settings', {}).get('delay_between_requests', 0.5)
        total = len(targets)
        
        for i, target in enumerate(targets):
            # 检查停止标志
            if self.stop_flag:
                if log_callback:
                    log_callback("[信息] 扫描已停止")
                break
            
            # 检查暂停
            self._pause_event.wait()
            
            url = target.get('url', '')
            username = target.get('username', '')
            password = target.get('password', '')
            
            if not url or not username:
                self.stats['errors'] += 1
                if log_callback:
                    log_callback(f"[跳过] 无效目标: URL={url}, 用户名={username}")
                if progress_callback:
                    progress_callback(i + 1, total)
                continue
            
            success, message, elapsed, sys_type = self.try_login_smart(url, username, password)
            
            result = {
                'url': url,
                'username': username,
                'password': password,
                'success': success,
                'message': message,
                'response_time': round(elapsed, 3),
                'system_type': sys_type,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            self.stats['total'] += 1
            if success:
                self.stats['success'] += 1
                self.results.append(result)
                if log_callback:
                    log_callback(f"[成功] {url} - {username}:{password} [{sys_type}] ({elapsed:.2f}秒)")
                if result_callback:
                    result_callback(result)
            elif '错误' in message or '超时' in message or '连接' in message:
                self.stats['errors'] += 1
                if log_callback:
                    log_callback(f"[错误] {url} - {username}:{password} - {message}")
            else:
                self.stats['failed'] += 1
            
            if progress_callback:
                progress_callback(i + 1, total)
            
            if delay > 0 and i < total - 1 and not self.stop_flag:
                time.sleep(delay)
        
        self.is_running = False
        return self.results


class BatchTargetPage(ttk.Frame):
    """独立的批量目标模式页面"""
    
    def __init__(self, parent, scanner: WeakpassScannerCore, log_callback=None,
                 scan_complete_callback=None, results_frame=None, notebook=None):
        super().__init__(parent)
        self.scanner = scanner
        self.log_callback = log_callback
        self.scan_complete_callback = scan_complete_callback  # 扫描完成时的回调
        self.results_frame = results_frame  # 结果页面引用
        self.notebook = notebook  # Notebook引用，用于切换标签页
        self.batch_targets = []
        self.scan_thread = None
        
        self.setup_ui()
    
    def setup_ui(self):
        """设置UI"""
        # 主容器使用PanedWindow实现可调整大小
        main_pane = ttk.PanedWindow(self, orient=tk.VERTICAL)
        main_pane.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 上半部分: 导入和预览
        top_frame = ttk.Frame(main_pane)
        main_pane.add(top_frame, weight=3)
        
        # 下半部分: 控制和日志
        bottom_frame = ttk.Frame(main_pane)
        main_pane.add(bottom_frame, weight=2)
        
        self.setup_import_section(top_frame)
        self.setup_control_section(bottom_frame)
    
    def setup_import_section(self, parent):
        """设置导入和预览区域"""
        # 说明框
        info_frame = ttk.LabelFrame(parent, text="📋 使用说明")
        info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        info_text = """批量目标模式支持CSV文件导入，每行包含一个完整的测试目标：
• URL列: 完整的登录接口地址 (如: http://example.com:8080/api/login)
• 用户名列: 待测试的用户名
• 密码列: 待测试的密码

✨ 智能功能:
• 自动识别CSV文件编码 (UTF-8/GBK/GB2312)
• 自动解析URL (协议/域名/端口/路径)
• 自动检测目标系统类型并匹配验证逻辑"""
        
        info_label = ttk.Label(info_frame, text=info_text, justify=tk.LEFT)
        info_label.pack(padx=10, pady=5, anchor=tk.W)
        
        # 导入控制栏
        import_frame = ttk.Frame(parent)
        import_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(import_frame, text="📂 导入CSV文件", command=self.import_csv, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(import_frame, text="➕ 手动添加", command=self.add_target_dialog, width=12).pack(side=tk.LEFT, padx=5)
        ttk.Button(import_frame, text="✏️ 编辑选中", command=self.edit_selected, width=12).pack(side=tk.LEFT, padx=5)
        ttk.Button(import_frame, text="🗑️ 删除选中", command=self.delete_selected, width=12).pack(side=tk.LEFT, padx=5)
        ttk.Button(import_frame, text="🧹 清空全部", command=self.clear_all, width=12).pack(side=tk.LEFT, padx=5)
        
        # 统计标签
        self.stats_label = ttk.Label(import_frame, text="📊 已导入: 0 个目标")
        self.stats_label.pack(side=tk.RIGHT, padx=10)
        
        # 数据预览表格
        preview_frame = ttk.LabelFrame(parent, text="📋 目标列表预览 (双击编辑)")
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 表格列定义
        columns = ("index", "url", "protocol", "host", "port", "path", "username", "password", "system_type")
        self.tree = ttk.Treeview(preview_frame, columns=columns, show="headings", height=12)
        
        # 设置列标题和宽度
        col_configs = [
            ("index", "#", 40),
            ("url", "完整URL", 250),
            ("protocol", "协议", 50),
            ("host", "主机", 120),
            ("port", "端口", 50),
            ("path", "接口路径", 100),
            ("username", "用户名", 100),
            ("password", "密码", 100),
            ("system_type", "系统类型", 100)
        ]
        
        for col_id, col_name, col_width in col_configs:
            self.tree.heading(col_id, text=col_name, command=lambda c=col_id: self.sort_column(c))
            self.tree.column(col_id, width=col_width, minwidth=30)
        
        # 滚动条
        y_scroll = ttk.Scrollbar(preview_frame, orient=tk.VERTICAL, command=self.tree.yview)
        x_scroll = ttk.Scrollbar(preview_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        
        # 布局
        self.tree.grid(row=0, column=0, sticky='nsew')
        y_scroll.grid(row=0, column=1, sticky='ns')
        x_scroll.grid(row=1, column=0, sticky='ew')
        
        preview_frame.grid_rowconfigure(0, weight=1)
        preview_frame.grid_columnconfigure(0, weight=1)
        
        # 双击编辑事件
        self.tree.bind('<Double-1>', self.on_double_click)
    
    def setup_control_section(self, parent):
        """设置控制和日志区域"""
        # 扫描控制栏
        control_frame = ttk.LabelFrame(parent, text="🎮 扫描控制")
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.start_btn = ttk.Button(btn_frame, text="▶️ 开始扫描", command=self.start_scan, width=12)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.pause_btn = ttk.Button(btn_frame, text="⏸️ 暂停", command=self.pause_scan, width=10, state=tk.DISABLED)
        self.pause_btn.pack(side=tk.LEFT, padx=5)
        
        self.resume_btn = ttk.Button(btn_frame, text="▶️ 继续", command=self.resume_scan, width=10, state=tk.DISABLED)
        self.resume_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(btn_frame, text="⏹️ 停止", command=self.stop_scan, width=10, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        # 分隔
        ttk.Separator(btn_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        # 扫描设置
        ttk.Label(btn_frame, text="超时(秒):").pack(side=tk.LEFT)
        self.timeout_var = tk.StringVar(value="10")
        ttk.Entry(btn_frame, textvariable=self.timeout_var, width=5).pack(side=tk.LEFT, padx=2)
        
        ttk.Label(btn_frame, text="间隔(秒):").pack(side=tk.LEFT, padx=(10, 0))
        self.delay_var = tk.StringVar(value="0.5")
        ttk.Entry(btn_frame, textvariable=self.delay_var, width=5).pack(side=tk.LEFT, padx=2)
        
        # 进度条
        progress_frame = ttk.Frame(control_frame)
        progress_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100, length=400)
        self.progress_bar.pack(side=tk.LEFT, padx=5)
        
        self.progress_label = ttk.Label(progress_frame, text="0/0 (0%)")
        self.progress_label.pack(side=tk.LEFT, padx=10)
        
        self.status_label = ttk.Label(progress_frame, text="状态: 就绪")
        self.status_label.pack(side=tk.RIGHT, padx=10)
        
        # 日志区域
        log_frame = ttk.LabelFrame(parent, text="📝 扫描日志")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, state=tk.NORMAL)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 日志控制
        log_btn_frame = ttk.Frame(log_frame)
        log_btn_frame.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Button(log_btn_frame, text="清空日志", command=self.clear_log, width=10).pack(side=tk.LEFT)
        ttk.Button(log_btn_frame, text="导出日志", command=self.export_log, width=10).pack(side=tk.LEFT, padx=5)
    
    def log(self, message: str):

        """添加日志消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        
        if self.log_callback:
            self.log_callback(message)
    
    def clear_log(self):
        """清空日志"""
        self.log_text.delete(1.0, tk.END)
    
    def export_log(self):
        """导出日志"""
        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt")]
        )
        if filepath:
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(self.log_text.get(1.0, tk.END))
                self.log(f"日志已导出到: {filepath}")
            except Exception as e:
                messagebox.showerror("错误", f"导出失败: {e}")
    
    def import_csv(self):
        """导入CSV文件"""
        filepath = filedialog.askopenfilename(
            filetypes=[("CSV文件", "*.csv"), ("所有文件", "*.*")]
        )
        if not filepath:
            return
        
        try:
            # 检测文件编码
            encoding = detect_encoding(filepath)
            self.log(f"检测到文件编码: {encoding}")
            
            # 读取CSV文件
            with open(filepath, 'r', encoding=encoding) as f:
                content = f.read()
            
            # 解析CSV
            lines = content.strip().split('\n')
            if len(lines) < 2:
                messagebox.showerror("错误", "CSV文件至少需要包含标题行和一行数据")
                return
            
            # 解析标题行
            header = lines[0].replace('\ufeff', '')
            columns = [normalize_column_name(col.strip().strip('"')) for col in header.split(',')]
            
            # 查找列索引
            url_idx, user_idx, pwd_idx = -1, -1, -1
            
            url_names = ['url', '地址', 'target', '目标', 'host', '主机', '链接', 'link']
            user_names = ['username', 'user', '用户名', '账号', 'account', 'login', '登录名']
            pwd_names = ['password', 'pwd', 'pass', '密码', 'passwd', '口令']
            
            for i, col in enumerate(columns):
                if any(name in col for name in url_names):
                    url_idx = i
                elif any(name in col for name in user_names):
                    user_idx = i
                elif any(name in col for name in pwd_names):
                    pwd_idx = i
            
            if url_idx == -1 or user_idx == -1 or pwd_idx == -1:
                if len(columns) >= 3:
                    url_idx, user_idx, pwd_idx = 0, 1, 2
                    self.log("警告: 未能识别列名，按默认顺序(URL,用户名,密码)解析")
                else:
                    messagebox.showerror("错误", f"无法识别CSV列。检测到的列: {columns}\n需要: URL, 用户名, 密码")
                    return
            
            self.log(f"列映射: URL={columns[url_idx]}, 用户名={columns[user_idx]}, 密码={columns[pwd_idx]}")
            
            # 清空现有数据
            self.batch_targets = []
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            # 解析数据行
            for line_num, line in enumerate(lines[1:], start=2):
                if not line.strip():
                    continue
                
                parts = line.split(',')
                if len(parts) < max(url_idx, user_idx, pwd_idx) + 1:
                    self.log(f"警告: 第{line_num}行格式不正确，跳过")
                    continue
                
                url = parts[url_idx].strip().strip('"')
                username = parts[user_idx].strip().strip('"')
                password = parts[pwd_idx].strip().strip('"') if pwd_idx < len(parts) else ''
                
                if url and username:
                    self.add_target(url, username, password)
            
            self.update_stats()
            self.log(f"成功导入 {len(self.batch_targets)} 个目标")
            
            if len(self.batch_targets) > 0:
                messagebox.showinfo("成功", f"成功导入 {len(self.batch_targets)} 个目标")
            
        except Exception as e:
            messagebox.showerror("错误", f"导入CSV失败: {e}")
            self.log(f"导入错误: {e}")
    
    def add_target(self, url: str, username: str, password: str):
        """添加一个目标"""
        # 解析URL
        url_info = URLParser.parse(url)
        
        # 检测系统类型
        sys_id, sys_name, _ = SystemFingerprint.detect(url)
        
        target = {
            'url': url_info['full_url'],
            'username': username,
            'password': password,
            'url_info': url_info,
            'system_type': sys_name
        }
        
        self.batch_targets.append(target)
        
        # 添加到表格
        index = len(self.batch_targets)
        self.tree.insert("", tk.END, values=(
            index,
            url_info['full_url'],
            url_info['protocol'],
            url_info['host'],
            url_info['port'],
            url_info['path'],
            username,
            password,
            sys_name
        ))
    
    def add_target_dialog(self):
        """手动添加目标对话框"""
        dialog = tk.Toplevel(self)
        dialog.title("添加目标")
        dialog.geometry("450x200")
        dialog.transient(self)
        dialog.grab_set()
        
        # 输入字段
        ttk.Label(dialog, text="URL:").grid(row=0, column=0, padx=10, pady=10, sticky=tk.W)
        url_entry = ttk.Entry(dialog, width=50)
        url_entry.grid(row=0, column=1, padx=10, pady=10)
        url_entry.insert(0, "http://")
        
        ttk.Label(dialog, text="用户名:").grid(row=1, column=0, padx=10, pady=10, sticky=tk.W)
        user_entry = ttk.Entry(dialog, width=50)
        user_entry.grid(row=1, column=1, padx=10, pady=10)
        
        ttk.Label(dialog, text="密码:").grid(row=2, column=0, padx=10, pady=10, sticky=tk.W)
        pwd_entry = ttk.Entry(dialog, width=50)
        pwd_entry.grid(row=2, column=1, padx=10, pady=10)
        
        def on_add():
            url = url_entry.get().strip()
            username = user_entry.get().strip()
            password = pwd_entry.get().strip()
            
            if not url or not username:
                messagebox.showwarning("警告", "URL和用户名不能为空")
                return
            
            self.add_target(url, username, password)
            self.update_stats()
            self.log(f"手动添加目标: {url} - {username}")
            dialog.destroy()
        
        btn_frame = ttk.Frame(dialog)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=20)
        
        ttk.Button(btn_frame, text="添加", command=on_add).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="取消", command=dialog.destroy).pack(side=tk.LEFT, padx=10)
    
    def edit_selected(self):
        """编辑选中的目标"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("警告", "请先选择要编辑的目标")
            return
        
        item = selected[0]
        values = self.tree.item(item, 'values')
        index = int(values[0]) - 1
        
        if index < 0 or index >= len(self.batch_targets):
            return
        
        dialog = tk.Toplevel(self)
        dialog.title("编辑目标")
        dialog.geometry("450x200")
        dialog.transient(self)
        dialog.grab_set()
        
        # 输入字段
        ttk.Label(dialog, text="URL:").grid(row=0, column=0, padx=10, pady=10, sticky=tk.W)
        url_entry = ttk.Entry(dialog, width=50)
        url_entry.grid(row=0, column=1, padx=10, pady=10)
        url_entry.insert(0, values[1])
        
        ttk.Label(dialog, text="用户名:").grid(row=1, column=0, padx=10, pady=10, sticky=tk.W)
        user_entry = ttk.Entry(dialog, width=50)
        user_entry.grid(row=1, column=1, padx=10, pady=10)
        user_entry.insert(0, values[6])
        
        ttk.Label(dialog, text="密码:").grid(row=2, column=0, padx=10, pady=10, sticky=tk.W)
        pwd_entry = ttk.Entry(dialog, width=50)
        pwd_entry.grid(row=2, column=1, padx=10, pady=10)
        pwd_entry.insert(0, values[7])
        
        def on_save():
            url = url_entry.get().strip()
            username = user_entry.get().strip()
            password = pwd_entry.get().strip()
            
            if not url or not username:
                messagebox.showwarning("警告", "URL和用户名不能为空")
                return
            
            # 更新数据
            url_info = URLParser.parse(url)
            sys_id, sys_name, _ = SystemFingerprint.detect(url)
            
            self.batch_targets[index] = {
                'url': url_info['full_url'],
                'username': username,
                'password': password,
                'url_info': url_info,
                'system_type': sys_name
            }
            
            # 更新表格
            self.tree.item(item, values=(
                index + 1,
                url_info['full_url'],
                url_info['protocol'],
                url_info['host'],
                url_info['port'],
                url_info['path'],
                username,
                password,
                sys_name
            ))
            
            self.log(f"已更新目标 #{index + 1}")
            dialog.destroy()
        
        btn_frame = ttk.Frame(dialog)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=20)
        
        ttk.Button(btn_frame, text="保存", command=on_save).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="取消", command=dialog.destroy).pack(side=tk.LEFT, padx=10)
    
    def on_double_click(self, event):
        """双击编辑"""
        self.edit_selected()
    
    def delete_selected(self):
        """删除选中的目标"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("警告", "请先选择要删除的目标")
            return
        
        if messagebox.askyesno("确认", f"确定要删除选中的 {len(selected)} 个目标吗?"):
            # 按索引从大到小删除，避免索引偏移
            indices = []
            for item in selected:
                values = self.tree.item(item, 'values')
                indices.append(int(values[0]) - 1)
            
            indices.sort(reverse=True)
            for idx in indices:
                if 0 <= idx < len(self.batch_targets):
                    del self.batch_targets[idx]
            
            # 重新加载表格
            self.reload_tree()
            self.update_stats()
            self.log(f"已删除 {len(selected)} 个目标")
    
    def clear_all(self):
        """清空所有目标"""
        if not self.batch_targets:
            return
        
        if messagebox.askyesno("确认", "确定要清空所有目标吗?"):
            self.batch_targets = []
            for item in self.tree.get_children():
                self.tree.delete(item)
            self.update_stats()
            self.log("已清空所有目标")
    
    def reload_tree(self):
        """重新加载表格数据"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        for i, target in enumerate(self.batch_targets):
            url_info = target.get('url_info', URLParser.parse(target['url']))
            self.tree.insert("", tk.END, values=(
                i + 1,
                target['url'],
                url_info['protocol'],
                url_info['host'],
                url_info['port'],
                url_info['path'],
                target['username'],
                target['password'],
                target.get('system_type', '未知')
            ))
    
    def update_stats(self):
        """更新统计信息"""
        count = len(self.batch_targets)
        self.stats_label.config(text=f"📊 已导入: {count} 个目标")
    
    def sort_column(self, col):
        """点击表头排序"""
        items = [(self.tree.set(item, col), item) for item in self.tree.get_children('')]
        items.sort()
        
        for index, (val, item) in enumerate(items):
            self.tree.move(item, '', index)
    
    def update_progress(self, current: int, total: int):
        """更新进度条"""
        percentage = (current / total) * 100 if total > 0 else 0
        self.progress_var.set(percentage)
        self.progress_label.config(text=f"{current}/{total} ({percentage:.1f}%)")
    
    def start_scan(self):
        """开始扫描"""
        if not self.batch_targets:
            messagebox.showwarning("警告", "没有可扫描的目标!\n请先导入CSV文件或手动添加目标")
            return
        
        # 更新配置
        try:
            timeout = int(self.timeout_var.get())
            delay = float(self.delay_var.get())
        except ValueError:
            timeout, delay = 10, 0.5
        
        self.scanner.config = {
            'scan_settings': {
                'timeout': timeout,
                'delay_between_requests': delay
            }
        }
        
        # 更新UI状态
        self.start_btn.config(state=tk.DISABLED)
        self.pause_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.NORMAL)
        self.resume_btn.config(state=tk.DISABLED)
        self.status_label.config(text="状态: 扫描中...")
        
        self.log(f"开始批量扫描，共 {len(self.batch_targets)} 个目标...")
        
        def scan_thread():
            try:
                results = self.scanner.scan_batch_smart(
                    self.batch_targets,
                    progress_callback=lambda c, t: self.after(0, lambda: self.update_progress(c, t)),
                    log_callback=lambda msg: self.after(0, lambda: self.log(msg)),
                    result_callback=lambda r: self.after(0, lambda: self.on_result(r))
                )
                self.after(0, lambda: self.scan_complete(results))
            except Exception as e:
                self.after(0, lambda: self.log(f"错误: {e}"))
                self.after(0, lambda: self.scan_complete([]))
        
        self.scan_thread = threading.Thread(target=scan_thread)
        self.scan_thread.start()
    
    def pause_scan(self):
        """暂停扫描"""
        self.scanner.pause()
        self.pause_btn.config(state=tk.DISABLED)
        self.resume_btn.config(state=tk.NORMAL)
        self.status_label.config(text="状态: 已暂停")
        self.log("[信息] 扫描已暂停")
    
    def resume_scan(self):
        """继续扫描"""
        self.scanner.resume()
        self.pause_btn.config(state=tk.NORMAL)
        self.resume_btn.config(state=tk.DISABLED)
        self.status_label.config(text="状态: 扫描中...")
        self.log("[信息] 扫描已继续")
    
    def stop_scan(self):
        """停止扫描"""
        self.scanner.stop()
        self.log("[信息] 正在停止扫描...")
    
    def on_result(self, result: Dict):
        """收到扫描结果时的回调"""
        pass  # 可以在这里添加实时结果处理
    
    def scan_complete(self, results: List[Dict]):
        """扫描完成"""
        self.start_btn.config(state=tk.NORMAL)
        self.pause_btn.config(state=tk.DISABLED)
        self.resume_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.DISABLED)
        
        stats = self.scanner.stats
        self.status_label.config(text=f"状态: 完成 - 成功:{stats['success']} 失败:{stats['failed']} 错误:{stats['errors']}")
        self.log(f"扫描完成! 发现 {stats['success']} 个弱口令")
        
        # 调用扫描完成回调，刷新结果页面
        if self.scan_complete_callback:
            self.scan_complete_callback()
        
        if stats['success'] > 0:
            # 自动切换到结果页面
            if self.notebook and self.results_frame:
                self.notebook.select(self.results_frame)
            messagebox.showinfo("扫描完成", f"发现 {stats['success']} 个弱口令!\n已自动切换到结果页面")


class WeakpassScannerGUI:
    """弱口令扫描器GUI应用 - v3.0"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("弱口令扫描器 v3.0 - 增强版")
        self.root.geometry("1100x800")
        self.root.minsize(900, 700)
        
        self.scanner = WeakpassScannerCore()
        
        self.setup_ui()
    
    def setup_ui(self):
        """设置用户界面"""
        # 创建标签页
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 标签页4: 结果 (需要先创建，供批量模式回调)
        self.results_frame = ttk.Frame(self.notebook)
        
        # 标签页1: 批量目标模式 (主要功能页面)
        self.batch_page = BatchTargetPage(
            self.notebook,
            self.scanner,
            log_callback=self.log,
            scan_complete_callback=self.refresh_results,
            results_frame=self.results_frame,
            notebook=self.notebook
        )
        self.notebook.add(self.batch_page, text="📋 批量目标模式")
        
        # 标签页2: 单目标模式
        self.single_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.single_frame, text="🎯 单目标模式")
        self.setup_single_tab()
        
        # 标签页3: 配置
        self.config_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.config_frame, text="⚙️ 配置")
        self.setup_config_tab()
        
        # 标签页4: 结果 (已在前面创建)
        self.notebook.add(self.results_frame, text="📊 扫描结果")
        self.setup_results_tab()
        
        # 标签页5: 关于
        self.about_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.about_frame, text="ℹ️ 关于")
        self.setup_about_tab()
        
        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        self.status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)
    
    def setup_single_tab(self):
        """设置单目标扫描标签页"""
        # 目标配置框
        target_frame = ttk.LabelFrame(self.single_frame, text="🎯 目标配置")
        target_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(target_frame, text="目标URL:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.url_var = tk.StringVar(value="http://")
        self.url_entry = ttk.Entry(target_frame, textvariable=self.url_var, width=70)
        self.url_entry.grid(row=0, column=1, columnspan=2, padx=5, pady=5, sticky=tk.W)
        
        ttk.Button(target_frame, text="🔍 检测系统类型", command=self.detect_system).grid(row=0, column=3, padx=5)
        
        self.system_type_label = ttk.Label(target_frame, text="系统类型: 未检测")
        self.system_type_label.grid(row=1, column=0, columnspan=4, padx=5, pady=5, sticky=tk.W)
        
        # 凭证配置框
        cred_frame = ttk.LabelFrame(self.single_frame, text="🔑 凭证字典")
        cred_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 用户名区域
        user_frame = ttk.Frame(cred_frame)
        user_frame.pack(fill=tk.BOTH, expand=True, side=tk.LEFT, padx=5, pady=5)
        
        ttk.Label(user_frame, text="用户名 (每行一个):").pack(anchor=tk.W)
        self.username_text = scrolledtext.ScrolledText(user_frame, width=30, height=10)
        self.username_text.pack(fill=tk.BOTH, expand=True)
        self.username_text.insert(tk.END, "admin\ntest\nuser")
        
        user_btn_frame = ttk.Frame(user_frame)
        user_btn_frame.pack(fill=tk.X)
        ttk.Button(user_btn_frame, text="从文件加载", 
                  command=lambda: self.load_file_to_text(self.username_text)).pack(side=tk.LEFT, padx=2)
        ttk.Button(user_btn_frame, text="清空", 
                  command=lambda: self.username_text.delete(1.0, tk.END)).pack(side=tk.LEFT, padx=2)
        
        # 密码区域
        pwd_frame = ttk.Frame(cred_frame)
        pwd_frame.pack(fill=tk.BOTH, expand=True, side=tk.LEFT, padx=5, pady=5)
        
        ttk.Label(pwd_frame, text="密码 (每行一个):").pack(anchor=tk.W)
        self.password_text = scrolledtext.ScrolledText(pwd_frame, width=30, height=10)
        self.password_text.pack(fill=tk.BOTH, expand=True)
        self.password_text.insert(tk.END, "123456\npassword\nadmin\nadmin123")
        
        pwd_btn_frame = ttk.Frame(pwd_frame)
        pwd_btn_frame.pack(fill=tk.X)
        ttk.Button(pwd_btn_frame, text="从文件加载", 
                  command=lambda: self.load_file_to_text(self.password_text)).pack(side=tk.LEFT, padx=2)
        ttk.Button(pwd_btn_frame, text="清空", 
                  command=lambda: self.password_text.delete(1.0, tk.END)).pack(side=tk.LEFT, padx=2)
        
        # 控制区域
        control_frame = ttk.Frame(self.single_frame)
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.single_start_btn = ttk.Button(control_frame, text="▶️ 开始扫描", command=self.start_single_scan)
        self.single_start_btn.pack(side=tk.LEFT, padx=5)
        
        self.single_stop_btn = ttk.Button(control_frame, text="⏹️ 停止", command=self.stop_single_scan, state=tk.DISABLED)
        self.single_stop_btn.pack(side=tk.LEFT, padx=5)
        
        # 进度条
        self.single_progress_var = tk.DoubleVar(value=0)
        self.single_progress_bar = ttk.Progressbar(control_frame, variable=self.single_progress_var, 
                                                   maximum=100, length=300)
        self.single_progress_bar.pack(side=tk.LEFT, padx=10)
        
        self.single_progress_label = ttk.Label(control_frame, text="0/0 (0%)")
        self.single_progress_label.pack(side=tk.LEFT)
        
        # 日志区域
        log_frame = ttk.LabelFrame(self.single_frame, text="📝 扫描日志")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.single_log_text = scrolledtext.ScrolledText(log_frame, height=8)
        self.single_log_text.pack(fill=tk.BOTH, expand=True)
    
    def setup_config_tab(self):
        """设置配置标签页"""
        # 配置文件区域
        file_frame = ttk.LabelFrame(self.config_frame, text="📁 配置文件")
        file_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(file_frame, text="加载配置", command=self.load_config_file).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(file_frame, text="保存配置", command=self.save_config_file).pack(side=tk.LEFT, padx=5, pady=5)
        
        # 请求设置
        req_frame = ttk.LabelFrame(self.config_frame, text="📨 请求设置")
        req_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(req_frame, text="用户名字段:").grid(row=0, column=0, padx=5, pady=2, sticky=tk.W)
        self.username_field_var = tk.StringVar(value="username")
        ttk.Entry(req_frame, textvariable=self.username_field_var, width=20).grid(row=0, column=1, padx=5, pady=2)
        
        ttk.Label(req_frame, text="密码字段:").grid(row=0, column=2, padx=5, pady=2, sticky=tk.W)
        self.password_field_var = tk.StringVar(value="password")
        ttk.Entry(req_frame, textvariable=self.password_field_var, width=20).grid(row=0, column=3, padx=5, pady=2)
        
        ttk.Label(req_frame, text="密码加密方式:").grid(row=1, column=0, padx=5, pady=2, sticky=tk.W)
        self.encryption_var = tk.StringVar(value="none")
        encryption_combo = ttk.Combobox(req_frame, textvariable=self.encryption_var, 
                                       values=["none", "md5", "md5_upper", "sha1", "sha256", "base64", "md5_base64"])
        encryption_combo.grid(row=1, column=1, padx=5, pady=2)
        
        # 自定义请求头
        header_frame = ttk.LabelFrame(self.config_frame, text="📋 自定义请求头 (JSON格式)")
        header_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.headers_text = scrolledtext.ScrolledText(header_frame, height=8)
        self.headers_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.headers_text.insert(tk.END, json.dumps({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept": "application/json, text/plain, */*"
        }, indent=2))
        
        # 扫描设置
        scan_frame = ttk.LabelFrame(self.config_frame, text="⚙️ 扫描设置")
        scan_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(scan_frame, text="超时时间(秒):").grid(row=0, column=0, padx=5, pady=2)
        self.cfg_timeout_var = tk.StringVar(value="10")
        ttk.Entry(scan_frame, textvariable=self.cfg_timeout_var, width=10).grid(row=0, column=1, padx=5, pady=2)
        
        ttk.Label(scan_frame, text="请求间隔(秒):").grid(row=0, column=2, padx=5, pady=2)
        self.cfg_delay_var = tk.StringVar(value="0.5")
        ttk.Entry(scan_frame, textvariable=self.cfg_delay_var, width=10).grid(row=0, column=3, padx=5, pady=2)
    
    def setup_results_tab(self):
        """设置结果标签页"""
        # 结果统计
        stats_frame = ttk.LabelFrame(self.results_frame, text="📈 统计信息")
        stats_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.result_stats_label = ttk.Label(stats_frame, text="总计: 0 | 成功: 0 | 失败: 0 | 错误: 0")
        self.result_stats_label.pack(padx=10, pady=5)
        
        # 结果表格
        table_frame = ttk.Frame(self.results_frame)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        columns = ("url", "username", "password", "status", "message", "system_type", "time")
        self.results_tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        
        col_configs = [
            ("url", "URL", 200),
            ("username", "用户名", 100),
            ("password", "密码", 100),
            ("status", "状态", 60),
            ("message", "消息", 150),
            ("system_type", "系统类型", 100),
            ("time", "响应时间", 80)
        ]
        
        for col_id, col_name, col_width in col_configs:
            self.results_tree.heading(col_id, text=col_name)
            self.results_tree.column(col_id, width=col_width)
        
        y_scroll = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.results_tree.yview)
        x_scroll = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.results_tree.xview)
        self.results_tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        
        self.results_tree.grid(row=0, column=0, sticky='nsew')
        y_scroll.grid(row=0, column=1, sticky='ns')
        x_scroll.grid(row=1, column=0, sticky='ew')
        
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        
        # 导出按钮
        btn_frame = ttk.Frame(self.results_frame)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(btn_frame, text="📄 导出JSON", command=self.export_json).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="📊 导出CSV", command=self.export_csv).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🧹 清空结果", command=self.clear_results).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🔄 刷新", command=self.refresh_results).pack(side=tk.LEFT, padx=5)
    
    def setup_about_tab(self):
        """设置关于标签页"""
        about_text = """
╔══════════════════════════════════════════════════════════════╗
║                    弱口令扫描器 v3.0                         ║
║                      增强版 - 2024                           ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  功能特性:                                                   ║
║  ✅ 批量目标模式 - 从CSV导入多个目标                        ║
║  ✅ 智能URL解析 - 自动识别协议/域名/端口/路径               ║
║  ✅ 系统指纹检测 - 自动识别目标系统类型                     ║
║  ✅ 暂停/继续/取消 - 完整的扫描控制                         ║
║  ✅ 多编码支持 - UTF-8/GBK/GB2312自动检测                   ║
║  ✅ 结果导出 - JSON/CSV格式                                 ║
║                                                              ║
║  支持的系统:                                                 ║
║  • 山鹰CRM系统 (自动适配)                                   ║
║  • HTTPBin测试服务                                          ║
║  • 通用JSON登录接口                                         ║
║                                                              ║
║  使用说明:                                                   ║
║  1. 切换到"批量目标模式"标签页                              ║
║  2. 导入CSV文件 (URL,用户名,密码)                           ║
║  3. 点击"开始扫描"                                          ║
║  4. 在"扫描结果"标签页查看结果                              ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
        """
        
        text_widget = tk.Text(self.about_frame, wrap=tk.WORD, height=25)
        text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text_widget.insert(tk.END, about_text)
        text_widget.config(state=tk.DISABLED)
    
    def log(self, message: str):
        """添加日志消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.single_log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.single_log_text.see(tk.END)
    
    def detect_system(self):
        """检测目标系统类型"""
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("警告", "请先输入目标URL")
            return
        
        sys_id, sys_name, config = SystemFingerprint.detect(url)
        self.system_type_label.config(text=f"系统类型: {sys_name}")
        self.log(f"检测到系统类型: {sys_name}")
        
        # 自动填充配置
        if config:
            self.username_field_var.set(config.get('username_field', 'username'))
            self.password_field_var.set(config.get('password_field', 'password'))
            self.encryption_var.set(config.get('password_encryption', 'none'))
            
            headers = config.get('headers', {})
            if headers:
                self.headers_text.delete(1.0, tk.END)
                self.headers_text.insert(tk.END, json.dumps(headers, indent=2))
    
    def load_file_to_text(self, text_widget):
        """将文件内容加载到文本框"""
        filepath = filedialog.askopenfilename(
            filetypes=[("文本文件", "*.txt"), ("CSV文件", "*.csv"), ("所有文件", "*.*")]
        )
        if filepath:
            try:
                encoding = detect_encoding(filepath)
                with open(filepath, 'r', encoding=encoding) as f:
                    content = f.read()
                text_widget.delete(1.0, tk.END)
                
                if filepath.endswith('.csv'):
                    lines = []
                    for line in content.split('\n'):
                        if line.strip() and not line.startswith('#'):
                            parts = line.split(',')
                            if parts:
                                lines.append(parts[0].strip().strip('"'))
                    content = '\n'.join(lines[1:] if lines else [])
                
                text_widget.insert(tk.END, content)
                self.log(f"已加载: {filepath}")
            except Exception as e:
                messagebox.showerror("错误", f"加载文件失败: {e}")
    
    def load_config_file(self):
        """从文件加载配置"""
        filepath = filedialog.askopenfilename(filetypes=[("JSON文件", "*.json")])
        if filepath:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                target = config.get('target', {})
                self.url_var.set(target.get('base_url', '') + target.get('login_endpoint', ''))
                
                request = config.get('request', {})
                body_template = request.get('body_template', {})
                
                for key, value in body_template.items():
                    if value == '${username}':
                        self.username_field_var.set(key)
                    elif value == '${password}':
                        self.password_field_var.set(key)
                
                self.encryption_var.set(request.get('password_encryption', 'none'))
                
                headers = request.get('headers', {})
                self.headers_text.delete(1.0, tk.END)
                self.headers_text.insert(tk.END, json.dumps(headers, indent=2))
                
                scan_settings = config.get('scan_settings', {})
                self.cfg_timeout_var.set(str(scan_settings.get('timeout', 10)))
                self.cfg_delay_var.set(str(scan_settings.get('delay_between_requests', 0.5)))
                
                self.log(f"已加载配置: {filepath}")
            except Exception as e:
                messagebox.showerror("错误", f"加载配置失败: {e}")
    
    def save_config_file(self):
        """保存当前配置到文件"""
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON文件", "*.json")]
        )
        if filepath:
            try:
                config = self.build_config()
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)
                self.log(f"已保存配置: {filepath}")
            except Exception as e:
                messagebox.showerror("错误", f"保存配置失败: {e}")
    
    def build_config(self) -> Dict:
        """从GUI输入构建配置字典"""
        try:
            headers = json.loads(self.headers_text.get(1.0, tk.END))
        except:
            headers = {}
        
        url = self.url_var.get()
        url_info = URLParser.parse(url)
        
        return {
            "target": {
                "name": "自定义目标",
                "base_url": URLParser.get_base_url(url),
                "login_endpoint": url_info['path'] or '/login',
                "method": "POST",
                "content_type": "application/json"
            },
            "request": {
                "headers": headers,
                "body_template": {
                    self.username_field_var.get(): "${username}",
                    self.password_field_var.get(): "${password}"
                },
                "password_encryption": self.encryption_var.get()
            },
            "response": {
                "success_indicators": [
                    {"type": "status_code", "value": 200},
                    {"type": "body_length_gt", "value": 50}
                ],
                "failure_indicators": [
                    {"type": "body_contains", "value": "error"},
                    {"type": "status_code", "value": 401}
                ]
            },
            "scan_settings": {
                "timeout": int(self.cfg_timeout_var.get()),
                "delay_between_requests": float(self.cfg_delay_var.get()),
                "max_workers": 1
            }
        }
    
    def get_credentials(self) -> List[Tuple[str, str]]:
        """从文本框获取凭证"""
        usernames = []
        for line in self.username_text.get(1.0, tk.END).split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                usernames.append(line)
        
        passwords = []
        for line in self.password_text.get(1.0, tk.END).split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                passwords.append(line)
        
        return [(u, p) for u in usernames for p in passwords]
    
    def update_single_progress(self, current: int, total: int):
        """更新单目标扫描进度条"""
        percentage = (current / total) * 100 if total > 0 else 0
        self.single_progress_var.set(percentage)
        self.single_progress_label.config(text=f"{current}/{total} ({percentage:.1f}%)")
        self.root.update_idletasks()
    
    def start_single_scan(self):
        """开始单目标扫描"""
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("警告", "请输入目标URL")
            return
        
        credentials = self.get_credentials()
        if not credentials:
            messagebox.showwarning("警告", "没有可扫描的凭证!")
            return
        
        # 构建目标列表
        targets = []
        for username, password in credentials:
            targets.append({
                'url': url,
                'username': username,
                'password': password
            })
        
        self.scanner.config = self.build_config()
        
        self.single_start_btn.config(state=tk.DISABLED)
        self.single_stop_btn.config(state=tk.NORMAL)
        self.status_var.set("扫描中...")
        self.log(f"开始单目标扫描，共 {len(targets)} 个凭证组合...")
        
        def scan_thread():
            try:
                results = self.scanner.scan_batch_smart(
                    targets,
                    progress_callback=lambda c, t: self.root.after(0, lambda: self.update_single_progress(c, t)),
                    log_callback=lambda msg: self.root.after(0, lambda: self.log(msg))
                )
                self.root.after(0, lambda: self.single_scan_complete(results))
            except Exception as e:
                self.root.after(0, lambda: self.log(f"错误: {e}"))
                self.root.after(0, lambda: self.single_scan_complete([]))
        
        self.scan_thread = threading.Thread(target=scan_thread)
        self.scan_thread.start()
    
    def stop_single_scan(self):
        """停止单目标扫描"""
        self.scanner.stop()
        self.log("正在停止扫描...")
    
    def single_scan_complete(self, results: List[Dict]):
        """单目标扫描完成回调"""
        self.single_start_btn.config(state=tk.NORMAL)
        self.single_stop_btn.config(state=tk.DISABLED)
        
        self.refresh_results()
        
        stats = self.scanner.stats
        self.status_var.set(f"完成 - 成功: {stats['success']}, 失败: {stats['failed']}, 错误: {stats['errors']}")
        self.log(f"扫描完成! 发现 {stats['success']} 个弱口令。")
        
        if stats['success'] > 0:
            self.notebook.select(self.results_frame)
            messagebox.showinfo("成功", f"发现 {stats['success']} 个弱口令!")
    
    def refresh_results(self):
        """刷新结果表格"""
        # 清空表格
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        
        # 添加结果
        for r in self.scanner.results:
            self.results_tree.insert("", tk.END, values=(
                r.get('url', ''),
                r['username'],
                r['password'],
                "✅ 成功" if r['success'] else "❌ 失败",
                r['message'],
                r.get('system_type', '未知'),
                f"{r['response_time']:.3f}秒"
            ))
        
        # 更新统计
        stats = self.scanner.stats
        self.result_stats_label.config(
            text=f"总计: {stats['total']} | 成功: {stats['success']} | 失败: {stats['failed']} | 错误: {stats['errors']}"
        )
    
    def export_json(self):
        """导出结果为JSON文件"""
        if not self.scanner.results:
            messagebox.showwarning("警告", "没有可导出的结果!")
            return
        
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON文件", "*.json")]
        )
        if filepath:
            try:
                output = {
                    'scan_time': datetime.now().isoformat(),
                    'statistics': self.scanner.stats,
                    'results': self.scanner.results
                }
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(output, f, indent=2, ensure_ascii=False)
                self.log(f"已导出到: {filepath}")
                messagebox.showinfo("成功", f"已导出到: {filepath}")
            except Exception as e:
                messagebox.showerror("错误", f"导出失败: {e}")
    
    def export_csv(self):
        """导出结果为CSV文件"""
        if not self.scanner.results:
            messagebox.showwarning("警告", "没有可导出的结果!")
            return
        
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV文件", "*.csv")]
        )
        if filepath:
            try:
                with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f)
                    writer.writerow(['URL', '用户名', '密码', '成功', '消息', '系统类型', '响应时间', '时间戳'])
                    for r in self.scanner.results:
                        writer.writerow([
                            r.get('url', ''),
                            r['username'],
                            r['password'],
                            r['success'],
                            r['message'],
                            r.get('system_type', '未知'),
                            r['response_time'],
                            r['timestamp']
                        ])
                self.log(f"已导出到: {filepath}")
                messagebox.showinfo("成功", f"已导出到: {filepath}")
            except Exception as e:
                messagebox.showerror("错误", f"导出失败: {e}")
    
    def clear_results(self):
        """清空所有结果"""
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        self.scanner.results = []
        self.scanner.stats = {'total': 0, 'success': 0, 'failed': 0, 'errors': 0}
        self.result_stats_label.config(text="总计: 0 | 成功: 0 | 失败: 0 | 错误: 0")
        self.log("结果已清空")
    
    def run(self):
        """启动应用"""
        self.root.mainloop()


def main():
    """主入口"""
    app = WeakpassScannerGUI()
    app.run()


if __name__ == "__main__":
    main()