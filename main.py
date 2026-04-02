"""
PUTM CAN Tester — punkt wejścia
Użycie:
  python main.py --help
  python main.py --interface peak --channel PCAN_USBBUS1
  python main.py --interface socketcan --channel can0
  python main.py --interface virtual --channel virtual0   # tryb offline
  python main.py --interface peak --channel PCAN_USBBUS1 --bus-load
"""

import argparse
import sys
import os
from datetime import datetime
import cantools

from can_tester    import connect, CANTestRunner
from putm_tests    import build_test_suite
from bus_load_test import run_bus_load_test, print_bus_load_report
from report        import generate_html
from rich.console  import Console

console = Console()


def parse_args():
    p = argparse.ArgumentParser(
        description="PUTM EV — tester magistrali CAN",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Przykłady:
  python main.py --interface peak --channel PCAN_USBBUS1
  python main.py --interface socketcan --channel can0
  python main.py --interface virtual --channel virtual0
  python main.py --interface peak --channel PCAN_USBBUS1 --bus-load --duration 30
        """
    )
    p.add_argument("--interface", "-i", default="virtual",
                   choices=["peak","pcan","socketcan","tosun","kvaser","vector","virtual"],
                   help="Interfejs CAN (domyślnie: virtual)")
    p.add_argument("--channel", "-c", default="virtual0",
                   help="Kanał (np. PCAN_USBBUS1, can0, virtual0)")
    p.add_argument("--bitrate", "-b", type=int, default=500_000,
                   help="Prędkość [bps] (domyślnie: 500000)")
    p.add_argument("--dbc1", default="PUTM_CAN_1.dbc",
                   help="Ścieżka do PUTM_CAN_1.dbc")
    p.add_argument("--dbc2", default="PUTM_CAN_2.dbc",
                   help="Ścieżka do PUTM_CAN_2.dbc")
    p.add_argument("--duration", "-d", type=float, default=10.0,
                   help="Czas zbierania ramek [s] (domyślnie: 10)")
    p.add_argument("--bus-load", action="store_true",
                   help="Uruchom również test obciążeniowy magistrali")
    p.add_argument("--bus-load-duration", type=float, default=30.0,
                   help="Czas testu bus load [s] (domyślnie: 30)")
    p.add_argument("--report", "-r", default=None,
                   help="Ścieżka do raportu HTML (domyślnie: auto-generowana w folderze reports/)")
    p.add_argument("--no-report", action="store_true",
                   help="Nie generuj raportu HTML")
    return p.parse_args()


def load_databases(dbc1: str, dbc2: str) -> cantools.db.Database:
    db = cantools.database.Database()
    for path in [dbc1, dbc2]:
        if not os.path.exists(path):
            console.print(f"[red]Nie znaleziono pliku DBC: {path}[/]")
            sys.exit(1)
        db.add_dbc_file(path)
        console.print(f"[green]Załadowano:[/] {path}  "
                      f"({len(db.messages)} wiadomości łącznie)")
    return db


def main():
    args = parse_args()

    console.rule("[bold cyan]PUTM CAN Tester")
    console.print(f"  Interfejs : [cyan]{args.interface}[/]")
    console.print(f"  Kanał     : [cyan]{args.channel}[/]")
    console.print(f"  Bitrate   : [cyan]{args.bitrate:,} bps[/]")
    console.print()

    # Wczytaj bazy DBC
    db = load_databases(args.dbc1, args.dbc2)

    # Połącz z magistralą
    bus = connect(args.interface, args.channel, args.bitrate)

    bus_load_results = None
    test_results     = []

    try:
        # ── Testy funkcjonalne ─────────────────────────────────────────────
        runner = CANTestRunner(bus, db, collect_time=args.duration)
        for tc in build_test_suite():
            runner.add(tc)

        test_results = runner.run_all()
        runner.summary()

        # ── Test obciążeniowy (opcjonalny) ─────────────────────────────────
        if args.bus_load:
            console.rule("[bold yellow]Bus Load & Stress Test")
            bus_load_results = run_bus_load_test(
                bus, db,
                duration=args.bus_load_duration,
                burst_interval=5.0,
                burst_frames=50,
            )
            print_bus_load_report(bus_load_results)

    finally:
        bus.shutdown()
        console.print("[dim]Połączenie CAN zamknięte[/]")

    # ── Raport HTML ────────────────────────────────────────────────────────
    if not args.no_report:
        # Automatyczne generowanie ścieżki z datą i godziną, jeśli użytkownik nie podał własnej
        if args.report is None:
            os.makedirs("reports", exist_ok=True)
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            report_path = os.path.join("reports", f"PUTM_CAN_Report_{timestamp}.html")
        else:
            report_path = args.report

        path = generate_html(
            results     = test_results,
            bus_load    = bus_load_results,
            interface   = f"{args.interface}:{args.channel}",
            collect_time= args.duration,
            output_path = report_path,
        )
        console.print(f"\n[green]Raport HTML:[/] {os.path.abspath(path)}")
        console.print("Otwórz w przeglądarce, żeby zobaczyć wyniki.\n")


if __name__ == "__main__":
    main()