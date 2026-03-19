"""Generate a self-contained HTML dashboard from a benchmark report."""
from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _esc(text: Any) -> str:
    """HTML-escape a value."""
    return html.escape(str(text)) if text is not None else ""


def _score_color(score: float | int | None, max_val: float = 5.0) -> str:
    """Return a CSS background colour for a 0-max_val score."""
    if score is None or (isinstance(score, (int, float)) and score < 0):
        return "#f0f0f0"
    ratio = float(score) / max_val
    if ratio >= 0.8:
        return "#c6efce"  # green
    if ratio >= 0.5:
        return "#ffeb9c"  # amber
    return "#ffc7ce"  # red


def _pct_color(val: float | None) -> str:
    """Colour for a 0-1 ratio."""
    return _score_color(val, max_val=1.0) if val is not None else "#f0f0f0"


def _fmt(val: float | int | None, decimals: int = 2) -> str:
    if val is None:
        return "—"
    if isinstance(val, int):
        return str(val)
    return f"{val:.{decimals}f}"


def _summary_card(label: str, value: str, color: str) -> str:
    return f"""<div class="card" style="border-left:4px solid {color}">
      <div class="card-value">{value}</div>
      <div class="card-label">{_esc(label)}</div>
    </div>"""


def generate_html(report: dict, title: str = "RAG Benchmark Dashboard") -> str:
    """Return a complete HTML string for the benchmark dashboard."""
    s = report["summary"]
    results = report["results"]
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # --- Summary cards ---
    cards = [
        _summary_card("Questions", str(s["total_questions"]), "#4a90d9"),
        _summary_card("Factual", str(s["factual_count"]), "#5b9bd5"),
        _summary_card("Reasoning", str(s["reasoning_count"]), "#70ad47"),
        _summary_card("Time", f"{_fmt(s['elapsed_seconds'], 1)}s", "#7f7f7f"),
    ]

    has_judge = s.get("avg_correctness") is not None

    # --- Metric bars ---
    metrics_rows = ""
    metric_items = [
        ("Retrieval Recall", s.get("avg_retrieval_recall"), 1.0),
        ("Retrieval Precision", s.get("avg_retrieval_precision"), 1.0),
    ]
    if has_judge:
        metric_items += [
            ("Correctness (all)", s.get("avg_correctness"), 5.0),
            ("Completeness (all)", s.get("avg_completeness"), 5.0),
            ("Correctness (factual)", s.get("avg_correctness_factual"), 5.0),
            ("Correctness (reasoning)", s.get("avg_correctness_reasoning"), 5.0),
            ("Completeness (factual)", s.get("avg_completeness_factual"), 5.0),
            ("Completeness (reasoning)", s.get("avg_completeness_reasoning"), 5.0),
        ]

    for label, val, max_val in metric_items:
        pct = (float(val) / max_val * 100) if val is not None else 0
        color = _score_color(val, max_val)
        display = f"{_fmt(val)}" + (f" / {int(max_val)}" if max_val > 1 else "")
        metrics_rows += f"""<div class="metric-row">
          <span class="metric-label">{_esc(label)}</span>
          <div class="metric-bar-bg">
            <div class="metric-bar" style="width:{pct:.0f}%;background:{color}">{display}</div>
          </div>
        </div>\n"""

    # --- Results table ---
    table_rows = ""
    for r in results:
        rc = _pct_color(r.get("retrieval_recall"))
        rp = _pct_color(r.get("retrieval_precision"))
        cc = _score_color(r.get("correctness"))
        cpc = _score_color(r.get("completeness"))
        q_short = _esc(r["question"][:80]) + ("…" if len(r["question"]) > 80 else "")
        gen_short = _esc(r.get("generated_answer", "")[:120]) + ("…" if len(r.get("generated_answer", "")) > 120 else "")
        exp_short = _esc(r.get("expected_answer", "")[:120]) + ("…" if len(r.get("expected_answer", "")) > 120 else "")
        type_badge_color = "#dce6f1" if r.get("type") == "factual" else "#e2efda"
        judge_exp = _esc(r.get("judge_explanation", ""))

        table_rows += f"""<tr>
          <td>{_esc(r.get('id'))}</td>
          <td><span class="type-badge" style="background:{type_badge_color}">{_esc(r.get('type'))}</span></td>
          <td class="q-cell" title="{_esc(r['question'])}">{q_short}</td>
          <td style="background:{rc}">{_fmt(r.get('retrieval_recall'))}</td>
          <td style="background:{rp}">{_fmt(r.get('retrieval_precision'))}</td>
          <td style="background:{cc}">{_fmt(r.get('correctness'), 0)}</td>
          <td style="background:{cpc}">{_fmt(r.get('completeness'), 0)}</td>
          <td>{r.get('num_citations', 0)}</td>
          <td class="detail-cell" title="{_esc(r.get('expected_answer', ''))}">{exp_short}</td>
          <td class="detail-cell" title="{_esc(r.get('generated_answer', ''))}">{gen_short}</td>
          <td class="detail-cell" title="{judge_exp}">{judge_exp[:80]}{"…" if len(r.get("judge_explanation", "")) > 80 else ""}</td>
        </tr>\n"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{_esc(title)}</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
         background:#f5f6fa; color:#333; padding:24px; }}
  h1 {{ font-size:1.6rem; margin-bottom:4px; }}
  .subtitle {{ color:#888; font-size:0.85rem; margin-bottom:20px; }}
  .cards {{ display:flex; gap:16px; flex-wrap:wrap; margin-bottom:24px; }}
  .card {{ background:#fff; border-radius:8px; padding:16px 20px; min-width:140px;
           box-shadow:0 1px 3px rgba(0,0,0,0.08); }}
  .card-value {{ font-size:1.5rem; font-weight:700; }}
  .card-label {{ font-size:0.8rem; color:#666; margin-top:2px; }}
  .metrics {{ background:#fff; border-radius:8px; padding:20px; margin-bottom:24px;
              box-shadow:0 1px 3px rgba(0,0,0,0.08); }}
  .metrics h2 {{ font-size:1.1rem; margin-bottom:14px; }}
  .metric-row {{ display:flex; align-items:center; margin-bottom:8px; }}
  .metric-label {{ width:200px; font-size:0.85rem; flex-shrink:0; }}
  .metric-bar-bg {{ flex:1; background:#eee; border-radius:4px; height:26px; position:relative; }}
  .metric-bar {{ height:100%; border-radius:4px; display:flex; align-items:center;
                 padding-left:10px; font-size:0.8rem; font-weight:600; min-width:fit-content; }}
  .table-wrap {{ background:#fff; border-radius:8px; padding:20px; box-shadow:0 1px 3px rgba(0,0,0,0.08); overflow-x:auto; }}
  .table-wrap h2 {{ font-size:1.1rem; margin-bottom:14px; }}
  .controls {{ display:flex; gap:12px; margin-bottom:12px; align-items:center; }}
  .controls select, .controls input {{ padding:6px 10px; border:1px solid #ddd; border-radius:4px; font-size:0.85rem; }}
  .controls input {{ width:240px; }}
  table {{ width:100%; border-collapse:collapse; font-size:0.82rem; }}
  th {{ background:#f0f2f5; position:sticky; top:0; padding:8px 6px; text-align:left; cursor:pointer;
       border-bottom:2px solid #ddd; white-space:nowrap; user-select:none; }}
  th:hover {{ background:#e2e5ea; }}
  td {{ padding:6px; border-bottom:1px solid #eee; vertical-align:top; }}
  .q-cell {{ max-width:240px; }}
  .detail-cell {{ max-width:200px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
  .type-badge {{ padding:2px 8px; border-radius:10px; font-size:0.75rem; font-weight:600; }}
  tr:hover {{ background:#f8f9fb; }}
  .legend {{ display:flex; gap:16px; margin-top:12px; font-size:0.78rem; color:#666; }}
  .legend-dot {{ display:inline-block; width:12px; height:12px; border-radius:2px; margin-right:4px; vertical-align:middle; }}
  .expand-btn {{ cursor:pointer; color:#4a90d9; text-decoration:underline; font-size:0.78rem; border:none; background:none; }}
</style>
</head>
<body>
<h1>{_esc(title)}</h1>
<div class="subtitle">Generated {generated_at}</div>

<div class="cards">
  {"".join(cards)}
</div>

<div class="metrics">
  <h2>Aggregate Metrics</h2>
  {metrics_rows}
  <div class="legend">
    <span><span class="legend-dot" style="background:#c6efce"></span>Good (&ge;80%)</span>
    <span><span class="legend-dot" style="background:#ffeb9c"></span>Fair (50–79%)</span>
    <span><span class="legend-dot" style="background:#ffc7ce"></span>Weak (&lt;50%)</span>
  </div>
</div>

<div class="table-wrap">
  <h2>Detailed Results</h2>
  <div class="controls">
    <select id="typeFilter" onchange="filterTable()">
      <option value="all">All types</option>
      <option value="factual">Factual only</option>
      <option value="reasoning">Reasoning only</option>
    </select>
    <input id="searchBox" type="text" placeholder="Search questions…" oninput="filterTable()">
  </div>
  <table id="resultsTable">
    <thead><tr>
      <th onclick="sortTable(0)">ID</th>
      <th onclick="sortTable(1)">Type</th>
      <th onclick="sortTable(2)">Question</th>
      <th onclick="sortTable(3)">Recall</th>
      <th onclick="sortTable(4)">Precision</th>
      <th onclick="sortTable(5)">Correct</th>
      <th onclick="sortTable(6)">Complete</th>
      <th onclick="sortTable(7)">Citations</th>
      <th>Expected Answer</th>
      <th>Generated Answer</th>
      <th>Judge Explanation</th>
    </tr></thead>
    <tbody>
      {table_rows}
    </tbody>
  </table>
</div>

<script>
let sortDir = {{}};
function sortTable(col) {{
  const table = document.getElementById('resultsTable');
  const tbody = table.tBodies[0];
  const rows = Array.from(tbody.rows);
  const dir = sortDir[col] = !(sortDir[col] || false);
  rows.sort((a, b) => {{
    let va = a.cells[col].textContent.trim();
    let vb = b.cells[col].textContent.trim();
    let na = parseFloat(va), nb = parseFloat(vb);
    if (!isNaN(na) && !isNaN(nb)) return dir ? na - nb : nb - na;
    return dir ? va.localeCompare(vb) : vb.localeCompare(va);
  }});
  rows.forEach(r => tbody.appendChild(r));
}}
function filterTable() {{
  const type = document.getElementById('typeFilter').value;
  const q = document.getElementById('searchBox').value.toLowerCase();
  const rows = document.querySelectorAll('#resultsTable tbody tr');
  rows.forEach(r => {{
    const rType = r.cells[1].textContent.trim();
    const rQ = r.cells[2].textContent.toLowerCase();
    const showType = type === 'all' || rType === type;
    const showQ = !q || rQ.includes(q);
    r.style.display = (showType && showQ) ? '' : 'none';
  }});
}}
</script>
</body>
</html>"""


def save_dashboard(report: dict, path: Path | None = None) -> Path:
    """Generate and save the HTML dashboard. Returns the output path."""
    from app.core.config import PROJECT_ROOT

    p = path or (PROJECT_ROOT / "benchmarks" / "dashboard.html")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(generate_html(report))
    return p
