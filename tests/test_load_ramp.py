import time
import can
import statistics
from rich.console import Console

console = Console()

class TestLoadRamp:
    name = "Test stabilności pod narastającym obciążeniem"

    def __init__(self, engine, config):
        self.engine = engine
        self.rx_id = config['dut']['rx_id']
        self.tx_id = config['dut']['tx_id']
        self.timeout = config['dut']['timeout_ms'] / 1000.0
        self.steps = [0, 20, 40, 60, 80, 90] 

    def run(self) -> dict:
        self.engine.flush_rx_buffer()
        ramp_data = []
        
        console.print(f"[bold yellow]Rozpoczynam Load Ramp Test...[/]")

        for load in self.steps:
            console.print(f"  -> Faza obciążenia: [bold]{load}%[/]")
            
            bg_frames_count = load * 8 
            
            latencies = []
            lost = 0
            
            for i in range(50):
                for _ in range(bg_frames_count // 10):
                    self.engine.send(can.Message(arbitration_id=0x7FF, data=[0]*8))
                
                t_start = time.perf_counter()
                self.engine.send(can.Message(arbitration_id=self.rx_id, data=[i, 0, 0, 0]))
                
                res = self.engine.recv(self.timeout)
                if res and res.arbitration_id == self.tx_id:
                    latencies.append((time.perf_counter() - t_start) * 1000)
                else:
                    lost += 1
                
                time.sleep(0.001) 

            avg_latency = statistics.mean(latencies) if latencies else 0
            loss_pct = (lost / 50) * 100
            
            ramp_data.append({
                "load": load,
                "avg_latency": avg_latency,
                "loss_pct": loss_pct
            })
            
            console.print(f"     Lat: {avg_latency:.2f}ms | Loss: {loss_pct}%")

        passed = ramp_data[3]['loss_pct'] < 5 
        
        return {
            "name": self.name,
            "passed": passed,
            "ramp_results": ramp_data 
        }