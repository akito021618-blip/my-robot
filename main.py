"""
外部ロボット制御 CLI

使い方:
    python main.py --host <ロボットのIPアドレス> [--port 9000]

コマンド例 (起動後に入力):
    forward 50 2.0   # speed=50, 2秒前進
    backward 30 1.5
    left 90
    right 45
    stop
    status
    ping
    quit
"""

import argparse
import sys
from robot_controller import RobotController


HELP_TEXT = """
利用可能なコマンド:
  forward [speed] [duration]  前進 (speed: 0-100, duration: 秒)
  backward [speed] [duration] 後退
  left [angle]                左回転 (angle: 度)
  right [angle]               右回転
  stop                        緊急停止
  status                      現在の状態を表示
  ping                        接続確認
  help                        このヘルプを表示
  quit / exit                 終了
"""


def run_cli(controller: RobotController) -> None:
    print(HELP_TEXT)
    while True:
        try:
            line = input("robot> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n終了します")
            break

        if not line:
            continue

        parts = line.split()
        cmd = parts[0].lower()

        try:
            if cmd in ("quit", "exit"):
                break
            elif cmd == "help":
                print(HELP_TEXT)
            elif cmd == "forward":
                speed = int(parts[1]) if len(parts) > 1 else 50
                duration = float(parts[2]) if len(parts) > 2 else 1.0
                print(controller.move_forward(speed, duration))
            elif cmd == "backward":
                speed = int(parts[1]) if len(parts) > 1 else 50
                duration = float(parts[2]) if len(parts) > 2 else 1.0
                print(controller.move_backward(speed, duration))
            elif cmd == "left":
                angle = int(parts[1]) if len(parts) > 1 else 90
                print(controller.turn_left(angle))
            elif cmd == "right":
                angle = int(parts[1]) if len(parts) > 1 else 90
                print(controller.turn_right(angle))
            elif cmd == "stop":
                print(controller.stop())
            elif cmd == "status":
                print(controller.get_status())
            elif cmd == "ping":
                ok = controller.ping()
                print("応答あり (ok)" if ok else "応答なし")
            else:
                print(f"不明なコマンド: {cmd}  (help で一覧表示)")
        except ConnectionError as e:
            print(f"[接続エラー] {e}")
        except Exception as e:
            print(f"[エラー] {e}")


def main() -> None:
    parser = argparse.ArgumentParser(description="外部ロボット制御 CLI")
    parser.add_argument("--host", default="127.0.0.1", help="ロボットのIPアドレス (デフォルト: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=9000, help="ポート番号 (デフォルト: 9000)")
    parser.add_argument("--timeout", type=float, default=5.0, help="タイムアウト秒数 (デフォルト: 5.0)")
    args = parser.parse_args()

    print(f"ロボットに接続中: {args.host}:{args.port}")
    try:
        with RobotController(args.host, args.port, args.timeout) as robot:
            print("接続成功")
            run_cli(robot)
    except ConnectionRefusedError:
        print(f"[エラー] 接続拒否: {args.host}:{args.port}")
        print("  ロボット（またはモックサーバー）が起動しているか確認してください。")
        print("  モック: python robot_server_mock.py")
        sys.exit(1)
    except OSError as e:
        print(f"[エラー] ネットワークエラー: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
