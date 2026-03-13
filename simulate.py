"""
2足歩行ロボット PyBullet シミュレーション

起動方法:
    python simulate.py [オプション]

オプション:
    --gui          GUI あり (デフォルト)
    --headless     GUI なし (CIやテスト向け)
    --hz HZ        シミュレーション周波数 (デフォルト: 240)
    --duration SEC 実行秒数 (デフォルト: 無限)
    --cycle-time T 歩行サイクル時間 (デフォルト: 0.8 s)

依存:
    pip install pybullet
"""

from __future__ import annotations

import argparse
import logging
import math
import os
import sys
import time

import pybullet as pb
import pybullet_data

from biped_controller import BipedController, GaitParams

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

URDF_PATH = os.path.join(os.path.dirname(__file__), "urdf", "biped.urdf")

# 直立時の胴体高さ [m]
# 脚長 (0.4) + 股関節~胴体重心 (0.15) + 足厚 (0.01) + 余裕
INITIAL_HEIGHT = 0.60


# ---------------------------------------------------------------------------
# シミュレーション本体
# ---------------------------------------------------------------------------

def build_robot(params: GaitParams) -> tuple[int, BipedController]:
    """ロボットをシーンに配置して制御器を返す"""
    robot_id = pb.loadURDF(
        URDF_PATH,
        basePosition=[0.0, 0.0, INITIAL_HEIGHT],
        baseOrientation=pb.getQuaternionFromEuler([0.0, 0.0, 0.0]),
        useFixedBase=False,
        flags=pb.URDF_USE_INERTIA_FROM_FILE,
    )
    ctrl = BipedController(robot_id, params)
    ctrl.setup()
    return robot_id, ctrl


def settle(robot_id: int, ctrl: BipedController, steps: int = 200) -> None:
    """ロボットを初期姿勢で着地させる"""
    for _ in range(steps):
        ctrl.update(t=0.0)
        pb.stepSimulation()


def log_status(robot_id: int, t: float) -> None:
    pos, orn = pb.getBasePositionAndOrientation(robot_id)
    roll, pitch, yaw = pb.getEulerFromQuaternion(orn)
    logger.info(
        "t=%.2fs  胴体高=%.3fm  roll=%.1f°  pitch=%.1f°",
        t, pos[2], math.degrees(roll), math.degrees(pitch),
    )


def run(
    gui: bool = True,
    hz: int = 240,
    duration: float | None = None,
    params: GaitParams | None = None,
) -> None:
    params = params or GaitParams()
    dt = 1.0 / hz

    # --- PyBullet 初期化 ---
    mode = pb.GUI if gui else pb.DIRECT
    client = pb.connect(mode)
    pb.setAdditionalSearchPath(pybullet_data.getDataPath())
    pb.setGravity(0, 0, -9.81)
    pb.setTimeStep(dt)

    if gui:
        pb.configureDebugVisualizer(pb.COV_ENABLE_GUI, 0)
        pb.configureDebugVisualizer(pb.COV_ENABLE_SHADOWS, 1)
        pb.resetDebugVisualizerCamera(
            cameraDistance=1.5,
            cameraYaw=45,
            cameraPitch=-20,
            cameraTargetPosition=[0, 0, 0.5],
        )

    # --- シーン構築 ---
    pb.loadURDF("plane.urdf")
    robot_id, ctrl = build_robot(params)

    # --- 着地・安定化 ---
    logger.info("初期化中...")
    settle(robot_id, ctrl, steps=300)
    logger.info("シミュレーション開始 (Ctrl+C で終了)")

    t = 0.0
    log_interval = 1.0
    next_log = log_interval

    try:
        while True:
            # 歩行コマンド送信
            ctrl.update(t)

            # 物理ステップ
            pb.stepSimulation()
            t += dt

            # カメラをロボットに追従 (GUI のみ)
            if gui:
                pos, _ = pb.getBasePositionAndOrientation(robot_id)
                pb.resetDebugVisualizerCamera(
                    cameraDistance=1.5,
                    cameraYaw=45,
                    cameraPitch=-20,
                    cameraTargetPosition=list(pos),
                )
                time.sleep(dt)  # リアルタイム表示

            # 定期ログ
            if t >= next_log:
                log_status(robot_id, t)
                next_log += log_interval

            # 転倒検出
            _, orn = pb.getBasePositionAndOrientation(robot_id)
            roll, pitch, _ = pb.getEulerFromQuaternion(orn)
            if abs(roll) > 1.2 or abs(pitch) > 1.2:
                logger.warning("転倒を検出しました (t=%.2fs)", t)
                break

            # 実行時間制限
            if duration is not None and t >= duration:
                logger.info("指定時間 %.1f s 経過。終了します。", duration)
                break

    except KeyboardInterrupt:
        logger.info("Ctrl+C を受信。終了します。")
    finally:
        pb.disconnect()


# ---------------------------------------------------------------------------
# エントリーポイント
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="2足歩行ロボット シミュレーション")
    parser.add_argument("--gui",       dest="gui", action="store_true",  default=True)
    parser.add_argument("--headless",  dest="gui", action="store_false")
    parser.add_argument("--hz",        type=int,   default=240,  help="シミュレーション周波数")
    parser.add_argument("--duration",  type=float, default=None, help="実行秒数 (省略=無限)")
    parser.add_argument("--cycle-time",type=float, default=0.8,  help="歩行サイクル時間 [s]")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    params = GaitParams(cycle_time=args.cycle_time)
    run(
        gui=args.gui,
        hz=args.hz,
        duration=args.duration,
        params=params,
    )
