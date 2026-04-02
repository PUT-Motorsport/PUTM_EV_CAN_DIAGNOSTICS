from time import time

class TestRobustness:
    name = "Test odporności (DLC Fuzzing)"

    def __init__(self, engine, config):
        self.engine = engine
        self.rx_id = config['dut']['rx_id']

    def run(self) -> dict:
        bad_msg = can.Message(arbitration_id=self.rx_id, data=[0xFF], dlc=1)
        self.engine.send(bad_msg)
        
        time.sleep(0.1)
        
        ping = can.Message(arbitration_id=self.rx_id, data=[0]*8)
        self.engine.send(ping)
        
        res = self.engine.recv(0.2)
        passed = res is not None 
        
        return {
            "name": self.name,
            "passed": passed,
            "details": "System stabilny po błędnym DLC" if passed else "Brak odpowiedzi - możliwy crash"
        }