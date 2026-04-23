import time
from rich.console import Console

console = Console()

class NetworkValidator:
    """Pasywny skaner magistrali CAN analizujący obecność węzłów i błędy sieciowe."""
    
    def __init__(self, engine, scan_config):
        self.engine = engine
        self.expected_nodes = scan_config.get('expected_nodes', {})
        self.duration = float(scan_config.get('duration_s', 3.0))

    def run_scan(self):
        console.print(f"\n[bold yellow]Rozpoczynam pasywne skanowanie sieci ({self.duration}s)...[/]")
        self.engine.flush_rx_buffer()

        # Inicjalizacja słownika wyników (na start zakładamy, że żaden moduł nie żyje)
        seen_nodes = {name: False for name in self.expected_nodes.keys()}
        total_frames = 0
        error_frames = 0
        
        start_time = time.time()

        # Pętla nasłuchująca
        while time.time() - start_time < self.duration:
            msg = self.engine.recv(0.1)
            
            if msg:
                total_frames += 1
                
                # Zliczanie błędów sprzętowych (Hardware Error Frames z transiwera)
                if msg.is_error_frame:
                    error_frames += 1
                else:
                    # Sprawdzamy czy złapana ramka to "Heartbeat" któregoś z naszych modułów
                    for node_name, expected_id in self.expected_nodes.items():
                        if msg.arbitration_id == expected_id:
                            seen_nodes[node_name] = True

        frames_per_second = total_frames / self.duration

        # --- WYPISYWANIE RAPORTU ---
        console.print("\n[bold cyan]=== RAPORT DIAGNOSTYCZNY BOLIDU ===[/]")
        
        for node, is_alive in seen_nodes.items():
            if is_alive:
                console.print(f"  [green]✅ {node:<12} - ONLINE (Wykryto sygnał)[/]")
            else:
                console.print(f"  [red]❌ {node:<12} - OFFLINE (Brak sygnału / Odłączony)[/]")

        console.print(f"\n[bold]Statystyki magistrali (Bus Load):[/]")
        console.print(f"  Przechwycone ramki: {total_frames} ({frames_per_second:.1f} msg/s)")
        
        if error_frames > 0:
            console.print(f"  [bold red]⚠ UWAGA: Wykryto ramki błędów (Error Frames): {error_frames}[/]")
            console.print("  [red]Sugestia: Sprawdź rezystory terminujące 120R, ciągłość kabli CAN_H/CAN_L lub jakość masy![/]")
        else:
            console.print(f"  [green]✅ Brak błędów warstwy fizycznej (Error Frames: 0)[/]")

        return seen_nodes