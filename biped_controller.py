"""
2足歩行ロボット 歩行制御モジュール

アプローチ: 正弦波 CPG（中枢パターン生成器）
  - 各関節角度を時刻 t の正弦波として生成
  - 左右の脚は π (180°) 位相差
  - 膝はスイング相のみ曲げる（常に ≥ 0）

ジョイント構成 (6 DOF):
  left_hip, left_knee, left_ankle
  right_hip, right_knee, right_ankle  ← 全て Y軸回転 (ピッチ)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

try:
    import pybullet as p
    PYBULLET_AVAILABLE = True
except ImportError:
    PYBULLET_AVAILABLE = False


# ---------------------------------------------------------------------------
# 歩行パラメータ
# ---------------------------------------------------------------------------

@dataclass
class GaitParams:
    """歩行パラメータ（チューニング可能）"""

    # ---- タイミング ----
    cycle_time: float = 0.8       # 1歩行サイクルの時間 [s]

    # ---- 振幅 ----
    hip_amplitude:   float = 0.35  # 股関節の最大角度 [rad] (~20°)
    knee_amplitude:  float = 0.45  # 膝関節の最大角度 [rad] (~26°)
    ankle_amplitude: float = 0.20  # 足首関節の最大角度 [rad] (~11°)

    # ---- 位相オフセット ----
    # 膝: スイング中期に最大になるようにオフセット
    knee_phase_offset:  float = 0.6   # [rad]
    # 足首: 蹴り出し → 着地を模倣
    ankle_phase_offset: float = -0.4  # [rad]

    # ---- PD ゲイン（PyBullet POSITION_CONTROL 用） ----
    kp_hip:   float = 1.0    # 股関節 位置ゲイン
    kd_hip:   float = 0.2    # 股関節 速度ゲイン
    kp_knee:  float = 1.0    # 膝      位置ゲイン
    kd_knee:  float = 0.2    # 膝      速度ゲイン
    kp_ankle: float = 0.5    # 足首    位置ゲイン
    kd_ankle: float = 0.1    # 足首    速度ゲイン

    # ---- 最大トルク [N] ----
    max_force_hip:   float = 300.0
    max_force_knee:  float = 300.0
    max_force_ankle: float = 150.0


# ---------------------------------------------------------------------------
# 歩行パターン生成器（PyBullet 不要: テスト可能）
# ---------------------------------------------------------------------------

class GaitGenerator:
    """
    時刻 t [s] → ジョイント目標角度 [rad] を計算する純粋な数学クラス。

    使用例::

        gen = GaitGenerator()
        targets = gen.compute(t=0.4)
        # → {"left_hip": ..., "left_knee": ..., ..., "right_ankle": ...}
    """

    JOINTS = (
        "left_hip",  "left_knee",  "left_ankle",
        "right_hip", "right_knee", "right_ankle",
    )

    def __init__(self, params: GaitParams | None = None) -> None:
        self.params = params or GaitParams()

    def compute(self, t: float) -> dict[str, float]:
        """時刻 t のジョイント目標角度を返す"""
        p = self.params
        omega = 2.0 * math.pi / p.cycle_time
        phi = omega * t

        targets: dict[str, float] = {}
        for side, base_offset in (("left", 0.0), ("right", math.pi)):
            phase = phi + base_offset

            # 股関節: 前後に振る正弦波
            targets[f"{side}_hip"] = p.hip_amplitude * math.sin(phase)

            # 膝: スイング相のみ曲げる（負値はクランプ）
            knee_raw = math.sin(phase + p.knee_phase_offset)
            targets[f"{side}_knee"] = p.knee_amplitude * max(knee_raw, 0.0)

            # 足首: 蹴り出し / 着地に合わせた位相
            targets[f"{side}_ankle"] = p.ankle_amplitude * math.sin(
                phase + p.ankle_phase_offset
            )

        return targets

    def phase(self, t: float) -> float:
        """現在の位相 [0, 2π) を返す"""
        return (2.0 * math.pi * t / self.params.cycle_time) % (2.0 * math.pi)


# ---------------------------------------------------------------------------
# PyBullet 制御器
# ---------------------------------------------------------------------------

class BipedController:
    """
    PyBullet ロボットに歩行コマンドを送る制御器。

    使用例::

        with pybullet.connect(pybullet.GUI):
            robot_id = pybullet.loadURDF("urdf/biped.urdf", ...)
            ctrl = BipedController(robot_id)
            ctrl.setup()
            while True:
                ctrl.update(t)
                pybullet.stepSimulation()
    """

    # URDF で定義したジョイント名
    _JOINT_NAMES = GaitGenerator.JOINTS

    def __init__(
        self,
        robot_id: int,
        params: GaitParams | None = None,
    ) -> None:
        if not PYBULLET_AVAILABLE:
            raise ImportError("pybullet がインストールされていません: pip install pybullet")
        self.robot_id = robot_id
        self.gait = GaitGenerator(params)
        self._joint_ids: dict[str, int] = self._build_joint_map()

    # ------------------------------------------------------------------
    # 初期化
    # ------------------------------------------------------------------

    def _build_joint_map(self) -> dict[str, int]:
        """ジョイント名 → インデックスのマップを作成"""
        mapping: dict[str, int] = {}
        n = p.getNumJoints(self.robot_id)
        for i in range(n):
            info = p.getJointInfo(self.robot_id, i)
            name: str = info[1].decode()
            if name in self._JOINT_NAMES:
                mapping[name] = i
        missing = set(self._JOINT_NAMES) - set(mapping)
        if missing:
            raise RuntimeError(f"URDF にジョイントが見つかりません: {missing}")
        return mapping

    def setup(self) -> None:
        """デフォルトモーターを無効化し、初期姿勢を設定する"""
        self._disable_default_motors()
        self._reset_initial_pose()

    def _disable_default_motors(self) -> None:
        """PyBullet のデフォルト速度制御モーターを無効化"""
        for idx in self._joint_ids.values():
            p.setJointMotorControl2(
                self.robot_id, idx,
                controlMode=p.VELOCITY_CONTROL,
                force=0,
            )

    def _reset_initial_pose(self) -> None:
        """直立姿勢 (膝を少し曲げた状態) に設定"""
        pose = {
            "left_hip":    0.10, "left_knee":  0.20, "left_ankle":  -0.10,
            "right_hip":  -0.10, "right_knee": 0.20, "right_ankle": -0.10,
        }
        for name, angle in pose.items():
            p.resetJointState(self.robot_id, self._joint_ids[name], angle)

    # ------------------------------------------------------------------
    # メインループから呼ぶ
    # ------------------------------------------------------------------

    def update(self, t: float) -> None:
        """時刻 t の目標角度を計算して PD 位置制御で送る"""
        targets = self.gait.compute(t)
        params = self.gait.params

        _gains: dict[str, tuple[float, float, float]] = {
            "hip":   (params.kp_hip,   params.kd_hip,   params.max_force_hip),
            "knee":  (params.kp_knee,  params.kd_knee,  params.max_force_knee),
            "ankle": (params.kp_ankle, params.kd_ankle, params.max_force_ankle),
        }

        for joint_name, target_angle in targets.items():
            # "left_hip" → "hip" の部分を取り出す
            joint_type = joint_name.split("_", 1)[1]  # hip / knee / ankle
            kp, kd, max_f = _gains[joint_type]
            idx = self._joint_ids[joint_name]

            p.setJointMotorControl2(
                self.robot_id,
                idx,
                controlMode=p.POSITION_CONTROL,
                targetPosition=target_angle,
                targetVelocity=0,
                positionGain=kp,
                velocityGain=kd,
                force=max_f,
            )

    # ------------------------------------------------------------------
    # ユーティリティ
    # ------------------------------------------------------------------

    def get_joint_states(self) -> dict[str, tuple[float, float]]:
        """全ジョイントの (角度, 角速度) を返す"""
        return {
            name: p.getJointState(self.robot_id, idx)[:2]
            for name, idx in self._joint_ids.items()
        }
