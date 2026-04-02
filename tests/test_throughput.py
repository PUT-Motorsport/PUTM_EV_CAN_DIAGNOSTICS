import time
import can
from rich.console import Console

console = Console()

class TestThroughput:
    name = "Test przepustowości (Burst 100 frames)"

    def __init__(self, engine, config):
        self.engine = engine
        self.rx_id = config['dut']['rx_id']
        self.tx_id = config['dut']['tx_id']
        self.burst_size = 100 

    def run(self) -> dict:
        self.engine.flush_rx_buffer()
        console.print(f"[yellow]Wysyłanie burstu {self.burst_size} ramek...[/]")
        
        for i in range(self.burst_size):
            msg = can.Message(arbitration_id=self.rx_id, data=[i, 0, 0, 0, 0, 0, 0, 0])
            self.engine.send(msg)

        received = 0
        timeout = time.time() + 2.0
        while time.time() < timeout and received < self.burst_size:
            rx = self.engine.recv(0.01)
            if rx and rx.arbitration_id == self.tx_id:
                received += 1

        passed = received == self.burst_size
        return {
            "name": self.name,
            "passed": passed,
            "sent": self.burst_size,
            "received": received,
            "loss_pct": ((self.burst_size - received) / self.burst_size) * 100
        }