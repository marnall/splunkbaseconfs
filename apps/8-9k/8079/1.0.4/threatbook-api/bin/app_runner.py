#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ThreatBook API 应用运行器
提供日志记录和 Splunk 连接功能
"""
import os
import signal
import sys
# 保持程序持续运行
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import splunklib.client as client
from splunk_utils import SplunkUtils
from logger_utils import get_logger
from config_flag_manager import get_config_flag, set_config_flag
# ---------------------------------------------------------------------------
# 日志配置
# ---------------------------------------------------------------------------

logger = get_logger()

# ---------------------------------------------------------------------------
# Splunk 连接
# ---------------------------------------------------------------------------

def connect_to_splunk() -> client.Service:
    """连接到 Splunk 服务（向后兼容函数）"""
    return SplunkUtils.connect_to_splunk()

if __name__ == "__main__":
    # 启动应用运行器
    logger.info("ThreatBook API 应用运行器启动中")
    time.sleep(10)

    try:
        # 连接Splunk服务
        service = connect_to_splunk()
        logger.info("Splunk连接成功")

        # 启动情报任务管理器
        from intelligence_task_manager import start_task_manager, stop_task_manager, get_task_manager_status
        start_task_manager(service)
        logger.info("情报任务管理器启动成功")

        # 设置信号处理
        def signal_handler(signum, frame):
            logger.info(f"接收到信号 {signum}，准备停止")
            stop_task_manager()
            sys.exit(0)

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

        # 主循环 - 持续运行
        logger.info("应用运行器进入持续运行模式")
        while True:
            try:
                time.sleep(60)
                #获取配置更新标志
                flag_value, timestamp, exists = get_config_flag()
                if exists and flag_value == "True":
                    logger.info("配置更新，重新启动任务管理器")
                    stop_task_manager()
                    start_task_manager(service)
                    set_config_flag("False", timestamp=True)


                status = get_task_manager_status()
                
                # 检查任务管理器状态
                if status['running'] and status['total_tasks'] > 0:
                    # 只在有变化时输出日志
                    if status['running_tasks'] > 0:
                        logger.info(f"任务管理器: 总任务={status['total_tasks']}, 正在运行={status['running_tasks']}")
                elif status['total_tasks'] == 0:
                    logger.warning("任务管理器无任务，尝试重新加载配置")
                    # 重新加载配置并启动任务
                    from intelligence_task_manager import task_manager
                    task_manager._load_and_schedule_tasks()
                else:
                    logger.warning("任务管理器异常，尝试重新启动")
                    start_task_manager()

            except Exception as e:
                logger.error(f"主循环异常: {e}")
                time.sleep(10)  # 短暂等待后继续

    except KeyboardInterrupt:
        logger.info("接收到停止信号")
        stop_task_manager()
    except Exception as e:
        logger.error(f"应用运行器异常: {e}")
        stop_task_manager()
    finally:
        stop_task_manager()
        logger.info("应用运行器执行完成")
