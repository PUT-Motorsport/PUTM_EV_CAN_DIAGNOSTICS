"""
PUTM CAN Tester — generator raportów HTML
"""

from __future__ import annotations
import os
from datetime import datetime
from collections import defaultdict
from can_tester import TestResult


def generate_html(results: list[TestResult],
                  bus_load: dict | None = None,
                  interface: str = "",
                  collect_time: float = 0,
                  output_path: str = "PUTM_CAN_Report.html"):

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    passed    = sum(1 for r in results if r.passed)
    total     = len(results)
    pct       = int(100 * passed / total) if total else 0
    color_pct = "#1a7a3c" if pct >= 80 else "#c47a00" if pct >= 50 else "#b52020"

    # Grupuj po kategorii
    by_cat = defaultdict(list)
    for r in results:
        by_cat[r.category].append(r)

    # Sekcje HTML per kategoria
    sections_html = ""
    for cat, cat_results in by_cat.items():
        cat_pass  = sum(1 for r in cat_results if r.passed)
        cat_total = len(cat_results)
        cat_ok    = cat_pass == cat_total
        rows = ""
        for r in cat_results:
            td = "pass" if r.passed else "fail"
            extra = f"<span class='actual'>{r.actual}</span>" if r.actual else ""
            rows += (f"<tr>"
                     f"<td class='tc'>{r.tc_id}</td>"
                     f"<td>{r.description}</td>"
                     f"<td class='{td}'>{'PASS' if r.passed else 'FAIL'}</td>"
                     f"<td>{extra}</td>"
                     f"</tr>")

        icon  = "✓" if cat_ok else "✗"
        cls   = "cat-pass" if cat_ok else "cat-fail"
        safe_id = cat.replace(" ", "_")
        sections_html += f"""
        <div class="category {cls}">
          <div class="cat-header" onclick="tog('{safe_id}')">
            <span class="cat-icon">{icon}</span>
            <span class="cat-name">{cat}</span>
            <span class="cat-score">{cat_pass}/{cat_total}</span>
          </div>
          <div class="cat-body" id="{safe_id}">
            <table><thead>
              <tr><th>ID</th><th>Opis</th><th>Status</th><th>Szczegóły</th></tr>
            </thead><tbody>{rows}</tbody></table>
          </div>
        </div>"""

    # Bus load sekcja
    bl_html = ""
    if bus_load:
        bl_pass  = sum(1 for v in bus_load.values() if isinstance(v, bool) and v)
        bl_total = sum(1 for v in bus_load.values() if isinstance(v, bool))
        bl_rows  = ""
        for k, v in bus_load.items():
            if isinstance(v, bool):
                td = "pass" if v else "fail"
                bl_rows += (f"<tr><td class='tc'>{k}</td>"
                            f"<td class='{td}'>{'PASS' if v else 'FAIL'}</td></tr>")
            else:
                bl_rows += f"<tr><td class='tc'>{k}</td><td>{v}</td></tr>"

        bl_ok  = bl_pass == bl_total
        bl_cls = "cat-pass" if bl_ok else "cat-fail"
        bl_html = f"""
        <div class="category {bl_cls}">
          <div class="cat-header" onclick="tog('bus_load')">
            <span class="cat-icon">{'✓' if bl_ok else '✗'}</span>
            <span class="cat-name">Bus Load & Stress</span>
            <span class="cat-score">{bl_pass}/{bl_total}</span>
          </div>
          <div class="cat-body" id="bus_load">
            <table><thead><tr><th>Parametr</th><th>Wynik</th></tr></thead>
            <tbody>{bl_rows}</tbody></table>
          </div>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="pl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PUTM CAN Test Report</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; }}
  body {{ margin: 0; font-family: 'Segoe UI', system-ui, sans-serif;
          background: #f0f2f5; color: #1a1a1a; font-size: 14px; }}
  .header {{ background: #0f1e36; color: #fff; padding: 20px 32px;
             display: flex; justify-content: space-between; align-items: flex-end; }}
  .header h1 {{ margin: 0; font-size: 20px; font-weight: 600; }}
  .header p  {{ margin: 4px 0 0; font-size: 12px; color: #6a8cb0; }}
  .meta {{ font-size: 12px; color: #6a8cb0; text-align: right; line-height: 1.6; }}
  .kpis {{ display: flex; gap: 16px; padding: 16px 32px;
           background: #fff; border-bottom: 1px solid #e0e4ec; flex-wrap: wrap; }}
  .kpi {{ text-align: center; padding: 10px 20px; border-radius: 8px;
          background: #f5f7fa; min-width: 90px; }}
  .kpi .v {{ font-size: 26px; font-weight: 700; color: {color_pct}; }}
  .kpi .l {{ font-size: 11px; color: #777; margin-top: 2px; }}
  .progress {{ height: 5px; background: #e0e4ec; }}
  .progress-fill {{ height: 100%; width: {pct}%;
                    background: {color_pct}; transition: width .4s; }}
  .content {{ padding: 20px 32px; max-width: 960px; }}
  .category {{ margin-bottom: 10px; border-radius: 8px; overflow: hidden;
               border: 1px solid #e0e4ec; background: #fff; }}
  .cat-header {{ display: flex; align-items: center; padding: 12px 16px;
                 cursor: pointer; user-select: none; gap: 10px;
                 transition: background .15s; }}
  .cat-header:hover {{ background: #f8f9fb; }}
  .cat-pass .cat-header {{ border-left: 4px solid #1a7a3c; }}
  .cat-fail .cat-header {{ border-left: 4px solid #b52020; }}
  .cat-icon {{ width: 18px; font-size: 14px; }}
  .cat-pass .cat-icon {{ color: #1a7a3c; }}
  .cat-fail .cat-icon {{ color: #b52020; }}
  .cat-name {{ flex: 1; font-weight: 500; }}
  .cat-score {{ font-size: 12px; color: #888; }}
  .cat-body {{ display: none; border-top: 1px solid #f0f0f0; }}
  .cat-body.open {{ display: block; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th {{ background: #f5f7fa; padding: 8px 12px; text-align: left;
        font-size: 12px; font-weight: 500; color: #555;
        border-bottom: 1px solid #e8eaef; }}
  td {{ padding: 7px 12px; border-bottom: 1px solid #f4f4f4;
        font-size: 13px; vertical-align: middle; }}
  td.tc {{ font-family: monospace; font-size: 12px; color: #555; width: 60px; }}
  td.pass {{ color: #1a7a3c; font-weight: 500; width: 60px; }}
  td.fail {{ color: #b52020; font-weight: 500; width: 60px; }}
  .actual {{ font-family: monospace; font-size: 11px; color: #777; }}
  tr:last-child td {{ border-bottom: none; }}
</style>
</head>
<body>
<div class="header">
  <div>
    <h1>PUTM EV — Raport testów CAN</h1>
    <p>python-can + cantools | Interfejs: {interface} | Czas zbierania: {collect_time:.0f}s</p>
  </div>
  <div class="meta">
    Wygenerowano: {timestamp}<br>
    Testów: {passed}/{total} zaliczonych
  </div>
</div>
<div class="kpis">
  <div class="kpi"><div class="v">{pct}%</div><div class="l">Wynik</div></div>
  <div class="kpi"><div class="v" style="color:#1a7a3c">{passed}</div><div class="l">PASS</div></div>
  <div class="kpi"><div class="v" style="color:#b52020">{total-passed}</div><div class="l">FAIL</div></div>
  <div class="kpi"><div class="v">{total}</div><div class="l">Łącznie</div></div>
</div>
<div class="progress"><div class="progress-fill"></div></div>
<div class="content">
  {sections_html}
  {bl_html}
</div>
<script>
function tog(id) {{
  var el = document.getElementById(id);
  el.classList.toggle('open');
}}
document.querySelectorAll('.cat-fail .cat-body').forEach(function(el) {{
  el.classList.add('open');
}});
</script>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    return output_path
