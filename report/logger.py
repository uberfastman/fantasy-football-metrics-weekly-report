import logging
from logging.handlers import RotatingFileHandler

import os
import sys


def get_logger(module_name=None, propagate=True):

    log_file_dir = "logs"
    log_file_name = "out.log"
    log_file = os.path.join(log_file_dir, log_file_name)

    if not os.path.exists(log_file_dir):
        os.makedirs(log_file_dir)

    log_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    sh = logging.StreamHandler(stream=sys.stderr)
    sh.setLevel(logging.INFO)
    sh.setFormatter(log_formatter)

    rfh = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
    rfh.setLevel(logging.INFO)
    rfh.setFormatter(log_formatter)

    if module_name:
        logger = logging.getLogger(module_name)
    else:
        logger = logging.getLogger()

    if logger.hasHandlers():
        logger.handlers = []

    logger.setLevel(logging.INFO)
    logger.addHandler(sh)
    logger.addHandler(rfh)

    if not propagate:
        logger.propagate = False

    return logger
