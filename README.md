# PUTM CAN Framework — Walidacja STM32 & ROS2

Automatyczne środowisko testowe typu Hardware-in-the-Loop (HIL) do badania wydajności, opóźnień i odporności na błędy autorskiej biblioteki CAN dla mikrokontrolerów STM32 oraz systemu ROS2.

Narzędzie generuje ruch na magistrali, weryfikuje poprawne odpowiedzi od układu (Device Under Test) oraz generuje raporty HTML i zrzuty ruchu (`.asc`).

## Instalacja

Zainstaluj wymagane pakiety Pythona (w tym dodany parser plików konfiguracyjnych):

    pip install -r requirements.txt

*(Wymaga pakietów: `python-can`, `cantools`, `rich`, `pyyaml`)*

## Konfiguracja (Plik `config.yaml`)

W nowej architekturze nie musisz już podawać długich flag w konsoli. Wszystkie główne parametry testowe, sprzętowe i adresacyjne są scentralizowane w pliku `config.yaml`.

```yaml
# Ustawienia magistrali (domyślnie 1 Mbps)
bus:
  interface: "virtual"   # Opcje: peak, socketcan, kvaser, virtual
  channel: "virtual0"    # Opcje: PCAN_USBBUS1, can0, virtual0
  bitrate: 1000000

# Parametry testowanego układu (Device Under Test - DUT)
dut:
  rx_id: 0x100      # ID, na które STM32 oczekuje wiadomości
  tx_id: 0x101      # ID, na którym STM32 odsyła odpowiedzi
  timeout_ms: 50    # Maksymalny czas odpowiedzi [ms]

# Foldery wyjściowe
paths:
  logs: "logs"
  reports: "reports"