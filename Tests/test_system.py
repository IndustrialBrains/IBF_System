"""Tests for IBF_System.sln"""
# pylint: disable=missing-function-docstring, missing-class-docstring
import sys
import unittest

from connection import cold_reset, conn, trigger_falling_edge, wait_cycles, wait_value

COLD_RESET = False
COLD_RESET = True


class TestSystem(unittest.TestCase):

    PREFIX = "PRG_TEST"
    PREFIX_SYS = "SystemBase"
    PREFIX_MODULE = f"{PREFIX}.fbDummyModule"

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
        conn.write_by_name(f"{self.PREFIX}.bEnableTests", True)
        return super().setUp()

    def _initalize(self):
        """After cold reset, system ends up in state `Safe`"""
        conn.write_by_name(f"{self.PREFIX_MODULE}.bAllowInit", True)

    def _enable(self):
        """Move from state `Safe` to state `Enable`"""
        self._initalize()
        conn.write_by_name(f"{self.PREFIX_MODULE}.bAllowIsSafe", True)
        conn.write_by_name(f"{self.PREFIX_MODULE}.bAllowReset", True)
        conn.write_by_name(f"{self.PREFIX_SYS}.ibEstopOk", True)
        # Reduce air pressure sensor delay (default 1sec)
        conn.write_by_name(f"{self.PREFIX_SYS}.fbAirpressureOk.tDelay", 0)
        conn.write_by_name(f"{self.PREFIX_SYS}.fbAirpressureOk.Istatus", True)
        wait_cycles(50)  # TODO: why so many cycles?
        trigger_falling_edge(f"{self.PREFIX_SYS}.fbCmdReset.Istatus")

    def _idle(self):
        """Move from state `Enable` to state `Idle`. Moves through state `Home`"""
        self._enable()
        conn.write_by_name(f"{self.PREFIX_MODULE}.bAllowHome", True)
        trigger_falling_edge(f"{self.PREFIX_SYS}.fbCmdStartSystem.Istatus")

    def _semiauto(self):
        """Move from state `Idle` to state `SemiAuto`"""
        self._idle()
        conn.write_by_name(f"{self.PREFIX_MODULE}.bAllowSemiAuto", True)
        trigger_falling_edge(f"{self.PREFIX_SYS}.fbCmdStartSystem.Istatus")

    def _automatic(self):
        """Move from state `SemiAuto` to state `Automatic`
        At least one module needs to be registered, because of the inverted bAutomatic feedback."""
        self._semiauto()
        conn.write_by_name(f"{self.PREFIX_MODULE}.bAllowAutomatic", True)
        trigger_falling_edge(f"{self.PREFIX_SYS}.fbCmdStartAuto.Istatus")

    def _manual(self, assert_ok: bool = False):
        conn.write_by_name(f"{self.PREFIX_MODULE}.bAllowManual", True)
        conn.write_by_name("GVL_HMI.fbHMIControl.bInScreenManual", True)
        conn.write_by_name(
            "GVL_Devices.fbManualController.stHMI.bEnabled", True
        )  # "Enable manual control" button in HMI
        if assert_ok:
            self.assertTrue(wait_value(f"{self.PREFIX_SYS}.bManual", True, 1))
        else:
            wait_value(f"{self.PREFIX_SYS}.bManual", True, 1)

    def test_01_initialize(self):
        self._initalize()
        self.assertTrue(wait_value(f"{self.PREFIX_SYS}.bInitialized", True, 1))

    def test_02_enable(self):
        self._enable()
        self.assertTrue(wait_value(f"{self.PREFIX_SYS}.bEnabled", True, 1))

    def test_03_idle(self):
        self._idle()
        self.assertTrue(wait_value(f"{self.PREFIX_SYS}.bHomed", True, 1))

    def test_04_semiauto(self):
        self._semiauto()
        self.assertTrue(wait_value(f"{self.PREFIX_SYS}.bSemiAuto", True, 1))
        self.assertFalse(conn.read_by_name(f"{self.PREFIX_SYS}.bAutomatic"))

    def test_05_automatic(self):
        self._automatic()
        self.assertTrue(wait_value(f"{self.PREFIX_SYS}.bAutomatic", True, 1))
        self.assertFalse(conn.read_by_name(f"{self.PREFIX_SYS}.bSemiAuto"))

    def test_06_manual_from_enabled(self):
        self._enable()
        self._manual(assert_ok=True)

    def test_06_manual_from_semiauto(self):
        self._semiauto()
        self._manual()
        wait_cycles(10)
        self.assertFalse(conn.read_by_name(f"{self.PREFIX_SYS}.bManual"))

    def test_06_manual_from_automatic(self):
        self._automatic()
        self._manual()
        wait_cycles(10)
        self.assertFalse(conn.read_by_name(f"{self.PREFIX_SYS}.bManual"))

    def test_06_manual_to_semiauto(self):
        self._enable()
        self._manual()
        self._semiauto()
        wait_cycles(10)
        self.assertFalse(conn.read_by_name(f"{self.PREFIX_SYS}.bSemiAuto"))

    def test_06_manual_to_auto(self):
        self._enable()
        self._manual()
        self._semiauto()
        wait_cycles(10)
        self.assertFalse(conn.read_by_name(f"{self.PREFIX_SYS}.bAutomatic"))

    def test_07_fault_estop(self):
        self._enable()
        conn.write_by_name(f"{self.PREFIX_SYS}.ibEstopOk", False)
        self.assertTrue(wait_value(f"{self.PREFIX_SYS}.bEnabled", False, 1))


if __name__ == "__main__":
    for _ in range(1):  # increase value to repeat the test
        test = unittest.main(verbosity=2, exit=False, failfast=True)
        if not test.result.wasSuccessful():
            sys.exit(-1)
