# my-robot — 外部ロボット制御システム

TCP/IPソケット通信を使って外部ロボットを操作するPythonパッケージです。

## ファイル構成

| ファイル | 説明 |
|---|---|
| `robot_controller.py` | ロボット制御クラス（メインライブラリ） |
| `main.py` | 対話式CLI |
| `robot_server_mock.py` | テスト用モックサーバー |
| `test_robot.py` | ユニットテスト |

## 通信プロトコル

JSON-over-TCP（改行区切り）を使用します。

**コマンド例:**
```json
{"command": "move", "direction": "forward", "speed": 50, "duration": 1.0}
{"command": "turn", "direction": "left", "angle": 90}
{"command": "stop"}
{"command": "status"}
{"command": "ping"}
```

**応答例:**
```json
{"status": "ok", "message": "..."}
```

## クイックスタート

### 1. モックサーバーで動作確認

```bash
# ターミナル1: モックサーバー起動
python robot_server_mock.py

# ターミナル2: CLI起動
python main.py --host 127.0.0.1 --port 9000
```

### 2. 実機への接続

```bash
python main.py --host <ロボットのIPアドレス> --port 9000
```

### 3. コードから利用

```python
from robot_controller import RobotController

with RobotController("192.168.1.100", port=9000) as robot:
    robot.move_forward(speed=50, duration=2.0)
    robot.turn_left(90)
    robot.stop()
    print(robot.get_status())
```

## CLI コマンド一覧

| コマンド | 説明 | 例 |
|---|---|---|
| `forward [speed] [duration]` | 前進 | `forward 70 3.0` |
| `backward [speed] [duration]` | 後退 | `backward 50 1.5` |
| `left [angle]` | 左回転 | `left 90` |
| `right [angle]` | 右回転 | `right 45` |
| `stop` | 緊急停止 | `stop` |
| `status` | 状態確認 | `status` |
| `ping` | 接続確認 | `ping` |
| `quit` / `exit` | 終了 | |

## テスト実行

```bash
python -m pytest test_robot.py -v
# または
python test_robot.py
```
