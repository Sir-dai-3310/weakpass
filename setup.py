#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WeakPass - 弱口令验证工具
安装配置文件
"""

from setuptools import setup, find_packages
import os

# 读取 README 文件
def read_file(filename):
    """读取文件内容"""
    with open(os.path.join(os.path.dirname(__file__), filename), encoding='utf-8') as f:
        return f.read()

# 读取依赖
def read_requirements(filename='requirements.txt'):
    """读取依赖列表"""
    requirements = []
    if os.path.exists(filename):
        with open(filename, encoding='utf-8') as f:
            requirements = [
                line.strip()
                for line in f
                if line.strip() and not line.startswith('#')
            ]
    return requirements

setup(
    name='weakpass',
    version='1.0.0',
    author='WeakPass Team',
    author_email='contact@weakpass.dev',
    description='弱口令验证工具 - 用于安全审计和学习',
    long_description=read_file('README.md'),
    long_description_content_type='text/markdown',
    url='https://github.com/yourusername/weakpass',
    packages=find_packages(),
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Topic :: Security',
        'Topic :: System :: Systems Administration',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.8',
    install_requires=read_requirements(),
    extras_require={
        'captcha': [
            'Pillow>=9.0.0',
            'pytesseract>=0.3.10',
            'opencv-python>=4.6.0',
            'numpy>=1.21.0',
            'easyocr>=1.7.0',
        ],
        'excel': [
            'pandas>=1.4.0',
            'openpyxl>=3.0.0',
            'xlrd>=2.0.0',
        ],
    },
    entry_points={
        'console_scripts': [
            'weakpass=main_app:main',
        ],
    },
    include_package_data=True,
    keywords='weakpass security password verification audit',
    project_urls={
        'Bug Reports': 'https://github.com/yourusername/weakpass/issues',
        'Source': 'https://github.com/yourusername/weakpass',
        'Documentation': 'https://github.com/yourusername/weakpass/blob/main/README.md',
    },
)