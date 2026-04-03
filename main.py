import yaml
from rich.console import Console
from core.can_engine import CanEngine
from core.report_gen import generate_html_report
from core.test_procedure import LibraryFullValidator

console = Console()

def main():
    console.rule("[bold cyan]PUTM HIL Validator — Uniwersalny Scenariusz")
    
    # 1. Ładowanie konfiguracji płytki
    with open("config.yaml", "r") as f:
        config = yaml.safe_load(f)

    engine = CanEngine(config)
    
    try:
        validator = LibraryFullValidator(engine, config)
        results = validator.run_all()
        
        report_path = generate_html_report(results, config['paths']['reports'])
        console.print(f"\n[green]Zakończono! Raport:[/] {report_path}")
        
    finally:
        engine.shutdown()

if __name__ == "__main__":
    main()