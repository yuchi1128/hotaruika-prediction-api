import logging.config

# ログ設定の辞書
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "[%(asctime)s] [%(levelname)s] [%(name)s] - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {
        "app": {  # 'app'という名前のロガーを設定
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
    "root": {  # Uvicornなどの他のライブラリのログも表示
        "handlers": ["console"],
        "level": "INFO",
    },
}

def setup_logging():
    """アプリケーションのロギングを設定する"""
    logging.config.dictConfig(LOGGING_CONFIG)