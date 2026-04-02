"""
PUTM CAN Tester — test obciążeniowy magistrali
Uruchamiany osobno: python bus_load_test.py [opcje]
"""

from __future__ import annotations
import time
import threading
import random
import argparse
from collections import defaultdict

import can
import cantools
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich import box as rbox

from can_tester import connect, FrameCollector, MessageStats

console = Console()

CRITICAL_IDS = {
    0x45:  "BMS_HV_main",
    0x25:  "Rearbox_Safety",
    0x10:  "Pc_MainData",
    0x287: "AMK_FR_AV1",
    0x289: "AMK_FL_AV1",
    0x285: "AMK_RR_AV1",
    0x283: "AMK_RL_AV1",
}

BAUDRATE        = 1_000_000
FRAME_BITS      = 111        # aproks. dla 8B DLC z bit stuffing
BURST_MSG_ID    = 0x7FF
BURST_PAYLOAD   = bytes([0xAA, 0xBB, 0xCC, 0xDD, 0x01, 0x02, 0x03, 0x04])


def run_bus_load_test(bus: can.BusABC, db: cantools.db.Database,
                      duration: float = 30.0,
                      burst_interval: float = 5.0,
                      burst_frames: int = 50) -> dict:

    collector = FrameCollector(bus, db)
    collector.start()

    results      = {}
    burst_count  = 0
    window_frames = 0
    window_start  = time.time()
    bus_load_by_phase: dict[str, list] = defaultdict(list)
    current_phase = "baseline"

    t_start    = time.time()
    last_burst = t_start

    def make_table(phase, load_now, bursts):
        t = Table(box=rbox.SIMPLE, show_header=True, header_style="bold")
        t.add_column("ECU krytyczny",    width=20)
        t.add_column("Ramek",  justify="right", width=8)
        t.add_column("Cykl avg",  justify="right", width=10)
        t.add_column("Status", width=10)

        with collector._lock:
            for mid, name in CRITICAL_IDS.items():
                s = collector.stats.get(mid)
                if s:
                    color = "green" if s.count > 0 else "red"
                    t.add_row(name[:20], str(s.count),
                              f"{s.avg_cycle_ms:.1f}ms" if s.avg_cycle_ms else "—",
                              f"[{color}]{'OK' if s.count > 0 else 'BRAK'}[/]")
                else:
                    t.add_row(name[:20], "0", "—", "[red]BRAK[/]")

        elapsed = time.time() - t_start
        info = (f"Faza: [cyan]{phase}[/]  "
                f"Bus load: [yellow]{load_now:.1f}%[/]  "
                f"Burst: {bursts}  "
                f"t={elapsed:.0f}/{duration:.0f}s")
        return Panel(t, title=info, border_style="dim")

    load_now = 0.0
    with Live(make_table(current_phase, load_now, burst_count),
              refresh_per_second=2, console=console) as live:

        while time.time() - t_start < duration:
            now = time.time()
            elapsed = now - t_start

            # Faza
            if elapsed < 5.0:
                current_phase = "baseline"
            else:
                current_phase = f"stress (burst #{burst_count})"

            # Generuj burst
            if elapsed >= 5.0 and now - last_burst >= burst_interval:
                for _ in range(burst_frames):
                    dlc = random.randint(4, 8)
                    msg = can.Message(
                        arbitration_id=BURST_MSG_ID,
                        data=BURST_PAYLOAD[:dlc],
                        is_extended_id=False,
                    )
                    try:
                        bus.send(msg)
                    except can.CanError:
                        pass
                    time.sleep(0.001)
                burst_count += 1
                last_burst = now

            # Odbierz ramkę
            msg = bus.recv(timeout=0.05)
            if msg and not msg.is_error_frame:
                window_frames += 1

            # Okno 1s -> bus load
            if now - window_start >= 1.0:
                bits = window_frames * FRAME_BITS
                load_now = (bits / BAUDRATE) * 100.0
                bus_load_by_phase[current_phase].append(load_now)
                window_frames = 0
                window_start  = now

            live.update(make_table(current_phase, load_now, burst_count))

    collector.stop()

    # Analiza
    with collector._lock:
        all_loads = [v for vals in bus_load_by_phase.values() for v in vals]
        baseline_loads = bus_load_by_phase.get("baseline", [0])
        stress_loads   = [v for k, v_list in bus_load_by_phase.items()
                          if "stress" in k for v in v_list]

        results["baseline_avg_pct"]      = sum(baseline_loads)/len(baseline_loads) if baseline_loads else 0
        results["stress_peak_pct"]       = max(stress_loads) if stress_loads else 0
        results["baseline_below_60pct"]  = results["baseline_avg_pct"] < 60
        results["stress_below_80pct"]    = results["stress_peak_pct"] < 80
        results["error_frames"]          = collector.errors
        results["no_error_frames"]       = collector.errors == 0
        results["bursts_generated"]      = burst_count

        for mid, name in CRITICAL_IDS.items():
            s = collector.stats.get(mid)
            key = f"critical_{name}_alive"
            results[key] = (s is not None and s.count > 0)

    return results


def print_bus_load_report(results: dict):
    console.rule("[bold]Raport Bus Load")
    console.print(f"  Baseline avg: [cyan]{results['baseline_avg_pct']:.1f}%[/]")
    console.print(f"  Stress peak:  [cyan]{results['stress_peak_pct']:.1f}%[/]")
    console.print(f"  Error frames: [red]{results['error_frames']}[/]")
    console.print(f"  Burstów:      {results['bursts_generated']}")
    console.print()

    passed = 0
    total  = 0
    for k, v in results.items():
        if not isinstance(v, bool):
            continue
        total += 1
        icon = "[green]PASS[/]" if v else "[red]FAIL[/]"
        if v:
            passed += 1
        console.print(f"  {icon}  {k}")

    pct = int(100 * passed / total) if total else 0
    console.print(f"\n  Wynik: {passed}/{total} ({pct}%)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PUTM Bus Load Test")
    parser.add_argument("--interface", default="virtual",
                        help="peak | socketcan | kvaser | virtual")
    parser.add_argument("--channel",   default="virtual0",
                        help="np. PCAN_USBBUS1, can0, virtual0")
    parser.add_argument("--dbc1",      default="PUTM_CAN_1.dbc")
    parser.add_argument("--dbc2",      default="PUTM_CAN_2.dbc")
    parser.add_argument("--duration",  type=float, default=30.0)
    parser.add_argument("--burst-interval", type=float, default=5.0)
    parser.add_argument("--burst-frames",   type=int,   default=50)
    args = parser.parse_args()

    db = cantools.database.Database()
    db.add_dbc_file(args.dbc1)
    db.add_dbc_file(args.dbc2)

    bus = connect(args.interface, args.channel)
    try:
        results = run_bus_load_test(
            bus, db,
            duration=args.duration,
            burst_interval=args.burst_interval,
            burst_frames=args.burst_frames,
        )
        print_bus_load_report(results)
    finally:
        bus.shutdown()
