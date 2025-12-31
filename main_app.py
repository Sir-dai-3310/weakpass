#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
弱口令验证工具 - 主界面
提供简洁易用的图形化界面，支持单个验证和批量验证
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import threading
import queue
import time
import csv
import os
import sys
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

# 导入核心模块
try:
    from core import (
        UnifiedVerifier, VerifyMode, LoginResult, LoginStatus,
        CaptchaRecognizer, CaptchaResult,
        BatchImporter, TargetInfo, ImportResult,
        get_supported_formats, EnhancedBatchImporter
    )
    CORE_AVAILABLE = True
except ImportError as e:
    print(f"核心模块导入失败: {e}")
    CORE_AVAILABLE = False


class WeakPasswordTool:
    """弱口令验证工具主界面"""
    
    def __init__(self):
        print("[DEBUG] 创建Tk窗口...")
        self.root = tk.Tk()
        self.root.title("弱口令验证工具 v2.0 - 统一验证器")
        self.root.geometry("1000x750")
        self.root.minsize(800, 600)

        print("[DEBUG] 窗口创建成功")

        # 核心组件
        self.verifier: Optional[UnifiedVerifier] = None
        self.captcha_recognizer: Optional[CaptchaRecognizer] = None
        self.batch_importer: Optional[EnhancedBatchImporter] = None

        # 任务队列
        self.task_queue = queue.Queue()
        self.result_queue = queue.Queue()

        # 批量任务数据
        self.batch_targets: List[TargetInfo] = []
        self.batch_results: List[Dict[str, Any]] = []

        # 运行状态
        self.is_running = False
        self.stop_flag = False

        print("[DEBUG] 初始化界面...")
        # 初始化界面
        self._init_ui()

        print("[DEBUG] 初始化核心组件...")
        # 初始化核心组件
        self._init_components()

        print("[DEBUG] 启动结果处理线程...")
        # 启动结果处理线程
        self._start_result_handler()

        print("[DEBUG] 设置窗口关闭事件...")
        # 窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

        print("[DEBUG] 强制显示窗口...")
        # 强制显示窗口在最前面
        self.root.lift()
        self.root.attributes('-topmost', True)
        self.root.after_idle(self.root.attributes, '-topmost', False)

        print("[DEBUG] 初始化完成")
    
    def _init_ui(self):
        """初始化用户界面"""
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(
            main_frame, 
            text="弱口令验证工具", 
            font=("微软雅黑", 18, "bold")
        )
        title_label.pack(pady=(0, 15))
        
        # 创建选项卡
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # 单个验证选项卡
        self._create_single_tab()
        
        # 批量验证选项卡
        self._create_batch_tab()
        
        # 日志区域
        self._create_log_area(main_frame)
        
        # 状态栏
        self._create_status_bar(main_frame)
    
    def _create_single_tab(self):
        """创建单个验证选项卡"""
        single_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(single_frame, text="单个验证")
        
        # 输入区域
        input_frame = ttk.LabelFrame(single_frame, text="登录信息", padding="10")
        input_frame.pack(fill=tk.X, pady=(0, 10))
        
        # URL输入
        url_row = ttk.Frame(input_frame)
        url_row.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(url_row, text="URL:", width=10).pack(side=tk.LEFT)
        self.url_entry = ttk.Entry(url_row, width=60)
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        ttk.Button(url_row, text="测试连接", command=self._test_connection, width=10).pack(side=tk.LEFT, padx=(5, 0))
        
        # 用户名输入
        user_row = ttk.Frame(input_frame)
        user_row.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(user_row, text="用户名:", width=10).pack(side=tk.LEFT)
        self.username_entry = ttk.Entry(user_row, width=40)
        self.username_entry.pack(side=tk.LEFT, padx=(5, 0))
        
        # 密码输入
        pass_row = ttk.Frame(input_frame)
        pass_row.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(pass_row, text="密码:", width=10).pack(side=tk.LEFT)
        self.password_entry = ttk.Entry(pass_row, width=40, show="*")
        self.password_entry.pack(side=tk.LEFT, padx=(5, 0))
        self.show_pass_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            pass_row, text="显示密码", 
            variable=self.show_pass_var,
            command=self._toggle_password
        ).pack(side=tk.LEFT, padx=(10, 0))
        
        # 验证码输入（可选）
        captcha_row = ttk.Frame(input_frame)
        captcha_row.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(captcha_row, text="验证码:", width=10).pack(side=tk.LEFT)
        self.captcha_entry = ttk.Entry(captcha_row, width=20)
        self.captcha_entry.pack(side=tk.LEFT, padx=(5, 0))
        ttk.Button(captcha_row, text="自动识别", command=self._auto_captcha, width=10).pack(side=tk.LEFT, padx=(5, 0))
        self.auto_captcha_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(captcha_row, text="自动识别验证码", variable=self.auto_captcha_var).pack(side=tk.LEFT, padx=(10, 0))
        
        # 按钮区域
        btn_frame = ttk.Frame(single_frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        self.verify_btn = ttk.Button(
            btn_frame, text="开始验证", 
            command=self._single_verify, 
            width=15
        )
        self.verify_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(
            btn_frame, text="清空输入", 
            command=self._clear_single_input, 
            width=10
        ).pack(side=tk.LEFT)
        
        # 结果显示区域
        result_frame = ttk.LabelFrame(single_frame, text="验证结果", padding="10")
        result_frame.pack(fill=tk.BOTH, expand=True)
        
        self.result_text = scrolledtext.ScrolledText(
            result_frame, height=10, wrap=tk.WORD,
            font=("Consolas", 10)
        )
        self.result_text.pack(fill=tk.BOTH, expand=True)
        
        # 配置结果文本颜色
        self.result_text.tag_config("success", foreground="#28a745")
        self.result_text.tag_config("error", foreground="#dc3545")
        self.result_text.tag_config("warning", foreground="#ffc107")
        self.result_text.tag_config("info", foreground="#17a2b8")
    
    def _create_batch_tab(self):
        """创建批量验证选项卡"""
        batch_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(batch_frame, text="批量验证")
        
        # 导入区域
        import_frame = ttk.LabelFrame(batch_frame, text="导入目标", padding="10")
        import_frame.pack(fill=tk.X, pady=(0, 10))
        
        import_row = ttk.Frame(import_frame)
        import_row.pack(fill=tk.X)
        
        ttk.Button(
            import_row, text="导入CSV", 
            command=lambda: self._import_file('csv'),
            width=12
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(
            import_row, text="导入Excel", 
            command=lambda: self._import_file('excel'),
            width=12
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(
            import_row, text="导出模板", 
            command=self._export_template,
            width=12
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(
            import_row, text="清空列表", 
            command=self._clear_batch_list,
            width=12
        ).pack(side=tk.LEFT)
        
        # 目标统计
        self.batch_stats_var = tk.StringVar(value="目标: 0 | 待验证: 0 | 成功: 0 | 失败: 0")
        ttk.Label(import_row, textvariable=self.batch_stats_var).pack(side=tk.RIGHT)
        
        # 目标列表
        list_frame = ttk.Frame(batch_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 创建表格
        columns = ('序号', 'URL', '用户名', '状态', '响应时间', '详情')
        self.batch_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=12)
        
        # 设置列
        self.batch_tree.heading('序号', text='序号')
        self.batch_tree.heading('URL', text='URL')
        self.batch_tree.heading('用户名', text='用户名')
        self.batch_tree.heading('状态', text='状态')
        self.batch_tree.heading('响应时间', text='响应时间')
        self.batch_tree.heading('详情', text='详情')
        
        self.batch_tree.column('序号', width=50)
        self.batch_tree.column('URL', width=300)
        self.batch_tree.column('用户名', width=120)
        self.batch_tree.column('状态', width=100)
        self.batch_tree.column('响应时间', width=80)
        self.batch_tree.column('详情', width=200)
        
        # 滚动条
        scrollbar_v = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.batch_tree.yview)
        scrollbar_h = ttk.Scrollbar(list_frame, orient=tk.HORIZONTAL, command=self.batch_tree.xview)
        self.batch_tree.configure(yscrollcommand=scrollbar_v.set, xscrollcommand=scrollbar_h.set)
        
        self.batch_tree.grid(row=0, column=0, sticky='nsew')
        scrollbar_v.grid(row=0, column=1, sticky='ns')
        scrollbar_h.grid(row=1, column=0, sticky='ew')
        
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        
        # 配置行颜色
        self.batch_tree.tag_configure('success', foreground='#28a745')
        self.batch_tree.tag_configure('failed', foreground='#dc3545')
        self.batch_tree.tag_configure('pending', foreground='#6c757d')
        self.batch_tree.tag_configure('running', foreground='#ffc107')
        
        # 控制按钮
        ctrl_frame = ttk.Frame(batch_frame)
        ctrl_frame.pack(fill=tk.X)
        
        self.batch_start_btn = ttk.Button(
            ctrl_frame, text="开始批量验证", 
            command=self._start_batch_verify,
            width=15
        )
        self.batch_start_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.batch_stop_btn = ttk.Button(
            ctrl_frame, text="停止", 
            command=self._stop_batch_verify,
            width=10, state=tk.DISABLED
        )
        self.batch_stop_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 进度条
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            ctrl_frame, variable=self.progress_var,
            length=200, mode='determinate'
        )
        self.progress_bar.pack(side=tk.LEFT, padx=(0, 10))
        
        # 导出结果
        ttk.Button(
            ctrl_frame, text="导出结果", 
            command=self._export_results,
            width=10
        ).pack(side=tk.RIGHT)
    
    def _create_log_area(self, parent):
        """创建日志区域"""
        log_frame = ttk.LabelFrame(parent, text="运行日志", padding="5")
        log_frame.pack(fill=tk.X, pady=(10, 0))
        
        # 日志工具栏
        log_toolbar = ttk.Frame(log_frame)
        log_toolbar.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(log_toolbar, text="清空日志", command=self._clear_log, width=10).pack(side=tk.LEFT)
        ttk.Button(log_toolbar, text="保存日志", command=self._save_log, width=10).pack(side=tk.LEFT, padx=(5, 0))
        
        # 日志文本
        self.log_text = scrolledtext.ScrolledText(
            log_frame, height=6, wrap=tk.WORD,
            font=("Consolas", 9)
        )
        self.log_text.pack(fill=tk.X)
        
        # 日志颜色
        self.log_text.tag_config("INFO", foreground="#17a2b8")
        self.log_text.tag_config("SUCCESS", foreground="#28a745")
        self.log_text.tag_config("WARNING", foreground="#ffc107")
        self.log_text.tag_config("ERROR", foreground="#dc3545")
    
    def _create_status_bar(self, parent):
        """创建状态栏"""
        status_frame = ttk.Frame(parent)
        status_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(status_frame, textvariable=self.status_var).pack(side=tk.LEFT)
        
        # 版本信息
        ttk.Label(status_frame, text="v1.0").pack(side=tk.RIGHT)
    
    def _init_components(self):
        """初始化核心组件"""
        if not CORE_AVAILABLE:
            self.log("核心模块不可用，部分功能受限", "WARNING")
            return

        try:
            print("[DEBUG] 创建UnifiedVerifier...")
            # 使用统一验证器（异步模式）
            self.verifier = UnifiedVerifier(mode=VerifyMode.ASYNC, max_concurrent=5)
            print("[DEBUG] UnifiedVerifier创建成功")

            print("[DEBUG] 创建CaptchaRecognizer...")
            self.captcha_recognizer = CaptchaRecognizer()
            print("[DEBUG] CaptchaRecognizer创建成功")

            print("[DEBUG] 创建EnhancedBatchImporter...")
            self.batch_importer = EnhancedBatchImporter()
            print("[DEBUG] EnhancedBatchImporter创建成功")

            self.log("核心组件初始化完成（异步模式）", "SUCCESS")
        except Exception as e:
            print(f"[ERROR] 初始化失败: {e}")
            import traceback
            traceback.print_exc()
            self.log(f"初始化失败: {e}", "ERROR")
    
    def _start_result_handler(self):
        """启动结果处理线程"""
        def handler():
            while True:
                try:
                    result = self.result_queue.get(timeout=0.1)
                    if result is None:
                        break
                    self.root.after(0, self._handle_result, result)
                except queue.Empty:
                    continue
                except Exception as e:
                    print(f"结果处理错误: {e}")
        
        self.result_thread = threading.Thread(target=handler, daemon=True)
        self.result_thread.start()
    
    def _handle_result(self, result: Dict[str, Any]):
        """处理验证结果"""
        result_type = result.get('type')
        
        if result_type == 'single':
            self._display_single_result(result.get('data'))
        elif result_type == 'batch':
            self._update_batch_item(result.get('index'), result.get('data'))
    
    def _toggle_password(self):
        """切换密码显示"""
        if self.show_pass_var.get():
            self.password_entry.config(show="")
        else:
            self.password_entry.config(show="*")
    
    def _test_connection(self):
        """测试连接"""
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("警告", "请输入URL")
            return

        if not self.verifier:
            self.log("验证器未初始化", "ERROR")
            return

        self.log(f"测试连接: {url}", "INFO")
        self.status_var.set("正在测试连接...")

        def test():
            try:
                # 使用异步验证测试连接
                target = TargetInfo(url=url, username="test", password="test")
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                async def run_test():
                    async with self.verifier:
                        return await self.verifier.verify_async(target)

                result = loop.run_until_complete(run_test())
                loop.close()

                if result.status == LoginStatus.CONNECTION_ERROR:
                    self.root.after(0, lambda: self._on_connection_tested(False, result.message))
                else:
                    self.root.after(0, lambda: self._on_connection_tested(True, "连接成功"))
            except Exception as e:
                self.root.after(0, lambda: self._on_connection_tested(False, str(e)))

        threading.Thread(target=test, daemon=True).start()
    
    def _on_connection_tested(self, success: bool, message: str):
        """连接测试完成回调"""
        self.status_var.set("就绪")
        if success:
            self.log(f"连接成功: {message}", "SUCCESS")
            messagebox.showinfo("连接测试", message)
        else:
            self.log(f"连接失败: {message}", "ERROR")
            messagebox.showerror("连接测试", message)
    
    def _auto_captcha(self):
        """自动识别验证码"""
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("警告", "请先输入URL")
            return
        
        self.log("正在识别验证码...", "INFO")
        messagebox.showinfo("提示", "验证码识别功能需要在登录验证过程中自动完成")
    
    def _single_verify(self):
        """单个验证"""
        url = self.url_entry.get().strip()
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        captcha = self.captcha_entry.get().strip() or None

        # 验证输入
        if not url:
            messagebox.showwarning("警告", "请输入URL")
            return
        if not username:
            messagebox.showwarning("警告", "请输入用户名")
            return
        if not password:
            messagebox.showwarning("警告", "请输入密码")
            return

        if not self.verifier:
            self.log("验证器未初始化", "ERROR")
            return

        # 禁用按钮
        self.verify_btn.config(state=tk.DISABLED)
        self.status_var.set("正在验证...")
        self.log(f"开始验证: {url} | {username}", "INFO")

        # 清空结果
        self.result_text.delete(1.0, tk.END)

        def verify():
            try:
                # 使用异步验证
                target = TargetInfo(url=url, username=username, password=password)
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                async def run_verify():
                    async with self.verifier:
                        return await self.verifier.verify_async(target)

                result = loop.run_until_complete(run_verify())
                loop.close()

                self.result_queue.put({'type': 'single', 'data': result})
            except Exception as e:
                self.result_queue.put({
                    'type': 'single',
                    'data': LoginResult(
                        success=False,
                        status=LoginStatus.UNKNOWN_ERROR,
                        message=f"验证异常: {str(e)}",
                        response_time=0,
                        url=url,
                        final_url=url,
                        page_changed=False
                    )
                })
            finally:
                self.root.after(0, lambda: self.verify_btn.config(state=tk.NORMAL))
                self.root.after(0, lambda: self.status_var.set("就绪"))

        threading.Thread(target=verify, daemon=True).start()
    
    def _display_single_result(self, result: LoginResult):
        """显示单个验证结果"""
        self.result_text.delete(1.0, tk.END)
        
        # 状态
        status_text = result.status.value if result.status else "未知"
        if result.success:
            self.result_text.insert(tk.END, f"✅ 验证结果: 成功\n", "success")
        else:
            self.result_text.insert(tk.END, f"❌ 验证结果: 失败\n", "error")
        
        self.result_text.insert(tk.END, f"\n状态: {status_text}\n")
        self.result_text.insert(tk.END, f"消息: {result.message}\n")
        self.result_text.insert(tk.END, f"响应时间: {result.response_time:.2f}秒\n")
        self.result_text.insert(tk.END, f"页面变化: {'是' if result.page_changed else '否'}\n")
        
        if result.details:
            self.result_text.insert(tk.END, f"\n详细信息:\n", "info")
            for key, value in result.details.items():
                self.result_text.insert(tk.END, f"  {key}: {value}\n")
        
        # 记录日志
        if result.success:
            self.log(f"验证成功: {result.message}", "SUCCESS")
        else:
            self.log(f"验证失败: {result.message}", "ERROR")
    
    def _clear_single_input(self):
        """清空单个验证输入"""
        self.url_entry.delete(0, tk.END)
        self.username_entry.delete(0, tk.END)
        self.password_entry.delete(0, tk.END)
        self.captcha_entry.delete(0, tk.END)
        self.result_text.delete(1.0, tk.END)
    
    def _import_file(self, file_type: str):
        """导入文件"""
        if file_type == 'csv':
            filetypes = [("CSV文件", "*.csv"), ("所有文件", "*.*")]
        else:
            filetypes = [("Excel文件", "*.xlsx *.xls"), ("所有文件", "*.*")]
        
        filepath = filedialog.askopenfilename(title="选择文件", filetypes=filetypes)
        if not filepath:
            return
        
        if not self.batch_importer:
            self.log("批量导入器未初始化", "ERROR")
            return
        
        self.log(f"正在导入: {filepath}", "INFO")
        
        result = self.batch_importer.import_file(filepath)
        
        if result.success:
            self.batch_targets = result.targets
            self._refresh_batch_list()
            self.log(f"导入成功: {result.valid_count}条有效记录", "SUCCESS")
            
            if result.warnings:
                for warning in result.warnings[:5]:
                    self.log(warning, "WARNING")
        else:
            self.log(f"导入失败: {result.errors[0] if result.errors else '未知错误'}", "ERROR")
            messagebox.showerror("导入失败", result.errors[0] if result.errors else "未知错误")
    
    def _refresh_batch_list(self):
        """刷新批量目标列表"""
        # 清空现有数据
        for item in self.batch_tree.get_children():
            self.batch_tree.delete(item)
        
        # 重置结果
        self.batch_results = []
        
        # 添加新数据
        for i, target in enumerate(self.batch_targets, 1):
            self.batch_tree.insert('', 'end', values=(
                i,
                target.url[:50] + "..." if len(target.url) > 50 else target.url,
                target.username,
                '待验证',
                '',
                ''
            ), tags=('pending',))
            self.batch_results.append({
                'target': target,
                'status': '待验证',
                'response_time': 0,
                'message': ''
            })
        
        self._update_batch_stats()
    
    def _update_batch_stats(self):
        """更新批量统计"""
        total = len(self.batch_targets)
        pending = sum(1 for r in self.batch_results if r['status'] == '待验证')
        success = sum(1 for r in self.batch_results if r['status'] == '成功')
        failed = sum(1 for r in self.batch_results if r['status'] == '失败')
        
        self.batch_stats_var.set(f"目标: {total} | 待验证: {pending} | 成功: {success} | 失败: {failed}")
    
    def _update_batch_item(self, index: int, result: LoginResult):
        """更新批量列表项"""
        items = self.batch_tree.get_children()
        if index >= len(items):
            return
        
        item = items[index]
        target = self.batch_targets[index]
        
        # 确定状态和标签
        if result.success:
            status = '成功'
            tag = 'success'
        else:
            status = '失败'
            tag = 'failed'
        
        # 更新显示
        self.batch_tree.item(item, values=(
            index + 1,
            target.url[:50] + "..." if len(target.url) > 50 else target.url,
            target.username,
            status,
            f"{result.response_time:.2f}s",
            result.message[:30] + "..." if len(result.message) > 30 else result.message
        ), tags=(tag,))
        
        # 更新结果数据
        self.batch_results[index] = {
            'target': target,
            'status': status,
            'response_time': result.response_time,
            'message': result.message,
            'result': result
        }
        
        self._update_batch_stats()
    
    def _start_batch_verify(self):
        """开始批量验证"""
        if not self.batch_targets:
            messagebox.showwarning("警告", "请先导入目标")
            return

        if not self.verifier:
            self.log("验证器未初始化", "ERROR")
            return

        self.is_running = True
        self.stop_flag = False

        self.batch_start_btn.config(state=tk.DISABLED)
        self.batch_stop_btn.config(state=tk.NORMAL)
        self.progress_var.set(0)
        self.status_var.set("正在批量验证...")

        self.log(f"开始批量验证，共{len(self.batch_targets)}个目标", "INFO")

        def batch_worker():
            try:
                # 使用异步批量验证
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                async def run_batch_verify():
                    async with self.verifier:
                        # 先await获取结果列表
                        results = await self.verifier.verify_batch(self.batch_targets)

                        # 然后遍历结果
                        for i, result in enumerate(results):
                            if self.stop_flag:
                                break

                            # 更新状态为运行中
                            self.root.after(0, lambda idx=i: self._set_item_running(idx))

                            # 发送结果到队列
                            self.result_queue.put({
                                'type': 'batch',
                                'index': i,
                                'data': result
                            })

                            # 更新进度
                            progress = (i + 1) / len(self.batch_targets) * 100
                            self.root.after(0, lambda p=progress: self.progress_var.set(p))

                loop.run_until_complete(run_batch_verify())
                loop.close()

            except Exception as e:
                self.log(f"批量验证异常: {str(e)}", "ERROR")
                import traceback
                traceback.print_exc()

            self.root.after(0, self._on_batch_complete)

        threading.Thread(target=batch_worker, daemon=True).start()
    
    def _set_item_running(self, index: int):
        """设置项目为运行中状态"""
        items = self.batch_tree.get_children()
        if index < len(items):
            item = items[index]
            values = list(self.batch_tree.item(item)['values'])
            values[3] = '验证中'
            self.batch_tree.item(item, values=values, tags=('running',))
    
    def _stop_batch_verify(self):
        """停止批量验证"""
        self.stop_flag = True
        self.log("正在停止批量验证...", "WARNING")
    
    def _on_batch_complete(self):
        """批量验证完成"""
        self.is_running = False
        self.batch_start_btn.config(state=tk.NORMAL)
        self.batch_stop_btn.config(state=tk.DISABLED)
        self.status_var.set("就绪")
        
        # 统计结果
        success = sum(1 for r in self.batch_results if r['status'] == '成功')
        failed = sum(1 for r in self.batch_results if r['status'] == '失败')
        
        if self.stop_flag:
            self.log("批量验证已停止", "WARNING")
        else:
            self.log(f"批量验证完成，成功: {success}，失败: {failed}", "SUCCESS")
        
        messagebox.showinfo("完成", f"批量验证完成\n成功: {success}\n失败: {failed}")
    
    def _clear_batch_list(self):
        """清空批量列表"""
        if self.is_running:
            messagebox.showwarning("警告", "请先停止当前验证")
            return
        
        self.batch_targets.clear()
        self.batch_results.clear()
        for item in self.batch_tree.get_children():
            self.batch_tree.delete(item)
        self._update_batch_stats()
        self.log("批量列表已清空", "INFO")
    
    def _export_template(self):
        """导出模板"""
        filepath = filedialog.asksaveasfilename(
            title="保存模板",
            defaultextension=".csv",
            filetypes=[("CSV文件", "*.csv")]
        )
        
        if not filepath:
            return
        
        if self.batch_importer:
            if self.batch_importer.export_template(filepath):
                self.log(f"模板已导出: {filepath}", "SUCCESS")
                messagebox.showinfo("成功", f"模板已保存到:\n{filepath}")
            else:
                self.log("模板导出失败", "ERROR")
        else:
            # 手动创建简单模板
            try:
                with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f)
                    writer.writerow(['URL', '用户名', '密码'])
                    writer.writerow(['https://example.com/login', 'admin', 'password123'])
                self.log(f"模板已导出: {filepath}", "SUCCESS")
                messagebox.showinfo("成功", f"模板已保存到:\n{filepath}")
            except Exception as e:
                self.log(f"模板导出失败: {e}", "ERROR")
    
    def _export_results(self):
        """导出结果"""
        if not self.batch_results:
            messagebox.showwarning("警告", "没有可导出的结果")
            return
        
        filepath = filedialog.asksaveasfilename(
            title="保存结果",
            defaultextension=".csv",
            filetypes=[("CSV文件", "*.csv"), ("所有文件", "*.*")]
        )
        
        if not filepath:
            return
        
        try:
            with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(['序号', 'URL', '用户名', '状态', '响应时间(秒)', '详情'])
                
                for i, result in enumerate(self.batch_results, 1):
                    target = result['target']
                    writer.writerow([
                        i,
                        target.url,
                        target.username,
                        result['status'],
                        f"{result['response_time']:.2f}",
                        result['message']
                    ])
            
            self.log(f"结果已导出: {filepath}", "SUCCESS")
            messagebox.showinfo("成功", f"结果已保存到:\n{filepath}")
            
        except Exception as e:
            self.log(f"导出失败: {e}", "ERROR")
            messagebox.showerror("错误", f"导出失败: {e}")
    
    def log(self, message: str, level: str = "INFO"):
        """添加日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_line = f"[{timestamp}] [{level}] {message}\n"
        
        self.log_text.insert(tk.END, log_line, level)
        self.log_text.see(tk.END)
        
        # 限制日志行数
        line_count = int(self.log_text.index('end-1c').split('.')[0])
        if line_count > 500:
            self.log_text.delete('1.0', '100.0')
    
    def _clear_log(self):
        """清空日志"""
        self.log_text.delete(1.0, tk.END)
    
    def _save_log(self):
        """保存日志"""
        filepath = filedialog.asksaveasfilename(
            title="保存日志",
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        
        if not filepath:
            return
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(self.log_text.get(1.0, tk.END))
            messagebox.showinfo("成功", f"日志已保存到:\n{filepath}")
        except Exception as e:
            messagebox.showerror("错误", f"保存失败: {e}")
    
    def _on_closing(self):
        """窗口关闭事件"""
        if self.is_running:
            if not messagebox.askyesno("确认", "正在运行验证任务，确定要退出吗？"):
                return
            self.stop_flag = True

        # 停止结果处理线程
        self.result_queue.put(None)

        self.root.destroy()
    
    def run(self):
        """运行应用"""
        self.root.mainloop()


def main():
    """主函数"""
    print("[DEBUG] 开始初始化应用...")
    try:
        app = WeakPasswordTool()
        print("[DEBUG] 应用初始化成功，启动主循环...")
        app.run()
        print("[DEBUG] 主循环结束")
    except Exception as e:
        print(f"[ERROR] 启动失败: {e}")
        import traceback
        traceback.print_exc()
        input("按回车键退出...")


if __name__ == "__main__":
    main()