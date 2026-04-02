# PUTM CAN Tester

Autonomiczny program do testowania magistrali CAN pojazdu elektrycznego PUTM.
Działa z terminala, nie wymaga TsMaster ani licencji.

## Instalacja

```bash
pip install -r requirements.txt
```

## Pliki DBC

Skopiuj `PUTM_CAN_1.dbc` i `PUTM_CAN_2.dbc` do tego samego folderu.

## Uruchomienie

### PEAK PCAN-USB (Windows / Linux)
```bash
python main.py --interface peak --channel PCAN_USBBUS1
```

### TOSUN / SocketCAN (Linux)
```bash
sudo ip link set can0 up type can bitrate 500000
python main.py --interface socketcan --channel can0
```

### Kvaser
```bash
python main.py --interface kvaser --channel 0
```

### Tryb offline (symulacja, bez sprzętu)
```bash
python main.py --interface virtual --channel virtual0
```

## Opcje

| Flaga | Opis | Domyślnie |
|-------|------|-----------|
| `--interface` | Interfejs CAN | `virtual` |
| `--channel` | Kanał | `virtual0` |
| `--bitrate` | Prędkość [bps] | `500000` |
| `--duration` | Czas zbierania ramek [s] | `10` |
| `--bus-load` | Uruchom test obciążeniowy | wyłączone |
| `--bus-load-duration` | Czas testu bus load [s] | `30` |
| `--report` | Ścieżka do raportu HTML | `PUTM_CAN_Report.html` |
| `--no-report` | Bez raportu HTML | — |
| `--dbc1` | Ścieżka do DBC1 | `PUTM_CAN_1.dbc` |
| `--dbc2` | Ścieżka do DBC2 | `PUTM_CAN_2.dbc` |

## Przykłady

```bash
# Szybki test 10s + raport
python main.py --interface peak --channel PCAN_USBBUS1

# Długi test 30s + bus load 60s
python main.py --interface peak --channel PCAN_USBBUS1 \
               --duration 30 --bus-load --bus-load-duration 60

# Tylko bus load, bez raportu
python main.py --interface socketcan --channel can0 \
               --bus-load --no-report

# Niestandardowe DBC i raport
python main.py --interface peak --channel PCAN_USBBUS1 \
               --dbc1 ~/projekty/PUTM_CAN_1.dbc \
               --dbc2 ~/projekty/PUTM_CAN_2.dbc \
               --report wyniki/sesja_01.html
```

## Struktura projektu

```
putm_tester/
├── main.py           ← punkt wejścia (uruchamiaj ten)
├── can_tester.py     ← silnik: połączenie, kolektor, runner
├── putm_tests.py     ← 49 definicji testów PUTM
├── bus_load_test.py  ← test obciążeniowy (można też uruchomić osobno)
├── report.py         ← generator raportu HTML
├── requirements.txt
└── README.md
```

## Pokrycie testów (49 testów)

| Kategoria | Testy | Co sprawdza |
|-----------|-------|-------------|
| BMS HV | TC01–TC06 | obecność, napięcie, temperatura, SOC, ok, precharge |
| BMS LV | TC07–TC11 | napięcie 12V, SOC, 8x temperatura ogniw |
| AMK (4x) | TC12–TC35 | cykl 5ms, SystemReady, bError, prędkość, temp. |
| Rearbox | TC36–TC39 | flagi safety, chłodzenie, ciśnienie |
| Frontbox | TC40–TC43 | pedał, hamulce, APPS implausibility |
| PC | TC44–TC47 | RTD, invertersReady, błędy inwerterów, temp. |
| PDU | TC48–TC49 | kanały aktywne, prąd łączny |
| Bus Load | osobny | baseline %, peak %, error frames, ECU alive |

## Dodawanie własnych testów

W `putm_tests.py` dodaj funkcję i zarejestruj ją w `build_test_suite()`:

```python
def _moj_test(c: FrameCollector) -> TestResult:
    ok, info = check_signal_range(c, 0x45, "temp_avg", 0, 55)
    return TestResult("", "", ok, actual=info)

# W build_test_suite():
tc("TC50", "BMS HV — temp avg < 55°C", _moj_test, "BMS HV"),
```
