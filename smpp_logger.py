import logging
from logging.handlers import RotatingFileHandler            #循环文件
from pathlib import Path

def get_logger(name):
    # print(f"{name=}")
    formatter = logging.Formatter(
        fmt='%(asctime)s [%(levelname)s]: %(filename)s(%(funcName)s:%(lineno)s) >> %(message)s')
        # fmt='%(asctime)s  [%(levelname)s]: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    log_file = Path.home() /f".{name}.log.txt"
    rfile_handler = RotatingFileHandler(log_file, maxBytes = 1024*1024, backupCount = 3)
    rfile_handler.setLevel(logging.INFO)
    rfile_handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    

    logger.addHandler(console_handler)
    logger.addHandler(rfile_handler)
    return logger

# logger = get_logger(__name__)
