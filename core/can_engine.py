import os
import can
from datetime import datetime

class CanEngine:
    def __init__(self, config):
        bus_cfg = config['bus']
        paths = config['paths']
        
        # Tworzenie folderu na logi
        os.makedirs(paths['logs'], exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(paths['logs'], f"trace_{timestamp}.asc")
        
        print(f"Łączenie z {bus_cfg['interface']}:{bus_cfg['channel']} @ {bus_cfg['bitrate']} bps")
        self.bus = can.interface.Bus(
            interface=bus_cfg['interface'],
            channel=bus_cfg['channel'],
            bitrate=bus_cfg['bitrate']
        )
        
        # Automatyczny rejestrator ruchu w tle
        self.logger = can.ASCWriter(log_file)
        self.notifier = can.Notifier(self.bus, [self.logger])
        print(f"Rozpoczęto logowanie do: {log_file}")

    def send(self, msg: can.Message):
        self.bus.send(msg)

    def recv(self, timeout: float = 0.1) -> can.Message:
        return self.bus.recv(timeout)

    def flush_rx_buffer(self):
        """Czyści bufor ze starych ramek przed rozpoczęciem nowego testu."""
        while self.bus.recv(timeout=0.0):
            pass

    def shutdown(self):
        self.notifier.stop()
        self.logger.stop()
        self.bus.shutdown()