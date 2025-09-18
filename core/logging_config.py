import logging
import sys
import json

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "level": record.levelname,
            "time": self.formatTime(record, self.datefmt),
            "msg": record.getMessage(),
            "module": record.module,
            "funcName": record.funcName,
            "lineno": record.lineno,
        }
        if hasattr(record, "extra"):
            log_record.update(record.extra)
        return json.dumps(log_record, ensure_ascii=False)

def setup_logging():
    # 控制台输出
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(JsonFormatter())
    # 文件输出
    file_handler = logging.FileHandler("llm_service.log", encoding="utf-8")
    file_handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers = [stream_handler, file_handler]

setup_logging()
logger = logging.getLogger("llm_service") 