"""
RobotController の統合テスト

モックサーバーを別スレッドで起動してテストします。
"""

import json
import socket
import threading
import time
import unittest

from robot_controller import RobotController
from robot_server_mock import handle_client


def start_mock_server(host: str, port: int) -> threading.Event:
    """テスト用モックサーバーをバックグラウンドで起動する"""
    ready = threading.Event()

    def serve():
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.bind((host, port))
            srv.listen()
            srv.settimeout(5)
            ready.set()
            try:
                while True:
                    try:
                        conn, addr = srv.accept()
                        t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
                        t.start()
                    except socket.timeout:
                        break
            except OSError:
                pass

    t = threading.Thread(target=serve, daemon=True)
    t.start()
    ready.wait(timeout=3)
    return ready


class TestRobotController(unittest.TestCase):
    HOST = "127.0.0.1"
    PORT = 19001  # テスト専用ポート

    @classmethod
    def setUpClass(cls):
        start_mock_server(cls.HOST, cls.PORT)
        time.sleep(0.1)

    def _robot(self) -> RobotController:
        r = RobotController(self.HOST, self.PORT, timeout=3.0)
        r.connect()
        return r

    def test_ping(self):
        with RobotController(self.HOST, self.PORT, timeout=3.0) as robot:
            self.assertTrue(robot.ping())

    def test_status(self):
        with RobotController(self.HOST, self.PORT, timeout=3.0) as robot:
            resp = robot.get_status()
            self.assertEqual(resp["status"], "ok")
            self.assertIn("battery", resp)

    def test_move_forward(self):
        with RobotController(self.HOST, self.PORT, timeout=3.0) as robot:
            resp = robot.move_forward(speed=60, duration=0.5)
            self.assertEqual(resp["status"], "ok")

    def test_move_backward(self):
        with RobotController(self.HOST, self.PORT, timeout=3.0) as robot:
            resp = robot.move_backward(speed=40, duration=0.5)
            self.assertEqual(resp["status"], "ok")

    def test_turn_left(self):
        with RobotController(self.HOST, self.PORT, timeout=3.0) as robot:
            resp = robot.turn_left(90)
            self.assertEqual(resp["status"], "ok")

    def test_turn_right(self):
        with RobotController(self.HOST, self.PORT, timeout=3.0) as robot:
            resp = robot.turn_right(45)
            self.assertEqual(resp["status"], "ok")

    def test_stop(self):
        with RobotController(self.HOST, self.PORT, timeout=3.0) as robot:
            resp = robot.stop()
            self.assertEqual(resp["status"], "ok")

    def test_context_manager(self):
        """with ブロックで自動的に接続・切断されることを確認"""
        with RobotController(self.HOST, self.PORT, timeout=3.0) as robot:
            self.assertIsNotNone(robot._sock)
        self.assertIsNone(robot._sock)


if __name__ == "__main__":
    unittest.main()
