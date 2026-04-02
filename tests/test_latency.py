import time
import can
from rich.console import Console

console = Console()

class TestLatency:
    """Mierzy czas odpowiedzi (Ping-Pong) biblioteki STM32/ROS2."""
    
    name = "Test opóźnień i reakcji (Latency Ping-Pong)"

    def __init__(self, engine, config):
        self.engine = engine
        self.rx_id = config['dut']['rx_id']
        self.tx_id = config['dut']['tx_id']
        self.timeout = config['dut']['timeout_ms'] / 1000.0
        self.iterations = 100  # Ile razy puszczamy ping-pong
        
    def run(self) -> dict:
        self.engine.flush_rx_buffer()
        rtt_times = []
        lost_frames = 0
        
        console.print(f"[yellow]Rozpoczynam {self.name} ({self.iterations} iteracji)...[/]")
        
        for i in range(self.iterations):
            # Tworzymy ramkę typu Ping (pierwszy bajt to numer sekwencyjny)
            msg = can.Message(arbitration_id=self.rx_id, data=[i, 0xAA, 0xBB], is_extended_id=False)
            
            t_start = time.perf_counter()
            self.engine.send(msg)
            
            # Czekamy na odpowiedź Pong z STM32
            response = None
            while True:
                rx_msg = self.engine.recv(self.timeout)
                if rx_msg is None:
                    break # Timeout
                if rx_msg.arbitration_id == self.tx_id and rx_msg.data[0] == i:
                    response = rx_msg
                    break
            
            t_end = time.perf_counter()
            
            if response:
                rtt_times.append((t_end - t_start) * 1000) # w milisekundach
            else:
                lost_frames += 1

        # Generowanie statystyk testu
        avg_rtt = sum(rtt_times)/len(rtt_times) if rtt_times else 0
        max_rtt = max(rtt_times) if rtt_times else 0
        
        passed = lost_frames == 0 and avg_rtt < 5.0 # Test zdany, jeśli nic nie zgubiono i czas < 5ms
        
        console.print(f"  Średni RTT: [cyan]{avg_rtt:.2f} ms[/]")
        console.print(f"  Max RTT:    [cyan]{max_rtt:.2f} ms[/]")
        console.print(f"  Zgubione:   [red]{lost_frames}[/]")
        
        return {
            "name": self.name,
            "passed": passed,
            "avg_rtt_ms": avg_rtt,
            "max_rtt_ms": max_rtt,
            "lost_frames": lost_frames
        }