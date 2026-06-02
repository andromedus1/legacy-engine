"""Unit tests for viz/theme.py — pure, no vl_convert dependency.

Covers all four strip_and_inject / THEME acceptance criteria from the feature spec.
"""

from __future__ import annotations

import copy

import pytest

from legacy_engine.viz.theme import CATEGORICAL, THEME, strip_and_inject


class TestStripAndInject:
    def test_injects_screen_theme_by_default(self, make_vl_spec):
        spec = make_vl_spec()
        result = strip_and_inject(spec)
        assert result["config"] == THEME["screen"]

    def test_replaces_conflicting_top_level_config(self, make_vl_spec):
        spec = make_vl_spec(config={"x": 1, "background": "white"})
        result = strip_and_inject(spec)
        # old config is gone, canonical theme injected
        assert result["config"] == THEME["screen"]
        assert "x" not in result["config"]

    def test_input_dict_not_mutated(self, make_vl_spec):
        spec = make_vl_spec(config={"x": 1})
        original = copy.deepcopy(spec)
        strip_and_inject(spec)
        assert spec == original, "strip_and_inject must not mutate the input spec"

    def test_other_top_level_keys_preserved(self, make_vl_spec):
        spec = make_vl_spec()
        result = strip_and_inject(spec)
        assert result["mark"] == "bar"
        assert result["encoding"] == spec["encoding"]
        assert result["data"] == spec["data"]

    def test_variant_print_injected_correctly(self, make_vl_spec):
        spec = make_vl_spec()
        result = strip_and_inject(spec, variant="print")
        assert result["config"] == THEME["print"]

    def test_unknown_variant_raises_key_error(self, make_vl_spec):
        spec = make_vl_spec()
        with pytest.raises(KeyError):
            strip_and_inject(spec, variant="bogus")


class TestThemeInvariants:
    @pytest.mark.parametrize("variant", ["screen", "print"])
    def test_dark_background_both_variants(self, variant):
        assert THEME[variant]["background"] == "#15181C", (
            f"Both variants must use dark bg #15181C, got {THEME[variant]['background']!r}"
        )

    @pytest.mark.parametrize("variant", ["screen", "print"])
    def test_no_black_in_categorical_palette(self, variant):
        palette = THEME[variant]["range"]["category"]
        assert "#000000" not in palette, (
            f"#000000 must not appear in the categorical palette for variant {variant!r}"
        )

    @pytest.mark.parametrize("variant", ["screen", "print"])
    def test_categorical_palette_length_8(self, variant):
        palette = THEME[variant]["range"]["category"]
        assert len(palette) == 8, (
            f"Categorical palette must have 8 entries, got {len(palette)}"
        )

    def test_print_title_font_size_greater_than_screen(self):
        screen_size = THEME["screen"]["title"]["fontSize"]
        print_size = THEME["print"]["title"]["fontSize"]
        assert print_size > screen_size, (
            f"print title fontSize ({print_size}) must be > screen ({screen_size})"
        )

    def test_print_label_font_size_greater_than_screen(self):
        screen_size = THEME["screen"]["axis"]["labelFontSize"]
        print_size = THEME["print"]["axis"]["labelFontSize"]
        assert print_size > screen_size, (
            f"print label fontSize ({print_size}) must be > screen ({screen_size})"
        )

    @pytest.mark.parametrize("variant", ["screen", "print"])
    def test_neither_variant_is_white_or_transparent(self, variant):
        bg = THEME[variant]["background"]
        assert bg not in ("white", "#ffffff", "#FFFFFF", "transparent", ""), (
            f"variant {variant!r} must not use white or transparent background, got {bg!r}"
        )

    @pytest.mark.parametrize("variant", ["screen", "print"])
    def test_diverging_scale_is_redyellowgreen(self, variant):
        diverging = THEME[variant]["range"]["diverging"]
        assert diverging == "redyellowgreen"


class TestCategoricalModuleConstant:
    def test_categorical_length(self):
        assert len(CATEGORICAL) == 8

    def test_no_black_in_categorical(self):
        assert "#000000" not in CATEGORICAL

    def test_light_tone_replacement_present(self):
        # The swap for #000000 should be a light tone (near-white/light-grey)
        assert "#E6E6E6" in CATEGORICAL
