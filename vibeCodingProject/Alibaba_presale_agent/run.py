"""
本地开发入口
    python run.py               # http://127.0.0.1:8000
    python run.py --port 9000
"""

import argparse

import uvicorn


def main():
    parser = argparse.ArgumentParser(description="百炼问答 Agent")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    uvicorn.run("app.server:app", host=args.host, port=args.port, reload=False)


if __name__ == "__main__":
    main()
