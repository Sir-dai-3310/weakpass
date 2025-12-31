#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
核心登录验证模块
提供单URL登录验证功能，支持自动识别验证码和页面变化检测
"""

import requests
import time
import re
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import hashlib


class LoginStatus(Enum):
    """登录状态枚举"""
    SUCCESS = "success"           # 登录成功
    PASSWORD_ERROR = "password_error"   # 密码错误
    USERNAME_ERROR = "username_error"   # 用户名错误
    CAPTCHA_ERROR = "captcha_error"     # 验证码错误
    CONNECTION_ERROR = "connection_error"  # 连接错误
    FORM_NOT_FOUND = "form_not_found"   # 未找到登录表单
    UNKNOWN_ERROR = "unknown_error"     # 未知错误


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
    details: Optional[Dict[str, Any]] = None


@dataclass
class FormInfo:
    """表单信息"""
    action: str
    method: str
    username_field: str
    password_field: str
    captcha_field: Optional[str]
    hidden_fields: Dict[str, str]
    captcha_img_url: Optional[str]


class LoginVerifier:
    """登录验证器"""
    
    # 常见的用户名字段名
    USERNAME_FIELDS = [
        'username', 'user', 'login', 'email', 'account', 'uin', 'id', 'name',
        'userName', 'loginName', 'userid', 'user_name', 'login_name', 'uid'
    ]
    
    # 常见的密码字段名
    PASSWORD_FIELDS = [
        'password', 'pwd', 'pass', 'passwd', 'secret', 'key',
        'passWord', 'login_password', 'user_pwd', 'loginPwd'
    ]
    
    # 常见的验证码字段名
    CAPTCHA_FIELDS = [
        'captcha', 'code', 'verify', 'authcode', 'vcode', 'checkcode',
        'verifyCode', 'captchaCode', 'imgCode', 'validateCode', 'yzm'
    ]
    
    # 登录成功关键词
    SUCCESS_KEYWORDS = [
        '欢迎', 'welcome', 'dashboard', 'logout', '退出', '主页', 'home',
        'profile', '设置', 'settings', 'admin', '用户中心', 'success',
        '登录成功', '成功', '个人中心', '控制台', '管理'
    ]
    
    # 登录失败关键词
    FAILURE_KEYWORDS = [
        '错误', 'error', '失败', 'failed', 'invalid', '用户名', '密码',
        '验证码', 'captcha', '登录', 'login', 'incorrect', 'wrong',
        '不正确', '不存在', '重新输入', '密码错误', '账号', '不匹配'
    ]
    
    # 密码错误特定关键词
    PASSWORD_ERROR_KEYWORDS = [
        '密码错误', '密码不正确', 'password incorrect', 'wrong password',
        'invalid password', '密码不匹配', '密码有误'
    ]
    
    # 用户名错误特定关键词
    USERNAME_ERROR_KEYWORDS = [
        '用户名不存在', '账号不存在', 'user not found', 'account not exist',
        '用户不存在', '账号错误', 'invalid username'
    ]
    
    # 验证码错误特定关键词
    CAPTCHA_ERROR_KEYWORDS = [
        '验证码错误', '验证码不正确', 'captcha error', 'invalid captcha',
        '验证码已过期', '验证码失效', 'wrong captcha'
    ]
    
    def __init__(self, timeout: int = 30, verify_ssl: bool = True):
        """
        初始化登录验证器
        
        Args:
            timeout: 请求超时时间（秒）
            verify_ssl: 是否验证SSL证书
        """
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.session = requests.Session()
        self._setup_session()
        
    def _setup_session(self):
        """设置会话"""
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
    def normalize_url(self, url: str) -> str:
        """标准化URL"""
        url = url.strip()
        if not url.startswith(('http://', 'https://')):
            url = 'http://' + url
        return url
    
    def test_connection(self, url: str) -> Tuple[bool, str]:
        """
        测试目标连接
        
        Args:
            url: 目标URL
            
        Returns:
            (成功标志, 消息)
        """
        try:
            url = self.normalize_url(url)
            response = self.session.get(
                url, 
                timeout=self.timeout, 
                verify=self.verify_ssl,
                allow_redirects=True
            )
            response.raise_for_status()
            return True, f"连接成功，状态码: {response.status_code}"
        except requests.exceptions.Timeout:
            return False, "连接超时"
        except requests.exceptions.ConnectionError:
            return False, "无法连接到目标服务器"
        except requests.exceptions.HTTPError as e:
            return False, f"HTTP错误: {e}"
        except Exception as e:
            return False, f"连接失败: {str(e)}"
    
    def analyze_login_form(self, url: str) -> Optional[FormInfo]:
        """
        分析登录表单
        
        Args:
            url: 登录页面URL
            
        Returns:
            FormInfo或None
        """
        try:
            url = self.normalize_url(url)
            response = self.session.get(
                url, 
                timeout=self.timeout, 
                verify=self.verify_ssl
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            forms = soup.find_all('form')
            
            # 查找最可能的登录表单
            login_form = self._find_login_form(forms)
            if not login_form:
                return None
            
            # 解析表单信息
            action = login_form.get('action', '')
            if action and not action.startswith(('http://', 'https://')):
                action = urljoin(url, action)
            elif not action:
                action = url
                
            method = login_form.get('method', 'POST').upper()
            
            # 查找输入字段
            username_field = self._find_field(login_form, self.USERNAME_FIELDS, 'text')
            password_field = self._find_field(login_form, self.PASSWORD_FIELDS, 'password')
            captcha_field = self._find_field(login_form, self.CAPTCHA_FIELDS, 'text')
            
            # 获取隐藏字段
            hidden_fields = self._get_hidden_fields(login_form)
            
            # 查找验证码图片
            captcha_img_url = self._find_captcha_image(soup, url)
            
            if not username_field or not password_field:
                return None
                
            return FormInfo(
                action=action,
                method=method,
                username_field=username_field,
                password_field=password_field,
                captcha_field=captcha_field,
                hidden_fields=hidden_fields,
                captcha_img_url=captcha_img_url
            )
            
        except Exception as e:
            return None
    
    def _find_login_form(self, forms: List) -> Optional[Any]:
        """查找登录表单"""
        for form in forms:
            # 检查是否包含密码字段
            password_inputs = form.find_all('input', {'type': 'password'})
            if password_inputs:
                return form
            
            # 检查表单action或id是否包含login相关关键词
            action = form.get('action', '').lower()
            form_id = form.get('id', '').lower()
            form_class = ' '.join(form.get('class', [])).lower()
            
            login_keywords = ['login', 'signin', 'auth', 'logon', '登录']
            if any(kw in action or kw in form_id or kw in form_class for kw in login_keywords):
                return form
        
        return forms[0] if forms else None
    
    def _find_field(self, form, field_names: List[str], input_type: str) -> Optional[str]:
        """查找表单字段"""
        # 首先按类型查找
        if input_type == 'password':
            inputs = form.find_all('input', {'type': 'password'})
            if inputs:
                return inputs[0].get('name', '')
        
        # 按名称查找
        for name in field_names:
            # 精确匹配
            input_tag = form.find('input', {'name': name})
            if input_tag:
                return name
            
            input_tag = form.find('input', {'id': name})
            if input_tag:
                return input_tag.get('name', name)
        
        # 模糊匹配
        for input_tag in form.find_all('input'):
            input_name = input_tag.get('name', '').lower()
            input_id = input_tag.get('id', '').lower()
            input_placeholder = input_tag.get('placeholder', '').lower()
            
            for name in field_names:
                if name in input_name or name in input_id or name in input_placeholder:
                    return input_tag.get('name', '')
        
        return None
    
    def _get_hidden_fields(self, form) -> Dict[str, str]:
        """获取隐藏字段"""
        hidden_fields = {}
        for input_tag in form.find_all('input', {'type': 'hidden'}):
            name = input_tag.get('name', '')
            value = input_tag.get('value', '')
            if name:
                hidden_fields[name] = value
        return hidden_fields
    
    def _find_captcha_image(self, soup: BeautifulSoup, base_url: str) -> Optional[str]:
        """查找验证码图片"""
        captcha_selectors = [
            'img[src*="captcha"]',
            'img[src*="code"]',
            'img[src*="verify"]',
            'img[src*="yzm"]',
            'img[alt*="验证码"]',
            'img[alt*="captcha"]',
            '.captcha img',
            '#captcha img',
            '.verify-code img',
        ]
        
        for selector in captcha_selectors:
            try:
                img = soup.select_one(selector)
                if img and img.get('src'):
                    src = img['src']
                    if not src.startswith(('http://', 'https://')):
                        src = urljoin(base_url, src)
                    return src
            except:
                continue
        
        return None
    
    def get_captcha_image(self, url: str) -> Optional[bytes]:
        """
        获取验证码图片
        
        Args:
            url: 验证码图片URL
            
        Returns:
            图片二进制数据或None
        """
        try:
            response = self.session.get(
                url, 
                timeout=self.timeout, 
                verify=self.verify_ssl
            )
            response.raise_for_status()
            return response.content
        except Exception as e:
            return None
    
    def verify_login(
        self, 
        url: str, 
        username: str, 
        password: str, 
        captcha: str = "",
        form_info: Optional[FormInfo] = None
    ) -> LoginResult:
        """
        执行登录验证
        
        Args:
            url: 登录页面URL
            username: 用户名
            password: 密码
            captcha: 验证码（可选）
            form_info: 表单信息（可选，如果不提供则自动分析）
            
        Returns:
            LoginResult
        """
        start_time = time.time()
        url = self.normalize_url(url)
        
        try:
            # 如果没有提供表单信息，自动分析
            if not form_info:
                form_info = self.analyze_login_form(url)
                if not form_info:
                    return LoginResult(
                        status=LoginStatus.FORM_NOT_FOUND,
                        success=False,
                        message="未找到登录表单",
                        response_time=time.time() - start_time,
                        url=url,
                        final_url=url,
                        page_changed=False
                    )
            
            # 获取登录前的页面内容哈希（用于比较页面变化）
            pre_login_response = self.session.get(url, timeout=self.timeout, verify=self.verify_ssl)
            pre_login_hash = self._get_content_hash(pre_login_response.text)
            pre_login_url = pre_login_response.url
            
            # 构建登录数据
            login_data = form_info.hidden_fields.copy()
            login_data[form_info.username_field] = username
            login_data[form_info.password_field] = password
            
            if form_info.captcha_field and captcha:
                login_data[form_info.captcha_field] = captcha
            
            # 发送登录请求
            if form_info.method == 'POST':
                response = self.session.post(
                    form_info.action,
                    data=login_data,
                    timeout=self.timeout,
                    verify=self.verify_ssl,
                    allow_redirects=True
                )
            else:
                response = self.session.get(
                    form_info.action,
                    params=login_data,
                    timeout=self.timeout,
                    verify=self.verify_ssl,
                    allow_redirects=True
                )
            
            response_time = time.time() - start_time
            
            # 分析登录结果
            post_login_hash = self._get_content_hash(response.text)
            page_changed = pre_login_hash != post_login_hash
            url_changed = pre_login_url != response.url
            
            # 判断登录状态
            status, message = self._analyze_login_result(
                response.text, 
                response.url, 
                url,
                page_changed,
                url_changed
            )
            
            return LoginResult(
                status=status,
                success=(status == LoginStatus.SUCCESS),
                message=message,
                response_time=response_time,
                url=url,
                final_url=response.url,
                page_changed=page_changed,
                details={
                    'url_changed': url_changed,
                    'status_code': response.status_code,
                    'content_length': len(response.text),
                    'pre_login_hash': pre_login_hash[:16],
                    'post_login_hash': post_login_hash[:16]
                }
            )
            
        except requests.exceptions.Timeout:
            return LoginResult(
                status=LoginStatus.CONNECTION_ERROR,
                success=False,
                message="请求超时",
                response_time=time.time() - start_time,
                url=url,
                final_url=url,
                page_changed=False
            )
        except requests.exceptions.ConnectionError:
            return LoginResult(
                status=LoginStatus.CONNECTION_ERROR,
                success=False,
                message="无法连接到服务器",
                response_time=time.time() - start_time,
                url=url,
                final_url=url,
                page_changed=False
            )
        except Exception as e:
            return LoginResult(
                status=LoginStatus.UNKNOWN_ERROR,
                success=False,
                message=f"登录过程中出现错误: {str(e)}",
                response_time=time.time() - start_time,
                url=url,
                final_url=url,
                page_changed=False
            )
    
    def _get_content_hash(self, content: str) -> str:
        """获取内容哈希"""
        # 移除可能变化的内容（如时间戳、CSRF令牌等）
        cleaned = re.sub(r'\d{10,}', '', content)  # 移除时间戳
        cleaned = re.sub(r'[a-f0-9]{32,}', '', cleaned)  # 移除长哈希
        return hashlib.md5(cleaned.encode()).hexdigest()
    
    def _analyze_login_result(
        self, 
        content: str, 
        final_url: str, 
        original_url: str,
        page_changed: bool,
        url_changed: bool
    ) -> Tuple[LoginStatus, str]:
        """
        分析登录结果
        
        Args:
            content: 响应内容
            final_url: 最终URL
            original_url: 原始URL
            page_changed: 页面是否变化
            url_changed: URL是否变化
            
        Returns:
            (登录状态, 消息)
        """
        content_lower = content.lower()
        
        # 检查密码错误关键词
        for keyword in self.PASSWORD_ERROR_KEYWORDS:
            if keyword.lower() in content_lower:
                return LoginStatus.PASSWORD_ERROR, f"密码错误: 检测到关键词 '{keyword}'"
        
        # 检查用户名错误关键词
        for keyword in self.USERNAME_ERROR_KEYWORDS:
            if keyword.lower() in content_lower:
                return LoginStatus.USERNAME_ERROR, f"用户名错误: 检测到关键词 '{keyword}'"
        
        # 检查验证码错误关键词
        for keyword in self.CAPTCHA_ERROR_KEYWORDS:
            if keyword.lower() in content_lower:
                return LoginStatus.CAPTCHA_ERROR, f"验证码错误: 检测到关键词 '{keyword}'"
        
        # 检查成功关键词
        success_count = 0
        for keyword in self.SUCCESS_KEYWORDS:
            if keyword.lower() in content_lower:
                success_count += 1
        
        # 检查失败关键词
        failure_count = 0
        for keyword in self.FAILURE_KEYWORDS:
            if keyword.lower() in content_lower:
                failure_count += 1
        
        # 综合判断
        # 情况1: URL明显变化（如跳转到dashboard、home等）
        final_path = urlparse(final_url).path.lower()
        success_paths = ['dashboard', 'home', 'index', 'main', 'admin', 'welcome', 'user']
        if url_changed and any(p in final_path for p in success_paths):
            return LoginStatus.SUCCESS, f"登录成功: 页面跳转到 {final_url}"
        
        # 情况2: 成功关键词多于失败关键词，且页面发生变化
        if success_count > failure_count and page_changed:
            return LoginStatus.SUCCESS, f"登录成功: 检测到{success_count}个成功关键词，页面已变化"
        
        # 情况3: 失败关键词更多
        if failure_count > 0 and failure_count >= success_count:
            return LoginStatus.PASSWORD_ERROR, f"登录失败: 检测到{failure_count}个失败关键词"
        
        # 情况4: 页面没有变化，可能登录失败
        if not page_changed and not url_changed:
            return LoginStatus.PASSWORD_ERROR, "登录失败: 页面无变化"
        
        # 情况5: 只有页面变化，无法确定
        if page_changed:
            return LoginStatus.SUCCESS, "可能登录成功: 页面发生变化，请人工确认"
        
        return LoginStatus.UNKNOWN_ERROR, "无法确定登录状态，请人工确认"
    
    def close(self):
        """关闭会话"""
        self.session.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def quick_verify(url: str, username: str, password: str, captcha: str = "") -> LoginResult:
    """
    快速验证函数
    
    Args:
        url: 登录页面URL
        username: 用户名
        password: 密码
        captcha: 验证码（可选）
        
    Returns:
        LoginResult
    """
    with LoginVerifier() as verifier:
        return verifier.verify_login(url, username, password, captcha)


if __name__ == "__main__":
    # 测试代码
    result = quick_verify("https://httpbin.org/post", "testuser", "testpass")
    print(f"状态: {result.status.value}")
    print(f"成功: {result.success}")
    print(f"消息: {result.message}")
    print(f"响应时间: {result.response_time:.2f}s")