import cantools
import os
import glob

class DBCLoader:
    def __init__(self):
        self.db = cantools.database.Database()
        self._load_all_dbc_files()

    def _load_all_dbc_files(self):
        """Pobiera i łączy wszystkie pliki .dbc z folderu database."""
        base_path = os.path.dirname(__file__)
        dbc_pattern = os.path.join(base_path, "*.dbc")
        dbc_files = glob.glob(dbc_pattern)

        if not dbc_files:
            print("[WARNING] Nie znaleziono żadnych plików .dbc w folderze database!")
            return

        for dbc_file in dbc_files:
            try:
                # Dodajemy kolejną bazę do głównego obiektu
                self.db.add_dbc_file(dbc_file)
                print(f"[INFO] Załadowano bazę: {os.path.basename(dbc_file)}")
            except Exception as e:
                print(f"[ERROR] Błąd podczas ładowania {dbc_file}: {e}")

    def get_message_info(self, msg_name):
        """Pobiera ID oraz DLC dla podanej nazwy wiadomości."""
        try:
            msg = self.db.get_message_by_name(msg_name)
            return {
                "id": msg.frame_id,
                "dlc": msg.length,
                "signals": [s.name for s in msg.signals]
            }
        except KeyError:
            print(f"[ERROR] Nie znaleziono wiadomości '{msg_name}' w żadnej bazie DBC!")
            return None

    def get_all_ids(self):
        """Zwraca listę wszystkich ID zdefiniowanych w sieci bolidu."""
        return [msg.frame_id for msg in self.db.messages]

    def decode_message(self, msg_id, data):
        """Dekoduje surowe dane CAN na czytelne wartości sygnałów."""
        try:
            return self.db.decode_message(msg_id, data)
        except Exception:
            return None