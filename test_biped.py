"""
GaitGenerator のユニットテスト (PyBullet 不要)

テスト対象:
  - 全ジョイントが返される
  - 左右の位相差が π
  - 膝角度は常に ≥ 0
  - 1サイクル後に位相が一周する
  - パラメータ変更が反映される
"""

import math
import unittest

from biped_controller import GaitGenerator, GaitParams


class TestGaitGenerator(unittest.TestCase):
    def setUp(self):
        self.gen = GaitGenerator()

    # ------------------------------------------------------------------
    # 基本動作
    # ------------------------------------------------------------------

    def test_returns_all_joints(self):
        targets = self.gen.compute(0.0)
        expected = {
            "left_hip", "left_knee", "left_ankle",
            "right_hip", "right_knee", "right_ankle",
        }
        self.assertEqual(set(targets.keys()), expected)

    def test_all_values_are_float(self):
        for t in [0.0, 0.1, 0.4, 0.8]:
            targets = self.gen.compute(t)
            for name, val in targets.items():
                self.assertIsInstance(val, float, f"{name} at t={t}")

    # ------------------------------------------------------------------
    # 左右の位相関係
    # ------------------------------------------------------------------

    def test_left_right_hip_antiphase(self):
        """左右の股関節は π 位相差 (符号が逆)"""
        for t in [0.0, 0.1, 0.2, 0.4]:
            targets = self.gen.compute(t)
            self.assertAlmostEqual(
                targets["left_hip"], -targets["right_hip"], places=10,
                msg=f"t={t}"
            )

    def test_left_right_ankle_antiphase(self):
        """左右の足首は π 位相差"""
        for t in [0.0, 0.15, 0.3]:
            targets = self.gen.compute(t)
            self.assertAlmostEqual(
                targets["left_ankle"], -targets["right_ankle"], places=10,
                msg=f"t={t}"
            )

    # ------------------------------------------------------------------
    # 膝の制約
    # ------------------------------------------------------------------

    def test_knee_non_negative(self):
        """膝角度は常に ≥ 0"""
        T = self.gen.params.cycle_time
        N = 200
        for i in range(N):
            t = T * i / N
            targets = self.gen.compute(t)
            self.assertGreaterEqual(targets["left_knee"],  0.0, f"left_knee at t={t:.3f}")
            self.assertGreaterEqual(targets["right_knee"], 0.0, f"right_knee at t={t:.3f}")

    def test_knee_max_within_amplitude(self):
        """膝の最大値は amplitude 以下"""
        p = self.gen.params
        T = p.cycle_time
        N = 500
        for i in range(N):
            t = T * i / N
            targets = self.gen.compute(t)
            for side in ("left", "right"):
                self.assertLessEqual(
                    targets[f"{side}_knee"],
                    p.knee_amplitude + 1e-9,
                    f"{side}_knee at t={t:.3f}",
                )

    # ------------------------------------------------------------------
    # 周期性
    # ------------------------------------------------------------------

    def test_periodic(self):
        """1サイクル後に同じ値に戻る"""
        T = self.gen.params.cycle_time
        for t in [0.0, 0.1, 0.3, T / 2]:
            a = self.gen.compute(t)
            b = self.gen.compute(t + T)
            for joint in GaitGenerator.JOINTS:
                self.assertAlmostEqual(
                    a[joint], b[joint], places=10,
                    msg=f"{joint} t={t:.2f}"
                )

    # ------------------------------------------------------------------
    # パラメータ変更
    # ------------------------------------------------------------------

    def test_hip_amplitude_scales(self):
        """hip_amplitude を 2 倍にすると股関節角度も 2 倍"""
        params1 = GaitParams(hip_amplitude=0.3)
        params2 = GaitParams(hip_amplitude=0.6)
        g1 = GaitGenerator(params1)
        g2 = GaitGenerator(params2)

        for t in [0.05, 0.2, 0.5]:
            self.assertAlmostEqual(
                g2.compute(t)["left_hip"],
                2.0 * g1.compute(t)["left_hip"],
                places=10,
            )

    def test_zero_amplitudes(self):
        """全振幅 0 の場合すべて 0"""
        params = GaitParams(
            hip_amplitude=0.0, knee_amplitude=0.0, ankle_amplitude=0.0
        )
        gen = GaitGenerator(params)
        for t in [0.0, 0.4, 0.8]:
            for val in gen.compute(t).values():
                self.assertAlmostEqual(val, 0.0, places=15)

    # ------------------------------------------------------------------
    # phase()
    # ------------------------------------------------------------------

    def test_phase_range(self):
        """phase() は [0, 2π) の範囲"""
        T = self.gen.params.cycle_time
        for i in range(100):
            t = T * i / 10.0
            phi = self.gen.phase(t)
            self.assertGreaterEqual(phi, 0.0)
            self.assertLess(phi, 2.0 * math.pi + 1e-12)


if __name__ == "__main__":
    unittest.main(verbosity=2)
