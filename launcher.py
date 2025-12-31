#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
弱口令验证工具 - 增强版启动器
支持交互式菜单、命令行参数和批量CSV导入
"""

import sys
import os
import argparse
import io
from pathlib import Path
from datetime import datetime

# 设置控制台输出编码
if sys.platform == 'win32':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except:
        pass

os.environ['PYTHONIOENCODING'] = 'utf-8'

# 添加当前目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)


def print_banner():
    """打印横幅"""
    print()
    print("=" * 60)
    print("       弱口令验证工具 v2.0 - 统一验证器")
    print("=" * 60)
    print()


def check_dependencies():
    """检查依赖"""
    missing = []
    
    try:
        import requests
    except ImportError:
        missing.append('requests')
    
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        missing.append('beautifulsoup4')
    
    if missing:
        print("[!] 缺少必需依赖:")
        for dep in missing:
            print(f"    - {dep}")
        print()
        print(f"    请运行: pip install {' '.join(missing)}")
        return False
    
    return True


def find_csv_files():
    """查找当前目录下的CSV文件"""
    csv_files = []
    for f in Path(current_dir).glob("*.csv"):
        # 排除结果文件
        if "_results_" not in f.name:
            csv_files.append(f)
    return csv_files


def get_sample_csv():
    """获取示例目标CSV文件"""
    sample = Path(current_dir) / "示例目标.csv"
    if sample.exists():
        return sample
    return None


def run_batch_verify(csv_path: str, output_dir: str = None, verbose: bool = False):
    """
    运行批量验证（使用新的统一验证器）

    Args:
        csv_path: CSV文件路径
        output_dir: 结果输出目录
        verbose: 是否显示详细信息
    """
    try:
        from core import UnifiedVerifier, VerifyMode, TargetInfo, LoginStatus
        from core.enhanced_batch_importer import EnhancedBatchImporter
        import csv
        import asyncio
    except ImportError as e:
        print(f"[!] 核心模块导入失败: {e}")
        return False

    print(f"[*] 初始化统一验证器（异步模式）...")
    importer = EnhancedBatchImporter()

    # 导入文件
    print(f"[*] 导入文件: {csv_path}")
    result = importer.import_file(csv_path)

    if not result.success:
        print(f"[!] 导入失败: {result.errors[0] if result.errors else '未知错误'}")
        return False

    print(f"[+] 导入成功: {result.valid_count} 条有效记录，{result.invalid_count} 条无效")

    if result.warnings:
        for warning in result.warnings[:3]:
            print(f"[!] 警告: {warning}")

    if not result.targets:
        print("[!] 没有可验证的目标")
        return False

    # 开始验证
    print()
    print(f"[*] 开始异步验证 {len(result.targets)} 个目标...")
    print("-" * 60)

    # 异步批量验证
    async def run_async_verify():
        from core.simple_config import get_simple_config_manager
        config_manager = get_simple_config_manager()

        async with UnifiedVerifier(
            config_manager,
            mode=VerifyMode.ASYNC,
            max_concurrent=5
        ) as verifier:
            return await verifier.verify_batch(result.targets, delay=0.3)

    # 运行异步验证
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        login_results = loop.run_until_complete(run_async_verify())
    finally:
        loop.close()

    # 处理结果
    results = []
    success_count = 0
    fail_count = 0

    for i, login_result in enumerate(login_results, 1):
        print(f"\n[{i}/{len(result.targets)}] {login_result.url}")
        print(f"    用户: {result.targets[i-1].username}")

        if login_result.success:
            print(f"    结果: [OK] 成功 - {login_result.message}")
            success_count += 1
        else:
            print(f"    结果: [FAIL] 失败 - {login_result.message}")
            fail_count += 1

        print(f"    耗时: {login_result.response_time:.2f}秒")

        results.append({
            'url': login_result.url,
            'username': result.targets[i-1].username,
            'password': result.targets[i-1].password,
            'success': login_result.success,
            'status': login_result.status.value if login_result.status else 'unknown',
            'message': login_result.message,
            'response_time': f"{login_result.response_time:.2f}"
        })

    # 汇总结果
    print()
    print("=" * 60)
    print("  验证结果汇总")
    print("=" * 60)
    print(f"  总计: {len(result.targets)}")
    print(f"  成功: {success_count}")
    print(f"  失败: {fail_count}")
    print(f"  成功率: {success_count/len(result.targets)*100:.1f}%")
    print()

    # 保存结果
    csv_name = Path(csv_path).stem
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = Path(output_dir or current_dir) / f"{csv_name}_results_{timestamp}.csv"

    try:
        with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'url', 'username', 'password', 'success', 'status', 'message', 'response_time'
            ])
            writer.writeheader()
            writer.writerows(results)
        print(f"[+] 结果已保存到: {output_file}")
    except Exception as e:
        print(f"[!] 保存结果失败: {e}")

    # 显示成功的目标
    if success_count > 0:
        print()
        print("成功的目标:")
        print("-" * 60)
        for r in results:
            if r['success']:
                print(f"  {r['url']}")
                print(f"    账号: {r['username']} / {r['password']}")

    return True


def run_gui():
    """启动图形界面"""
    print("[*] 启动图形界面...")
    try:
        from main_app import main as run_app
        run_app()
    except ImportError as e:
        print(f"[!] 导入错误: {e}")
        print("[!] 请确保所有核心文件存在")
    except Exception as e:
        print(f"[!] 启动失败: {e}")
        import traceback
        traceback.print_exc()


def interactive_menu():
    """交互式菜单"""
    while True:
        print()
        print("=" * 60)
        print("  弱口令验证工具 - 功能菜单")
        print("=" * 60)
        print()
        print("  [1] 启动图形界面")
        print("  [2] 快速验证 - 示例目标.csv")
        print("  [3] 批量验证 - 选择CSV文件")
        print("  [4] 查看帮助")
        print("  [0] 退出")
        print()
        
        try:
            choice = input("请选择功能 [0-4]: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[*] 已退出")
            break
        
        if choice == '0':
            print("\n[*] 再见！")
            break
        
        elif choice == '1':
            run_gui()
            break
        
        elif choice == '2':
            sample_csv = get_sample_csv()
            if sample_csv:
                print()
                run_batch_verify(str(sample_csv))
                input("\n按回车键继续...")
            else:
                print("\n[!] 未找到 示例目标.csv 文件")
                input("\n按回车键继续...")
        
        elif choice == '3':
            csv_files = find_csv_files()
            if not csv_files:
                print("\n[!] 当前目录下没有找到CSV文件")
                input("\n按回车键继续...")
                continue
            
            print("\n可用的CSV文件:")
            for i, f in enumerate(csv_files, 1):
                print(f"  [{i}] {f.name}")
            print("  [0] 返回")
            
            try:
                file_choice = input("\n请选择文件 [0-{}]: ".format(len(csv_files))).strip()
                if file_choice == '0':
                    continue
                idx = int(file_choice) - 1
                if 0 <= idx < len(csv_files):
                    print()
                    run_batch_verify(str(csv_files[idx]))
                    input("\n按回车键继续...")
                else:
                    print("[!] 无效选择")
            except (ValueError, EOFError, KeyboardInterrupt):
                continue
        
        elif choice == '4':
            print()
            print("=" * 60)
            print("  弱口令验证工具 v2.0 使用帮助")
            print("=" * 60)
            print()
            print("  新功能:")
            print("  - 统一验证器：支持同步/异步两种模式")
            print("  - 异步并发：性能提升100%+")
            print("  - 简化配置：开箱即用，无需配置文件")
            print("  - 自动编码检测：支持GBK/UTF-8")
            print()
            print("  功能说明:")
            print("  - 支持对登录页面进行弱口令验证")
            print("  - 支持批量导入CSV/Excel文件")
            print("  - 支持自动识别数字字母验证码")
            print()
            print("  CSV文件格式:")
            print("  - 第一行为标题行")
            print("  - 必须包含: URL, 用户名, 密码 三列")
            print("  - 支持的列名: url/URL/网址, username/用户名, password/密码")
            print()
            print("  命令行使用:")
            print("  - python launcher.py              交互式菜单")
            print("  - python launcher.py --gui        直接启动图形界面")
            print("  - python launcher.py --batch 目标.csv  直接批量验证")
            print("  - python launcher.py --sample     验证示例目标.csv")
            print()
            print("  性能对比:")
            print("  - 同步验证: 3个目标约9秒")
            print("  - 异步验证: 3个目标约4秒（提升105%）")
            print()
            input("按回车键返回...")
        
        else:
            print("\n[!] 无效选择，请输入 0-4")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='弱口令验证工具 v2.0 - 统一验证器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python launcher.py              交互式菜单
  python launcher.py --gui        启动图形界面
  python launcher.py --batch 目标.csv  批量验证
  python launcher.py --sample     验证示例目标.csv

新功能:
  - 统一验证器：支持同步/异步两种模式
  - 异步并发：性能提升100%+
  - 简化配置：开箱即用
  - 自动编码检测：支持GBK/UTF-8
        """
    )

    parser.add_argument('--gui', action='store_true', help='直接启动图形界面')
    parser.add_argument('--batch', metavar='FILE', help='批量验证CSV文件')
    parser.add_argument('--sample', action='store_true', help='验证示例目标.csv')
    parser.add_argument('-o', '--output', metavar='DIR', help='结果输出目录')
    parser.add_argument('-v', '--verbose', action='store_true', help='显示详细信息')

    args = parser.parse_args()

    print_banner()

    # 检查依赖
    if not check_dependencies():
        return

    print("[+] 依赖检查通过")

    # 根据参数执行不同功能
    if args.gui:
        run_gui()

    elif args.batch:
        if not os.path.exists(args.batch):
            print(f"[!] 文件不存在: {args.batch}")
            return
        run_batch_verify(args.batch, args.output, args.verbose)

    elif args.sample:
        sample_csv = get_sample_csv()
        if sample_csv:
            run_batch_verify(str(sample_csv), args.output, args.verbose)
        else:
            print("[!] 未找到 示例目标.csv 文件")

    else:
        # 显示交互式菜单
        interactive_menu()


if __name__ == "__main__":
    main()