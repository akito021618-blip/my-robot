"""
ロボットサーバーのモック実装

実機がない環境でテストするための簡易サーバーです。
RobotController からのコマンドを受け付け、ダミー応答を返します。

使い方:
    python robot_server_mock.py
"""

import json
import logging
import socket
import threading

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

HOST = "127.0.0.1"
PORT = 9000


def handle_client(conn: socket.socket, addr) -> None:
    logger.info("クライアント接続: %s", addr)
    with conn:
        buf = b""
        while True:
            chunk = conn.recv(4096)
            if not chunk:
                break
            buf += chunk
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                try:
                    cmd = json.loads(line.strip())
                except json.JSONDecodeError:
                    response = {"status": "error", "message": "invalid JSON"}
                else:
                    response = process_command(cmd)

                conn.sendall((json.dumps(response) + "\n").encode())

    logger.info("クライアント切断: %s", addr)


def process_command(cmd: dict) -> dict:
    command = cmd.get("command")
    logger.info("コマンド受信: %s", cmd)

    if command == "ping":
        return {"status": "ok", "message": "pong"}

    if command == "status":
        return {
            "status": "ok",
            "battery": 85,
            "position": {"x": 0.0, "y": 0.0, "theta": 0.0},
            "moving": False,
        }

    if command == "move":
        direction = cmd.get("direction", "forward")
        speed = cmd.get("speed", 50)
        duration = cmd.get("duration", 1.0)
        return {
            "status": "ok",
            "message": f"{direction} で speed={speed}, duration={duration}s 移動しました",
        }

    if command == "turn":
        direction = cmd.get("direction", "left")
        angle = cmd.get("angle", 90)
        return {"status": "ok", "message": f"{direction} に {angle}度 回転しました"}

    if command == "stop":
        return {"status": "ok", "message": "停止しました"}

    return {"status": "error", "message": f"不明なコマンド: {command}"}


def main() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, PORT))
        server.listen()
        logger.info("モックサーバー起動: %s:%d", HOST, PORT)
        while True:
            conn, addr = server.accept()
            thread = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            thread.start()


if __name__ == "__main__":
    main()
