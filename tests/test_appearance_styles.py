"""Declared CSS contracts for Phase 7, not a browser or a CSS cascade engine.

The small reader understands the project's intentionally simple palette rules,
balanced blocks, declarations, and parent media conditions. It does NOT calculate
specificity, inheritance, transparency, native-control rendering, or layout.
Real computed colors and keyboard/mobile usability still require browser checks.

Semantic names below are a test-first implementation contract, not a copy of a
desired palette: contrast is calculated from actual production declarations.
"""

from dataclasses import dataclass
from pathlib import Path
import re

import pytest


STYLESHEET = Path(__file__).resolve().parents[1] / "static" / "css" / "style.css"
ROLES = (
    "--page-bg", "--surface-bg", "--text", "--text-muted", "--accent-text",
    "--action-bg", "--action-text", "--action-hover-bg", "--control-bg",
    "--control-text", "--control-border", "--placeholder-text", "--focus-ring",
    "--selected-bg", "--selected-text", "--selected-border", "--notice-bg",
    "--notice-text", "--warning-bg", "--warning-text", "--error-bg",
    "--error-text", "--error-border", "--emphasis-bg", "--emphasis-text",
    "--emphasis-muted", "--line",
)


@dataclass
class CssRule:
    selectors: tuple[str, ...]
    declarations: dict[str, str]
    conditions: tuple[str, ...] = ()


def without_comments(css):
    """Remove comments while preserving comment-looking quoted strings."""
    output = []
    quote = None
    index = 0
    while index < len(css):
        char = css[index]
        if quote:
            output.append(char)
            if char == "\\" and index + 1 < len(css):
                index += 1
                output.append(css[index])
            elif char == quote:
                quote = None
        elif char in "\"'":
            quote = char
            output.append(char)
        elif css.startswith("/*", index):
            end = css.find("*/", index + 2)
            if end < 0:
                raise ValueError("Unterminated CSS comment")
            output.append(" ")
            index = end + 1
        else:
            output.append(char)
        index += 1
    if quote:
        raise ValueError("Unterminated CSS string")
    return "".join(output)


def split_outside(value, separator):
    """Split selector/declaration lists outside quotes and parentheses."""
    pieces = []
    start = 0
    depth = 0
    quote = None
    escaped = False
    for index, char in enumerate(value):
        if escaped:
            escaped = False
        elif quote:
            if char == "\\":
                escaped = True
            elif char == quote:
                quote = None
        elif char in "\"'":
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth < 0:
                raise ValueError("Unbalanced CSS parentheses")
        elif char == separator and depth == 0:
            pieces.append(value[start:index].strip())
            start = index + 1
    if quote or depth:
        raise ValueError("Unbalanced CSS declaration or selector")
    pieces.append(value[start:].strip())
    return pieces


def read_rules(css):
    """Read flat rules with their enclosing @media contexts, recursively."""
    css = without_comments(css)

    def parse(source, parents=()):
        rules = []
        cursor = 0
        while source[cursor:].strip():
            opening = source.find("{", cursor)
            if opening < 0:
                raise ValueError("Expected a CSS rule block")
            header = source[cursor:opening].strip()
            if not header or "}" in header:
                raise ValueError("Malformed CSS selector/header")
            depth = 1
            quote = None
            escaped = False
            closing = opening + 1
            while closing < len(source) and depth:
                char = source[closing]
                if escaped:
                    escaped = False
                elif quote:
                    if char == "\\":
                        escaped = True
                    elif char == quote:
                        quote = None
                elif char in "\"'":
                    quote = char
                elif char == "{":
                    depth += 1
                elif char == "}":
                    depth -= 1
                closing += 1
            if depth:
                raise ValueError("Unbalanced CSS braces")
            body = source[opening + 1:closing - 1]
            if header.startswith("@media"):
                rules.extend(parse(body, parents + (header,)))
            else:
                declarations = {}
                for entry in split_outside(body, ";"):
                    if not entry:
                        continue
                    property_name, colon, value = entry.partition(":")
                    if not colon or not property_name.strip() or not value.strip():
                        raise ValueError(f"Malformed CSS declaration: {entry!r}")
                    declarations[property_name.strip()] = value.strip()
                rules.append(CssRule(
                    tuple(split_outside(header, ",")), declarations, parents,
                ))
            cursor = closing
        return rules

    return parse(css)


def normalized_selector(selector):
    selector = re.sub(r"(['\"])(system|light|dark)\1", r"\2", selector)
    return re.sub(r"\s+", "", selector)


def automatic_root(selector):
    # Whitespace between the root and :not(), or between two :not() clauses,
    # is a descendant combinator. Never erase it before verifying the grammar.
    selector = re.sub(r"(['\"])(system|light|dark)\1", r"\2", selector.strip())
    if not re.fullmatch(r"(?::root|html)(?::not\([^()]*\))+", selector):
        return False
    negations = re.findall(r":not\(([^()]*)\)", selector)
    clauses = []
    for negation in negations:
        branches = negation.split(",")
        values = []
        for branch in branches:
            attribute = re.fullmatch(r"\[\s*data-appearance\s*=\s*(light|dark)\s*\]", branch.strip())
            if not attribute:
                return False
            values.append(attribute.group(1))
        clauses.append(values)
    expected = {"light", "dark"}
    if len(negations) == 2:
        # Each exclusion is exactly one root attribute, not a descendant,
        # unrelated pseudo-class, extra branch, or :not(*).
        return all(len(clause) == 1 for clause in clauses) and {clause[0] for clause in clauses} == expected
    if len(negations) == 1:
        return len(clauses[0]) == 2 and set(clauses[0]) == expected
    return False


def positive_dark_condition(condition):
    """Recognize the supported simple, positive device-dark media grammar."""
    return bool(re.fullmatch(
        r"@media\s+(?:(?:only\s+)?(?:screen|all)\s+and\s+)?"
        r"\(\s*prefers-color-scheme\s*:\s*dark\s*\)",
        condition.strip(), flags=re.I,
    ))


def device_dark_context(conditions):
    color_conditions = [condition for condition in conditions if
                        "prefers-color-scheme" in condition.lower()]
    return bool(color_conditions) and all(positive_dark_condition(condition) for condition in color_conditions)


def hidden_appearance_selector(selector):
    """Only positive hidden guards for actual appearance nodes (or all nodes)."""
    # A space before [hidden] would target a descendant, not the known node.
    selector = selector.strip()
    known_nodes = {
        "#appearance-control", ".appearance-control", "[data-appearance-control]",
        "#appearance-fallback", ".appearance-fallback",
        "#appearance-status", ".appearance-status",
    }
    return selector == "[hidden]" or selector in {f"{node}[hidden]" for node in known_nodes}


def palette(rules, mode):
    """Merge only a mode's explicit root declarations, not an entire cascade."""
    result = {}
    for rule in rules:
        if mode == "light":
            matched = not rule.conditions and any(
                normalized_selector(selector) in {":root", "html"}
                for selector in rule.selectors
            )
        elif mode == "dark":
            matched = not rule.conditions and any(
                normalized_selector(selector) in {
                    ':root[data-appearance=dark]', 'html[data-appearance=dark]',
                } for selector in rule.selectors
            )
        else:
            dark_device = device_dark_context(rule.conditions)
            matched = dark_device and any(automatic_root(selector) for selector in rule.selectors)
        if matched:
            result.update(rule.declarations)
    assert result, f"Missing {mode} root palette in the production stylesheet"
    return result


def color_tokens(rules, mode):
    """Root aliases remain available when a mode overrides semantic roles."""
    tokens = palette(rules, "light")
    if mode != "light":
        tokens.update(palette(rules, mode))
    return tokens


VARIABLE = re.compile(r"var\(\s*(--[\w-]+)\s*\)")


def resolve_color(value, tokens, visited=()):
    """Resolve simple aliases and opaque sRGB hex/rgb colors only."""
    value = re.sub(r"\s*!important\s*$", "", value).strip()
    variable = VARIABLE.fullmatch(value)
    if variable:
        name = variable.group(1)
        if name in visited:
            raise ValueError(f"Cyclic CSS color alias: {name}")
        if name not in tokens:
            raise ValueError(f"Missing CSS color alias: {name}")
        return resolve_color(tokens[name], tokens, visited + (name,))
    named = {"black": "#000000", "white": "#ffffff"}
    value = named.get(value.lower(), value)
    if re.fullmatch(r"#[\da-fA-F]{3}", value):
        value = "#" + "".join(char * 2 for char in value[1:])
    if re.fullmatch(r"#[\da-fA-F]{6}", value):
        return tuple(int(value[index:index + 2], 16) / 255 for index in (1, 3, 5))
    match = re.fullmatch(r"rgba?\(([^()]*)\)", value, flags=re.I)
    if match:
        parts = re.split(r"[,\s/]+", match.group(1).strip())
        if len(parts) == 4:
            if float(parts.pop()) != 1:
                raise ValueError("Transparent colors require a real rendered-background audit")
        if len(parts) == 3:
            channels = tuple(
                float(part[:-1]) / 100 if part.endswith("%") else float(part) / 255
                for part in parts
            )
            if all(0 <= channel <= 1 for channel in channels):
                return channels
    raise ValueError(f"Expected an opaque sRGB palette color, got {value!r}")


def contrast(first, second):
    def luminance(channels):
        linear = [
            channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4
            for channel in channels
        ]
        return sum(channel * weight for channel, weight in zip(linear, (0.2126, 0.7152, 0.0722)))

    values = sorted((luminance(first), luminance(second)))
    return (values[1] + 0.05) / (values[0] + 0.05)


def declared_properties(rules, selector):
    properties = {}
    for rule in rules:
        if not rule.conditions and any(
            normalized_selector(candidate) == normalized_selector(selector)
            for candidate in rule.selectors
        ):
            properties.update(rule.declarations)
    return properties


def references_role(value, role, tokens, visited=()):
    for name in VARIABLE.findall(value):
        if name == role:
            return True
        if name not in visited and references_role(tokens.get(name, ""), role, tokens, visited + (name,)):
            return True
    return False


@pytest.fixture
def css_rules():
    # The existing file is present. Missing feature assertions belong in tests,
    # never in fixture setup where they would be reported as setup errors.
    return read_rules(STYLESHEET.read_text(encoding="utf-8"))


def test_css_reader_preserves_quotes_comments_and_nested_media():
    rules = read_rules('''
        /* A fake :root { --ignored: red; } */
        :root { --a: #fff; --a: #000; content: "/* not a comment */; }"; }
        @media (prefers-color-scheme: dark) {
          @media (min-width: 1px) {
            html:not([data-appearance="light"]):not([data-appearance="dark"]) {
              --a: rgb(100%, 100%, 100%); color-scheme: dark;
            }
          }
        }
    ''')
    assert len(rules) == 2
    assert rules[0].declarations == {"--a": "#000", "content": '"/* not a comment */; }"'}
    assert rules[0].conditions == ()
    assert rules[1].conditions == (
        "@media (prefers-color-scheme: dark)", "@media (min-width: 1px)",
    )
    assert palette(rules, "automatic")["--a"] == "rgb(100%, 100%, 100%)"


def test_selector_reader_does_not_split_function_or_quoted_commas():
    assert split_outside('input:has([data-value="a,b"]), :root:not(.a, .b)', ",") == [
        'input:has([data-value="a,b"])', ':root:not(.a, .b)',
    ]


@pytest.mark.parametrize("css", ["/* unfinished", "body { color: red;", "body { missing; }"])
def test_css_reader_reports_malformed_input(css):
    with pytest.raises(ValueError):
        read_rules(css)


@pytest.mark.parametrize("selector, expected", [
    (':root:not([data-appearance="light"]):not([data-appearance="dark"])', True),
    ("html:not([data-appearance=light],[data-appearance=dark])", True),
    ("html:not([data-appearance=dark]):not([data-appearance=light])", True),
    (":root:not([data-appearance='dark'], [data-appearance='light'])", True),
    (":root:not( [data-appearance = 'dark'] , [data-appearance = 'light'] )", True),
    (':root:not([data-appearance="light"])', False),
    (':root[data-appearance="dark"]', False),
    ('.card:not([data-appearance=light]):not([data-appearance=dark])', False),
    ("html:not([data-appearance=light] .child):not([data-appearance=dark] .child)", False),
    ("html:not([data-appearance=light],[data-appearance=dark],*)", False),
    ("html:not([data-appearance=light]):not([data-appearance=dark]):not(*)", False),
    ("html:not([data-appearance=light]):not([data-appearance=dark]):not(.unrelated)", False),
    ("html:not([data-appearance=light]):not([data-appearance=dark], .unrelated)", False),
    ("html:not([data-appearance=light]):not([data-appearance=light])", False),
    ("html :not([data-appearance=light]):not([data-appearance=dark])", False),
    ("html:not([data-appearance=light]) :not([data-appearance=dark])", False),
])
def test_automatic_selector_reader_requires_root_and_both_manual_exclusions(selector, expected):
    assert automatic_root(selector) is expected


@pytest.mark.parametrize("condition, expected", [
    ("@media (prefers-color-scheme: dark)", True),
    ("@media screen and (prefers-color-scheme: dark)", True),
    ("@media only screen and (prefers-color-scheme: dark)", True),
    ("@media all and (prefers-color-scheme: dark)", True),
    ("@media not all and (prefers-color-scheme: dark)", False),
    ("@media not screen and (prefers-color-scheme: dark)", False),
    ("@media (prefers-color-scheme: light)", False),
    ("@media (prefers-color-scheme: dark), (prefers-color-scheme: light)", False),
    ("@media (prefers-color-scheme: dark) or (min-width: 1px)", False),
])
def test_device_media_reader_requires_a_supported_positive_dark_query(condition, expected):
    assert positive_dark_condition(condition) is expected
    rules = read_rules(f'''{condition} {{
        html:not([data-appearance=light]):not([data-appearance=dark]) {{ color-scheme: dark; }}
    }}''')
    if expected:
        assert palette(rules, "automatic")["color-scheme"] == "dark"
    else:
        with pytest.raises(AssertionError, match="Missing automatic root palette"):
            palette(rules, "automatic")


def test_nested_positive_query_cannot_hide_an_inverted_parent_device_condition():
    rules = read_rules('''@media not all and (prefers-color-scheme: dark) {
        @media (prefers-color-scheme: dark) {
            html:not([data-appearance=light]):not([data-appearance=dark]) { color-scheme: dark; }
        }
    }''')
    with pytest.raises(AssertionError, match="Missing automatic root palette"):
        palette(rules, "automatic")


@pytest.mark.parametrize("selector, expected", [
    ("[hidden]", True), ("#appearance-control[hidden]", True),
    (".appearance-control[hidden]", True), ("[data-appearance-control][hidden]", True),
    ("#appearance-fallback[hidden]", True), ("#appearance-status[hidden]", True),
    ("#appearance-control:not([hidden])", False),
    (".not-appearance[hidden]", False), (".appearance-control:not([hidden])", False),
    ("#appearance-fallback:not([hidden])", False),
    ("#appearance-control[hidden] .child", False), (".unrelated[hidden]", False),
    ("#appearance-control [hidden]", False), (".appearance-control [hidden]", False),
])
def test_hidden_selector_reader_requires_an_exact_positive_known_guard(selector, expected):
    assert hidden_appearance_selector(selector) is expected


@pytest.mark.parametrize("value, expected", [
    ("#fff", (1, 1, 1)), ("#000000", (0, 0, 0)),
    ("rgb(255, 0, 0)", (1, 0, 0)), ("rgb(0% 100% 0%)", (0, 1, 0)),
    ("rgba(0, 0, 255, 1)", (0, 0, 1)), ("white", (1, 1, 1)),
])
def test_color_reader_matches_independent_literals(value, expected):
    assert resolve_color(value, {}) == expected


def test_color_aliases_and_role_reader_follow_declared_aliases():
    tokens = {"--old-name": "var(--new-name)", "--new-name": "#fff"}
    assert resolve_color("var(--old-name)", tokens) == (1, 1, 1)
    assert references_role("1px solid var(--old-name)", "--new-name", tokens)
    assert not references_role("#fff", "--new-name", tokens)


@pytest.mark.parametrize("value, tokens", [
    ("var(--missing)", {}),
    ("var(--a)", {"--a": "var(--b)", "--b": "var(--a)"}),
    ("rgba(0,0,0,.5)", {}), ("rgb(999, 0, 0)", {}),
])
def test_color_reader_rejects_unresolved_cyclic_or_nonopaque_values(value, tokens):
    with pytest.raises(ValueError):
        resolve_color(value, tokens)


def test_contrast_arithmetic_uses_known_independent_endpoints_and_threshold():
    black = resolve_color("#000", {})
    white = resolve_color("#fff", {})
    assert contrast(black, white) == pytest.approx(21)
    assert contrast(white, black) == pytest.approx(21)
    assert contrast(white, white) == pytest.approx(1)
    assert contrast(resolve_color("#777", {}), white) == pytest.approx(4.478089, abs=0.000001)
    assert contrast(resolve_color("#777", {}), white) < 4.5


@pytest.mark.parametrize("mode", ["light", "dark", "automatic"])
def test_each_mode_declares_a_complete_semantic_palette(css_rules, mode):
    tokens = palette(css_rules, mode)
    missing = sorted(set(ROLES) - set(tokens))
    assert not missing, f"{mode} palette is missing semantic roles: {missing}"
    tokens = color_tokens(css_rules, mode)
    for name in ROLES:
        resolve_color(f"var({name})", tokens)


@pytest.mark.parametrize("mode, expected", [("light", "light"), ("dark", "dark"), ("automatic", "dark")])
def test_native_controls_receive_the_effective_color_scheme(css_rules, mode, expected):
    assert palette(css_rules, mode).get("color-scheme") == expected


def test_manual_and_device_dark_declarations_cannot_drift(css_rules):
    manual = palette(css_rules, "dark")
    automatic = palette(css_rules, "automatic")
    assert set(ROLES) <= manual.keys() and set(ROLES) <= automatic.keys()
    manual_tokens = color_tokens(css_rules, "dark")
    automatic_tokens = color_tokens(css_rules, "automatic")
    assert {name: resolve_color(f"var({name})", manual_tokens) for name in ROLES} == {
        name: resolve_color(f"var({name})", automatic_tokens) for name in ROLES
    }


def test_device_palette_rules_never_override_either_manual_mode(css_rules):
    device_rules = [rule for rule in css_rules if device_dark_context(rule.conditions)
                    and (set(ROLES) & rule.declarations.keys() or "color-scheme" in rule.declarations)]
    assert device_rules, "A script-independent device-dark palette is required"
    for rule in device_rules:
        for selector in rule.selectors:
            assert automatic_root(selector), (
                "Each device-dark root palette rule must exclude both manual "
                f"Light and manual Dark; got {selector!r}"
            )


def test_dark_is_a_deliberately_darker_palette_not_just_a_state_name(css_rules):
    light = color_tokens(css_rules, "light")
    dark = color_tokens(css_rules, "dark")
    assert "--page-bg" in light and "--page-bg" in dark
    light_color = resolve_color("var(--page-bg)", light)
    dark_color = resolve_color("var(--page-bg)", dark)
    assert all(dark_channel < light_channel for dark_channel, light_channel in zip(dark_color, light_color))
    assert contrast(light_color, dark_color) >= 4.5


TEXT_PAIRS = [
    ("--text", "--page-bg"), ("--text", "--surface-bg"),
    ("--text-muted", "--page-bg"), ("--text-muted", "--surface-bg"),
    ("--accent-text", "--page-bg"), ("--accent-text", "--surface-bg"),
    ("--action-text", "--action-bg"), ("--action-text", "--action-hover-bg"),
    ("--control-text", "--control-bg"), ("--placeholder-text", "--control-bg"),
    ("--selected-text", "--selected-bg"), ("--notice-text", "--notice-bg"),
    ("--warning-text", "--warning-bg"), ("--error-text", "--error-bg"),
    ("--error-text", "--surface-bg"), ("--emphasis-text", "--emphasis-bg"),
    ("--emphasis-muted", "--emphasis-bg"),
]
BOUNDARY_PAIRS = [
    ("--control-border", "--control-bg"), ("--control-border", "--surface-bg"),
    ("--selected-border", "--selected-bg"), ("--selected-border", "--surface-bg"),
    ("--error-border", "--control-bg"), ("--error-border", "--surface-bg"),
    ("--focus-ring", "--page-bg"), ("--focus-ring", "--surface-bg"),
    ("--focus-ring", "--control-bg"),
]


@pytest.mark.parametrize("mode", ["light", "dark"])
@pytest.mark.parametrize("foreground, background", TEXT_PAIRS)
def test_declared_ordinary_text_pairs_reach_4_5_to_1(css_rules, mode, foreground, background):
    tokens = color_tokens(css_rules, mode)
    assert foreground in tokens and background in tokens, f"Missing {mode} contrast roles {foreground}/{background}"
    ratio = contrast(resolve_color(f"var({foreground})", tokens), resolve_color(f"var({background})", tokens))
    assert ratio >= 4.5, f"{mode}: {foreground} on {background} is {ratio:.3f}:1; expected at least 4.5:1"


@pytest.mark.parametrize("mode", ["light", "dark"])
@pytest.mark.parametrize("foreground, background", BOUNDARY_PAIRS)
def test_declared_essential_boundaries_reach_3_to_1(css_rules, mode, foreground, background):
    tokens = color_tokens(css_rules, mode)
    assert foreground in tokens and background in tokens, f"Missing {mode} boundary roles {foreground}/{background}"
    ratio = contrast(resolve_color(f"var({foreground})", tokens), resolve_color(f"var({background})", tokens))
    assert ratio >= 3, f"{mode}: {foreground} against {background} is {ratio:.3f}:1; expected at least 3:1"


# Representative declared component-role connections. This guards against good
# tokens that are never used, while a later browser audit still checks actual
# inherited/overridden colors on every component and state.
COMPONENT_ROLES = [
    (":root", "background", "--page-bg"), (":root", "color", "--text"),
    (".button-primary", "background", "--action-bg"),
    (".button-primary", "color", "--action-text"),
    (".button-primary:hover", "background", "--action-hover-bg"),
    (".form-field input", "background", "--control-bg"),
    (".form-field select", "color", "--control-text"),
    (".form-field input", "border", "--control-border"),
    (".form-field input::placeholder", "color", "--placeholder-text"),
    (":focus-visible", "outline", "--focus-ring"),
    (".interest-option:has(input:checked)", "background", "--selected-bg"),
    (".interest-option:has(input:checked)", "color", "--selected-text"),
    (".interest-option:has(input:checked)", "border-color", "--selected-border"),
    (".family-option:has(input:checked)", "background", "--selected-bg"),
    (".flash-message", "background", "--notice-bg"),
    (".flash-message", "color", "--notice-text"),
    (".saved-local-disclosure", "background", "--notice-bg"),
    (".saved-local-disclosure", "color", "--notice-text"),
    (".itinerary-caution", "background", "--warning-bg"),
    (".itinerary-caution", "color", "--warning-text"),
    (".form-errors", "background", "--error-bg"),
    (".save-error", "color", "--error-text"),
    (".field-error", "color", "--error-text"),
    ('[aria-invalid="true"]', "border-color", "--error-border"),
    (".itinerary-cost-card", "background", "--emphasis-bg"),
    (".itinerary-cost-card", "color", "--emphasis-text"),
    (".itinerary-total-caption", "color", "--emphasis-muted"),
    (".example-place", "background", "--surface-bg"),
    (".saved-trip-card", "background", "--surface-bg"),
    (".idea-card", "background", "--surface-bg"),
]


@pytest.mark.parametrize("selector, property_name, role", COMPONENT_ROLES)
def test_representative_components_use_their_semantic_color_roles(css_rules, selector, property_name, role):
    declarations = declared_properties(css_rules, selector)
    assert property_name in declarations, f"Missing declared {selector} {property_name}"
    light = palette(css_rules, "light")
    assert references_role(declarations[property_name], role, light), (
        f"{selector} {property_name} must use {role} (directly or through an alias); "
        f"got {declarations[property_name]!r}"
    )


def test_hidden_appearance_controls_have_a_declared_display_none_guard(css_rules):
    guards = [
        rule for rule in css_rules if not rule.conditions and any(
            hidden_appearance_selector(selector)
            for selector in rule.selectors
        )
    ]
    assert any(re.fullmatch(r"none\s*(?:!important)?", rule.declarations.get("display", "")) for rule in guards), (
        "Respect initially hidden controls and initialized hidden fallback/status "
        "even when their ordinary layout uses flex/grid."
    )


def test_existing_reduced_motion_keeps_smooth_scroll_and_animations_disabled(css_rules):
    reduced = [rule for rule in css_rules if any(
        re.search(r"prefers-reduced-motion\s*:\s*reduce", condition) for condition in rule.conditions
    )]
    assert any("html" in rule.selectors and rule.declarations.get("scroll-behavior") == "auto" for rule in reduced)
    assert any(
        "*" in rule.selectors
        and re.fullmatch(r"(?:0(?:\.0+)?(?:s|ms)|0?\.0+1ms)\s*(?:!important)?", rule.declarations.get("transition-duration", ""))
        and re.fullmatch(r"(?:0(?:\.0+)?(?:s|ms)|0?\.0+1ms)\s*(?:!important)?", rule.declarations.get("animation-duration", ""))
        for rule in reduced
    )


def test_dark_mode_does_not_use_an_inversion_filter(css_rules):
    for rule in css_rules:
        for property_name in ("filter", "backdrop-filter"):
            assert not re.search(r"\binvert\s*\(", rule.declarations.get(property_name, ""), re.I), (
                "Dark mode needs a designed palette, not a blanket inversion filter."
            )


def test_theme_does_not_add_whole_page_color_flash_transitions(css_rules):
    for selector in (":root", "html", "body", "*"):
        declarations = declared_properties(css_rules, selector)
        transition = declarations.get("transition-property", declarations.get("transition", ""))
        assert not re.search(r"\b(?:all|color|background(?:-color)?|color-scheme)\b", transition)


def test_filled_button_does_not_animate_background_during_theme_changes(css_rules):
    # Browser regression: instant Dark text over a still-transitioning Light
    # fill briefly measured 1.776:1. Movement may animate; palette changes may not.
    declarations = declared_properties(css_rules, ".button")
    transition = declarations.get("transition-property", declarations.get("transition", ""))
    assert not re.search(r"\b(?:all|color|background(?:-color)?)\b", transition), (
        "Filled button colors must change together when appearance changes; "
        "background-color interpolation can create unreadable intermediate fills."
    )
