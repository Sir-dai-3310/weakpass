#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版登录验证模块
针对不同类型的目标提供更智能的验证策略
"""

import requests
import time
import re
import json
from urllib.parse import urljoin, urlparse, parse_qs
from bs4 import BeautifulSoup
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import hashlib


class LoginStatus(Enum):
    """登录状态枚举"""
    SUCCESS = "登录成功"
    PASSWORD_ERROR = "密码错误"
    USERNAME_ERROR = "用户名错误"
    CAPTCHA_ERROR = "验证码错误"
    CAPTCHA_REQUIRED = "需要验证码"
    CONNECTION_ERROR = "连接错误"
    FORM_NOT_FOUND = "未找到登录表单"
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
    details: Optional[Dict[str, Any]] = None


class EnhancedLoginVerifier:
    """增强版登录验证器"""
    
    # 常见用户名字段
    USERNAME_FIELDS = [
        'username', 'user', 'login', 'email', 'account', 'uin', 'id', 'name',
        'userName', 'loginName', 'userid', 'user_name', 'login_name', 'uid',
        'mobile', 'phone', 'tel', 'loginId', 'userCode', 'usercode'
    ]
    
    # 常见密码字段
    PASSWORD_FIELDS = [
        'password', 'pwd', 'pass', 'passwd', 'secret', 'key',
        'passWord', 'login_password', 'user_pwd', 'loginPwd', 'userPwd'
    ]
    
    # 常见验证码字段
    CAPTCHA_FIELDS = [
        'captcha', 'code', 'verify', 'authcode', 'vcode', 'checkcode',
        'verifyCode', 'captchaCode', 'imgCode', 'validateCode', 'yzm',
        'randCode', 'captchaInput'
    ]
    
    # 登录成功标志 - 扩展版
    SUCCESS_INDICATORS = [
        # 关键词
        '欢迎', 'welcome', 'dashboard', 'logout', '退出', '主页', 'home',
        'profile', '设置', 'settings', 'admin', '用户中心', '成功',
        '登录成功', '个人中心', '控制台', '管理', '工作台', 'workspace',
        '您好', 'hello', 'success', 'true', '注销', 'signout',
        # JSON响应标志
        '"success":true', '"code":0', '"code":"0"', '"code":200',
        '"status":true', '"result":true', '"ok":true',
        '"success": true', '"code": 0', '"code": "0"', '"code": 200',
        '"msg":"成功"', '"message":"成功"', '"msg":"success"',
        # 特定系统成功标志
        '"resultCode":"0"', '"errCode":0', '"error":0',
        'token', 'access_token', 'session', 'jsessionid'
    ]
    
    # 登录失败标志 - 扩展版
    FAILURE_INDICATORS = [
        '错误', 'error', '失败', 'failed', 'invalid', 'incorrect', 'wrong',
        '不正确', '不存在', '重新输入', '密码错误', '不匹配',
        '用户名或密码', '账号或密码', 'username or password',
        '"success":false', '"code":-1', '"code":1', '"code":401',
        '"code":500', '"status":false', '"result":false',
        '"success": false', '"code": -1', '"code": 1',
        '验证码错误', '验证码失效', '验证码过期',
        'unauthorized', 'forbidden', '禁止访问', '无权限'
    ]
    
    # 需要验证码标志
    CAPTCHA_REQUIRED_INDICATORS = [
        '请输入验证码', '验证码', 'captcha', '请填写验证码',
        '图形验证码', '滑动验证', '点击验证'
    ]
    
    def __init__(self, timeout: int = 30, verify_ssl: bool = False, max_retries: int = 3):
        """初始化验证器"""
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.max_retries = max_retries
        self.session = requests.Session()
        self._setup_session()
    
    def _setup_session(self):
        """设置会话"""
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/json',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Cache-Control': 'no-cache',
        })
        
        # 禁用SSL警告
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    def normalize_url(self, url: str) -> str:
        """标准化URL"""
        url = url.strip()
        if not url.startswith(('http://', 'https://')):
            url = 'http://' + url
        return url
    
    def detect_target_type(self, url: str) -> str:
        """
        检测目标类型
        
        Returns:
            目标类型: 'api', 'form', 'json_api', 'unknown'
        """
        parsed = urlparse(url)
        path = parsed.path.lower()
        
        # httpbin测试API
        if 'httpbin' in parsed.netloc:
            return 'httpbin'
        
        # 常见API端点
        api_indicators = ['/api/', '/rest/', '/v1/', '/v2/', '/service/', '/ws/']
        if any(ind in path for ind in api_indicators):
            return 'json_api'
        
        # JSP/ASP等传统表单
        form_indicators = ['.jsp', '.asp', '.aspx', '.php', '/login', '/signin', '/auth']
        if any(ind in path for ind in form_indicators):
            return 'form'
        
        return 'auto'
    
    def verify_login(
        self,
        url: str,
        username: str,
        password: str,
        captcha: str = "",
        extra_params: Dict[str, str] = None
    ) -> LoginResult:
        """
        执行登录验证
        
        Args:
            url: 登录URL
            username: 用户名
            password: 密码
            captcha: 验证码（可选）
            extra_params: 额外参数（可选）
        
        Returns:
            LoginResult
        """
        start_time = time.time()
        url = self.normalize_url(url)
        
        try:
            target_type = self.detect_target_type(url)
            
            # 特殊处理 CRM 系统
            if 'crmzzapp' in url.lower():
                return self._verify_crm_get(url, username, password, start_time)
            elif target_type == 'httpbin':
                return self._verify_httpbin(url, username, password, start_time)
            elif target_type == 'json_api':
                return self._verify_json_api(url, username, password, captcha, extra_params, start_time)
            else:
                return self._verify_form(url, username, password, captcha, extra_params, start_time)
                
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
        except requests.exceptions.ConnectionError as e:
            return LoginResult(
                status=LoginStatus.CONNECTION_ERROR,
                success=False,
                message=f"连接失败: {str(e)[:50]}",
                response_time=time.time() - start_time,
                url=url,
                final_url=url,
                page_changed=False
            )
        except Exception as e:
            return LoginResult(
                status=LoginStatus.UNKNOWN_ERROR,
                success=False,
                message=f"验证错误: {str(e)[:100]}",
                response_time=time.time() - start_time,
                url=url,
                final_url=url,
                page_changed=False
            )
    
    def _verify_crm_get(self, url: str, username: str, password: str, start_time: float) -> LoginResult:
        """
        验证 CRM 系统的 GET 方法登录
        CRM 系统使用 GET 请求而不是 POST
        """
        base_url = url
        api_url = f"{base_url}/api/user/login"
        
        # 先访问主页获取 session
        try:
            self.session.get(base_url, timeout=self.timeout, verify=False)
        except:
            pass
        
        # 尝试不同的参数格式
        params_list = [
            {'username': username, 'password': password},
            {'userName': username, 'passWord': password},
            {'loginName': username, 'password': password},
        ]
        
        for params in params_list:
            try:
                response = self.session.get(
                    api_url,
                    params=params,
                    timeout=self.timeout,
                    verify=False
                )
                
                response_time = time.time() - start_time
                
                # 检查响应
                try:
                    data = response.json()
                    
                    # 检查成功 - 直接返回 true
                    if data is True or data == 'true':
                        return LoginResult(
                            status=LoginStatus.SUCCESS,
                            success=True,
                            message="登录成功",
                            response_time=response_time,
                            url=base_url,
                            final_url=response.url,
                            page_changed=True,
                            details={'method': 'GET', 'params': params}
                        )
                    
                    # 检查其他成功标志
                    success_keys = ['token', 'access_token', 'sessionId', 'userId', 'user']
                    success_codes = [0, 200, '0', '200', 'success', True]
                    
                    code = data.get('code') or data.get('resultCode') or data.get('status')
                    msg = data.get('msg') or data.get('message') or ''
                    
                    if code in success_codes or any(key in data for key in success_keys):
                        if '错误' not in str(msg) and 'error' not in str(msg).lower() and '非法' not in str(msg):
                            return LoginResult(
                                status=LoginStatus.SUCCESS,
                                success=True,
                                message=f"登录成功: {msg or 'OK'}",
                                response_time=response_time,
                                url=base_url,
                                final_url=response.url,
                                page_changed=True,
                                details={'method': 'GET', 'params': params}
                            )
                    
                    # 检查失败
                    if '密码' in str(msg) or 'password' in str(msg).lower():
                        return LoginResult(
                            status=LoginStatus.PASSWORD_ERROR,
                            success=False,
                            message=f"密码错误: {msg}",
                            response_time=response_time,
                            url=base_url,
                            final_url=response.url,
                            page_changed=False
                        )
                    
                except:
                    # 检查文本响应
                    if 'true' in response.text.lower():
                        return LoginResult(
                            status=LoginStatus.SUCCESS,
                            success=True,
                            message="登录成功",
                            response_time=response_time,
                            url=base_url,
                            final_url=response.url,
                            page_changed=True
                        )
                
            except Exception:
                continue
        
        return LoginResult(
            status=LoginStatus.PASSWORD_ERROR,
            success=False,
            message="登录失败",
            response_time=time.time() - start_time,
            url=base_url,
            final_url=base_url,
            page_changed=False
        )
    
    def _verify_httpbin(self, url: str, username: str, password: str, start_time: float) -> LoginResult:
        """
        验证httpbin类型的测试API
        httpbin.org/post 会回显POST数据，用于测试
        """
        data = {
            'username': username,
            'password': password
        }
        
        response = self.session.post(
            url,
            data=data,
            timeout=self.timeout,
            verify=self.verify_ssl
        )
        
        response_time = time.time() - start_time
        
        # httpbin会回显数据，检查是否包含我们发送的数据
        try:
            json_response = response.json()
            form_data = json_response.get('form', {})
            
            # 如果回显了我们的用户名和密码，视为"成功"（测试目的）
            if form_data.get('username') == username and form_data.get('password') == password:
                return LoginResult(
                    status=LoginStatus.SUCCESS,
                    success=True,
                    message="httpbin测试成功：数据已正确发送并回显",
                    response_time=response_time,
                    url=url,
                    final_url=response.url,
                    page_changed=True,
                    details={'response': json_response}
                )
        except:
            pass
        
        return LoginResult(
            status=LoginStatus.UNKNOWN_ERROR,
            success=False,
            message="httpbin测试响应异常",
            response_time=response_time,
            url=url,
            final_url=response.url,
            page_changed=False
        )
    
    def _verify_json_api(
        self,
        url: str,
        username: str,
        password: str,
        captcha: str,
        extra_params: Dict[str, str],
        start_time: float
    ) -> LoginResult:
        """验证JSON API类型的登录"""
        
        # 尝试多种常见的JSON格式
        json_payloads = [
            {'username': username, 'password': password},
            {'userName': username, 'passWord': password},
            {'user': username, 'pwd': password},
            {'loginName': username, 'password': password},
            {'account': username, 'password': password},
            {'mobile': username, 'password': password},
        ]
        
        if captcha:
            for payload in json_payloads:
                payload['captcha'] = captcha
                payload['code'] = captcha
        
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        }
        
        for payload in json_payloads:
            try:
                response = self.session.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=self.timeout,
                    verify=self.verify_ssl
                )
                
                result = self._analyze_json_response(response, url, start_time)
                if result.success:
                    return result
                    
            except:
                continue
        
        # 如果JSON都失败，尝试表单提交
        return self._verify_form(url, username, password, captcha, extra_params, start_time)
    
    def _analyze_json_response(self, response, url: str, start_time: float) -> LoginResult:
        """分析JSON响应"""
        response_time = time.time() - start_time
        content = response.text.lower()
        
        # 检查成功标志
        for indicator in self.SUCCESS_INDICATORS:
            if indicator.lower() in content:
                return LoginResult(
                    status=LoginStatus.SUCCESS,
                    success=True,
                    message=f"登录成功: 检测到成功标志",
                    response_time=response_time,
                    url=url,
                    final_url=response.url,
                    page_changed=True,
                    details={'indicator': indicator}
                )
        
        # 检查失败标志
        for indicator in self.FAILURE_INDICATORS:
            if indicator.lower() in content:
                return LoginResult(
                    status=LoginStatus.PASSWORD_ERROR,
                    success=False,
                    message=f"登录失败: 检测到失败标志",
                    response_time=response_time,
                    url=url,
                    final_url=response.url,
                    page_changed=False,
                    details={'indicator': indicator}
                )
        
        return LoginResult(
            status=LoginStatus.UNKNOWN_ERROR,
            success=False,
            message="无法确定登录结果",
            response_time=response_time,
            url=url,
            final_url=response.url,
            page_changed=False
        )
    
    def _verify_form(
        self,
        url: str,
        username: str,
        password: str,
        captcha: str,
        extra_params: Dict[str, str],
        start_time: float
    ) -> LoginResult:
        """验证表单类型的登录"""
        
        # 首先获取登录页面
        try:
            page_response = self.session.get(url, timeout=self.timeout, verify=self.verify_ssl)
            pre_content = page_response.text
            pre_url = page_response.url
        except Exception as e:
            return LoginResult(
                status=LoginStatus.CONNECTION_ERROR,
                success=False,
                message=f"无法获取登录页面: {str(e)[:50]}",
                response_time=time.time() - start_time,
                url=url,
                final_url=url,
                page_changed=False
            )
        
        # 解析表单
        soup = BeautifulSoup(pre_content, 'html.parser')
        form_info = self._extract_form_info(soup, url)
        
        # 构建登录数据
        login_data = {}
        
        if form_info:
            login_data = form_info['hidden_fields'].copy()
            action_url = form_info['action']
            
            if form_info['username_field']:
                login_data[form_info['username_field']] = username
            if form_info['password_field']:
                login_data[form_info['password_field']] = password
            if form_info['captcha_field'] and captcha:
                login_data[form_info['captcha_field']] = captcha
        else:
            action_url = url
            # 尝试通用字段名
            login_data = {
                'username': username,
                'password': password,
            }
        
        # 添加额外参数
        if extra_params:
            login_data.update(extra_params)
        
        # 也尝试其他常见字段名组合
        field_combinations = [
            {'username': username, 'password': password},
            {'userName': username, 'passWord': password},
            {'user': username, 'pwd': password},
            {'loginName': username, 'loginPwd': password},
        ]
        
        for combo in field_combinations:
            test_data = login_data.copy()
            test_data.update(combo)
            
            try:
                # 提交登录
                response = self.session.post(
                    action_url,
                    data=test_data,
                    timeout=self.timeout,
                    verify=self.verify_ssl,
                    allow_redirects=True
                )
                
                result = self._analyze_login_response(
                    response, pre_content, pre_url, url, start_time
                )
                
                if result.success:
                    return result
                    
            except Exception as e:
                continue
        
        # 返回最后一次尝试的结果
        return self._analyze_login_response(
            response, pre_content, pre_url, url, start_time
        )
    
    def _extract_form_info(self, soup: BeautifulSoup, base_url: str) -> Optional[Dict]:
        """提取表单信息"""
        forms = soup.find_all('form')
        
        for form in forms:
            # 查找密码字段
            pwd_input = form.find('input', {'type': 'password'})
            if not pwd_input:
                continue
            
            # 获取表单action
            action = form.get('action', '')
            if action and not action.startswith(('http://', 'https://')):
                action = urljoin(base_url, action)
            elif not action:
                action = base_url
            
            # 查找用户名字段
            username_field = None
            for field_name in self.USERNAME_FIELDS:
                inp = form.find('input', {'name': field_name})
                if inp:
                    username_field = field_name
                    break
            
            # 如果没找到，尝试查找text类型的input
            if not username_field:
                text_inputs = form.find_all('input', {'type': ['text', 'email', 'tel']})
                for inp in text_inputs:
                    name = inp.get('name', '')
                    if name:
                        username_field = name
                        break
            
            password_field = pwd_input.get('name', 'password')
            
            # 查找验证码字段
            captcha_field = None
            for field_name in self.CAPTCHA_FIELDS:
                inp = form.find('input', {'name': field_name})
                if inp:
                    captcha_field = field_name
                    break
            
            # 获取隐藏字段
            hidden_fields = {}
            for hidden in form.find_all('input', {'type': 'hidden'}):
                name = hidden.get('name', '')
                value = hidden.get('value', '')
                if name:
                    hidden_fields[name] = value
            
            return {
                'action': action,
                'username_field': username_field,
                'password_field': password_field,
                'captcha_field': captcha_field,
                'hidden_fields': hidden_fields
            }
        
        return None
    
    def _analyze_login_response(
        self,
        response,
        pre_content: str,
        pre_url: str,
        original_url: str,
        start_time: float
    ) -> LoginResult:
        """分析登录响应"""
        response_time = time.time() - start_time
        content = response.text
        content_lower = content.lower()
        
        # 计算页面变化
        page_changed = self._content_changed(pre_content, content)
        url_changed = pre_url != response.url
        
        # 1. 检查是否需要验证码
        for indicator in self.CAPTCHA_REQUIRED_INDICATORS:
            if indicator.lower() in content_lower:
                # 检查是否在登录后的页面（非初始登录页）
                if page_changed or url_changed:
                    continue  # 可能是成功后的页面也有验证码相关文字
                return LoginResult(
                    status=LoginStatus.CAPTCHA_REQUIRED,
                    success=False,
                    message="需要验证码",
                    response_time=response_time,
                    url=original_url,
                    final_url=response.url,
                    page_changed=page_changed
                )
        
        # 2. 检查成功标志
        success_score = 0
        matched_success = []
        for indicator in self.SUCCESS_INDICATORS:
            if indicator.lower() in content_lower:
                success_score += 1
                matched_success.append(indicator)
        
        # 3. 检查失败标志
        failure_score = 0
        matched_failure = []
        for indicator in self.FAILURE_INDICATORS:
            if indicator.lower() in content_lower:
                failure_score += 1
                matched_failure.append(indicator)
        
        # 4. 检查URL变化（跳转到新页面通常表示成功）
        if url_changed:
            final_path = urlparse(response.url).path.lower()
            success_paths = ['dashboard', 'home', 'index', 'main', 'admin', 'welcome', 
                           'user', 'center', 'portal', 'workspace', 'console']
            failure_paths = ['login', 'signin', 'auth', 'error', 'fail']
            
            if any(p in final_path for p in success_paths):
                success_score += 3
            elif any(p in final_path for p in failure_paths):
                failure_score += 2
        
        # 5. 综合判断
        # 明确成功
        if success_score > failure_score and (success_score >= 2 or (page_changed and success_score >= 1)):
            return LoginResult(
                status=LoginStatus.SUCCESS,
                success=True,
                message=f"登录成功: 匹配{success_score}个成功标志",
                response_time=response_time,
                url=original_url,
                final_url=response.url,
                page_changed=page_changed,
                details={'success_indicators': matched_success[:3]}
            )
        
        # 明确失败
        if failure_score > success_score:
            return LoginResult(
                status=LoginStatus.PASSWORD_ERROR,
                success=False,
                message=f"登录失败: 匹配{failure_score}个失败标志",
                response_time=response_time,
                url=original_url,
                final_url=response.url,
                page_changed=page_changed,
                details={'failure_indicators': matched_failure[:3]}
            )
        
        # URL变化且页面变化，可能成功
        if url_changed and page_changed:
            return LoginResult(
                status=LoginStatus.SUCCESS,
                success=True,
                message="可能登录成功: URL和页面均已变化",
                response_time=response_time,
                url=original_url,
                final_url=response.url,
                page_changed=page_changed
            )
        
        # 仅页面变化
        if page_changed:
            return LoginResult(
                status=LoginStatus.SUCCESS,
                success=True,
                message="可能登录成功: 页面内容已变化",
                response_time=response_time,
                url=original_url,
                final_url=response.url,
                page_changed=page_changed
            )
        
        # 无法确定
        return LoginResult(
            status=LoginStatus.PASSWORD_ERROR,
            success=False,
            message="登录失败: 页面无明显变化",
            response_time=response_time,
            url=original_url,
            final_url=response.url,
            page_changed=page_changed
        )
    
    def _content_changed(self, content1: str, content2: str) -> bool:
        """检查内容是否发生实质性变化"""
        # 移除可能的动态内容
        def clean(text):
            text = re.sub(r'\d{10,}', '', text)  # 时间戳
            text = re.sub(r'[a-f0-9]{32,}', '', text)  # hash
            text = re.sub(r'token["\s:=]+["\']?[\w-]+["\']?', '', text, flags=re.I)
            text = re.sub(r'csrf["\s:=]+["\']?[\w-]+["\']?', '', text, flags=re.I)
            text = re.sub(r'\s+', ' ', text)
            return text.strip()
        
        c1 = clean(content1)
        c2 = clean(content2)
        
        # 计算相似度
        if len(c1) == 0 or len(c2) == 0:
            return len(c1) != len(c2)
        
        # 如果长度差异超过10%，认为有变化
        len_diff = abs(len(c1) - len(c2)) / max(len(c1), len(c2))
        if len_diff > 0.1:
            return True
        
        # 计算hash差异
        h1 = hashlib.md5(c1.encode()).hexdigest()
        h2 = hashlib.md5(c2.encode()).hexdigest()
        
        return h1 != h2
    
    def test_connection(self, url: str) -> Tuple[bool, str]:
        """测试连接"""
        try:
            url = self.normalize_url(url)
            response = self.session.get(
                url,
                timeout=self.timeout,
                verify=self.verify_ssl,
                allow_redirects=True
            )
            return True, f"连接成功 (状态码: {response.status_code})"
        except requests.exceptions.Timeout:
            return False, "连接超时"
        except requests.exceptions.ConnectionError:
            return False, "无法连接"
        except Exception as e:
            return False, f"连接失败: {str(e)[:50]}"
    
    def close(self):
        """关闭会话"""
        self.session.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# 兼容旧版接口
LoginVerifier = EnhancedLoginVerifier


def quick_verify(url: str, username: str, password: str, captcha: str = "") -> LoginResult:
    """快速验证"""
    with EnhancedLoginVerifier() as verifier:
        return verifier.verify_login(url, username, password, captcha)


if __name__ == "__main__":
    # 测试
    print("测试 httpbin.org...")
    result = quick_verify("https://httpbin.org/post", "testuser", "testpass")
    print(f"状态: {result.status.value}")
    print(f"成功: {result.success}")
    print(f"消息: {result.message}")
    print(f"响应时间: {result.response_time:.2f}s")