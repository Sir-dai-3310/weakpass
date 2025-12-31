#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
进度管理模块
支持进度保存、恢复和断点续扫
"""

import json
import pickle
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
import hashlib

from .async_verifier import TargetInfo, LoginResult, LoginStatus


@dataclass
class ScanSession:
    """扫描会话"""
    session_id: str
    created_at: str
    updated_at: str
    targets: List[TargetInfo]
    completed_indices: List[int] = field(default_factory=list)
    results: List[LoginResult] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)
    stats: Dict[str, int] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.session_id:
            self.session_id = self._generate_session_id()
        if not self.created_at:
            self.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if not self.updated_at:
            self.updated_at = self.created_at
    
    def _generate_session_id(self) -> str:
        """生成会话ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        random_str = hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()[:8]
        return f"scan_{timestamp}_{random_str}"
    
    def get_progress(self) -> Tuple[int, int]:
        """获取进度 (已完成, 总数)"""
        return len(self.completed_indices), len(self.targets)
    
    def get_completion_rate(self) -> float:
        """获取完成率 (0-1)"""
        completed, total = self.get_progress()
        return completed / total if total > 0 else 0.0
    
    def is_completed(self) -> bool:
        """是否已完成"""
        completed, total = self.get_progress()
        return completed >= total
    
    def get_remaining_targets(self) -> List[TargetInfo]:
        """获取剩余目标"""
        return [t for i, t in enumerate(self.targets) if i not in self.completed_indices]
    
    def add_result(self, index: int, result: LoginResult):
        """添加结果"""
        if index not in self.completed_indices:
            self.completed_indices.append(index)
        
        # 替换或添加结果
        for i, r in enumerate(self.results):
            if hasattr(r, 'target') and hasattr(r.target, 'index') and r.target.index == index:
                self.results[i] = result
                break
        else:
            self.results.append(result)
        
        # 更新时间
        self.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 更新统计
        self._update_stats()
    
    def _update_stats(self):
        """更新统计信息"""
        self.stats = {
            'total': len(self.targets),
            'completed': len(self.completed_indices),
            'remaining': len(self.targets) - len(self.completed_indices),
            'success': sum(1 for r in self.results if r.success),
            'failed': sum(1 for r in self.results if not r.success and r.status != LoginStatus.UNKNOWN_ERROR),
            'errors': sum(1 for r in self.results if r.status in [LoginStatus.CONNECTION_ERROR, LoginStatus.TIMEOUT_ERROR, LoginStatus.UNKNOWN_ERROR])
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'session_id': self.session_id,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'targets': [t.to_dict() for t in self.targets],
            'completed_indices': self.completed_indices,
            'results': [
                {
                    'status': r.status.value,
                    'success': r.success,
                    'message': r.message,
                    'response_time': r.response_time,
                    'url': r.url,
                    'final_url': r.final_url,
                    'page_changed': r.page_changed,
                    'details': r.details,
                    'timestamp': r.timestamp,
                    'target_index': r.details.get('target_index') if r.details else None
                }
                for r in self.results
            ],
            'config': self.config,
            'stats': self.stats
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScanSession':
        """从字典创建"""
        targets = []
        for t_data in data.get('targets', []):
            targets.append(TargetInfo(
                url=t_data['url'],
                username=t_data['username'],
                password=t_data['password'],
                extra=t_data.get('extra'),
                index=t_data.get('index', 0),
                source_file=t_data.get('source_file')
            ))
        
        results = []
        for r_data in data.get('results', []):
            results.append(LoginResult(
                status=LoginStatus(r_data['status']),
                success=r_data['success'],
                message=r_data['message'],
                response_time=r_data['response_time'],
                url=r_data['url'],
                final_url=r_data['final_url'],
                page_changed=r_data['page_changed'],
                details=r_data.get('details'),
                timestamp=r_data.get('timestamp')
            ))
        
        session = cls(
            session_id=data.get('session_id'),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at'),
            targets=targets,
            completed_indices=data.get('completed_indices', []),
            results=results,
            config=data.get('config', {}),
            stats=data.get('stats', {})
        )
        
        return session


class ProgressManager:
    """进度管理器"""
    
    def __init__(self, save_dir: str = "sessions"):
        """
        初始化进度管理器
        
        Args:
            save_dir: 保存目录
        """
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(exist_ok=True)
        self.current_session: Optional[ScanSession] = None
    
    def create_session(
        self,
        targets: List[TargetInfo],
        config: Optional[Dict[str, Any]] = None
    ) -> ScanSession:
        """
        创建新会话
        
        Args:
            targets: 目标列表
            config: 配置
            
        Returns:
            ScanSession对象
        """
        session = ScanSession(
            targets=targets,
            config=config or {}
        )
        self.current_session = session
        return session
    
    def load_session(self, session_id: str) -> Optional[ScanSession]:
        """
        加载会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            ScanSession对象或None
        """
        filepath = self.save_dir / f"{session_id}.json"
        
        if not filepath.exists():
            return None
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            session = ScanSession.from_dict(data)
            self.current_session = session
            return session
            
        except Exception as e:
            print(f"加载会话失败: {e}")
            return None
    
    def save_session(self, session: Optional[ScanSession] = None) -> bool:
        """
        保存会话
        
        Args:
            session: 会话对象（默认使用当前会话）
            
        Returns:
            是否成功
        """
        session = session or self.current_session
        
        if not session:
            return False
        
        try:
            filepath = self.save_dir / f"{session.session_id}.json"
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(session.to_dict(), f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            print(f"保存会话失败: {e}")
            return False
    
    def delete_session(self, session_id: str) -> bool:
        """
        删除会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            是否成功
        """
        filepath = self.save_dir / f"{session_id}.json"
        
        if not filepath.exists():
            return False
        
        try:
            filepath.unlink()
            return True
        except Exception as e:
            print(f"删除会话失败: {e}")
            return False
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """
        列出所有会话
        
        Returns:
            会话信息列表
        """
        sessions = []
        
        for filepath in self.save_dir.glob("*.json"):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                completed, total = len(data.get('completed_indices', [])), len(data.get('targets', []))
                
                sessions.append({
                    'session_id': data.get('session_id'),
                    'created_at': data.get('created_at'),
                    'updated_at': data.get('updated_at'),
                    'total_targets': total,
                    'completed_targets': completed,
                    'completion_rate': completed / total if total > 0 else 0.0,
                    'stats': data.get('stats', {})
                })
                
            except Exception as e:
                print(f"读取会话 {filepath.name} 失败: {e}")
        
        # 按创建时间倒序排列
        sessions.sort(key=lambda x: x['created_at'], reverse=True)
        
        return sessions
    
    def export_results(
        self,
        session_id: str,
        output_file: str,
        format: str = "csv"
    ) -> bool:
        """
        导出结果
        
        Args:
            session_id: 会话ID
            output_file: 输出文件路径
            format: 格式 (csv, json)
            
        Returns:
            是否成功
        """
        session = self.load_session(session_id)
        
        if not session:
            return False
        
        try:
            if format == "csv":
                import csv
                
                with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        '序号', 'URL', '用户名', '密码',
                        '状态', '成功', '消息',
                        '响应时间(秒)', '时间戳'
                    ])
                    
                    for i, result in enumerate(session.results):
                        target = session.targets[i] if i < len(session.targets) else None
                        writer.writerow([
                            i + 1,
                            result.url,
                            target.username if target else '',
                            target.password if target else '',
                            result.status.value,
                            result.success,
                            result.message,
                            f"{result.response_time:.3f}",
                            result.timestamp
                        ])
                
            elif format == "json":
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(session.to_dict(), f, indent=2, ensure_ascii=False)
            
            else:
                return False
            
            return True
            
        except Exception as e:
            print(f"导出结果失败: {e}")
            return False
    
    def cleanup_old_sessions(self, max_age_days: int = 7):
        """
        清理旧会话
        
        Args:
            max_age_days: 最大保留天数
        """
        from datetime import timedelta
        
        cutoff_time = datetime.now() - timedelta(days=max_age_days)
        
        for filepath in self.save_dir.glob("*.json"):
            try:
                # 获取文件修改时间
                mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
                
                if mtime < cutoff_time:
                    filepath.unlink()
                    print(f"已删除旧会话: {filepath.name}")
                    
            except Exception as e:
                print(f"清理会话 {filepath.name} 失败: {e}")


# 便捷函数
def create_progress_manager(save_dir: str = "sessions") -> ProgressManager:
    """创建进度管理器"""
    return ProgressManager(save_dir)


def save_progress(session: ScanSession, save_dir: str = "sessions") -> bool:
    """快速保存进度"""
    manager = ProgressManager(save_dir)
    return manager.save_session(session)


def load_progress(session_id: str, save_dir: str = "sessions") -> Optional[ScanSession]:
    """快速加载进度"""
    manager = ProgressManager(save_dir)
    return manager.load_session(session_id)


if __name__ == "__main__":
    # 测试代码
    print("测试进度管理...")
    
    # 创建进度管理器
    manager = create_progress_manager()
    
    # 创建测试目标
    targets = [
        TargetInfo(url=f"https://example{i}.com/login", username=f"user{i}", password=f"pass{i}", index=i)
        for i in range(1, 6)
    ]
    
    # 创建会话
    session = manager.create_session(targets, config={'max_concurrent': 3})
    print(f"创建会话: {session.session_id}")
    
    # 添加一些结果
    for i in range(3):
        result = LoginResult(
            status=LoginStatus.SUCCESS if i % 2 == 0 else LoginStatus.PASSWORD_ERROR,
            success=i % 2 == 0,
            message=f"测试结果 {i}",
            response_time=0.5 + i * 0.1,
            url=targets[i].url,
            final_url=targets[i].url,
            page_changed=i % 2 == 0
        )
        session.add_result(i, result)
    
    # 保存会话
    manager.save_session()
    print(f"保存会话成功")
    
    # 列出会话
    sessions = manager.list_sessions()
    print(f"\n会话列表:")
    for s in sessions:
        print(f"  {s['session_id']} - {s['completion_rate']:.1%} 完成")
    
    # 加载会话
    loaded = manager.load_session(session.session_id)
    if loaded:
        print(f"\n加载会话: {loaded.session_id}")
        print(f"进度: {loaded.get_completion_rate():.1%}")
        print(f"剩余: {len(loaded.get_remaining_targets())}")
    
    # 导出结果
    output_file = manager.save_dir / f"{session.session_id}_results.csv"
    manager.export_results(session.session_id, str(output_file))
    print(f"\n导出结果到: {output_file}")