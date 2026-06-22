"""
缓存管理模块

提供统一的缓存管理功能，支持不同资源类型的缓存操作
"""

import threading
from typing import Any, Optional, Dict
from cachetools import TTLCache
from logger_utils import get_logger

logger = get_logger()


class CacheManager:
    """缓存管理器"""
    
    def __init__(self, max_size: int = 10000, ttl_seconds: int = 3600):
        """
        初始化缓存管理器
        
        Args:
            max_size: 最大缓存数量，默认10000条
            ttl_seconds: 缓存过期时间（秒），默认3600秒（1小时）
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        
        # 为不同资源类型创建独立的缓存
        self._caches: Dict[str, TTLCache] = {}
        self._lock = threading.RLock()  # 使用可重入锁
        
        logger.debug(f"缓存管理器初始化完成: max_size={max_size}, ttl={ttl_seconds}秒")
    
    def _get_cache(self, resource_type: str) -> TTLCache:
        """
        获取指定资源类型的缓存
        
        Args:
            resource_type: 资源类型 ('ip', 'domain', 'file')
            
        Returns:
            TTLCache: 对应的缓存实例
        """
        with self._lock:
            if resource_type not in self._caches:
                self._caches[resource_type] = TTLCache(
                    maxsize=self.max_size,
                    ttl=self.ttl_seconds
                )
                logger.info(f"为资源类型 {resource_type} 创建缓存")
            return self._caches[resource_type]
    
    def get(self, resource: str, resource_type: str) -> Optional[Any]:
        """
        从缓存中获取资源数据
        
        Args:
            resource: 资源值（如IP地址、域名、文件哈希）
            resource_type: 资源类型 ('ip', 'domain', 'file')
            
        Returns:
            Optional[Any]: 缓存的数据，如果不存在则返回None
        """
        if not resource or not resource_type:
            return None
            
        try:
            cache = self._get_cache(resource_type)
            result = cache.get(resource)
            
            if result is not None:
                logger.debug(f"缓存命中: {resource_type}={resource}")
            else:
                logger.debug(f"缓存未命中: {resource_type}={resource}")
                
            return result
        except Exception as e:
            logger.error(f"获取缓存失败 ({resource_type}={resource}): {e}")
            return None
    
    def set(self, resource: str, resource_type: str, data: Any) -> bool:
        """
        将资源数据存入缓存
        
        Args:
            resource: 资源值（如IP地址、域名、文件哈希）
            resource_type: 资源类型 ('ip', 'domain', 'file')
            data: 要缓存的数据
            
        Returns:
            bool: 是否成功存入缓存
        """
        if not resource or not resource_type or data is None:
            return False
            
        try:
            cache = self._get_cache(resource_type)
            cache[resource] = data
            logger.debug(f"数据已缓存: {resource_type}={resource}")
            return True
        except Exception as e:
            logger.error(f"存入缓存失败 ({resource_type}={resource}): {e}")
            return False
    


# 全局缓存管理器实例
cache_manager = CacheManager()
