#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
弱口令验证工具 - 命令行批量验证脚本
用于直接从命令行对CSV文件进行批量验证
"""

import sys
import os
import argparse
from pathlib import Path
from datetime import datetime
import io

# 设置控制台输出编码
if sys.platform == 'win32':
    # Windows下强制使用UTF-8输出
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except:
        pass

# 设置编码
os.environ['PYTHONIOENCODING'] = 'utf-8'

# 添加当前目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# 导入核心模块
try:
    from core import (
        LoginVerifier, LoginResult, LoginStatus,
        BatchImporter, TargetInfo, ImportResult
    )
    CORE_AVAILABLE = True
except ImportError as e:
    print(f"核心模块导入失败: {e}")
    CORE_AVAILABLE = False
    sys.exit(1)


def print_banner():
    """打印横幅"""
    print("=" * 60)
    print("  弱口令验证工具 - 命令行批量验证")
    print("=" * 60)
    print()


def verify_targets(filepath: str, output_file: str = None, verbose: bool = False):
    """
    验证目标文件
    
    Args:
        filepath: 目标文件路径
        output_file: 结果输出文件路径
        verbose: 是否显示详细信息
    """
    # 初始化组件
    print("[*] 初始化组件...")
    importer = BatchImporter()
    verifier = LoginVerifier(timeout=30, verify_ssl=False)
    
    # 导入文件
    print(f"[*] 导入文件: {filepath}")
    result = importer.import_file(filepath)
    
    if not result.success:
        print(f"[!] 导入失败: {result.errors[0] if result.errors else '未知错误'}")
        return
    
    print(f"[+] 导入成功: {result.valid_count} 条有效记录，{result.invalid_count} 条无效")
    
    if result.warnings:
        for warning in result.warnings[:5]:
            print(f"[!] 警告: {warning}")
    
    if not result.targets:
        print("[!] 没有可验证的目标")
        return
    
    # 开始验证
    print()
    print(f"[*] 开始验证 {len(result.targets)} 个目标...")
    print("-" * 60)
    
    results = []
    success_count = 0
    fail_count = 0
    error_count = 0
    
    for i, target in enumerate(result.targets, 1):
        print(f"\n[{i}/{len(result.targets)}] 验证: {target.url}")
        print(f"    用户名: {target.username}")
        
        try:
            login_result = verifier.verify_login(
                url=target.url,
                username=target.username,
                password=target.password
            )
            
            status_str = "成功" if login_result.success else "失败"
            status_icon = "[OK]" if login_result.success else "[FAIL]"
            
            print(f"    结果: {status_icon} {status_str}")
            print(f"    消息: {login_result.message}")
            print(f"    响应时间: {login_result.response_time:.2f}秒")
            
            if verbose and login_result.details:
                print(f"    详情: {login_result.details}")
            
            if login_result.success:
                success_count += 1
            else:
                fail_count += 1
            
            results.append({
                'url': target.url,
                'username': target.username,
                'password': target.password,
                'success': login_result.success,
                'status': login_result.status.value,
                'message': login_result.message,
                'response_time': login_result.response_time
            })
            
        except Exception as e:
            print(f"    结果: [ERROR] 错误")
            print(f"    消息: {str(e)}")
            error_count += 1
            
            results.append({
                'url': target.url,
                'username': target.username,
                'password': target.password,
                'success': False,
                'status': 'error',
                'message': str(e),
                'response_time': 0
            })
    
    # 打印汇总
    print()
    print("=" * 60)
    print("  验证结果汇总")
    print("=" * 60)
    print(f"  总计: {len(result.targets)}")
    print(f"  成功: {success_count}")
    print(f"  失败: {fail_count}")
    print(f"  错误: {error_count}")
    print()
    
    # 保存结果
    if output_file:
        save_results(results, output_file)
        print(f"[+] 结果已保存到: {output_file}")
    
    # 显示成功的目标
    if success_count > 0:
        print()
        print("成功的目标:")
        print("-" * 60)
        for r in results:
            if r['success']:
                print(f"  {r['url']} | {r['username']} | {r['password']}")


def save_results(results: list, output_file: str):
    """保存结果到文件"""
    import csv
    
    with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'url', 'username', 'password', 'success', 'status', 'message', 'response_time'
        ])
        writer.writeheader()
        writer.writerows(results)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='弱口令验证工具 - 命令行批量验证',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python cli_verify.py targets.csv
  python cli_verify.py targets.csv -o results.csv
  python cli_verify.py targets.csv -v
        """
    )
    
    parser.add_argument('file', help='目标文件路径 (CSV/Excel)')
    parser.add_argument('-o', '--output', help='结果输出文件路径')
    parser.add_argument('-v', '--verbose', action='store_true', help='显示详细信息')
    
    args = parser.parse_args()
    
    print_banner()
    
    # 检查文件是否存在
    if not os.path.exists(args.file):
        print(f"[!] 文件不存在: {args.file}")
        sys.exit(1)
    
    # 设置默认输出文件
    output_file = args.output
    if not output_file:
        base_name = Path(args.file).stem
        output_file = f"{base_name}_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    # 运行验证
    verify_targets(args.file, output_file, args.verbose)


if __name__ == "__main__":
    main()