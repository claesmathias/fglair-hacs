"""Tests for temperature conversion helpers and device-type detection in climate.py."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from custom_components.fujitsu_airstage.climate import (
    _adjust_to_celsius,
    _celsius_to_adjust,
    _display_to_celsius,
    _device_type,
)


class TestAdjustTemperature:
    """adjust_temperature: API stores tenths of °C (210 = 21.0 °C)."""

    def test_typical_value(self):
        assert _adjust_to_celsius(210) == 21.0

    def test_minimum(self):
        assert _adjust_to_celsius(160) == 16.0

    def test_maximum(self):
        assert _adjust_to_celsius(300) == 30.0

    def test_none_returns_none(self):
        assert _adjust_to_celsius(None) is None

    def test_round_trip(self):
        for celsius in [16.0, 18.0, 21.0, 24.5, 30.0]:
            assert _adjust_to_celsius(_celsius_to_adjust(celsius)) == celsius


class TestCelsiusToAdjust:
    def test_typical(self):
        assert _celsius_to_adjust(21.0) == 210

    def test_rounds_correctly(self):
        assert _celsius_to_adjust(21.5) == 215


class TestDisplayTemperature:
    """display_temperature uses APK lookup-table formula: trunc((raw - 5000) / 50) * 0.5."""

    # Values verified against the TEMPERATURES array in FGLair 3.4.2 APK build.js
    def test_21_celsius(self):
        # 5000 + 21/0.5 * 50 = 5000 + 2100 = 7100; formula: trunc((7100-5000)/50)*0.5 = 21.0
        assert _display_to_celsius(7100) == 21.0

    def test_21_5_celsius(self):
        assert _display_to_celsius(7150) == 21.5

    def test_16_celsius(self):
        assert _display_to_celsius(5000 + int(16 / 0.5) * 50) == 16.0

    def test_30_celsius(self):
        assert _display_to_celsius(5000 + int(30 / 0.5) * 50) == 30.0

    def test_none_returns_none(self):
        assert _display_to_celsius(None) is None

    def test_not_divide_by_ten(self):
        # The original bug: dividing by 10 gives 710 for raw=7100 instead of 21
        raw = 7100
        assert _display_to_celsius(raw) == 21.0
        assert _display_to_celsius(raw) != raw / 10


    def test_odd_step_rounds_toward_zero(self):
        # Table rows: 7125 → 21.0, 4975 → 0.0, 4025 → -9.5 (FGLair 3.4.3 temperatures.js)
        assert _display_to_celsius(7125) == 21.0
        assert _display_to_celsius(4975) == 0.0
        assert _display_to_celsius(4025) == -9.5

    def test_negative_values(self):
        assert _display_to_celsius(4000) == -10.0
        assert _display_to_celsius(4900) == -1.0

    def test_table_bounds(self):
        assert _display_to_celsius(9500) == 45.0
        assert _display_to_celsius(3999) is None
        assert _display_to_celsius(9501) is None
        assert _display_to_celsius(0) is None
        assert _display_to_celsius(65535) is None


class TestDeviceType:
    def test_fgl_models(self):
        assert _device_type("AP-WA1E") == "fgl"
        assert _device_type("AP-WC2E") == "fgl"
        assert _device_type("AP-WD1E") == "fgl"
        assert _device_type("AP-WF2E") == "fgl"

    def test_fglb_models(self):
        assert _device_type("AP-WB1E") == "fglb"
        assert _device_type("AP-WB2E") == "fglb"

    def test_generic_ac(self):
        assert _device_type("AEH-W4B1") == "ac"
        assert _device_type("unknown") == "ac"
        assert _device_type("") == "ac"

    def test_dev_suffix_is_stripped(self):
        # FGLair template_types.js strips "-dev" from development firmware models
        assert _device_type("AP-WD1E-dev") == "fgl"
        assert _device_type("AP-WB2E-dev") == "fglb"

    def test_none_model(self):
        assert _device_type(None) == "ac"

    def test_fgl_does_not_match_fglb_pattern(self):
        # AP-WB should be fglb, not fgl
        assert _device_type("AP-WB1E") != "fgl"
