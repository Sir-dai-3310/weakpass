#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用向导模块
提供首次使用向导和模板下载功能
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Callable, Optional, List, Dict, Any
from pathlib import Path
import json
import csv
from enum import Enum

from .enhanced_batch_importer import EnhancedBatchImporter, ImportFormat, get_supported_formats


class WizardStep(Enum):
    """向导步骤"""
    WELCOME = 0
    DEPENDENCY_CHECK = 1
    TEMPLATE_DOWNLOAD = 2
    QUICK_START = 3
    COMPLETE = 4


class SetupWizard:
    """设置向导"""
    
    def __init__(self, parent: tk.Tk, on_complete: Optional[Callable] = None):
        """
        初始化向导
        
        Args:
            parent: 父窗口
            on_complete: 完成回调
        """
        self.parent = parent
        self.on_complete = on_complete
        
        # 创建向导窗口
        self.window = tk.Toplevel(parent)
        self.window.title("弱口令验证工具 - 首次使用向导")
        self.window.geometry("700x500")
        self.window.resizable(False, False)
        
        # 居中显示
        self.window.transient(parent)
        self.window.grab_set()
        
        # 当前步骤
        self.current_step = WizardStep.WELCOME
        
        # 组件
        self.content_frame = ttk.Frame(self.window, padding="20")
        self.content_frame.pack(fill=tk.BOTH, expand=True)
        
        self.button_frame = ttk.Frame(self.window, padding="10")
        self.button_frame.pack(fill=tk.X)
        
        # 显示欢迎页面
        self.show_step(WizardStep.WELCOME)
    
    def show_step(self, step: WizardStep):
        """显示指定步骤"""
        self.current_step = step
        
        # 清空内容区域
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # 根据步骤显示不同内容
        if step == WizardStep.WELCOME:
            self._show_welcome()
        elif step == WizardStep.DEPENDENCY_CHECK:
            self._show_dependency_check()
        elif step == WizardStep.TEMPLATE_DOWNLOAD:
            self._show_template_download()
        elif step == WizardStep.QUICK_START:
            self._show_quick_start()
        elif step == WizardStep.COMPLETE:
            self._show_complete()
        
        # 更新按钮
        self._update_buttons()
    
    def _show_welcome(self):
        """显示欢迎页面"""
        # 标题
        title_label = ttk.Label(
            self.content_frame,
            text="欢迎使用弱口令验证工具",
            font=("微软雅黑", 18, "bold")
        )
        title_label.pack(pady=(20, 10))
        
        # 说明文本
        welcome_text = """
弱口令验证工具是一个用于授权安全测试的工具，帮助您：
• 批量验证多个目标账号的密码强度
• 自动识别数字/字母验证码
• 支持多种导入格式（CSV、Excel、TXT）
• 提供详细的验证报告

本向导将帮助您完成首次设置，包括：
✓ 检查依赖环境
✓ 下载模板文件
✓ 快速开始使用

点击"下一步"开始设置。
        """
        
        text_label = ttk.Label(
            self.content_frame,
            text=welcome_text,
            justify=tk.LEFT,
            font=("微软雅黑", 10)
        )
        text_label.pack(pady=20, padx=40, anchor=tk.W)
        
        # 图标/图片区域（可选）
        icon_frame = ttk.Frame(self.content_frame)
        icon_frame.pack(pady=30)
        
        # 使用文本图标
        icon_label = ttk.Label(
            icon_frame,
            text="🔐",
            font=("Segoe UI Emoji", 64)
        )
        icon_label.pack()
    
    def _show_dependency_check(self):
        """显示依赖检查页面"""
        # 标题
        title_label = ttk.Label(
            self.content_frame,
            text="检查依赖环境",
            font=("微软雅黑", 16, "bold")
        )
        title_label.pack(pady=(20, 10))
        
        # 检查结果区域
        self.dep_results_frame = ttk.Frame(self.content_frame)
        self.dep_results_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # 检查按钮
        check_btn = ttk.Button(
            self.dep_results_frame,
            text="开始检查",
            command=self._check_dependencies
        )
        check_btn.pack(pady=10)
        
        # 说明文本
        info_text = """
工具需要以下依赖才能正常运行：

必需依赖：
• requests - HTTP请求库
• beautifulsoup4 - HTML解析库

可选依赖（增强功能）：
• aiohttp - 异步支持（推荐）
• Pillow, pytesseract - 验证码识别
• pandas, openpyxl - Excel文件支持
        """
        
        info_label = ttk.Label(
            self.content_frame,
            text=info_text,
            justify=tk.LEFT,
            font=("微软雅黑", 9)
        )
        info_label.pack(pady=10, padx=20, anchor=tk.W)
    
    def _check_dependencies(self):
        """检查依赖"""
        # 清空结果区域
        for widget in self.dep_results_frame.winfo_children():
            if widget.winfo_class() != 'TButton':
                widget.destroy()
        
        dependencies = [
            ('requests', '必需'),
            ('beautifulsoup4', '必需'),
            ('aiohttp', '推荐'),
            ('Pillow', '可选'),
            ('pytesseract', '可选'),
            ('pandas', '可选'),
            ('openpyxl', '可选')
        ]
        
        all_installed = True
        
        for dep, level in dependencies:
            try:
                __import__(dep)
                status = "✓ 已安装"
                status_color = "green"
            except ImportError:
                status = "✗ 未安装"
                status_color = "red"
                if level == "必需":
                    all_installed = False
            
            # 创建结果行
            row_frame = ttk.Frame(self.dep_results_frame)
            row_frame.pack(fill=tk.X, pady=2, padx=20)
            
            name_label = ttk.Label(row_frame, text=f"{dep:20s}", width=20)
            name_label.pack(side=tk.LEFT)
            
            level_label = ttk.Label(row_frame, text=f"{level:6s}", width=6)
            level_label.pack(side=tk.LEFT, padx=10)
            
            status_label = ttk.Label(row_frame, text=status, foreground=status_color)
            status_label.pack(side=tk.LEFT)
        
        # 安装按钮
        if not all_installed:
            install_btn = ttk.Button(
                self.dep_results_frame,
                text="安装缺失的依赖",
                command=self._install_dependencies
            )
            install_btn.pack(pady=10)
        
        # 完成状态
        self.dep_check_complete = True
        self.dep_all_installed = all_installed
    
    def _install_dependencies(self):
        """安装依赖"""
        import subprocess
        import sys
        
        try:
            # 显示安装信息
            info_label = ttk.Label(
                self.dep_results_frame,
                text="正在安装依赖，请稍候...",
                foreground="blue"
            )
            info_label.pack(pady=10)
            
            self.window.update()
            
            # 安装核心依赖
            subprocess.check_call([
                sys.executable, "-m", "pip", "install",
                "requests", "beautifulsoup4", "aiohttp"
            ])
            
            # 重新检查
            self._check_dependencies()
            
            messagebox.showinfo("成功", "依赖安装完成！")
            
        except Exception as e:
            messagebox.showerror("错误", f"安装失败: {e}")
    
    def _show_template_download(self):
        """显示模板下载页面"""
        # 标题
        title_label = ttk.Label(
            self.content_frame,
            text="下载模板文件",
            font=("微软雅黑", 16, "bold")
        )
        title_label.pack(pady=(20, 10))
        
        # 说明文本
        info_text = """
下载模板文件可以快速开始批量验证：

目标文件模板：
• CSV格式 - 最常用格式
• Excel格式 - 支持xlsx/xls
• JSON格式 - 适合程序化使用

字典文件模板：
• 用户名字典 - 包含常见用户名
• 密码字典 - 包含常见弱密码
        """
        
        info_label = ttk.Label(
            self.content_frame,
            text=info_text,
            justify=tk.LEFT,
            font=("微软雅黑", 10)
        )
        info_label.pack(pady=10, padx=20, anchor=tk.W)
        
        # 模板按钮区域
        template_frame = ttk.LabelFrame(self.content_frame, text="选择模板", padding="15")
        template_frame.pack(fill=tk.X, pady=20, padx=20)
        
        # 目标文件模板
        target_frame = ttk.Frame(template_frame)
        target_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(target_frame, text="目标文件:").pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            target_frame,
            text="CSV模板",
            command=lambda: self._download_template('csv')
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            target_frame,
            text="Excel模板",
            command=lambda: self._download_template('excel')
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            target_frame,
            text="JSON模板",
            command=lambda: self._download_template('json')
        ).pack(side=tk.LEFT, padx=5)
        
        # 字典文件模板
        dict_frame = ttk.Frame(template_frame)
        dict_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(dict_frame, text="字典文件:").pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            dict_frame,
            text="用户名字典",
            command=lambda: self._download_dict('usernames')
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            dict_frame,
            text="密码字典",
            command=lambda: self._download_dict('passwords')
        ).pack(side=tk.LEFT, padx=5)
    
    def _download_template(self, format: str):
        """下载模板"""
        importer = EnhancedBatchImporter()
        
        # 选择保存位置
        filetypes = {
            'csv': [("CSV文件", "*.csv")],
            'excel': [("Excel文件", "*.xlsx")],
            'json': [("JSON文件", "*.json")]
        }
        
        filepath = filedialog.asksaveasfilename(
            title="保存模板文件",
            defaultextension=f".{format}",
            filetypes=filetypes.get(format, [("所有文件", "*.*")])
        )
        
        if filepath:
            format_map = {
                'csv': ImportFormat.CSV,
                'excel': ImportFormat.EXCEL,
                'json': ImportFormat.JSON
            }
            
            success = importer.export_template(filepath, format_map.get(format))
            
            if success:
                messagebox.showinfo("成功", f"模板已保存到:\n{filepath}")
            else:
                messagebox.showerror("错误", "保存模板失败")
    
    def _download_dict(self, dict_type: str):
        """下载字典"""
        # 字典内容
        dictionaries = {
            'usernames': [
                "# 用户名字典\n",
                "# 每行一个用户名\n\n",
                "admin\n",
                "administrator\n",
                "root\n",
                "test\n",
                "user\n",
                "guest\n"
            ],
            'passwords': [
                "# 密码字典\n",
                "# 每行一个密码\n\n",
                "123456\n",
                "password\n",
                "admin\n",
                "12345678\n",
                "qwerty\n",
                "abc123\n"
            ]
        }
        
        # 选择保存位置
        filetypes = {
            'usernames': [("文本文件", "*.txt")],
            'passwords': [("文本文件", "*.txt")]
        }
        
        default_name = {
            'usernames': 'usernames.txt',
            'passwords': 'passwords.txt'
        }
        
        filepath = filedialog.asksaveasfilename(
            title="保存字典文件",
            defaultfilename=default_name.get(dict_type, 'dict.txt'),
            filetypes=filetypes.get(dict_type, [("所有文件", "*.*")])
        )
        
        if filepath:
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.writelines(dictionaries.get(dict_type, []))
                
                messagebox.showinfo("成功", f"字典已保存到:\n{filepath}")
            except Exception as e:
                messagebox.showerror("错误", f"保存字典失败: {e}")
    
    def _show_quick_start(self):
        """显示快速开始页面"""
        # 标题
        title_label = ttk.Label(
            self.content_frame,
            text="快速开始",
            font=("微软雅黑", 16, "bold")
        )
        title_label.pack(pady=(20, 10))
        
        # 快速开始步骤
        steps_text = """
步骤 1: 准备目标文件
• 使用下载的模板或创建自己的目标文件
• 添加要测试的目标URL、用户名和密码

步骤 2: 启动工具
• 运行图形界面：双击"启动图形界面.bat"
• 或使用命令行：python launcher.py --gui

步骤 3: 导入目标
• 在"批量验证"选项卡点击"导入CSV"
• 选择准备好的目标文件

步骤 4: 开始扫描
• 点击"开始批量验证"
• 查看实时进度和结果

步骤 5: 导出结果
• 扫描完成后点击"导出结果"
• 选择保存位置和格式
        """
        
        steps_label = ttk.Label(
            self.content_frame,
            text=steps_text,
            justify=tk.LEFT,
            font=("微软雅黑", 10)
        )
        steps_label.pack(pady=20, padx=30, anchor=tk.W)
    
    def _show_complete(self):
        """显示完成页面"""
        # 标题
        title_label = ttk.Label(
            self.content_frame,
            text="设置完成！",
            font=("微软雅黑", 18, "bold"),
            foreground="green"
        )
        title_label.pack(pady=(30, 10))
        
        # 成功图标
        icon_label = ttk.Label(
            self.content_frame,
            text="✓",
            font=("Segoe UI Emoji", 64),
            foreground="green"
        )
        icon_label.pack(pady=20)
        
        # 说明文本
        complete_text = """
您已完成首次设置，现在可以开始使用工具了！

重要提示：
• 本工具仅用于授权的安全测试
• 请遵守相关法律法规
• 妥善保管测试账号信息
• 定期更新密码字典

需要帮助？
• 查看使用说明.md
• 访问项目文档
        """
        
        text_label = ttk.Label(
            self.content_frame,
            text=complete_text,
            justify=tk.LEFT,
            font=("微软雅黑", 10)
        )
        text_label.pack(pady=20, padx=40)
    
    def _update_buttons(self):
        """更新按钮状态"""
        # 清空按钮区域
        for widget in self.button_frame.winfo_children():
            widget.destroy()
        
        # 上一步按钮
        if self.current_step != WizardStep.WELCOME:
            prev_btn = ttk.Button(
                self.button_frame,
                text="上一步",
                command=self._prev_step
            )
            prev_btn.pack(side=tk.LEFT)
        
        # 下一步/完成按钮
        if self.current_step == WizardStep.COMPLETE:
            next_btn = ttk.Button(
                self.button_frame,
                text="开始使用",
                command=self._finish
            )
            next_btn.pack(side=tk.RIGHT)
        else:
            next_btn = ttk.Button(
                self.button_frame,
                text="下一步",
                command=self._next_step
            )
            next_btn.pack(side=tk.RIGHT)
        
        # 跳过按钮
        if self.current_step != WizardStep.WELCOME and self.current_step != WizardStep.COMPLETE:
            skip_btn = ttk.Button(
                self.button_frame,
                text="跳过",
                command=self._finish
            )
            skip_btn.pack(side=tk.RIGHT, padx=10)
    
    def _next_step(self):
        """下一步"""
        if self.current_step == WizardStep.WELCOME:
            self.show_step(WizardStep.DEPENDENCY_CHECK)
        elif self.current_step == WizardStep.DEPENDENCY_CHECK:
            self.show_step(WizardStep.TEMPLATE_DOWNLOAD)
        elif self.current_step == WizardStep.TEMPLATE_DOWNLOAD:
            self.show_step(WizardStep.QUICK_START)
        elif self.current_step == WizardStep.QUICK_START:
            self.show_step(WizardStep.COMPLETE)
    
    def _prev_step(self):
        """上一步"""
        if self.current_step == WizardStep.DEPENDENCY_CHECK:
            self.show_step(WizardStep.WELCOME)
        elif self.current_step == WizardStep.TEMPLATE_DOWNLOAD:
            self.show_step(WizardStep.DEPENDENCY_CHECK)
        elif self.current_step == WizardStep.QUICK_START:
            self.show_step(WizardStep.TEMPLATE_DOWNLOAD)
    
    def _finish(self):
        """完成向导"""
        self.window.destroy()
        
        if self.on_complete:
            self.on_complete()


def show_wizard(parent: tk.Tk, on_complete: Optional[Callable] = None) -> SetupWizard:
    """
    显示设置向导
    
    Args:
        parent: 父窗口
        on_complete: 完成回调
        
    Returns:
        SetupWizard对象
    """
    wizard = SetupWizard(parent, on_complete)
    return wizard


if __name__ == "__main__":
    # 测试向导
    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口
    
    def on_complete():
        print("向导完成")
        root.destroy()
    
    wizard = show_wizard(root, on_complete)
    
    root.mainloop()