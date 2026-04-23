import time
import can
import statistics

class TestLoadRamp:
    """Test stabilności płytki w warunkach potężnego zanieczyszczenia magistrali."""
    name = "Test stabilności pod narastającym obciążeniem (Stress Test)"

    def __init__(self, engine, config):
        self.engine = engine
        self.rx_id = config['dut']['rx_id']
        self.tx_id = config['dut']['tx_id']
        self.timeout = config['dut']['timeout_ms'] / 1000.0
        self.steps = [0, 20, 40, 60, 80, 90] 

    def run(self) -> dict:
        self.engine.flush_rx_buffer()
        ramp_data = []

        for load in self.steps:
            bg_frames_count = load * 8 
            latencies = []
            lost = 0
            
            for i in range(50):
                # 1. Generowanie szumu na szynie
                for _ in range(bg_frames_count // 10):
                    self.engine.send(can.Message(arbitration_id=0x7FF, data=[0]*8))
                
                # 2. Wysyłanie właściwej ramki do płytki
                t_start = time.perf_counter()
                self.engine.send(can.Message(arbitration_id=self.rx_id, data=[i, 0, 0, 0]))
                
                # 3. Inteligentne nasłuchiwanie (ignorujemy nasz własny szum)
                t_wait = time.perf_counter()
                res = None
                while time.perf_counter() - t_wait < self.timeout:
                    msg = self.engine.recv(0.02)
                    if msg and msg.arbitration_id == self.tx_id:
                        res = msg
                        break

                if res:
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

        # Test uznajemy za zaliczony, jeśli przy 60% obciążenia strata jest mniejsza niż 5%
        passed = ramp_data[3]['loss_pct'] < 5 
        
        return {
            "name": self.name,
            "passed": passed,
            "ramp_results": ramp_data 
        }