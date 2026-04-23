import yaml
import os
from database.dbc_loader import DBCLoader
from core.can_engine import CanEngine
from core.report_gen import generate_html_report
from tests.test_procedure import LibraryFullValidator
from rich.console import Console

console = Console()

def main():
    console.rule("[bold cyan]PUT Motorsport HIL - Konfiguracja Dynamiczna")

    # 1. Załaduj plik konfiguracyjny YAML
    try:
        with open("config.yaml", "r", encoding="utf-8") as f:
            full_config = yaml.safe_load(f)
    except FileNotFoundError:
        console.print("[red]BŁĄD: Nie znaleziono pliku config.yaml![/]")
        return

    # 2. Pobierz dane aktywnego celu (Target)
    target_name = full_config.get("active_target")
    target_settings = full_config.get("targets", {}).get(target_name)

    if not target_settings:
        console.print(f"[red]BŁĄD: Profil '{target_name}' nie istnieje w config.yaml![/]")
        return

    # 3. Inicjalizacja bazy DBC i pobranie ID/DLC
    dbc = DBCLoader()
    rx_info = dbc.get_message_info(target_settings['rx_frame'])
    tx_info = dbc.get_message_info(target_settings['tx_frame'])

    if not rx_info or not tx_info:
        console.print("[red]BŁĄD: Nie znaleziono wskazanych ramek w plikach DBC![/]")
        return

    # 4. Budowa finalnego słownika konfiguracji dla silnika i testów
    config = {
        'bus': full_config['bus'],
        'dut': {
            'target_name': target_name,
            'rx_id': rx_info['id'],
            'tx_id': tx_info['id'],
            'rx_dlc': rx_info['dlc'],
            'timeout_ms': target_settings['timeout_ms']
        },
        'all_dbc_ids': dbc.get_all_ids(),
        'paths': full_config['paths']
    }

    # 5. Uruchomienie procedury testowej
    try:
        engine = CanEngine(config)
        validator = LibraryFullValidator(engine, config)
        
        console.print(f"\n[bold green]>>> TESTOWANIE: {target_name} <<<[/]")
        console.print(f"  RX (z DBC): 0x{config['dut']['rx_id']:03X} [{target_settings['rx_frame']}]")
        console.print(f"  TX (z DBC): 0x{config['dut']['tx_id']:03X} [{target_settings['tx_frame']}]")
        
        results = validator.run_all()
        
        # Generowanie raportu
        report_path = generate_html_report(results, config['paths']['reports'])
        console.print(f"\n[green]Sukces! Raport:[/][bold] {report_path}[/]")

    except Exception as e:
        console.print(f"[bold red]Błąd wykonania: {e}[/]")
    finally:
        if 'engine' in locals(): engine.shutdown()

if __name__ == "__main__":
    main()