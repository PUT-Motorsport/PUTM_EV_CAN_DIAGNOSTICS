"""
PUTM CAN Tester — silnik testowy
Obsługuje: PEAK, TOSUN (socketcan), Kvaser, Virtual (offline)
Wymaga:    pip install python-can cantools rich
"""

from __future__ import annotations
import time
import threading
import statistics
from dataclasses import dataclass, field
from typing import Callable, Optional
from collections import defaultdict

import can
import cantools
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from rich import box

console = Console()

# ─── Struktury danych ────────────────────────────────────────────────────────

@dataclass
class TestResult:
    tc_id: str
    description: str
    passed: bool
    actual: str = ""
    expected: str = ""
    category: str = "general"

@dataclass
class MessageStats:
    msg_id: int
    name: str
    count: int = 0
    timestamps: list = field(default_factory=list)
    last_data: Optional[bytes] = None

    @property
    def cycle_times_ms(self) -> list[float]:
        if len(self.timestamps) < 2:
            return []
        return [(self.timestamps[i+1] - self.timestamps[i]) * 1000
                for i in range(len(self.timestamps) - 1)]

    @property
    def avg_cycle_ms(self) -> float:
        ct = self.cycle_times_ms
        return statistics.mean(ct) if ct else 0.0

    @property
    def max_cycle_ms(self) -> float:
        ct = self.cycle_times_ms
        return max(ct) if ct else 0.0

    @property
    def jitter_ms(self) -> float:
        ct = self.cycle_times_ms
        return statistics.stdev(ct) if len(ct) > 1 else 0.0


# ─── Połączenie z magistralą ─────────────────────────────────────────────────

def connect(interface: str, channel: str, bitrate: int = 500_000) -> can.BusABC:
    """
    interface: 'peak'     → PCAN-USB     (PEAK)
               'socketcan'→ socketcan    (TOSUN na Linux / SocketCAN)
               'kvaser'   → Kvaser       (Kvaser Leaf)
               'vector'   → Vector CANalyzer
               'virtual'  → offline symulacja
    channel:  'PCAN_USBBUS1', 'can0', '0', 'Virtual0' ...
    """
    INTERFACE_MAP = {
        "peak":      "pcan",
        "pcan":      "pcan",
        "socketcan": "socketcan",
        "tosun":     "socketcan",
        "kvaser":    "kvaser",
        "vector":    "vector",
        "virtual":   "virtual",
    }
    iface = INTERFACE_MAP.get(interface.lower(), interface.lower())

    console.print(f"[cyan]Łączę:[/] {iface}  channel={channel}  bitrate={bitrate}")
    bus = can.interface.Bus(interface=iface, channel=channel, bitrate=bitrate)
    console.print("[green]Połączono z magistralą CAN[/]")
    return bus


# ─── Kolektor ramek ──────────────────────────────────────────────────────────

class FrameCollector:
    """Zbiera ramki CAN w tle przez zadany czas."""

    def __init__(self, bus: can.BusABC, db: cantools.db.Database):
        self.bus   = bus
        self.db    = db
        self.stats: dict[int, MessageStats] = {}
        self.raw:   list[can.Message]       = []
        self.errors = 0
        self._stop  = threading.Event()
        self._lock  = threading.Lock()

    def _worker(self):
        while not self._stop.is_set():
            msg = self.bus.recv(timeout=0.05)
            if msg is None:
                continue
            if msg.is_error_frame:
                with self._lock:
                    self.errors += 1
                continue
            with self._lock:
                self.raw.append(msg)
                mid = msg.arbitration_id
                if mid not in self.stats:
                    try:
                        name = self.db.get_message_by_frame_id(mid).name
                    except KeyError:
                        name = f"0x{mid:03X}"
                    self.stats[mid] = MessageStats(msg_id=mid, name=name)
                s = self.stats[mid]
                s.count += 1
                s.timestamps.append(msg.timestamp)
                s.last_data = bytes(msg.data)

    def start(self):
        self._stop.clear()
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        self._thread.join(timeout=2)

    def get_decoded(self, msg_id: int) -> Optional[dict]:
        """Dekoduje ostatnią ramkę danego ID używając DBC."""
        s = self.stats.get(msg_id)
        if s is None or s.last_data is None:
            return None
        try:
            db_msg = self.db.get_message_by_frame_id(msg_id)
            return db_msg.decode(s.last_data, decode_choices=False)
        except Exception:
            return None


# ─── Definicja testu ─────────────────────────────────────────────────────────

class TestCase:
    """
    Pojedynczy przypadek testowy. Parametry:
      tc_id       : unikalny identyfikator np. "TC01"
      description : opis
      fn          : funkcja(collector) -> TestResult
      category    : grupowanie w raporcie
    """
    def __init__(self, tc_id: str, description: str,
                 fn: Callable[[FrameCollector], TestResult],
                 category: str = "general"):
        self.tc_id       = tc_id
        self.description = description
        self.fn          = fn
        self.category    = category

    def run(self, collector: FrameCollector) -> TestResult:
        try:
            result = self.fn(collector)
            result.tc_id       = self.tc_id
            result.description = self.description
            result.category    = self.category
            return result
        except Exception as e:
            return TestResult(
                tc_id=self.tc_id,
                description=self.description,
                passed=False,
                actual=f"EXCEPTION: {e}",
                category=self.category,
            )


# ─── Silnik testowy ──────────────────────────────────────────────────────────

class CANTestRunner:
    def __init__(self, bus: can.BusABC, db: cantools.db.Database,
                 collect_time: float = 10.0):
        self.bus          = bus
        self.db           = db
        self.collect_time = collect_time
        self.test_cases:  list[TestCase]   = []
        self.results:     list[TestResult] = []

    def add(self, tc: TestCase):
        self.test_cases.append(tc)

    def run_all(self) -> list[TestResult]:
        console.rule("[bold cyan]PUTM CAN Tester")

        # Zbieranie ramek
        collector = FrameCollector(self.bus, self.db)
        console.print(f"[yellow]Zbieranie ramek przez {self.collect_time}s...[/]")
        collector.start()

        # Live podgląd podczas zbierania
        with Live(self._live_table(collector), refresh_per_second=2,
                  console=console) as live:
            t0 = time.time()
            while time.time() - t0 < self.collect_time:
                time.sleep(0.5)
                live.update(self._live_table(collector))

        collector.stop()

        console.print(f"\n[cyan]Zebrano {len(collector.raw)} ramek, "
                      f"błędy: {collector.errors}[/]\n")

        # Wykonanie testów
        self.results = []
        for tc in self.test_cases:
            r = tc.run(collector)
            self.results.append(r)
            icon  = "[green]PASS[/]" if r.passed else "[red]FAIL[/]"
            extra = f"  → {r.actual}" if not r.passed and r.actual else ""
            console.print(f"  {icon}  {r.tc_id:25s}  {r.description}{extra}")

        return self.results

    def _live_table(self, collector: FrameCollector) -> Panel:
        t = Table(box=box.SIMPLE, show_header=True, header_style="bold")
        t.add_column("ID",    style="cyan",  width=8)
        t.add_column("Nazwa", width=28)
        t.add_column("Ramek", justify="right", width=7)
        t.add_column("Cykl avg", justify="right", width=10)
        t.add_column("Jitter", justify="right", width=8)

        with collector._lock:
            for mid, s in sorted(collector.stats.items()):
                t.add_row(
                    f"0x{mid:03X}",
                    s.name[:28],
                    str(s.count),
                    f"{s.avg_cycle_ms:.1f} ms" if s.avg_cycle_ms else "—",
                    f"{s.jitter_ms:.2f} ms"    if s.jitter_ms    else "—",
                )
        return Panel(t, title="[cyan]Live — ruch CAN[/]", border_style="dim")

    def summary(self):
        passed = sum(1 for r in self.results if r.passed)
        total  = len(self.results)
        pct    = int(100 * passed / total) if total else 0
        bar_w  = 30
        filled = int(bar_w * passed / total) if total else 0
        bar    = "█" * filled + "░" * (bar_w - filled)
        color  = "green" if pct >= 80 else "yellow" if pct >= 50 else "red"
        console.print()
        console.rule("[bold]Podsumowanie")
        console.print(f"  [{color}]{bar}[/]  {passed}/{total} ({pct}%)")
        console.print()


# ─── Helpers do pisania testów ───────────────────────────────────────────────

def check_present(collector: FrameCollector, msg_id: int) -> bool:
    return msg_id in collector.stats and collector.stats[msg_id].count > 0

def check_signal_range(collector: FrameCollector, msg_id: int,
                        signal: str, min_val: float, max_val: float
                        ) -> tuple[bool, str]:
    decoded = collector.get_decoded(msg_id)
    if decoded is None:
        return False, "brak ramki"
    val = decoded.get(signal)
    if val is None:
        return False, f"brak sygnału {signal}"
    ok = min_val <= val <= max_val
    return ok, f"{signal}={val:.2f} (oczekiwano {min_val}..{max_val})"

def check_cycle(collector: FrameCollector, msg_id: int,
                expected_ms: float, tolerance_ms: float) -> tuple[bool, str]:
    s = collector.stats.get(msg_id)
    if s is None or len(s.timestamps) < 5:
        return False, "za mało ramek do pomiaru"
    avg = s.avg_cycle_ms
    ok  = abs(avg - expected_ms) <= tolerance_ms
    return ok, f"avg={avg:.2f}ms max={s.max_cycle_ms:.2f}ms jitter={s.jitter_ms:.2f}ms"

def check_bit_flag(collector: FrameCollector, msg_id: int,
                   signal: str, expected: int) -> tuple[bool, str]:
    decoded = collector.get_decoded(msg_id)
    if decoded is None:
        return False, "brak ramki"
    val = decoded.get(signal)
    if val is None:
        return False, f"brak sygnału {signal}"
    ok = int(val) == expected
    return ok, f"{signal}={int(val)} (oczekiwano {expected})"
