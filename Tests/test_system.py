"""Tests for IBF_System.sln"""
# pylint: disable=missing-function-docstring, missing-class-docstring
import sys
import unittest

from connection import cold_reset, conn, wait_cycles

COLD_RESET = False
COLD_RESET = True


class TestSystem(unittest.TestCase):

    PREFIX = "SystemBase"

    @classmethod
    def setUpClass(cls) -> None:
        conn.open()
        return super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        conn.close()

    def setUp(self) -> None:
        if COLD_RESET:
            cold_reset()
        return super().setUp()

    @staticmethod
    def _trigger_falling_edge(var: str) -> None:
        conn.write_by_name(var, True)
        wait_cycles(1)
        conn.write_by_name(var, False)
        wait_cycles(1)

    def _initalize(self):
        """After cold reset, system ends up in state `Safe`"""
        wait_cycles(7)  # it takes 7 cycles to initialize (tested with breakpoint)
        self.assertEqual(
            conn.read_by_name(f"{self.PREFIX}.fbFaultHandler.nActiveFaults"),
            0,
        )

    def _enable(self):
        """Move from state `Safe` to state `Enable`"""
        self._initalize()
        conn.write_by_name(f"{self.PREFIX}.ibEstopOk", True)
        conn.write_by_name(f"{self.PREFIX}.ibSystemSafetyOk", True)
        conn.write_by_name(f"{self.PREFIX}.fbAirpressureOk.Istatus", True)
        wait_cycles(150)  # a whole lot of cycles! why?

    def _idle(self):
        """Move from state `Enable` to state `Idle`. Moves through state `Home`"""
        self._enable()
        self._trigger_falling_edge(f"{self.PREFIX}.fbCmdStartSystem.Istatus")

    def _semiauto(self):
        """Move from state `Idle` to state `SemiAuto`"""
        self._idle()
        self._trigger_falling_edge(f"{self.PREFIX}.fbCmdStartSystem.Istatus")

    def _automatic(self):
        """Move from state `SemiAuto` to state `Automatic`
        At least one module needs to be registered, because of the inverted bAutomatic feedback."""
        self._semiauto()
        self._trigger_falling_edge(f"{self.PREFIX}.fbCmdStartAuto.Istatus")

    def test_01_initialize(self):
        self._initalize()
        self.assertTrue(conn.read_by_name(f"{self.PREFIX}.bInitialized"))

    def test_02_enable(self):
        self._enable()
        self.assertTrue(conn.read_by_name(f"{self.PREFIX}.bEnabled"))

    def test_03_idle(self):
        self._idle()
        self.assertTrue(conn.read_by_name(f"{self.PREFIX}.bHomed"))

    def test_04_semiauto(self):
        self._semiauto()
        self.assertTrue(conn.read_by_name(f"{self.PREFIX}.bSemiAuto"))

    def test_05_automatic(self):
        self._automatic()
        self.assertTrue(conn.read_by_name(f"{self.PREFIX}.bAutomatic"))


if __name__ == "__main__":
    for _ in range(1):  # increase value to repeat the test
        test = unittest.main(verbosity=2, exit=False, failfast=True)
        if not test.result.wasSuccessful():
            sys.exit(-1)
