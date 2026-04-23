import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import yaml
import sys

from database.dbc_loader import DBCLoader
from core.can_engine import CanEngine
from core.report_gen import generate_html_report
from tests.test_procedure import LibraryFullValidator
from tests.test_load_ramp import TestLoadRamp
from tests.test_network import NetworkValidator

class GUIConsoleOutput:
    def __init__(self, text_widget):
        self.text_widget = text_widget
    def write(self, string):
        self.text_widget.insert(tk.END, string)
        self.text_widget.see(tk.END)
    def flush(self): pass

class CanTesterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("PUT Motorsport - Vehicle System Tester")
        self.root.geometry("850x650")
        self.root.configure(padx=10, pady=10)

        self.config = None
        self.dbc = None
        
        self.setup_ui()
        self.load_initial_data()

    def setup_ui(self):
        # --- ZAKŁADKI (TABS) ---
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.X, expand=False, pady=(0, 10))

        self.tab_single = ttk.Frame(self.notebook, padding=(10, 10))
        self.notebook.add(self.tab_single, text="🛠️ Diagnostyka Modułu (HIL)")

        self.tab_network = ttk.Frame(self.notebook, padding=(10, 10))
        self.notebook.add(self.tab_network, text="🏎️ Skaner Sieci Bolidu")

        # --- ZAWARTOSĆ KARTY 1 (HIL) - PEŁNA DYNAMIKA ---
        ttk.Label(self.tab_single, text="1. Wybierz Profil / Moduł z DBC:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.target_var = tk.StringVar()
        self.cb_targets = ttk.Combobox(self.tab_single, textvariable=self.target_var, state="readonly", width=35)
        self.cb_targets.grid(row=0, column=1, padx=10, pady=2)
        self.cb_targets.bind("<<ComboboxSelected>>", self.on_target_select)

        # Dynamiczne listy ramek z DBC
        ttk.Label(self.tab_single, text="2. Tester WYSYŁA (Bodziec ataku):").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.cb_tester_tx = ttk.Combobox(self.tab_single, state="readonly", width=35)
        self.cb_tester_tx.grid(row=1, column=1, padx=10, pady=2)

        ttk.Label(self.tab_single, text="3. Tester ODBIERA (Heartbeat płytki):").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.cb_tester_rx = ttk.Combobox(self.tab_single, state="readonly", width=35)
        self.cb_tester_rx.grid(row=2, column=1, padx=10, pady=2)

        # Przyciski
        frame_buttons = ttk.Frame(self.tab_single)
        frame_buttons.grid(row=3, column=0, columnspan=2, pady=10, sticky=tk.W)
        self.btn_run_tests = ttk.Button(frame_buttons, text="▶ Testy Funkcjonalne (Atak)", command=self.start_functional_tests)
        self.btn_run_tests.pack(side=tk.LEFT, padx=(0, 10))
        self.btn_run_ramp = ttk.Button(frame_buttons, text="▶ Test Obciążeniowy (Stress)", command=self.start_ramp_test)
        self.btn_run_ramp.pack(side=tk.LEFT)

        # --- ZAWARTOŚĆ KARTY 2 (SKANER SIECI) ---
        lbl_net = ttk.Label(self.tab_network, text="Skanuje magistralę w poszukiwaniu urządzeń zdefiniowanych w config.yaml")
        lbl_net.pack(anchor=tk.W, pady=(0, 10))
        
        self.btn_scan_network = ttk.Button(self.tab_network, text="📡 Skanuj Cały Bolid", command=self.start_network_scan)
        self.btn_scan_network.pack(anchor=tk.W)

        # --- WSPÓLNA KONSOLA ---
        frame_console = ttk.LabelFrame(self.root, text="Terminal Wyjściowy", padding=(10, 10))
        frame_console.pack(fill=tk.BOTH, expand=True)

        self.console_text = scrolledtext.ScrolledText(frame_console, bg="#1e1e1e", fg="#00ff00", font=("Consolas", 10))
        self.console_text.pack(fill=tk.BOTH, expand=True)
        sys.stdout = GUIConsoleOutput(self.console_text)

    def load_initial_data(self):
        print("[INFO] Start systemu...")
        try:
            with open("config.yaml", "r", encoding="utf-8") as f:
                self.config = yaml.safe_load(f)
            
            self.dbc = DBCLoader()
            
            all_msg_names = sorted([msg.name for msg in self.dbc.db.messages])
            self.cb_tester_tx['values'] = all_msg_names
            self.cb_tester_rx['values'] = all_msg_names

            dbc_nodes = set()
            for msg in self.dbc.db.messages:
                for sender in msg.senders:
                    if sender and sender != "Vector__XXX":
                        dbc_nodes.add(sender)

            if hasattr(self.dbc.db, 'nodes'):
                for node in self.dbc.db.nodes:
                    if node.name != "Vector__XXX":
                        dbc_nodes.add(node.name)

            # 3. Łączenie Nodów z DBC i Profili z YAML
            yaml_targets = list(self.config.get("targets", {}).keys())
            all_targets = sorted(list(set(yaml_targets + list(dbc_nodes))))
            
            self.cb_targets['values'] = all_targets
            
            if self.cb_targets['values']:
                self.cb_targets.set(self.cb_targets['values'][0])
                self.on_target_select()
                
            print(f"[INFO] Zbudowano drzewo z {len(all_targets)} profilami/modułami. Gotowe do testów!")
        except Exception as e:
            print(f"[BŁĄD] {e}")
            

    def on_target_select(self, event=None):
        """Auto-uzupełnianie ramek RX/TX na podstawie wybranego profilu lub Noda z DBC."""
        target = self.target_var.get()
        
        if target in self.config.get("targets", {}):
            settings = self.config["targets"][target]
            self.cb_tester_tx.set(settings['rx_frame']) 
            self.cb_tester_rx.set(settings['tx_frame']) 
        else:
            node_tx_messages = [msg.name for msg in self.dbc.db.messages if target in msg.senders]
            
            if node_tx_messages:
                self.cb_tester_rx.set(node_tx_messages[0]) 
            else:
                self.cb_tester_rx.set("")
            
            self.cb_tester_tx.set("") 
            print(f"[INFO] Wybrano moduł z DBC: {target}. Sprawdź i uzupełnij ramki testowe.")

    def build_test_config(self):
        """Zamiast YAML, buduje config na podstawie TEGO CO WIDAĆ W DROPDOWNACH."""
        tester_tx_name = self.cb_tester_tx.get() 
        tester_rx_name = self.cb_tester_rx.get() 

        if not tester_tx_name or not tester_rx_name:
            raise ValueError("Musisz wybrać ramki do wysyłania i odbierania z list rozwijanych!")

        rx_info = self.dbc.get_message_info(tester_tx_name)
        tx_info = self.dbc.get_message_info(tester_rx_name)

        return {
            'bus': self.config['bus'],
            'dut': {
                'rx_id': rx_info['id'],  
                'tx_id': tx_info['id'],  
                'rx_dlc': rx_info['dlc'],
                'timeout_ms': 150 
            },
            'paths': self.config['paths']
        }

    def set_buttons_state(self, state):
        self.btn_run_tests.config(state=state)
        self.btn_run_ramp.config(state=state)
        self.btn_scan_network.config(state=state)

    # --- WĄTKI URUCHAMIAJĄCE ---
    def start_functional_tests(self):
        self.set_buttons_state(tk.DISABLED)
        threading.Thread(target=self._run_functional_thread, daemon=True).start()

    def _run_functional_thread(self):
        try:
            print("\n[INFO] Budowanie konfiguracji HIL...")
            config = self.build_test_config()
            engine = CanEngine(config)
            validator = LibraryFullValidator(engine, config)
            report_path = generate_html_report(validator.run_all(), config['paths']['reports'])
            print(f"[SUKCES] Raport: {report_path}")
        except Exception as e: print(f"[BŁĄD] {e}")
        finally:
            if 'engine' in locals(): engine.shutdown()
            self.root.after(0, lambda: self.set_buttons_state(tk.NORMAL))

    def start_ramp_test(self):
        self.set_buttons_state(tk.DISABLED)
        threading.Thread(target=self._run_ramp_thread, daemon=True).start()

    def _run_ramp_thread(self):
        try:
            print("\n[INFO] Budowanie konfiguracji HIL do testu obciążeniowego...")
            config = self.build_test_config()
            engine = CanEngine(config)
            
            ramp_test = TestLoadRamp(engine, config)
            result = ramp_test.run()
            
            report_path = generate_html_report([result], config['paths']['reports'], is_stress_test=True)
            
            if result['passed']:
                print(f"\n[SUKCES] Płytka przeszła testy! Raport: {report_path}")
            else:
                print(f"\n[PORAŻKA] Zbyt duża utrata ramek. Raport: {report_path}")

        except Exception as e:
            print(f"\n[BŁĄD] Wystąpił błąd krytyczny: {e}")

    def start_network_scan(self):
        self.set_buttons_state(tk.DISABLED)
        self.console_text.delete(1.0, tk.END)
        threading.Thread(target=self._run_scan_thread, daemon=True).start()

    def _run_scan_thread(self):
        try:
            config = {'bus': self.config['bus'], 'paths': self.config['paths']}
            engine = CanEngine(config)
            scanner = NetworkValidator(engine, self.config['network_scan'])
            scanner.run_scan()
        except Exception as e: print(f"[BŁĄD] {e}")
        finally:
            if 'engine' in locals(): engine.shutdown()
            self.root.after(0, lambda: self.set_buttons_state(tk.NORMAL))

if __name__ == "__main__":
    root = tk.Tk()
    app = CanTesterGUI(root)
    root.mainloop()