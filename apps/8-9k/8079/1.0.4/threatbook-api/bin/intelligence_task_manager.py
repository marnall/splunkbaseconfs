#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ThreatBook 情报任务管理器
支持动态配置和多种执行频率的任务调度系统
"""

import json
import os
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Callable, Any
from collections import defaultdict
from functools import partial

import splunklib.client as client
import splunklib.results as results

from logger_utils import get_logger
from config_reader import read_configuration
from data_writer import create_data_writer
from intelligence_api_handler import IntelligenceAPIHandler, IntelligenceType as APIIntelligenceType
from splunk_utils import SplunkUtils

logger = get_logger()

class IntelligenceType(Enum):
    """情报类型枚举"""
    IP = "ip_intelligence"
    DOMAIN = "domain_intelligence"
    FILE = "file_intelligence"

@dataclass
class DataSource:
    """数据源配置"""
    name: str
    spl: str
    index: str

@dataclass
class IntelligenceConfig:
    """情报配置"""
    apikey: str
    select_rate: int  # 执行频率（分钟）
    output_index: str
    datasource: List[DataSource]

@dataclass
class TaskInfo:
    """任务信息"""
    task_id: str
    intelligence_type: IntelligenceType
    config: IntelligenceConfig
    is_running: bool = False

class IntelligenceTaskManager:
    """情报任务管理器"""

    def __init__(self):
        # 使用线程安全的集合
        self.tasks: Dict[str, TaskInfo] = {}
        self.service: Optional[client.Service] = None
        self.api_handler: Optional[IntelligenceAPIHandler] = None
        self.data_writer: Optional[Any] = None

        # 线程安全的计数器
        self._task_counters = defaultdict(int)

        # 线程锁，用于保护任务字典的访问
        self._tasks_lock = threading.RLock()

        # 停止事件，用于通知所有线程停止
        self._stop_event = threading.Event()

        # 存储所有任务线程的引用
        self._task_threads: Dict[str, threading.Thread] = {}

        # 时间持久化文件路径 - 使用Splunk应用数据目录
        # 从 bin/ 目录向上到 splunk/ 目录，然后创建 var/lib
        splunk_app_dir = os.path.dirname(__file__)  # bin/ 目录
        splunk_app_dir = os.path.dirname(splunk_app_dir)  # splunk/ 目录
        app_data_dir = os.path.join(splunk_app_dir, "var", "lib")
        os.makedirs(app_data_dir, exist_ok=True)
        self.time_state_file = os.path.join(app_data_dir, "task_execution_times.json")
        self.execution_times = self._load_execution_times()


    def start(self, service: Optional[client.Service] = None):
        """启动任务管理器"""
        logger.info("启动情报任务管理器")

        # 使用传入的Splunk服务或创建新连接
        try:
            self.service = SplunkUtils.connect_to_splunk()
            logger.info("Splunk连接成功")
                
            # 初始化API处理器和数据写入器
            self.api_handler = IntelligenceAPIHandler()
            self.data_writer = create_data_writer(self.service)
            logger.debug("API处理器和数据写入器初始化成功")

        except Exception as e:
            logger.error(f"连接Splunk失败: {e}")
            return

        # 初始加载配置并启动任务
        self._load_and_schedule_tasks()

    def stop(self):
        """停止任务管理器"""
        logger.info("停止情报任务管理器")

        # 设置停止事件，通知所有线程停止
        self._stop_event.set()
        logger.info("已设置停止事件，通知所有任务线程停止")

        # 等待所有任务线程结束（最多等待10秒）
        max_wait_time = 10
        wait_interval = 1
        waited_time = 0

        with self._tasks_lock:
            task_threads = list(self._task_threads.values())

        while waited_time < max_wait_time and task_threads:
            # 检查是否还有活跃的线程
            active_threads = [t for t in task_threads if t.is_alive()]
            if not active_threads:
                break

            logger.info(f"等待 {len(active_threads)} 个任务线程结束...")
            time.sleep(wait_interval)
            waited_time += wait_interval

        # 清理资源
        with self._tasks_lock:
            self.tasks.clear()
            self._task_threads.clear()

        # 重置停止事件，为下次启动做准备
        self._stop_event.clear()

        if waited_time >= max_wait_time:
            logger.warning(f"等待线程结束超时，强制停止")
        else:
            logger.info("所有任务线程已正常停止")

    def _load_config_from_splunk(self) -> Dict:
        """从Splunk读取配置"""
        try:
            config = read_configuration()
            return {
                'ip_intelligence_config': self._parse_json_config(config.get('ip_intelligence_config', '[]')),
                'domain_intelligence_config': self._parse_json_config(config.get('domain_intelligence_config', '[]')),
                'file_intelligence_config': self._parse_json_config(config.get('file_intelligence_config', '[]')),
                'ip_intelligence_url': config.get('ip_intelligence_url', ''),
                'domain_intelligence_url': config.get('domain_intelligence_url', ''),
                'file_intelligence_url': config.get('file_intelligence_url', '')
            }
        except Exception as e:
            logger.error(f"读取配置失败: {e}")
            return {}

    def _parse_json_config(self, config_str: str) -> List:
        """解析JSON配置字符串"""
        try:
            return json.loads(config_str) if config_str else []
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {config_str}, 错误: {e}")
            return []

    def _load_and_schedule_tasks(self):
        """加载配置并调度任务"""
        try:
            # 加载新配置（在锁外执行，避免长时间持有锁）
            config = self._load_config_from_splunk()
            if not config:
                logger.warning("无法加载配置，跳过任务调度")
                return

            # 取消现有任务（在锁外执行，避免死锁）
            self._cancel_all_tasks()
            logger.info(f"调度任务前获取配置：{config}")

            # 调度各种情报任务（在锁外执行，避免死锁）
            self._schedule_intelligence_tasks(
                IntelligenceType.IP,
                config.get('ip_intelligence_config', []),
                config.get('ip_intelligence_url', '')
            )

            self._schedule_intelligence_tasks(
                IntelligenceType.DOMAIN,
                config.get('domain_intelligence_config', []),
                config.get('domain_intelligence_url', '')
            )

            self._schedule_intelligence_tasks(
                IntelligenceType.FILE,
                config.get('file_intelligence_config', []),
                config.get('file_intelligence_url', '')
            )

            logger.info(f"任务调度完成，共调度 {len(self.tasks)} 个任务")

        except Exception as e:
            logger.error(f"加载和调度任务失败: {e}")

    def _schedule_intelligence_tasks(self, intelligence_type: IntelligenceType, configs: List[Dict], api_url: str):
        """调度情报任务"""
        for i, config_dict in enumerate(configs):
            try:
                # 解析配置
                intelligence_config = self._parse_intelligence_config(config_dict)
                if not intelligence_config:
                    continue

                # 为每个数据源创建独立任务
                for j, datasource in enumerate(intelligence_config.datasource):
                    task_id = f"{intelligence_type.value}_{i}_{j}_{datasource.index}"

                    # 创建任务信息
                    task_info = TaskInfo(
                        task_id=task_id,
                        intelligence_type=intelligence_type,
                        config=intelligence_config
                    )

                    # 添加任务信息（线程安全）
                    with self._tasks_lock:
                        self.tasks[task_id] = task_info

                    # 创建线程异步执行任务
                    task_thread = threading.Thread(
                        target=self._create_task_executor,
                        args=(task_id, intelligence_type, intelligence_config),
                        name=f"TaskExecutor-{task_id}",
                        daemon=True
                    )

                    # 保存线程引用
                    with self._tasks_lock:
                        self._task_threads[task_id] = task_thread

                    task_thread.start()
                    logger.debug(f"已启动异步任务线程: {task_id}")

            except Exception as e:
                logger.error(f"调度{intelligence_type.value}任务失败: {e}")

    def _parse_intelligence_config(self, config_dict: Dict) -> Optional[IntelligenceConfig]:
        """解析情报配置"""
        try:
            datasources = []
            for ds in config_dict.get('datasource', []):
                datasources.append(DataSource(
                    name=ds.get('name', ''),
                    spl=ds.get('spl', ''),
                    index=ds.get('index', '')
                ))

            return IntelligenceConfig(
                apikey=config_dict.get('apikey', ''),
                select_rate=config_dict.get('select_rate', 10),
                output_index=config_dict.get('output_index', ''),
                datasource=datasources
            )
        except Exception as e:
            logger.error(f"解析情报配置失败: {e}")
            return None

    def _create_task_executor(self, task_id: str, intelligence_type: IntelligenceType, config) -> None:
        """任务执行器，使用while循环检查执行间隔"""
        logger.info(f"启动任务执行器: {task_id}")

        while True:
            try:
                # 检查停止事件
                if self._stop_event.is_set():
                    logger.info(f"任务 {task_id} 收到停止信号，退出执行器")
                    break

                # 检查任务是否还存在（可能被停止）
                with self._tasks_lock:
                    if task_id not in self.tasks:
                        logger.info(f"任务 {task_id} 已不存在，退出执行器")
                        break

                # 获取当前时间
                current_time = datetime.now()

                # 获取上次执行完成时间
                last_execution_time = self._get_last_execution_time(task_id)

                # 计算时间间隔（分钟）
                if last_execution_time:
                    time_diff = (current_time - last_execution_time).total_seconds() / 60
                    logger.debug(f"任务 {task_id} 距离上次执行完成时间: {time_diff:.2f} 分钟")
                else:
                    # 首次执行
                    time_diff = float('inf')
                    logger.debug(f"任务 {task_id} 首次执行")

                # 每次执行前都重新读取最新配置
                latest_config, latest_datasource, latest_api_url = self._get_latest_task_config(task_id, intelligence_type)

                # 检查是否达到执行间隔
                if time_diff >= latest_config.select_rate:
                    logger.info(f"任务 {task_id} ==========开始执行 (间隔: {time_diff:.1f}分钟)==========")

                    # 更新任务状态为运行中
                    with self._tasks_lock:
                        if task_id in self.tasks:
                            self.tasks[task_id].is_running = True

                    # 执行任务
                    try:
                        # 使用任务开始时间作为查询的latest时间
                        self._execute_intelligence_task(task_id, intelligence_type, latest_config, latest_datasource,
                                                        latest_api_url, current_time)
                    except Exception as e:
                        logger.error(f"任务 {task_id} 执行失败: {e}")
                    finally:
                        # 更新任务状态为完成
                        with self._tasks_lock:
                            if task_id in self.tasks:
                                self.tasks[task_id].is_running = False

                        # 任务执行完成后，更新执行时间（使用查询的latest时间，确保下次查询连续）
                        self._update_execution_time(task_id, current_time)

                        # 打印大致的下次执行时间
                        next_execution_time = current_time + timedelta(minutes=latest_config.select_rate)
                        logger.info(f"任务 {task_id} 下次执行时间: {next_execution_time}")

                else:
                    # 减少日志输出频率，只在debug模式下输出
                    pass

                time.sleep(1)

            except Exception as e:
                logger.error(f"任务执行器异常 {task_id}: {e}")
                # 更新错误状态
                with self._tasks_lock:
                    if task_id in self.tasks:
                        self.tasks[task_id].is_running = False

                time.sleep(1)


    def _get_latest_task_config(self, task_id: str, intelligence_type: IntelligenceType) -> tuple:
        """获取任务的最新配置"""
        try:
            # 从当前配置中重新读取该任务的配置
            current_config = self._load_config_from_splunk()
            if not current_config:
                logger.error(f"无法加载配置，使用默认配置")
                return IntelligenceConfig("", 10, "", []), DataSource("", "", ""), ""

            # 根据情报类型获取对应的配置
            config_key = f"{intelligence_type.value}_config"
            configs = current_config.get(config_key, [])
            api_url_key = f"{intelligence_type.value}_url"
            api_url = current_config.get(api_url_key, "")

            # 从task_id中提取索引信息来匹配配置
            task_parts = task_id.split('_')
            if len(task_parts) < 4:
                logger.error(f"任务ID格式错误: {task_id}")
                return IntelligenceConfig("", 10, "", []), DataSource("", "", ""), api_url

            try:
                config_index = int(task_parts[2])
                datasource_index = int(task_parts[3])
            except (ValueError, IndexError):
                logger.error(f"无法解析任务ID: {task_id}")
                return IntelligenceConfig("", 10, "", []), DataSource("", "", ""), api_url

            # 找到对应的任务配置
            if config_index < len(configs):
                config_dict = configs[config_index]
                parsed_config = self._parse_intelligence_config(config_dict)
                if parsed_config and datasource_index < len(parsed_config.datasource):
                    datasource = parsed_config.datasource[datasource_index]
                    logger.debug(f"获取到任务 {task_id} 的最新配置")
                    return parsed_config, datasource, api_url
                else:
                    logger.warning(f"任务 {task_id} 的数据源配置不存在")
            else:
                logger.warning(f"任务 {task_id} 的配置索引不存在")

            # 如果找不到配置，返回默认配置
            return IntelligenceConfig("", 10, "", []), DataSource("", "", ""), api_url

        except Exception as e:
            logger.error(f"获取任务 {task_id} 最新配置失败: {e}")
            return IntelligenceConfig("", 10, "", []), DataSource("", "", ""), ""

    def _load_execution_times(self) -> Dict[str, str]:
        """加载任务执行时间记录"""
        try:
            if os.path.exists(self.time_state_file):
                with open(self.time_state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"加载执行时间记录失败: {e}")
            return {}

    def _save_execution_times(self):
        """保存任务执行时间记录"""
        try:
            with open(self.time_state_file, 'w', encoding='utf-8') as f:
                json.dump(self.execution_times, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存执行时间记录失败: {e}")

    def _get_last_execution_time(self, task_id: str) -> Optional[datetime]:
        """获取任务的上次执行时间"""
        time_str = self.execution_times.get(task_id)
        if time_str:
            try:
                # 尝试解析时间戳
                timestamp = float(time_str)
                return datetime.fromtimestamp(timestamp)
            except (ValueError, TypeError):
                logger.warning(f"任务 {task_id} 的时间格式无效: {time_str}")
        return None

    def _update_execution_time(self, task_id: str, execution_time: datetime):
        """更新任务执行时间"""
        # 使用时间戳存储
        self.execution_times[task_id] = str(execution_time.timestamp())
        self._save_execution_times()

    def _extract_table_fields(self, spl_query: str) -> str:
        """
        从 Splunk 查询中提取 rename 子句的字段名

        Args:
            spl_query: Splunk 查询语句，如 'index="ip_input" | rename src_ip as src_ip, dest_ip as dest_ip'

        Returns:
            str: 提取的字段名，如 'src_ip, dest_ip'
        """
        import re

        # 查找 rename 子句
        rename_match = re.search(r'rename\s+(.+?)(?:\s*\||$)', spl_query, re.IGNORECASE)
        if not rename_match:
            return ''

        rename_clause = rename_match.group(1).strip()

        # 解析 rename 子句中的字段
        # 匹配模式：field_name as alias_name 或 field_name
        field_pattern = r'(\w+)\s+as\s+(\w+)|(\w+)'

        fields = []
        for match in re.finditer(field_pattern, rename_clause):
            if match.group(1) and match.group(2):  # 有 as 子句
                # 提取 as 后面的字段名
                as_field = match.group(2).strip()
                fields.append(as_field)
            elif match.group(3):  # 没有 as 子句
                # 使用原字段名
                original_field = match.group(3).strip()
                fields.append(original_field)

        return ', '.join(fields) if fields else ''

    def _execute_intelligence_task(self, task_id: str, intelligence_type: IntelligenceType,
                                 config: IntelligenceConfig, datasource: DataSource, api_url: str, query_time: datetime):
        """执行情报任务"""
        try:
            # 获取上次执行完成时间
            last_execution_time = self._get_last_execution_time(task_id)

            # 构建时间范围查询条件（使用时间戳）
            # query_time 是任务开始时间，作为查询的 latest 时间
            latest_timestamp = int(query_time.timestamp())

            if last_execution_time:
                # 使用上次查询的latest时间作为本次查询的earliest时间，确保时间连续
                earliest_timestamp = int(last_execution_time.timestamp())
                logger.debug(f"任务 {task_id} 查询时间范围: {earliest_timestamp} 到 {latest_timestamp}")
            else:
                # 首次执行，直接返回，不查询历史数据
                logger.info(f"任务 {task_id} 首次执行，跳过查询，等待下次执行")
                return

            # 从查询中提取字段名
            sql_fields = self._extract_table_fields(datasource.spl)

            # 根据情报类型设置去重字段
            if intelligence_type == IntelligenceType.IP:
                dedup_fields = "ip,host"
            elif intelligence_type == IntelligenceType.DOMAIN:
                dedup_fields = "domain,host"
            elif intelligence_type == IntelligenceType.FILE:
                dedup_fields = "hash,host"
            

            query = f'search earliest={earliest_timestamp} latest={latest_timestamp} {datasource.spl} | dedup {dedup_fields} | table {sql_fields}'

            logger.info(f"任务 {task_id} 执行查询: {query}")

            # 1. 执行Splunk查询获取数据
            query_results = self._execute_splunk_query(query)
            if not query_results:
                logger.warning(f"任务 {task_id} 未查询到数据")
                return

            # 2. 调用对应的API接口
            api_results = self._call_intelligence_api(intelligence_type, api_url, config.apikey, query_results, config.output_index)
            if not api_results:
                logger.warning(f"任务 {task_id} API调用未返回数据")
                return

            # 3. 将结果写入输出索引
            self._write_results_to_index(config.output_index, api_results, intelligence_type.value)

            logger.info(f"任务 {task_id} 处理完成，处理了 {len(query_results)} 条输入，{len(api_results)} 条输出")

        except Exception as e:
            logger.error(f"执行情报任务失败 {task_id}: {e}")
            raise

    def _execute_splunk_query(self, spl_query: str) -> List[Dict]:
        """执行Splunk查询"""
        try:
            # 创建搜索任务
            job = self.service.jobs.create(spl_query, timeout=300)

            # 等待任务完成
            while not job.is_done():
                time.sleep(1)

            # 处理结果，使用JSONResultsReader，在results()方法中指定output_mode
            results_reader = results.JSONResultsReader(job.results(output_mode='json'))
            query_results = []

            for result in results_reader:
                if isinstance(result, dict):
                    query_results.append(result)

            logger.info(f"Splunk查询完成，返回 {len(query_results)} 条记录")
            return query_results

        except Exception as e:
            logger.error(f"执行Splunk查询失败: {e}")
            return []

    def _call_intelligence_api(self, intelligence_type: IntelligenceType, api_url: str,
                             apikey: str, query_results: List[Dict], output_index: str) -> List[Dict]:
        """调用情报API"""
        try:
            # 根据情报类型提取相应的字段
            fields_to_query = self._extract_fields_for_api(intelligence_type, query_results)
            if not fields_to_query:
                logger.warning(f"未找到 {intelligence_type.value} 需要查询的字段")
                return []

            # 转换情报类型枚举
            api_intelligence_type = self._convert_intelligence_type(intelligence_type)

            # 调用API
            api_results = self.api_handler.call_intelligence_api(
                api_intelligence_type, api_url, apikey, fields_to_query, output_index
            )

            logger.debug(f"API调用完成，返回 {len(api_results)} 条结果")
            return api_results

        except Exception as e:
            logger.error(f"调用情报API失败: {e}")
            return []

    def _convert_intelligence_type(self, intelligence_type: IntelligenceType) -> APIIntelligenceType:
        """转换情报类型枚举"""
        if intelligence_type == IntelligenceType.IP:
            return APIIntelligenceType.IP
        elif intelligence_type == IntelligenceType.DOMAIN:
            return APIIntelligenceType.DOMAIN
        elif intelligence_type == IntelligenceType.FILE:
            return APIIntelligenceType.FILE
        else:
            raise ValueError(f"不支持的情报类型: {intelligence_type}")

    def _extract_fields_for_api(self, intelligence_type: IntelligenceType, query_results: List[Dict]) -> List[tuple]:
        """根据情报类型提取需要查询的字段"""
        result_list = []
        for result in query_results:
            if intelligence_type == IntelligenceType.IP:
                # IP情报需要查询IP字段
                if 'ip' in result:
                    dest_ip = result.get('host', '')
                    tuple_result = (result['ip'], dest_ip)
                    result_list.append(tuple_result)
            elif intelligence_type == IntelligenceType.DOMAIN:
                # 域名情报需要查询域名字段
                if 'domain' in result:
                    dest_ip = result.get('host', '')
                    tuple_result = (result['domain'], dest_ip)
                    result_list.append(tuple_result)
            elif intelligence_type == IntelligenceType.FILE:
                if 'hash' in result:
                    dest_ip = result.get('host', '')
                    tuple_result = (result['hash'], dest_ip)
                    result_list.append(tuple_result)

        return result_list


    def _write_results_to_index(self, output_index: str, results: List[Dict], intelligence_type: str):
        """将结果写入输出索引"""
        try:
            # 获取最新配置
            latest_config = SplunkUtils.get_splunk_config()

            # 直接写入结果，传入最新配置
            success = self.data_writer.write_intelligence_results(
                output_index, results, intelligence_type, latest_config
            )

            if success:
                logger.info(f"成功写入 {len(results)} 条结果到索引 {output_index}")
            else:
                logger.error(f"写入索引 {output_index} 失败")

        except Exception as e:
            logger.error(f"写入索引失败: {e}")

    def _cancel_all_tasks(self):
        """取消所有任务"""
        try:
            # 设置停止事件
            self._stop_event.set()

            # 等待线程结束
            with self._tasks_lock:
                task_threads = list(self._task_threads.values())

            # 等待所有线程结束（最多等待5秒）
            max_wait_time = 5
            wait_interval = 0.1
            waited_time = 0

            while waited_time < max_wait_time and task_threads:
                active_threads = [t for t in task_threads if t.is_alive()]
                if not active_threads:
                    break
                time.sleep(wait_interval)
                waited_time += wait_interval

            # 清理资源
            with self._tasks_lock:
                self.tasks.clear()
                self._task_threads.clear()

            # 重置停止事件
            self._stop_event.clear()

            logger.debug("已取消所有任务")
        except Exception as e:
            logger.error(f"取消任务失败: {e}")

    def get_task_status(self) -> Dict:
        """获取任务状态"""
        # 获取任务状态（线程安全）
        with self._tasks_lock:
            task_list = [
                {
                    'task_id': task.task_id,
                    'is_running': task.is_running
                }
                for task in self.tasks.values()
            ]

        # 统计任务数
        total_tasks = len(task_list)
        running_tasks = len([task for task in task_list if task['is_running']])

        return {
            'running': total_tasks > 0,  # 有任务存在就认为管理器在运行
            'total_tasks': total_tasks,  # 总任务数
            'running_tasks': running_tasks,  # 正在运行的任务数
            'task_list': task_list
        }

# 全局任务管理器实例
task_manager = IntelligenceTaskManager()

def start_task_manager(service: Optional[client.Service] = None):
    """启动任务管理器"""
    task_manager.start(service)

def stop_task_manager():
    """停止任务管理器"""
    task_manager.stop()

def get_task_manager_status():
    """获取任务管理器状态"""
    return task_manager.get_task_status()
