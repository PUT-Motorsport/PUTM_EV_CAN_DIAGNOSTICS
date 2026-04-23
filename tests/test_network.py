import time
from rich.console import Console

console = Console()

class NetworkValidator:
    """Pasywny skaner magistrali CAN. Nie wymaga już pliku YAML!"""
    
    def __init__(self, engine, expected_nodes_dict, duration=3.0):
        self.engine = engine
        # Otrzymuje słownik w formacie: {"Frontbox": 0x010, "Inverter": 0x281}
        self.expected_nodes = expected_nodes_dict
        self.duration = duration

    def run_scan(self):
        console.print(f"\n[bold yellow]Rozpoczynam skanowanie ({self.duration}s)...[/]")
        self.engine.flush_rx_buffer()

        seen_nodes = {name: False for name in self.expected_nodes.keys()}
        total_frames = 0
        error_frames = 0
        
        start_time = time.time()

        while time.time() - start_time < self.duration:
            msg = self.engine.recv(0.1)
            
            if msg:
                total_frames += 1
                if msg.is_error_frame:
                    error_frames += 1
                else:
                    for node_name, expected_id in self.expected_nodes.items():
                        if msg.arbitration_id == expected_id:
                            seen_nodes[node_name] = True

        frames_per_second = total_frames / self.duration

        console.print("\n[bold cyan]=== RAPORT DIAGNOSTYCZNY BOLIDU ===[/]")
        for node, is_alive in seen_nodes.items():
            if is_alive:
                console.print(f"  [green]✅ {node:<15} - ONLINE[/]")
            else:
                console.print(f"  [red]❌ {node:<15} - OFFLINE (Brak sygnału)[/]")

        console.print(f"\n[bold]Statystyki (Bus Load):[/] {total_frames} ramek ({frames_per_second:.1f} msg/s)")
        if error_frames > 0:
            console.print(f"  [bold red]⚠ UWAGA: Ramki błędów (Error Frames): {error_frames}[/]")
        else:
            console.print(f"  [green]✅ Brak błędów fizycznych (Error Frames: 0)[/]")

        return seen_nodes