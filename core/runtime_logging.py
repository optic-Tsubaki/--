"""桌宠运行日志与未处理异常记录。"""

from __future__ import annotations

import logging
import sys
from pathlib import Path


def configure_runtime_logging(logs_dir: Path) -> None:
    """将运行错误保存在项目数据目录，便于排查且不写入仓库。"""
    logs_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("studypet")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    log_file = logs_dir / "studypet.log"
    if not any(
        isinstance(handler, logging.FileHandler)
        and Path(handler.baseFilename) == log_file
        for handler in logger.handlers
    ):
        handler = logging.FileHandler(log_file, encoding="utf-8")
        handler.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
        )
        logger.addHandler(handler)

    def log_unhandled_exception(
        exception_type: type[BaseException],
        exception: BaseException,
        traceback: object,
    ) -> None:
        if issubclass(exception_type, KeyboardInterrupt):
            sys.__excepthook__(exception_type, exception, traceback)
            return
        logger.critical(
            "未处理异常",
            exc_info=(exception_type, exception, traceback),
        )

    sys.excepthook = log_unhandled_exception
