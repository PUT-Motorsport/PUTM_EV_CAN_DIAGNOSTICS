import os
from datetime import datetime

def generate_html_report(results, report_dir="reports", is_stress_test=False):
    """
    Generuje raport HTML. Obsługuje zarówno testy funkcjonalne (Lista słowników)
    jak i testy obciążeniowe (Load Ramp).
    """
    os.makedirs(report_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    
    # Wybór nazwy pliku w zależności od typu testu
    prefix = "STRESS_Ramp" if is_stress_test else "HIL_Functional"
    filename = f"{prefix}_Report_{timestamp}.html"
    filepath = os.path.join(report_dir, filename)

    # --- HTML HEADER ---
    html_content = f"""
    <!DOCTYPE html>
    <html lang="pl">
    <head>
        <meta charset="UTF-8">
        <title>Raport z Testów CAN</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; background-color: #f4f4f9; }}
            h1 {{ color: #333; border-bottom: 2px solid #d32f2f; padding-bottom: 10px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; background-color: #fff; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
            th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
            th {{ background-color: #d32f2f; color: white; }}
            .pass {{ color: green; font-weight: bold; }}
            .fail {{ color: red; font-weight: bold; }}
        </style>
    </head>
    <body>
        <h1>Raport Systemu PUT Motorsport HIL</h1>
        <p><strong>Wygenerowano:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
    """

    # --- LOGIKA DLA TESTU OBCIĄŻENIOWEGO (STRESS TEST) ---
    if is_stress_test:
        test_data = results[0] # Pobieramy wynik z listy jednoelementowej
        is_passed = test_data.get('passed', False)
        status_text = "<span class='pass'>ZALICZONY</span>" if is_passed else "<span class='fail'>NIEZALICZONY</span>"
        
        html_content += f"""
        <h2>Typ testu: Test Wydajnościowy (Load Ramp)</h2>
        <h3>Wynik końcowy: {status_text}</h3>
        <table>
            <tr>
                <th>Faza Obciążenia Szyny</th>
                <th>Średnie Opóźnienie (RTT)</th>
                <th>Utrata Ramek (Loss)</th>
            </tr>
        """
        for step in test_data.get('ramp_results', []):
            loss_class = "fail" if step['loss_pct'] > 5 else "pass"
            html_content += f"""
            <tr>
                <td><strong>{step['load']}%</strong></td>
                <td>{step['avg_latency']:.2f} ms</td>
                <td class="{loss_class}">{step['loss_pct']:.1f}%</td>
            </tr>
            """
        html_content += "</table>"

    # --- LOGIKA DLA STANDARDOWYCH TESTÓW FUNKCJONALNYCH ---
    else:
        passed_count = sum(1 for r in results if r['passed'])
        total_count = len(results)
        html_content += f"""
        <h2>Typ testu: Diagnostyka Bezpieczeństwa (HIL)</h2>
        <h3>Zaliczono: {passed_count} / {total_count}</h3>
        <table>
            <tr>
                <th>Nazwa Testu</th>
                <th>Status</th>
                <th>Wynik / Parametry</th>
            </tr>
        """
        for r in results:
            status_class = "pass" if r['passed'] else "fail"
            status_text = "PASS" if r['passed'] else "FAIL"
            html_content += f"""
            <tr>
                <td>{r['name']}</td>
                <td class="{status_class}">{status_text}</td>
                <td>{r['actual']}</td>
            </tr>
            """
        html_content += "</table>"

    # --- HTML FOOTER ---
    html_content += """
    </body>
    </html>
    """

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_content)

    return filepath