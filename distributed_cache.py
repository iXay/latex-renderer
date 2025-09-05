#!/usr/bin/env python3
"""
分布式缓存管理模块 - 每个任务独立缓存文件
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

class DistributedCacheManager:
    """分布式缓存管理器"""
    
    def __init__(self, cache_dir: str = "cache"):
        self.cache_dir = Path(cache_dir)
        self.file_caches_dir = self.cache_dir / "file_caches"
        self.summary_file = self.cache_dir / "summary.json"
        
        # 确保目录存在
        self.cache_dir.mkdir(exist_ok=True)
        self.file_caches_dir.mkdir(exist_ok=True)
    
    def _get_cache_file_path(self, file_path: str) -> Path:
        """获取缓存文件路径 - 使用更可读的文件名"""
        # 从文件路径中提取基础文件名（不含目录和扩展名）
        from pathlib import Path as PathLib
        base_name = PathLib(file_path).stem
        
        # 为了确保文件名安全和唯一性，对特殊字符进行替换
        # 并在末尾添加路径哈希的短版本来避免冲突
        safe_name = base_name.replace('/', '_').replace('\\', '_').replace(' ', '_')
        path_hash = hashlib.md5(file_path.encode('utf-8')).hexdigest()[:8]
        
        return self.file_caches_dir / f"{safe_name}_{path_hash}.cache"
    
    def _save_json(self, file_path: Path, data: dict):
        """保存JSON文件"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"警告: 保存JSON文件失败 {file_path}: {e}")
    
    def _load_json(self, file_path: Path) -> dict:
        """加载JSON文件"""
        try:
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"警告: 加载JSON文件失败 {file_path}: {e}")
        return {}
    
    def is_file_cached(self, file_path: str) -> bool:
        """检查文件是否已被缓存"""
        return self._get_cache_file_path(file_path).exists()
    
    def get_cached_result(self, file_path: str) -> Optional[dict]:
        """获取文件的缓存结果"""
        cache_file = self._get_cache_file_path(file_path)
        if cache_file.exists():
            cached_data = self._load_json(cache_file)
            if cached_data and "original_file_path" in cached_data:
                return cached_data
        return None
    
    def save_file_cache(self, file_path: str, cache_entry: dict):
        """保存文件缓存（无锁，进程安全）"""
        cache_file = self._get_cache_file_path(file_path)
        
        # 添加元数据到缓存条目
        enhanced_cache_entry = {
            "original_file_path": file_path,
            "cache_file": str(cache_file),
            "cached_at": datetime.now().isoformat(),
            **cache_entry
        }
        
        # 直接保存到独立的缓存文件（无需加锁）
        self._save_json(cache_file, enhanced_cache_entry)
    
    def get_processed_files(self) -> List[str]:
        """获取所有已处理的文件列表"""
        processed_files = []
        
        for cache_file in self.file_caches_dir.glob("*.cache"):
            cached_data = self._load_json(cache_file)
            if cached_data and "original_file_path" in cached_data:
                processed_files.append(cached_data["original_file_path"])
        
        return processed_files
    
    def get_cache_summary(self) -> dict:
        """生成缓存汇总信息"""
        summary = {
            "total_cached_files": 0,
            "total_formulas": 0,
            "total_texts": 0,
            "total_errors": 0,
            "cache_files": [],
            "generated_at": datetime.now().isoformat()
        }
        
        for cache_file in self.file_caches_dir.glob("*.cache"):
            cached_data = self._load_json(cache_file)
            if cached_data and "original_file_path" in cached_data:
                summary["total_cached_files"] += 1
                summary["cache_files"].append({
                    "file_path": cached_data["original_file_path"],
                    "cache_file": str(cache_file),
                    "timestamp": cached_data.get("timestamp", "unknown")
                })
                
                # 累计统计信息
                if "stats" in cached_data:
                    stats = cached_data["stats"]
                    summary["total_formulas"] += stats.get("formulas_count", 0)
                    summary["total_texts"] += stats.get("texts_count", 0)
                    summary["total_errors"] += stats.get("errors_count", 0)
        
        return summary
    
    def save_summary(self):
        """保存汇总信息到文件"""
        summary = self.get_cache_summary()
        self._save_json(self.summary_file, summary)
        return summary
    
    def clear_cache(self, file_path: Optional[str] = None):
        """清除缓存"""
        if file_path:
            cache_file = self._get_cache_file_path(file_path)
            if cache_file.exists():
                cache_file.unlink()
                print(f"已清除文件缓存: {file_path}")
        else:
            for cache_file in self.file_caches_dir.glob("*.cache"):
                cache_file.unlink()
            print("已清除所有缓存文件")
