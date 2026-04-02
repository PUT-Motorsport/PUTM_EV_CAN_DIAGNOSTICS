import os
from datetime import datetime

def generate_html_report(results, output_dir="reports"):
    """Generuje raport HTML na podstawie wyników testów wydajnościowych."""
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filepath = os.path.join(output_dir, f"STM32_ROS2_CAN_Report_{timestamp}.html")

    passed_count = sum(1 for r in results if r.get("passed", False))
    total_count = len(results)
    
    if total_count == 0:
        main_color = "#888"
    elif passed_count == total_count:
        main_color = "#1a7a3c" 
    else:
        main_color = "#b52020"

    rows_html = ""
    for r in results:
        status_text = "PASS" if r.get("passed") else "FAIL"
        status_color = "#1a7a3c" if r.get("passed") else "#b52020"
        
        details = ""
        for key, value in r.items():
            if key not in ["name", "passed"]:
                val_str = f"{value:.2f}" if isinstance(value, float) else str(value)
                details += f"<b>{key}</b>: {val_str}<br>"

        rows_html += f"""
        <tr>
            <td style="font-weight: bold;">{r.get('name', 'Nieznany test')}</td>
            <td style="color: {status_color}; font-weight: bold;">{status_text}</td>
            <td style="font-family: monospace; font-size: 13px;">{details}</td>
        </tr>
        """

    html_content = f"""
    <!DOCTYPE html>
    <html lang="pl">
    <head>
        <meta charset="UTF-8">
        <title>Raport walidacji STM32/ROS2 CAN</title>
        <style>
            body {{ font-family: 'Segoe UI', sans-serif; background: #f0f2f5; color: #333; margin: 0; padding: 20px; }}
            .container {{ max-width: 900px; margin: 0 auto; background: #fff; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            h1 {{ border-bottom: 2px solid {main_color}; padding-bottom: 10px; }}
            .summary {{ font-size: 18px; margin-bottom: 20px; font-weight: bold; color: {main_color}; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th, td {{ padding: 12px 15px; border-bottom: 1px solid #ddd; text-align: left; }}
            th {{ background-color: #f8f9fa; color: #555; text-transform: uppercase; font-size: 14px; }}
            tr:hover {{ background-color: #f1f1f1; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Testy wydajnościowe CAN (STM32 & ROS2)</h1>
            <p>Wygenerowano: <b>{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</b></p>
            <div class="summary">Wynik końcowy: {passed_count} / {total_count} testów zaliczonych</div>
            
            <table>
                <thead>
                    <tr>
                        <th style="width: 40%;">Nazwa testu</th>
                        <th style="width: 15%;">Status</th>
                        <th style="width: 45%;">Pomiary / Parametry</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>
        </div>
    </body>
    </html>
    """

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    return filepath