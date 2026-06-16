import os
import json
import logging
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGS_DIR = os.path.join(BASE_DIR, "logs")
RUNTIME_DIR = os.path.join(LOGS_DIR, "runtime")
TOKENS_DIR = os.path.join(LOGS_DIR, "tokens")


class SizeAndTimeRotatingFileHandler(TimedRotatingFileHandler):
    def __init__(self, filename, when='midnight', interval=1, backupCount=30,
                 max_bytes=5*1024*1024, encoding='utf-8'):
        self.max_bytes = max_bytes
        super().__init__(filename, when=when, interval=interval,
                         backupCount=backupCount, encoding=encoding)

    def shouldRollover(self, record):
        if super().shouldRollover(record):
            return True
        if self.max_bytes > 0 and os.path.exists(self.baseFilename):
            if os.path.getsize(self.baseFilename) >= self.max_bytes:
                return True
        return False


def _ensure_dirs():
    os.makedirs(RUNTIME_DIR, exist_ok=True)
    os.makedirs(TOKENS_DIR, exist_ok=True)


def init_logger():
    _ensure_dirs()

    runtime_log = logging.getLogger("tavlite")
    runtime_log.setLevel(logging.INFO)
    runtime_handler = SizeAndTimeRotatingFileHandler(
        filename=os.path.join(RUNTIME_DIR, "runtime.log"),
        when='midnight',
        interval=1,
        backupCount=30,
        max_bytes=5*1024*1024,
    )
    runtime_handler.setLevel(logging.INFO)
    runtime_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    runtime_log.addHandler(runtime_handler)

    tokens_log = logging.getLogger("tavlite_tokens")
    tokens_log.setLevel(logging.INFO)
    tokens_log.propagate = False
    tokens_handler = SizeAndTimeRotatingFileHandler(
        filename=os.path.join(TOKENS_DIR, "tokens.log"),
        when='midnight',
        interval=1,
        backupCount=90,
        max_bytes=5*1024*1024,
    )
    tokens_handler.setLevel(logging.INFO)
    tokens_handler.setFormatter(logging.Formatter("%(message)s"))
    tokens_log.addHandler(tokens_handler)


def get_runtime_logger(name=None):
    if name:
        return logging.getLogger(f"tavlite.{name}")
    return logging.getLogger("tavlite")


def log_tokens(model: str, usage) -> None:
    try:
        prompt_tokens = getattr(usage, 'prompt_tokens', 0)
        completion_tokens = getattr(usage, 'completion_tokens', 0)
        timestamp = datetime.now().isoformat()
        record = {
            "timestamp": timestamp,
            "model": model,
            "usage": str(usage),
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
        }
        tokens_log = logging.getLogger("tavlite_tokens")
        tokens_log.info(json.dumps(record, ensure_ascii=False))
        from src import state
        state.update_token_usage(timestamp, model, prompt_tokens, completion_tokens)
    except Exception:
        pass
