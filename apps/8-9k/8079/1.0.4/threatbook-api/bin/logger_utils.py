#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志工具模块
提供统一的日志配置功能
"""

import logging
import os
import sys
from datetime import datetime


def get_logger() -> logging.Logger:
    """简单的日志配置。"""
    logger = logging.getLogger(__name__)
    if logger.handlers:
        return logger  # 已初始化

    logger.setLevel(logging.INFO)
    today = datetime.now().strftime("%Y-%m-%d")
    # 使用Splunk应用数据目录存储日志
    bin_dir = os.path.dirname(os.path.abspath(__file__))  # bin/ 目录
    splunk_app_dir = os.path.dirname(bin_dir)  # splunk/ 目录
    log_dir = os.path.join(splunk_app_dir, "var", "log")
    os.makedirs(log_dir, exist_ok=True)
    file_handler = logging.FileHandler(os.path.join(log_dir, f"threatbook_api_{today}.log"))
    fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    # 对于 Splunk 脚本输入，使用 stderr 来避免被标记为 ERROR
    # 同时添加一个简单的控制台处理器用于调试
    stderr_handler = logging.StreamHandler(sys.stdout)
    stderr_handler.setFormatter(fmt)
    logger.addHandler(stderr_handler)

    return logger
