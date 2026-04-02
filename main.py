import os
import yaml
from rich.console import Console

from core.can_engine import CanEngine
from core.report_gen import generate_html_report
from tests.test_latency import TestLatency
from tests.test_throughput import TestThroughput 
from tests.test_robustness import TestRobustness

console = Console()

def load_config(path="config.yaml"):
    if not os.path.exists(path):
        console.print(f"[red]Brak pliku {path}[/]")
        exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def main():
    console.rule("[bold cyan]PUTM CAN Test Framework")
    
    config = load_config()
    engine = CanEngine(config)
    
    test_suite = [
        TestLatency(engine, config),
        TestThroughput(engine, config),
        TestRobustness(engine, config)
    ]
    
    results = []
    try:
        console.print("\n[bold]Wykonywanie testów:[/]")
        for test in test_suite:
            res = test.run()
            results.append(res)
            
            icon = "[green]PASS[/]" if res["passed"] else "[red]FAIL[/]"
            console.print(f"{icon} {test.name}\n")
            
    finally:
        engine.shutdown()
        console.print("[dim]Połączenie z magistralą zamknięte.[/]")

    passed_count = sum(1 for r in results if r["passed"])
    console.rule("[bold]Podsumowanie")
    console.print(f"Zaliczono: [bold]{passed_count}/{len(results)}[/]")
    
    report_path = generate_html_report(results, output_dir=config['paths']['reports'])
    console.print(f"\n[green]Wygenerowano raport HTML:[/] {os.path.abspath(report_path)}")
    console.print("Możesz go teraz otworzyć w przeglądarce.")

if __name__ == "__main__":
    main()