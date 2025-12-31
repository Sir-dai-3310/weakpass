#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
弱口令验证工具 - 启动脚本
简洁版本，直接启动主程序
"""

import sys
import os

# 设置编码
os.environ['PYTHONIOENCODING'] = 'utf-8'

# 添加当前目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)


def check_dependencies():
    """检查核心依赖"""
    missing = []
    
    # 检查必需依赖
    try:
        import requests
    except ImportError:
        missing.append('requests')
    
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        missing.append('beautifulsoup4')
    
    try:
        import tkinter
    except ImportError:
        missing.append('tkinter (Python自带)')
    
    if missing:
        print("缺少必需依赖:")
        for dep in missing:
            print(f"  - {dep}")
        print("\n请运行: pip install " + " ".join([d for d in missing if 'tkinter' not in d]))
        return False
    
    # 检查可选依赖
    optional_missing = []
    
    try:
        import PIL
    except ImportError:
        optional_missing.append('Pillow')
    
    try:
        import pytesseract
    except ImportError:
        optional_missing.append('pytesseract')
    
    try:
        import cv2
    except ImportError:
        optional_missing.append('opencv-python')
    
    if optional_missing:
        print("可选依赖未安装(验证码识别功能需要):")
        for dep in optional_missing:
            print(f"  - {dep}")
        print("可选安装: pip install " + " ".join(optional_missing))
        print()
    
    return True


def main():
    """主函数"""
    print("=" * 50)
    print("  弱口令验证工具 v1.0")
    print("=" * 50)
    print()
    
    # 检查依赖
    print("检查依赖...")
    if not check_dependencies():
        input("按回车键退出...")
        return
    
    print("依赖检查通过!")
    print()
    print("启动图形界面...")
    
    try:
        from main_app import main as run_app
        run_app()
    except ImportError as e:
        print(f"导入错误: {e}")
        print("请确保所有核心文件存在")
        input("按回车键退出...")
    except Exception as e:
        print(f"启动失败: {e}")
        import traceback
        traceback.print_exc()
        input("按回车键退出...")


if __name__ == "__main__":
    main()