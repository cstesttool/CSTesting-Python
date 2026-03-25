"""
HTML report generation. Writes to report/ folder.
"""
import html
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

from .types import RunResult


def _escape(s: str) -> str:
    return html.escape(s, quote=True)


def _format_duration(ms: Optional[float]) -> str:
    if ms is None or ms < 0:
        return "—"
    if ms < 1000:
        return f"{round(ms)}ms"
    return f"{ms / 1000:.1f}s"


def _format_total_time(ms: float) -> str:
    if ms < 60000:
        return f"{ms / 1000:.1f}s"
    m = int(ms // 60000)
    s = int((ms % 60000) / 1000)
    return f"{m}m {s}s"


def _test_search_text(row: Dict) -> str:
    parts = [
        row.get("file") or "",
        row.get("suite", ""),
        row.get("test", ""),
        * (row.get("tags") or []),
    ]
    return " ".join(parts).lower()


def _build_test_row_html(row: Dict, index: int) -> str:
    status = row.get("status", "pass")
    duration_str = _format_duration(row.get("duration"))
    status_label = "Passed" if status == "pass" else ("Failed" if status == "fail" else "Skipped")
    search_text = _escape(_test_search_text(row))
    description = f"{_escape(row.get('suite', ''))} {'›' if row.get('suite') and row.get('test') else ''} {_escape(row.get('test', ''))}".strip()

    steps = row.get("steps") or []
    failed_idx = row.get("failed_step_index")
    steps_html_parts = []
    if steps:
        for i, s in enumerate(steps):
            is_failed = failed_idx is not None and i == failed_idx
            is_skipped = failed_idx is not None and i > failed_idx
            step_status = "failed" if is_failed else ("skipped" if is_skipped else "passed")
            step_icon = "✗" if is_failed else ("−" if is_skipped else "✓")
            skipped_label = ' <span class="report-step-skipped-label">(skipped)</span>' if is_skipped else ""
            steps_html_parts.append(
                f'<div class="report-step-row">'
                f'<span class="report-step-icon report-step-{step_status}">{step_icon}</span>'
                f'<span class="report-step-index">{i + 1}</span>'
                f'<span class="report-step-title">{_escape(s)}{skipped_label}</span>'
                f"</div>"
            )
        steps_html = f'<div class="report-section"><div class="report-section-title">Steps</div><div class="report-steps-list">{"".join(steps_html_parts)}</div></div>'
    else:
        steps_html = '<div class="report-section"><div class="report-section-title">Steps</div><p class="report-no-steps">No steps recorded. Use <code>step(\'name\')</code> in your test to record steps.</p></div>'

    error = row.get("error")
    error_block = ""
    if error:
        err_msg = _escape(getattr(error, "message", None) or (error.args[0] if error.args else str(error)))
        err_stack = ""
        if hasattr(error, "__traceback__") and error.__traceback__:
            import traceback
            err_stack = _escape("".join(traceback.format_tb(error.__traceback__)))
        error_block = f'<div class="report-section report-error-section"><div class="report-section-title">Error</div><div class="report-error-content"><pre class="report-error-message">{err_msg}</pre><pre class="report-error-stack">{err_stack}</pre><button type="button" class="report-copy-btn" data-copy="error">Copy</button></div></div>'

    tags = row.get("tags") or []
    tags_html = (
        '<div class="report-tags-row">'
        + "".join(f'<span class="report-tag">{_escape(t)}</span>' for t in tags)
        + "</div>"
    ) if tags else ""
    file_line = f'<div class="report-source">{_escape(row.get("file", ""))}</div>' if row.get("file") else ""

    return f'''
    <div class="report-test-row report-test-{status}" data-expanded="false" data-search="{search_text}" data-index="{index}">
      <span class="report-dot {status}"></span>
      <div class="report-test-body">
        <div class="report-test-header" role="button" tabindex="0" aria-expanded="false">
          <span class="report-test-name">{description}</span>
          <span class="report-test-meta">
            <span class="report-test-duration" title="Duration">{duration_str}</span>
            <span class="report-status-badge status-{status}">{status_label}</span>
            <span class="report-chevron">▶</span>
          </span>
        </div>
        {tags_html}
        {file_line}
        <div class="report-test-details">
          {steps_html}
          {error_block}
        </div>
      </div>
    </div>'''


def _build_file_group_html(file_key: str, file_label: str, tests: List[Dict], start_index: int) -> str:
    count = len(tests)
    passed = sum(1 for t in tests if t.get("status") == "pass")
    failed = sum(1 for t in tests if t.get("status") == "fail")
    skipped = sum(1 for t in tests if t.get("status") == "skip")
    tests_html = "".join(_build_test_row_html(t, start_index + i) for i, t in enumerate(tests))
    file_id = "file-" + _escape(file_key).replace(" ", "_").replace("/", "_").replace("\\", "_")
    group_search = _escape((file_key + " " + " ".join(_test_search_text(t) for t in tests)).lower())

    return f'''
  <div class="report-file-group" data-file="{_escape(file_key)}" data-search="{group_search}">
    <div class="report-file-header" role="button" tabindex="0" aria-expanded="true" data-target="{file_id}">
      <span class="report-file-chevron">▼</span>
      <span class="report-file-path">{_escape(file_label)}</span>
      <span class="report-file-count">{count} test{"s" if count != 1 else ""}</span>
      <span class="report-file-badges">
        {"<span class=\"report-file-badge pass\">✓ " + str(passed) + "</span>" if passed else ""}
        {"<span class=\"report-file-badge fail\">× " + str(failed) + "</span>" if failed else ""}
        {"<span class=\"report-file-badge skip\">⊘ " + str(skipped) + "</span>" if skipped else ""}
      </span>
    </div>
    <div id="{file_id}" class="report-file-tests">
      {tests_html}
    </div>
  </div>'''


def generate_html_report(result: RunResult) -> str:
    passed = result.passed
    failed = result.failed
    skipped = result.skipped
    total = result.total
    passed_tests = result.passed_tests or []
    skipped_tests = result.skipped_tests or []
    errors = result.errors or []

    all_tests: List[Dict] = []
    for t in passed_tests:
        all_tests.append({
            "suite": t.suite,
            "test": t.test,
            "status": "pass",
            "duration": t.duration,
            "steps": t.steps,
            "file": t.file,
            "tags": t.tags,
        })
    for e in errors:
        all_tests.append({
            "suite": e["suite"],
            "test": e["test"],
            "status": "fail",
            "duration": e.get("duration"),
            "steps": e.get("steps"),
            "error": e.get("error"),
            "failed_step_index": e.get("failed_step_index", e.get("failedStepIndex")),
            "file": e.get("file"),
            "tags": e.get("tags"),
        })
    for t in skipped_tests:
        all_tests.append({
            "suite": t.suite,
            "test": t.test,
            "status": "skip",
            "duration": t.duration or 0,
            "steps": t.steps,
            "file": t.file,
            "tags": t.tags,
        })

    by_file: Dict[str, List[Dict]] = {}
    for row in all_tests:
        key = row.get("file") or "(no file)"
        if key not in by_file:
            by_file[key] = []
        by_file[key].append(row)

    index = 0
    file_groups_html = ""
    for file_key in sorted(by_file.keys()):
        file_groups_html += _build_file_group_html(file_key, file_key, by_file[file_key], index)
        index += len(by_file[file_key])

    date_str = datetime.now().strftime("%m/%d/%Y, %I:%M:%S %p")
    total_time_str = _format_total_time(result.duration)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>CSTesting Report</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ font-family: system-ui, -apple-system, 'Segoe UI', sans-serif; margin: 0; padding: 0; background: #0f172a; color: #e2e8f0; line-height: 1.5; }}
    .report-top {{ display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 16px; padding: 16px 24px; background: #1e293b; border-bottom: 1px solid #334155; }}
    .report-search-wrap {{ flex: 1; min-width: 200px; max-width: 400px; }}
    .report-search-wrap input {{ width: 100%; padding: 10px 12px 10px 36px; border: 1px solid #475569; border-radius: 8px; background: #0f172a; color: #e2e8f0; font-size: 14px; }}
    .report-summary {{ display: flex; align-items: center; flex-wrap: wrap; gap: 16px; font-size: 14px; }}
    .report-summary-item.passed {{ color: #22c55e; }}
    .report-summary-item.failed {{ color: #ef4444; }}
    .report-summary-item.skipped {{ color: #eab308; }}
    .report-content {{ padding: 16px 24px 32px; }}
    .report-file-group {{ margin-bottom: 8px; border-radius: 8px; background: #1e293b; overflow: hidden; border: 1px solid #334155; }}
    .report-file-header {{ display: flex; align-items: center; gap: 10px; padding: 12px 16px; cursor: pointer; }}
    .report-file-header:hover {{ background: #334155; }}
    .report-file-group.collapsed .report-file-tests {{ display: none; }}
    .report-test-row {{ display: flex; align-items: flex-start; gap: 10px; margin-top: 8px; border-radius: 6px; background: #0f172a; border: 1px solid #334155; }}
    .report-test-row.hidden {{ display: none !important; }}
    .report-file-group.hidden {{ display: none !important; }}
    .report-test-header {{ display: flex; justify-content: space-between; align-items: center; padding: 12px 14px; cursor: pointer; }}
    .report-test-row.expanded .report-test-details {{ max-height: 3000px; }}
    .report-test-details {{ max-height: 0; overflow: hidden; transition: max-height 0.25s ease-out; }}
    .report-dot.pass {{ background: #22c55e; }}
    .report-dot.fail {{ background: #ef4444; }}
    .report-dot.skip {{ background: #eab308; }}
    .report-status-badge.status-pass {{ background: rgba(34, 197, 94, 0.2); color: #22c55e; }}
    .report-status-badge.status-fail {{ background: rgba(239, 68, 68, 0.2); color: #ef4444; }}
    .report-status-badge.status-skip {{ background: rgba(234, 179, 8, 0.2); color: #eab308; }}
    .report-step-row {{ display: flex; align-items: center; gap: 10px; padding: 10px 12px; font-size: 13px; border-bottom: 1px solid #1e293b; }}
    .report-error-section .report-error-content {{ border: 1px solid #7f1d1d; border-radius: 6px; background: rgba(127, 29, 29, 0.15); padding: 12px; }}
    .report-error-message {{ margin: 0; font-size: 13px; white-space: pre-wrap; color: #fca5a5; }}
  </style>
</head>
<body>
  <div class="report-top">
    <div class="report-search-wrap" style="position:relative">
      <span class="report-search-icon" aria-hidden="true">🔍</span>
      <input type="text" id="report-search" placeholder="Search by file name, test name, or tag..." autocomplete="off" />
    </div>
    <div class="report-summary-block">
      <div class="report-summary">
        <span class="report-summary-item">All {total}</span>
        <span class="report-summary-item passed">✓ Passed {passed}</span>
        <span class="report-summary-item failed">× Failed {failed}</span>
        <span class="report-summary-item skipped">Skipped {skipped}</span>
      </div>
      <div class="report-meta">{_escape(date_str)} · Total time: {total_time_str}</div>
    </div>
  </div>
  <div class="report-content">
    {file_groups_html or "<p class=\"report-empty-msg\">No tests to show.</p>"}
  </div>
  <script>
(function() {{
  var searchInput = document.getElementById('report-search');
  var fileGroups = document.querySelectorAll('.report-file-group');
  var testRows = document.querySelectorAll('.report-test-row');
  function onSearch() {{
    var q = (searchInput.value || '').trim().toLowerCase();
    if (!q) {{
      fileGroups.forEach(function(g) {{ g.classList.remove('hidden'); }});
      testRows.forEach(function(r) {{ r.classList.remove('hidden'); }});
      return;
    }}
    fileGroups.forEach(function(group) {{
      var groupSearch = group.getAttribute('data-search') || '';
      var tests = group.querySelectorAll('.report-test-row');
      var anyVisible = false;
      tests.forEach(function(row) {{
        var match = (groupSearch + ' ' + (row.getAttribute('data-search') || '')).indexOf(q) !== -1;
        row.classList.toggle('hidden', !match);
        if (match) anyVisible = true;
      }});
      group.classList.toggle('hidden', !anyVisible);
    }});
  }}
  searchInput.addEventListener('input', onSearch);
  document.querySelectorAll('.report-file-header').forEach(function(header) {{
    header.addEventListener('click', function() {{ header.closest('.report-file-group').classList.toggle('collapsed'); }});
  }});
  document.querySelectorAll('.report-test-header').forEach(function(header) {{
    header.addEventListener('click', function() {{ header.closest('.report-test-row').classList.toggle('expanded'); }});
  }});
}})();
  </script>
</body>
</html>"""
    return html_content


def write_report(
    result: RunResult,
    cwd: Optional[str] = None,
    report_dir: str = "report",
    filename: str = "report.html",
) -> str:
    from pathlib import Path
    base = Path(cwd or ".").resolve()
    report_path = base / report_dir / filename
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(generate_html_report(result), encoding="utf-8")
    return str(report_path)
