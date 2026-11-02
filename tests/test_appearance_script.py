"""Execute the real appearance asset; this is not a browser/CSS engine.

Node is a development-test prerequisite, never a production server dependency.
The harness supplies observable DOM/storage APIs, not appearance decisions.
"""

import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "static" / "js" / "appearance.js"
HARNESS = Path(__file__).with_name("appearance_harness.cjs")
KEY = "tripplanner.appearance"
MODES = ("system", "light", "dark")
APPEARANCE_NODES = {"appearance", "appearance-control", "appearance-fallback", "appearance-status"}


def run_javascript(options=None, *, script=SCRIPT):
    """Fail within a test, not import/fixture discovery, if runtime/asset is absent."""
    assert script.is_file(), "Phase 7 requires the actual static/js/appearance.js asset."
    configured = os.environ.get("TRIPPLANNER_NODE")
    node = configured or shutil.which("node")
    assert node, "Install Node for development tests or set TRIPPLANNER_NODE to its executable."
    if configured:
        assert Path(configured).is_file(), "TRIPPLANNER_NODE must name an existing Node executable."
    result = subprocess.run(
        [str(node), str(HARNESS), str(script)],
        input=json.dumps(options or {}),
        text=True,
        capture_output=True,
        timeout=8,
        check=False,
        cwd=ROOT,
    )
    assert result.returncode == 0, f"Appearance harness failed: {result.stderr[-2000:]}"
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as error:
        pytest.fail(f"Appearance harness did not return JSON: {error}: {result.stdout[-1000:]}")


def state(result, stage="ready"):
    return next(item for item in result["snapshots"] if item["stage"] == stage)


def assert_no_errors(result):
    assert result["errors"] == [], "The appearance script must not throw during load or selection."


def writes(result):
    return [item for item in result["operations"] if item["kind"] == "storage-write"]


def assert_only_appearance_storage(result):
    for item in result["operations"]:
        assert item["kind"] not in {"storage-clear", "storage-remove"}
        if item["kind"] in {"storage-read", "storage-write"}:
            assert item["key"] == KEY
    for snapshot in result["snapshots"]:
        assert snapshot["values"]["tripplanner.draft"] == "unrelated draft sentinel"
        assert snapshot["values"]["other.preference"] == "leave this alone"


def unrelated_page_operations(result):
    """Allow fixed header feedback/readiness changes, never ordinary page writes."""
    violations = []
    forbidden = {"trip-field-read", "trip-field-write", "unrelated-query", "submit", "navigation", "focus", "blur", "scroll", "network", "html-mutation", "console-error"}
    for operation in result["operations"]:
        kind = operation["kind"]
        identifier = operation.get("id")
        if kind in forbidden:
            violations.append(operation)
        elif kind == "text" and identifier not in {"appearance-status", "appearance-fallback"}:
            violations.append(operation)
        elif kind in {"availability", "attribute", "class-mutation"} and identifier not in APPEARANCE_NODES | {"html"}:
            violations.append(operation)
        elif kind == "attribute" and identifier == "html" and (
            operation["name"] != "data-appearance" or operation["value"] not in MODES
        ):
            violations.append(operation)
    return violations


@pytest.mark.parametrize("remembered", MODES)
def test_remembered_mode_applies_before_header_exists(remembered):
    result = run_javascript({"stored": remembered, "domReady": False})
    assert_no_errors(result)
    early = state(result, "early")
    assert early["mode"] == remembered
    assert early["disabled"] and early["hidden"]
    assert early["bindings"] == 0
    assert writes(result) == []


@pytest.mark.parametrize("remembered", MODES)
@pytest.mark.parametrize("ready_state", ["loading", "interactive", "complete"])
def test_binding_handles_document_lifecycle_and_syncs_selector(remembered, ready_state):
    result = run_javascript({"stored": remembered, "readyState": ready_state})
    assert_no_errors(result)
    ready = state(result)
    assert ready["mode"] == ready["selected"] == remembered
    assert ready["disabled"] is False and ready["hidden"] is False
    assert ready["fallbackHidden"] is True
    assert ready["bindings"] == 1, "Bind one change handler, not competing persistence handlers."
    assert ready["status"] == "", "Do not announce persistence on startup."
    assert writes(result) == []


@pytest.mark.parametrize("remembered", [None, "", "Dark", "LIGHT", " dark ", " system", "device", "null", "undefined", "{}", "[object Object]", "<img src=x onerror=alert(1)>", '\" onmouseover=\"alert(1)', "light; background:red"])
def test_unrecognized_storage_is_system_without_sanitizing_or_writing_back(remembered):
    result = run_javascript({"stored": remembered})
    assert_no_errors(result)
    assert state(result, "early")["mode"] == "system"
    assert state(result)["selected"] == "system"
    assert writes(result) == []
    assert_only_appearance_storage(result)
    attributes = [op for op in result["operations"] if op["kind"] == "attribute" and op["id"] == "html"]
    assert attributes and all(op["name"] == "data-appearance" and op["value"] == "system" for op in attributes)
    classes = [op for op in result["operations"] if op["kind"] == "class-mutation"]
    baseline = run_javascript()
    assert_no_errors(baseline)
    assert classes == [op for op in baseline["operations"] if op["kind"] == "class-mutation"], "Invalid stored text must not become CSS classes; fixed readiness classes are allowed."


def test_missing_key_is_not_created_on_visit():
    result = run_javascript()
    assert_no_errors(result)
    assert state(result)["mode"] == "system"
    assert KEY not in state(result)["values"]
    assert writes(result) == []


@pytest.mark.parametrize("remembered", [None, *MODES])
@pytest.mark.parametrize("selected", MODES)
def test_explicit_selection_applies_and_persists_exact_enum(remembered, selected):
    result = run_javascript({"stored": remembered, "steps": [{"select": selected}]})
    assert_no_errors(result)
    changed = state(result, "step-0")
    assert changed["mode"] == changed["selected"] == selected
    assert changed["values"][KEY] == selected
    assert writes(result) == [{"kind": "storage-write", "key": KEY, "value": selected, "failed": False}]
    assert_only_appearance_storage(result)


def test_repeated_selections_keep_last_choice_and_are_the_only_writes():
    result = run_javascript({"steps": [{"select": "dark"}, {"select": "light"}, {"select": "system"}]})
    assert_no_errors(result)
    assert [item["value"] for item in writes(result)] == ["dark", "light", "system"]
    assert state(result, "step-2")["values"][KEY] == "system"
    assert_only_appearance_storage(result)


@pytest.mark.parametrize("fault", ["getterThrows", "readThrows"])
def test_storage_read_fault_uses_system_without_disabling_control_or_writing(fault):
    result = run_javascript({"stored": "dark", fault: True})
    assert_no_errors(result)
    ready = state(result)
    assert ready["mode"] == ready["selected"] == "system"
    assert ready["disabled"] is False and ready["hidden"] is False
    assert "PRIVATE" not in ready["status"]
    assert writes(result) == []


@pytest.mark.parametrize("fault", ["getter", "write"])
@pytest.mark.parametrize("selected", MODES)
def test_write_failure_keeps_current_selection_and_honest_feedback(fault, selected):
    result = run_javascript({"stored": "light", "steps": [{"fault": {fault: True}, "select": selected}]})
    assert_no_errors(result)
    changed = state(result, "step-0")
    assert changed["mode"] == changed["selected"] == selected
    assert changed["values"][KEY] == "light"
    assert changed["disabled"] is False
    message = changed["status"].lower()
    assert message and "page" in message and any(term in message for term in ["remember", "persist", "save"])
    assert any(term in message for term in ["could not", "couldn't", "cannot", "can't", "unable"])
    assert "private" not in message and "exception" not in message
    assert "saved successfully" not in message


@pytest.mark.parametrize("initial_fault", ["getterThrows", "readThrows", "writeThrows"])
def test_later_successful_write_recovers_independently_of_initial_read_fault(initial_fault):
    result = run_javascript({
        initial_fault: True,
        "steps": [
            {"fault": {"write": True}, "select": "dark"},
            {"fault": {"getter": False, "read": False, "write": False}, "select": "light"},
        ],
    })
    assert_no_errors(result)
    assert state(result, "step-0")["status"]
    recovered = state(result, "step-1")
    assert recovered["mode"] == recovered["selected"] == "light"
    assert recovered["values"][KEY] == "light"
    assert not any(term in recovered["status"].lower() for term in ["could not", "couldn't", "cannot", "can't", "unable", "only this page", "this page only"])


@pytest.mark.parametrize("selected", ["", "Dark", " dark ", "unexpected", '<img onerror="alert(1)">'])
def test_unknown_event_value_never_reaches_root_or_storage(selected):
    result = run_javascript({"stored": "light", "steps": [{"select": selected}]})
    assert_no_errors(result)
    assert state(result, "step-0")["mode"] in MODES
    assert state(result, "step-0")["selected"] in MODES
    for operation in writes(result):
        assert operation["value"] in MODES
    for operation in result["operations"]:
        if operation["kind"] == "attribute" and operation["id"] == "html":
            assert operation["value"] in MODES


@pytest.mark.parametrize("missing", [["appearance"], ["appearance-control"], ["appearance-fallback"], ["appearance-status"], ["appearance-fallback", "appearance-status"], ["appearance", "appearance-control", "appearance-fallback", "appearance-status"]])
def test_missing_optional_header_nodes_do_not_break_page_execution(missing):
    result = run_javascript({"stored": "dark", "missing": missing, "steps": [{"select": "light"}]})
    assert_no_errors(result)
    assert state(result, "early")["mode"] == "dark"
    assert state(result, "step-0")["mode"] in MODES
    if state(result)["bindings"] == 0:
        assert state(result)["disabled"], "A control with no handler must remain unavailable."


def test_control_only_becomes_available_after_change_handler_is_bound():
    result = run_javascript()
    assert_no_errors(result)
    availability = [op for op in result["operations"] if op["kind"] == "availability" and op["id"] in {"appearance", "appearance-control"} and op["value"] is False]
    assert {op["id"] for op in availability} == {"appearance", "appearance-control"}
    assert all(op["bindings"] >= 1 for op in availability)


def test_theme_does_not_read_or_change_trip_fields_or_trigger_page_actions():
    result = run_javascript({"stored": "dark", "steps": [{"select": "light"}, {"select": "system"}, {"fault": {"write": True}, "select": "dark"}]})
    assert_no_errors(result)
    assert unrelated_page_operations(result) == []
    assert_only_appearance_storage(result)
    assert not any(op["kind"] == "window-listener" and op["type"] == "storage" for op in result["operations"]), "Live cross-tab synchronization is outside this increment."


def test_harness_executes_the_supplied_file_instead_of_implementing_theme(tmp_path):
    probe = tmp_path / "probe.js"
    probe.write_text('document.documentElement.setAttribute("data-proof", "actual script executed");', encoding="utf-8")
    result = run_javascript(script=probe)
    assert_no_errors(result)
    assert state(result)["mode"] is None, "The harness must not implement default or theme decisions."
    assert state(result)["disabled"] and state(result)["hidden"]
    assert {"kind": "attribute", "id": "html", "name": "data-proof", "value": "actual script executed"} in result["operations"]


def test_harness_reflects_initial_and_changed_boolean_attributes(tmp_path):
    probe = tmp_path / "boolean-probe.js"
    probe.write_text('''
const control = document.getElementById("appearance");
const wrapper = document.getElementById("appearance-control");
if (!control.disabled || !control.hasAttribute("disabled")) throw new Error("initial disabled mismatch");
if (!wrapper.hidden || !wrapper.hasAttribute("hidden")) throw new Error("initial hidden mismatch");
control.disabled = false;
wrapper.hidden = false;
if (control.hasAttribute("disabled") || wrapper.hasAttribute("hidden")) throw new Error("property removal mismatch");
control.setAttribute("disabled", "");
wrapper.setAttribute("hidden", "");
if (!control.disabled || !wrapper.hidden) throw new Error("attribute addition mismatch");
control.removeAttribute("disabled");
wrapper.removeAttribute("hidden");
if (control.disabled || wrapper.hidden) throw new Error("attribute removal mismatch");
control.disabled = true;
wrapper.hidden = true;
if (!control.hasAttribute("disabled") || !wrapper.hasAttribute("hidden")) throw new Error("property addition mismatch");
''', encoding="utf-8")
    result = run_javascript({"readyState": "complete"}, script=probe)
    assert_no_errors(result)


def test_harness_detects_body_text_attributes_and_navigation_mutations(tmp_path):
    probe = tmp_path / "page-mutation-probe.js"
    probe.write_text('''
document.body.textContent = "trip form lost";
document.body.setAttribute("data-unrelated", "changed");
document.body.hidden = true;
document.body.classList.add("unexpected");
window.location = "/other-page";
window.location.href = "/another-page";
document.location = "/third-page";
''', encoding="utf-8")
    result = run_javascript(script=probe)
    assert_no_errors(result)
    violations = unrelated_page_operations(result)
    assert {operation["kind"] for operation in violations} == {"text", "attribute", "availability", "class-mutation", "navigation"}
    assert len([operation for operation in violations if operation["kind"] == "navigation"]) == 3
    assert len(violations) == 7


def test_harness_separates_early_execution_from_dom_ready_and_records_premature_enable(tmp_path):
    probe = tmp_path / "lifecycle-probe.js"
    probe.write_text('''
if (document.getElementById("appearance") !== null) throw new Error("Header arrived too soon");
document.documentElement.setAttribute("data-proof", "early");
document.addEventListener("DOMContentLoaded", function () {
  const control = document.getElementById("appearance");
  control.disabled = false;
  control.addEventListener("change", function () { document.documentElement.setAttribute("data-proof", "changed"); });
});
''', encoding="utf-8")
    result = run_javascript({"steps": [{"select": "dark"}]}, script=probe)
    assert_no_errors(result)
    early_ops = result["operations"][:state(result, "early")["operations"]]
    assert any(op.get("value") == "early" for op in early_ops)
    assert not any(op["kind"] == "listener" for op in early_ops)
    enabled = next(op for op in result["operations"] if op["kind"] == "availability")
    assert enabled["bindings"] == 0, "The harness must expose premature control enabling."
    assert any(op.get("value") == "changed" for op in result["operations"])


@pytest.mark.parametrize("fault", ["getterThrows", "readThrows", "writeThrows"])
def test_harness_exposes_uncaught_storage_faults_without_swallowing_them(tmp_path, fault):
    probe = tmp_path / "fault-probe.js"
    operation = 'window.localStorage.setItem("tripplanner.appearance", "dark")' if fault == "writeThrows" else 'window.localStorage.getItem("tripplanner.appearance")'
    probe.write_text(operation, encoding="utf-8")
    result = run_javascript({fault: True}, script=probe)
    assert len(result["errors"]) == 1
    assert "PRIVATE" in result["errors"][0]["message"]
    assert KEY not in state(result)["values"]


def test_harness_bounds_script_and_callback_execution(tmp_path):
    probe = tmp_path / "loop-probe.js"
    probe.write_text('document.addEventListener("DOMContentLoaded", function () { while (true) {} });', encoding="utf-8")
    result = run_javascript(script=probe)
    assert len(result["errors"]) == 1
    assert result["errors"][0]["stage"] == "DOMContentLoaded"
    assert "timed out" in result["errors"][0]["message"].lower()
