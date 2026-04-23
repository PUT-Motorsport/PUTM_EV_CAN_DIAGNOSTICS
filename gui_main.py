import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import sys
import os

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
        self.root.title("PUT Motorsport - System Diagnostyczny CAN")
        self.root.geometry("850x650")
        self.root.configure(padx=10, pady=10)

        self.dbc = None
        self.dbc_nodes_map = {} # Do mapowania Noda na jego ID Heartbeatu
        
        self.var_interface = tk.StringVar(value="kvaser")
        self.var_channel = tk.StringVar(value="0")
        self.var_bitrate = tk.StringVar(value="1000000")
        self.var_scan_time = tk.DoubleVar(value=3.0)
        
        self.setup_ui()
        self.load_dbc_data()

    def setup_ui(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.X, expand=False, pady=(0, 10))

        # --- ZAKŁADKA 1: HIL ---
        self.tab_single = ttk.Frame(self.notebook, padding=(10, 10))
        self.notebook.add(self.tab_single, text="🛠️ Diagnostyka Modułu")

        ttk.Label(self.tab_single, text="1. Wybierz Profil / Moduł z DBC:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.target_var = tk.StringVar()
        self.cb_targets = ttk.Combobox(self.tab_single, textvariable=self.target_var, state="readonly", width=35)
        self.cb_targets.grid(row=0, column=1, padx=10, pady=2)
        self.cb_targets.bind("<<ComboboxSelected>>", self.on_target_select)

        ttk.Label(self.tab_single, text="2. Tester WYSYŁA (Atak):").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.cb_tester_tx = ttk.Combobox(self.tab_single, state="readonly", width=35)
        self.cb_tester_tx.grid(row=1, column=1, padx=10, pady=2)

        ttk.Label(self.tab_single, text="3. Tester ODBIERA (Heartbeat):").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.cb_tester_rx = ttk.Combobox(self.tab_single, state="readonly", width=35)
        self.cb_tester_rx.grid(row=2, column=1, padx=10, pady=2)

        frame_buttons = ttk.Frame(self.tab_single)
        frame_buttons.grid(row=3, column=0, columnspan=2, pady=10, sticky=tk.W)
        self.btn_run_tests = ttk.Button(frame_buttons, text="▶ Testy Funkcjonalne", command=self.start_functional_tests)
        self.btn_run_tests.pack(side=tk.LEFT, padx=(0, 10))
        self.btn_run_ramp = ttk.Button(frame_buttons, text="▶ Test Obciążeniowy", command=self.start_ramp_test)
        self.btn_run_ramp.pack(side=tk.LEFT)

        # --- ZAKŁADKA 2: SKANER SIECI ---
        self.tab_network = ttk.Frame(self.notebook, padding=(10, 10))
        self.notebook.add(self.tab_network, text="🏎️ Skaner Bolidu")
        
        ttk.Label(self.tab_network, text="Skaner automatycznie sprawdzi obecność urządzeń z bazy DBC.").pack(anchor=tk.W, pady=(0, 10))
        
        frame_scan_opts = ttk.Frame(self.tab_network)
        frame_scan_opts.pack(anchor=tk.W, fill=tk.X, pady=(0, 10))
        ttk.Label(frame_scan_opts, text="Czas skanowania (s):").pack(side=tk.LEFT)
        ttk.Entry(frame_scan_opts, textvariable=self.var_scan_time, width=5).pack(side=tk.LEFT, padx=5)
        
        self.btn_scan_network = ttk.Button(self.tab_network, text="📡 Skanuj Cały Bolid", command=self.start_network_scan)
        self.btn_scan_network.pack(anchor=tk.W)

        # --- ZAKŁADKA 3: USTAWIENIA SPRZĘTU (Zastępuje YAML) ---
        self.tab_settings = ttk.Frame(self.notebook, padding=(10, 10))
        self.notebook.add(self.tab_settings, text="⚙️ Ustawienia Kvaser/CAN")

        ttk.Label(self.tab_settings, text="Interfejs:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Combobox(self.tab_settings, textvariable=self.var_interface, values=["kvaser", "pcan", "virtual", "socketcan"], state="readonly").grid(row=0, column=1, padx=10)

        ttk.Label(self.tab_settings, text="Kanał (Channel):").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(self.tab_settings, textvariable=self.var_channel).grid(row=1, column=1, padx=10)

        ttk.Label(self.tab_settings, text="Prędkość (Bitrate):").grid(row=2, column=0, sticky=tk.W, pady=5)
        ttk.Combobox(self.tab_settings, textvariable=self.var_bitrate, values=["500000", "1000000"], state="readonly").grid(row=2, column=1, padx=10)

        # --- KONSOLA ---
        frame_console = ttk.LabelFrame(self.root, text="Terminal Wyjściowy", padding=(10, 10))
        frame_console.pack(fill=tk.BOTH, expand=True)

        self.console_text = scrolledtext.ScrolledText(frame_console, bg="#1e1e1e", fg="#00ff00", font=("Consolas", 10))
        self.console_text.pack(fill=tk.BOTH, expand=True)
        sys.stdout = GUIConsoleOutput(self.console_text)

    def load_dbc_data(self):
        print("[INFO] Wczytywanie bazy DBC...")
        try:
            self.dbc = DBCLoader()
            
            # Pobieranie wszystkich ramek
            all_msg_names = sorted([msg.name for msg in self.dbc.db.messages])
            self.cb_tester_tx['values'] = all_msg_names
            self.cb_tester_rx['values'] = all_msg_names

            # Auto-Odkrywanie Node'ów i ich głównych ramek
            dbc_nodes = set()
            for msg in self.dbc.db.messages:
                for sender in msg.senders:
                    if sender and sender != "Vector__XXX":
                        dbc_nodes.add(sender)
                        # Jeśli Node nie ma przypisanej ramki w słowniku, przypisujemy pierwszą znalezioną
                        if sender not in self.dbc_nodes_map:
                            self.dbc_nodes_map[sender] = msg.frame_id

            if hasattr(self.dbc.db, 'nodes'):
                for node in self.dbc.db.nodes:
                    if node.name != "Vector__XXX":
                        dbc_nodes.add(node.name)

            all_targets = sorted(list(dbc_nodes))
            self.cb_targets['values'] = all_targets
            
            if self.cb_targets['values']:
                self.cb_targets.set(self.cb_targets['values'][0])
                self.on_target_select()
                
            print(f"[INFO] Baza gotowa. Znaleziono urządzeń: {len(all_targets)}.")
        except Exception as e:
            print(f"[BŁĄD] {e}")

    def on_target_select(self, event=None):
        target = self.target_var.get()
        node_tx_messages = [msg.name for msg in self.dbc.db.messages if target in msg.senders]
        
        if node_tx_messages:
            self.cb_tester_rx.set(node_tx_messages[0]) 
        else:
            self.cb_tester_rx.set("")
        
        self.cb_tester_tx.set("") 
        print(f"[INFO] Wybrano: {target}. Upewnij się, że ramki są poprawne.")

    def build_system_config(self):
        """Zbiera ustawienia ze wszystkich pól GUI (zastępuje YAML)."""
        # Konwersja kanału: jeśli wpiszesz "0", zostaje int 0 (dla kvasera), jak string "can0" to string.
        channel_val = self.var_channel.get()
        if channel_val.isdigit(): channel_val = int(channel_val)

        return {
            'bus': {
                'interface': self.var_interface.get(),
                'channel': channel_val,
                'bitrate': int(self.var_bitrate.get())
            },
            'paths': {'logs': 'logs', 'reports': 'reports'}
        }

    def build_hil_config(self, base_config):
        """Dodaje ustawienia HIL do głównej konfiguracji."""
        tester_tx_name = self.cb_tester_tx.get() 
        tester_rx_name = self.cb_tester_rx.get() 

        if not tester_tx_name or not tester_rx_name:
            raise ValueError("Wybierz ramki do testu z list rozwijanych!")

        rx_info = self.dbc.get_message_info(tester_tx_name)
        tx_info = self.dbc.get_message_info(tester_rx_name)

        base_config['dut'] = {
            'rx_id': rx_info['id'],  
            'tx_id': tx_info['id'],  
            'rx_dlc': rx_info['dlc'],
            'timeout_ms': 150 
        }
        return base_config

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
            config = self.build_hil_config(self.build_system_config())
            engine = CanEngine(config)
            validator = LibraryFullValidator(engine, config)
            report_path = generate_html_report(validator.run_all(), config['paths']['reports'])
            print(f"[SUKCES] Raport zapisany: {report_path}")
        except Exception as e: print(f"[BŁĄD] {e}")
        finally:
            if 'engine' in locals(): engine.shutdown()
            self.root.after(0, lambda: self.set_buttons_state(tk.NORMAL))

    def start_ramp_test(self):
        self.set_buttons_state(tk.DISABLED)
        threading.Thread(target=self._run_ramp_thread, daemon=True).start()

    def _run_ramp_thread(self):
        try:
            config = self.build_hil_config(self.build_system_config())
            engine = CanEngine(config)
            ramp_test = TestLoadRamp(engine, config)
            result = ramp_test.run()
            report_path = generate_html_report([result], config['paths']['reports'], is_stress_test=True)
            print(f"[ZAKOŃCZONO] Raport zapisany: {report_path}")
        except Exception as e: print(f"[BŁĄD] {e}")
        finally:
            if 'engine' in locals(): engine.shutdown()
            self.root.after(0, lambda: self.set_buttons_state(tk.NORMAL))

    def start_network_scan(self):
        self.set_buttons_state(tk.DISABLED)
        self.console_text.delete(1.0, tk.END)
        threading.Thread(target=self._run_scan_thread, daemon=True).start()

    def _run_scan_thread(self):
        try:
            config = self.build_system_config()
            engine = CanEngine(config)
            
            # Skaner dostaje słownik bezpośrednio wygenerowany z bazy DBC!
            duration = self.var_scan_time.get()
            scanner = NetworkValidator(engine, self.dbc_nodes_map, duration)
            scanner.run_scan()
            
        except Exception as e: print(f"[BŁĄD] {e}")
        finally:
            if 'engine' in locals(): engine.shutdown()
            self.root.after(0, lambda: self.set_buttons_state(tk.NORMAL))

if __name__ == "__main__":
    root = tk.Tk()
    app = CanTesterGUI(root)
    root.mainloop()