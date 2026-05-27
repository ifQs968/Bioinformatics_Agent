"""
Bioinformatics Agent — 主入口。
启动 FastAPI 后端服务。
"""
import sys
import uvicorn
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import config


def main():
    try:
        config.validate()
    except ValueError as e:
        print(f"\n{'='*60}")
        print(f"  配置错误: {e}")
        print(f"{'='*60}\n")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  Bioinformatics Agent API Server")
    print(f"  地址: http://{config.APP_HOST}:{config.APP_PORT}")
    print(f"  文档: http://{config.APP_HOST}:{config.APP_PORT}/docs")
    print(f"  API:  http://{config.APP_HOST}:{config.APP_PORT}/api/research")
    print(f"{'='*60}\n")

    uvicorn.run(
        "backend.api.server:app",
        host=config.APP_HOST,
        port=config.APP_PORT,
        log_level=config.LOG_LEVEL.lower(),
        reload=False,
    )


if __name__ == "__main__":
    main()
