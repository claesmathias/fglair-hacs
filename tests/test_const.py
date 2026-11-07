"""Tests for mode/fan mappings in const.py."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from custom_components.fujitsu_airstage.const import (
    FGL_MODE_TO_HA,
    HA_MODE_TO_FGL,
    FGL_FAN_TO_HA,
    HA_FAN_TO_FGL,
    AC_MODE_TO_HA,
    HA_MODE_TO_AC,
    AC_FAN_TO_HA,
    HA_FAN_TO_AC,
)


class TestFglModeMappings:
    def test_known_values(self):
        assert FGL_MODE_TO_HA[0] == "off"
        assert FGL_MODE_TO_HA[2] == "auto"
        assert FGL_MODE_TO_HA[3] == "cool"
        assert FGL_MODE_TO_HA[4] == "dry"
        assert FGL_MODE_TO_HA[5] == "fan_only"
        assert FGL_MODE_TO_HA[6] == "heat"

    def test_ha_to_fgl_round_trip(self):
        # Every HA→FGL value must map back to the same HA mode
        for ha_mode, fgl_val in HA_MODE_TO_FGL.items():
            assert FGL_MODE_TO_HA[fgl_val] == ha_mode, (
                f"Round-trip failed: {ha_mode} → {fgl_val} → {FGL_MODE_TO_HA[fgl_val]}"
            )

    def test_turn_on_uses_value_1(self):
        # The app sends operation_mode=1 when pressing the power button.
        # This value is NOT in HA_MODE_TO_FGL (it is a wake signal, not a mode).
        assert 1 not in HA_MODE_TO_FGL.values(), (
            "operation_mode=1 should never be set as a regular mode; only async_turn_on uses it"
        )

    def test_value_1_reads_as_off(self):
        # FGLair operation_modes.js: "on" (1) has isOff: true — the unit is
        # still waking up and restoring its last mode.
        assert FGL_MODE_TO_HA[1] == "off"

    def test_off_maps_to_zero(self):
        assert HA_MODE_TO_FGL["off"] == 0


class TestFglFanMappings:
    def test_known_values(self):
        # Values from the FGLair APK air_volumes.js MODES object
        assert FGL_FAN_TO_HA[0] == "quiet"
        assert FGL_FAN_TO_HA[1] == "low"
        assert FGL_FAN_TO_HA[2] == "medium"
        assert FGL_FAN_TO_HA[3] == "high"
        assert FGL_FAN_TO_HA[4] == "auto"

    def test_round_trip(self):
        for fgl_val, ha_fan in FGL_FAN_TO_HA.items():
            assert HA_FAN_TO_FGL[ha_fan] == fgl_val


class TestAcModeMappings:
    def test_known_values(self):
        assert AC_MODE_TO_HA[0] == "fan_only"
        assert AC_MODE_TO_HA[1] == "heat"
        assert AC_MODE_TO_HA[2] == "cool"
        assert AC_MODE_TO_HA[3] == "dry"
        assert AC_MODE_TO_HA[4] == "auto"

    def test_round_trip(self):
        for ac_val, ha_mode in AC_MODE_TO_HA.items():
            assert HA_MODE_TO_AC[ha_mode] == ac_val


class TestAcFanMappings:
    def test_known_values(self):
        assert AC_FAN_TO_HA[0] == "auto"
        assert AC_FAN_TO_HA[5] == "lower"
        assert AC_FAN_TO_HA[6] == "low"
        assert AC_FAN_TO_HA[7] == "medium"
        assert AC_FAN_TO_HA[8] == "high"
        assert AC_FAN_TO_HA[9] == "higher"

    def test_round_trip(self):
        for ac_val, ha_fan in AC_FAN_TO_HA.items():
            assert HA_FAN_TO_AC[ha_fan] == ac_val
