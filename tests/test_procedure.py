import time
import can

class LibraryFullValidator:
    """Uniwersalna procedura walidacyjna (HIL) dla urządzeń na szynie CAN."""

    def __init__(self, engine, config):
        self.engine = engine
        self.rx_id = config['dut']['rx_id']
        self.tx_id = config['dut']['tx_id']
        self.timeout = config['dut']['timeout_ms'] / 1000.0

    def run_all(self):
        return [
            self._test_ping_pong(),
            self._test_invalid_dlc(),
            self._test_unknown_id(),
            self._test_malformed_frame(),
            self._test_unauthorized_access(),
            self._test_bus_off_recovery()
        ]

    # --- FUNKCJE POMOCNICZE (Inteligentne filtrowanie) ---

    def _wait_for_tx(self, expected_id, timeout):
        """Czeka na konkretną ramkę, ignorując całkowicie szum tła z innych urządzeń."""
        t_start = time.time()
        while time.time() - t_start < timeout:
            msg = self.engine.recv(0.05)
            if msg and msg.arbitration_id == expected_id:
                return msg
        return None

    def _check_if_alive(self):
        """Sprawdza, czy płytka przetrwała poprzedni atak i nadal odpowiada."""
        self.engine.flush_rx_buffer()
        self.engine.send(can.Message(arbitration_id=self.rx_id, data=[0]*8, is_extended_id=False))
        return self._wait_for_tx(self.tx_id, self.timeout) is not None

    # --- WŁAŚCIWE SCENARIUSZE TESTOWE ---

    def _test_ping_pong(self):
        self.engine.flush_rx_buffer()
        t_start = time.perf_counter()
        
        self.engine.send(can.Message(arbitration_id=self.rx_id, data=[0xDE, 0xAD, 0xBE, 0xEF, 1, 2, 3, 4]))
        rx = self._wait_for_tx(self.tx_id, self.timeout)
        t_end = time.perf_counter()
        
        passed = rx is not None
        return {
            "name": "Odbiór/Wysył/Czas (a,b,f)", 
            "passed": passed, 
            "actual": f"RTT: {(t_end - t_start) * 1000:.2f}ms" if passed else "Timeout"
        }

    def _test_invalid_dlc(self):
        self.engine.send(can.Message(arbitration_id=self.rx_id, data=[0x42], dlc=1))
        time.sleep(0.05)
        alive = self._check_if_alive()
        return {"name": "Błędne DLC (i)", "passed": alive, "actual": "Stabilny" if alive else "CRASH"}

    def _test_unknown_id(self, unknown_id=0x7EE):
        self.engine.flush_rx_buffer()
        self.engine.send(can.Message(arbitration_id=unknown_id, data=[0]*8))
        
        t_start = time.time()
        while time.time() - t_start < 0.15:
            rx = self.engine.recv(0.05)
            # Jeśli odebraliśmy coś, co NIE JEST naturalnym biciem serca testowanej płytki ani BMS:
            if rx and rx.arbitration_id not in [self.tx_id, 0x055]: 
                return {"name": "Nieznane ID (d)", "passed": False, "actual": f"Błąd: Zareagował na 0x{rx.arbitration_id:03X}"}
                
        return {"name": "Nieznane ID (d)", "passed": True, "actual": "Zignorowano poprawnie"}

    def _test_malformed_frame(self):
        self.engine.send(can.Message(arbitration_id=self.rx_id, data=[], dlc=0))
        time.sleep(0.05)
        alive = self._check_if_alive()
        return {"name": "Pusta ramka (c)", "passed": alive, "actual": "Stabilny" if alive else "CRASH"}

    def _test_unauthorized_access(self):
        protected_id = 0x040
        self.engine.flush_rx_buffer()
        self.engine.send(can.Message(arbitration_id=protected_id, data=[0xDE, 0xAD]))
        rx = self._wait_for_tx(protected_id, 0.1)
        passed = rx is None
        return {"name": "Nieautoryzowany dostęp (e)", "passed": passed, "actual": "Zablokowano" if passed else "Błąd: Zareagował"}

    def _test_bus_off_recovery(self):
        for i in range(50):
            self.engine.send(can.Message(arbitration_id=self.rx_id, data=[i]*8))
        time.sleep(0.2)
        alive = self._check_if_alive()
        return {"name": "Bus-Off Recovery (g,h)", "passed": alive, "actual": "Odzyskał łączność" if alive else "Zawisł"}