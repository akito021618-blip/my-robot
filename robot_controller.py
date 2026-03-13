"""
外部ロボット制御モジュール

TCP/IPソケット通信を使って外部ロボットに接続し、
移動・停止などのコマンドを送信します。
"""

import socket
import time
import json
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class RobotController:
    """外部ロボットとのTCP/IP通信を管理するコントローラー"""

    DEFAULT_PORT = 9000

    def __init__(self, host: str, port: int = DEFAULT_PORT, timeout: float = 5.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self._sock: socket.socket | None = None

    # ------------------------------------------------------------------
    # 接続管理
    # ------------------------------------------------------------------

    def connect(self) -> None:
        """ロボットに接続する"""
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.settimeout(self.timeout)
        self._sock.connect((self.host, self.port))
        logger.info("ロボットに接続しました: %s:%d", self.host, self.port)

    def disconnect(self) -> None:
        """ロボットとの接続を閉じる"""
        if self._sock:
            self._sock.close()
            self._sock = None
            logger.info("ロボットとの接続を切断しました")

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *_):
        self.disconnect()

    # ------------------------------------------------------------------
    # コマンド送受信
    # ------------------------------------------------------------------

    def _send(self, command: dict) -> dict:
        """コマンドをJSON形式で送信し、応答を受け取る"""
        if self._sock is None:
            raise ConnectionError("ロボットに接続されていません。connect() を先に呼んでください。")

        payload = (json.dumps(command) + "\n").encode()
        self._sock.sendall(payload)
        logger.debug("送信: %s", command)

        raw = b""
        while not raw.endswith(b"\n"):
            chunk = self._sock.recv(4096)
            if not chunk:
                raise ConnectionError("ロボットから応答がありません")
            raw += chunk

        response = json.loads(raw.strip())
        logger.debug("受信: %s", response)
        return response

    # ------------------------------------------------------------------
    # 移動コマンド
    # ------------------------------------------------------------------

    def move_forward(self, speed: int = 50, duration: float = 1.0) -> dict:
        """前進する (speed: 0-100, duration: 秒)"""
        logger.info("前進: speed=%d, duration=%.1fs", speed, duration)
        return self._send({"command": "move", "direction": "forward",
                           "speed": speed, "duration": duration})

    def move_backward(self, speed: int = 50, duration: float = 1.0) -> dict:
        """後退する (speed: 0-100, duration: 秒)"""
        logger.info("後退: speed=%d, duration=%.1fs", speed, duration)
        return self._send({"command": "move", "direction": "backward",
                           "speed": speed, "duration": duration})

    def turn_left(self, angle: int = 90) -> dict:
        """左回転する (angle: 度)"""
        logger.info("左回転: %d度", angle)
        return self._send({"command": "turn", "direction": "left", "angle": angle})

    def turn_right(self, angle: int = 90) -> dict:
        """右回転する (angle: 度)"""
        logger.info("右回転: %d度", angle)
        return self._send({"command": "turn", "direction": "right", "angle": angle})

    def stop(self) -> dict:
        """緊急停止する"""
        logger.info("停止")
        return self._send({"command": "stop"})

    # ------------------------------------------------------------------
    # ユーティリティ
    # ------------------------------------------------------------------

    def get_status(self) -> dict:
        """ロボットの現在状態を取得する"""
        return self._send({"command": "status"})

    def ping(self) -> bool:
        """ロボットが応答するか確認する"""
        try:
            resp = self._send({"command": "ping"})
            return resp.get("status") == "ok"
        except Exception:
            return False
