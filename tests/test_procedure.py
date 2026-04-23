import time
import can
from rich.console import Console

console = Console()

class LibraryFullValidator:
    """
    Uniwersalna procedura walidacyjna dla biblioteki CAN (STM32 / ROS2).
    Realizuje punkty kontrolne od a) do i).
    """

    def __init__(self, engine, config):
        self.engine = engine
        self.config = config
        self.rx_id = config['dut']['rx_id']
        self.tx_id = config['dut']['tx_id']
        self.timeout = config['dut']['timeout_ms'] / 1000.0

    def run_all(self):
        """Uruchamia pełny zestaw testów ujednolicony dla każdej płytki."""
        results = []
        
        # a, b, f) Test podstawowy: Wysył, Odbiór i Czas reakcji
        results.append(self._test_ping_pong())

        # i) Reakcja na ramkę o złych parametrach (DLC)
        results.append(self._test_invalid_dlc())

        # d) Reakcja na ramkę spoza DBC (nieznane ID)
        results.append(self._test_unknown_id())

        # c) Reakcja na niepoprawną ramkę (pusta / DLC 0)
        results.append(self._test_malformed_frame())

        # e) Nieautoryzowany dostęp (ID chronione)
        results.append(self._test_unauthorized_access())

        # g, h) Reakcja na brak możliwości komunikacji (Stress/Overflow/Bus-off)
        results.append(self._test_bus_off_recovery())

        return results

    # --- Implementacja konkretnych scenariuszy ---

    def _test_ping_pong(self):
        """a, b, f) Sprawdzenie poprawnego obiegu danych i jittera."""
        self.engine.flush_rx_buffer()
        t_start = time.perf_counter()
        
        # Wysyłamy testowy wzorzec danych
        test_data = [0xDE, 0xAD, 0xBE, 0xEF, 0x01, 0x02, 0x03, 0x04]
        self.engine.send(can.Message(arbitration_id=self.rx_id, data=test_data))
        
        rx = self.engine.recv(self.timeout)
        t_end = time.perf_counter()
        
        passed = rx is not None and rx.arbitration_id == self.tx_id
        rtt = (t_end - t_start) * 1000 if passed else 0
        
        return {
            "name": "Odbiór/Wysył/Czas (a,b,f)", 
            "passed": passed, 
            "actual": f"RTT: {rtt:.2f}ms" if passed else "Brak odpowiedzi (Timeout)"
        }

    def _test_invalid_dlc(self):
        """i) Wysyłka ramki z DLC mniejszym niż zadeklarowane w bibliotece."""
        # Wysyłamy DLC=1 zamiast 8
        self.engine.send(can.Message(arbitration_id=self.rx_id, data=[0x42], dlc=1))
        time.sleep(0.05)
        
        # Sprawdzamy, czy system nie doznał awarii i nadal reaguje na poprawne zapytania
        alive = self._check_if_alive()
        return {
            "name": "Błędne DLC (i)", 
            "passed": alive, 
            "actual": "System stabilny" if alive else "CRASH: Brak reakcji po błędnym DLC"
        }

    def _test_unknown_id(self, unknown_id=0x7EE):
        # 1. Wysyłamy obce ID używając obiektu z python-can
        msg = can.Message(
            arbitration_id=unknown_id, 
            data=[0, 0, 0, 0, 0, 0, 0, 0], 
            is_extended_id=False
        )
        self.engine.send(msg)
        
        # 2. Nasłuchujemy krótko, czy płytka w ogóle zareaguje na to ID
        rx_msg = self.engine.recv(0.15) 
        
        if rx_msg is not None:
            # Tester wykrył jakikolwiek ruch po wysłaniu obcego ID (nawet jeśli to naturalny ruch płytki)
            return {"status": "FAIL", "actual": f"BŁĄD: Wykryto odpowiedź po obcym ID: 0x{rx_msg.arbitration_id:03X}"}
            
        return {"status": "PASS", "actual": "Brak reakcji na obce ID (Filtry OK)"}

    def _test_malformed_frame(self):
        """c) Reakcja na ramkę o zerowej długości danych."""
        self.engine.send(can.Message(arbitration_id=self.rx_id, data=[], dlc=0))
        time.sleep(0.05)
        
        alive = self._check_if_alive()
        return {
            "name": "Niepoprawna ramka - DLC 0 (c)", 
            "passed": alive, 
            "actual": "Stabilny" if alive else "Niestabilny / Brak reakcji"
        }

    def _test_unauthorized_access(self):
        """e) Próba wysyłki na ID chronione (np. dostęp do konfiguracji)."""
        protected_id = 0x040  # Przykład ID krytycznego dla konfiguracji
        self.engine.send(can.Message(arbitration_id=protected_id, data=[0xDE, 0xAD]))
        
        # System powinien odrzucić ramkę lub nie wysyłać potwierdzenia aplikacji
        rx = self.engine.recv(0.1)
        passed = rx is None
        return {
            "name": "Nieautoryzowany dostęp (e)", 
            "passed": passed, 
            "actual": "Zablokowano dostęp" if passed else "BŁĄD: System zareagował na ID chronione"
        }

    def _test_bus_off_recovery(self):
        """g, h) Symulacja przeciążenia RX i sprawdzenie powrotu do pracy."""
        # "Zasypujemy" bibliotekę dużą liczbą ramek (Stress Test)
        for i in range(50):
            msg = can.Message(arbitration_id=self.rx_id, data=[i]*8)
            self.engine.send(msg)
            
        # Dajemy czas na ewentualny proces Bus-Off Recovery (Auto-Bus-On)
        time.sleep(0.2)
        alive = self._check_if_alive()
        
        return {
            "name": "Bus-Off Recovery / RX Overflow (g, h)", 
            "passed": alive, 
            "actual": "System odzyskał łączność" if alive else "FAIL: System zawisł po przeciążeniu"
        }

    def _check_if_alive(self):
        """Metoda pomocnicza weryfikująca, czy węzeł nadal komunikuje się z testerem."""
        self.engine.flush_rx_buffer()
        ping_msg = can.Message(arbitration_id=self.rx_id, data=[0x00]*8)
        self.engine.send(ping_msg)
        return self.engine.recv(self.timeout) is not None