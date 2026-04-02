"""
PUTM EV — definicje testów
Importowane przez main.py

Każdy test to funkcja(collector) -> TestResult
"""

from can_tester import (
    TestCase, TestResult, FrameCollector,
    check_present, check_signal_range, check_cycle, check_bit_flag,
)

# ─── ID wiadomości (z DBC) ───────────────────────────────────────────────────
ID = {
    "BMS_HV":    0x45,
    "BMS_LV":    0x55,
    "BMS_LV_T":  0x56,
    "RB_SAFE":   0x25,
    "RB_TEMP":   0x26,
    "RB_MISC":   0x27,
    "DRV_IN":    0x05,
    "FRONT":     0x35,
    "PC_MAIN":   0x10,
    "PC_TEMP":   0x60,
    "PC_LAP":    0x11,
    "PDU_CH":    0x30,
    "PDU_DATA":  0x31,
    "AMK_FR_AV1": 0x287,
    "AMK_FL_AV1": 0x289,
    "AMK_RR_AV1": 0x285,
    "AMK_RL_AV1": 0x283,
    "AMK_FR_AV2": 0x285,
    "AMK_FL_AV2": 0x186,
    "AMK_RR_AV2": 0x184,
    "AMK_RL_AV2": 0x183,
}

AMK_POSITIONS = {
    "FR": {"av1": 0x287, "av2": 0x285},
    "FL": {"av1": 0x289, "av2": 0x186},
    "RR": {"av1": 0x285, "av2": 0x184},
    "RL": {"av1": 0x283, "av2": 0x183},
}

# ─── BMS HV ──────────────────────────────────────────────────────────────────

def _bms_hv_present(c): 
    ok = check_present(c, ID["BMS_HV"])
    return TestResult("", "", ok, actual="" if ok else "brak ramki")

def _bms_hv_voltage(c):
    ok, info = check_signal_range(c, ID["BMS_HV"], "voltage_sum", 20000, 55000)
    return TestResult("", "", ok, actual=info)

def _bms_hv_temp(c):
    ok, info = check_signal_range(c, ID["BMS_HV"], "temp_max", 0, 60)
    return TestResult("", "", ok, actual=info)

def _bms_hv_soc(c):
    ok, info = check_signal_range(c, ID["BMS_HV"], "soc", 10, 1023)
    return TestResult("", "", ok, actual=info)

def _bms_hv_ok_flag(c):
    ok, info = check_bit_flag(c, ID["BMS_HV"], "ok", 1)
    return TestResult("", "", ok, actual=info)

def _bms_hv_precharge(c):
    ok, info = check_bit_flag(c, ID["BMS_HV"], "precharge", 1)
    return TestResult("", "", ok, actual=info)

# ─── BMS LV ──────────────────────────────────────────────────────────────────

def _bms_lv_present(c):
    ok = check_present(c, ID["BMS_LV"])
    return TestResult("", "", ok, actual="" if ok else "brak ramki")

def _bms_lv_voltage(c):
    ok, info = check_signal_range(c, ID["BMS_LV"], "voltage_sum", 1100, 1500)
    return TestResult("", "", ok, actual=info)

def _bms_lv_soc(c):
    ok, info = check_signal_range(c, ID["BMS_LV"], "soc", 20, 255)
    return TestResult("", "", ok, actual=info)

def _bms_lv_temp_present(c):
    ok = check_present(c, ID["BMS_LV_T"])
    return TestResult("", "", ok, actual="" if ok else "brak ramki temp")

def _bms_lv_cells_temp(c):
    decoded = c.get_decoded(ID["BMS_LV_T"])
    if decoded is None:
        return TestResult("", "", False, actual="brak ramki")
    over = {k: v for k, v in decoded.items() if float(v) > 60}
    ok   = len(over) == 0
    info = "OK" if ok else f"przekroczone: {over}"
    return TestResult("", "", ok, actual=info)

# ─── AMK Inverters ───────────────────────────────────────────────────────────

def _amk_factory(pos: str, field: str):
    """Generuje funkcje testowe dla danej pozycji inwertera."""

    def _present_av1(c):
        ok = check_present(c, AMK_POSITIONS[pos]["av1"])
        return TestResult("", "", ok, actual="" if ok else "brak AV1")

    def _present_av2(c):
        ok = check_present(c, AMK_POSITIONS[pos]["av2"])
        return TestResult("", "", ok, actual="" if ok else "brak AV2")

    def _cycle(c):
        ok, info = check_cycle(c, AMK_POSITIONS[pos]["av1"],
                                expected_ms=5.0, tolerance_ms=2.0)
        return TestResult("", "", ok, actual=info)

    def _no_error(c):
        decoded = c.get_decoded(AMK_POSITIONS[pos]["av1"])
        if decoded is None:
            return TestResult("", "", False, actual="brak ramki")
        err = decoded.get("AMK_bError", 0)
        ok  = int(err) == 0
        return TestResult("", "", ok, actual=f"bError={int(err)}")

    def _system_ready(c):
        decoded = c.get_decoded(AMK_POSITIONS[pos]["av1"])
        if decoded is None:
            return TestResult("", "", False, actual="brak ramki")
        rdy = decoded.get("AMK_bSystemReady", 0)
        ok  = int(rdy) == 1
        return TestResult("", "", ok, actual=f"SystemReady={int(rdy)}")

    def _velocity(c):
        ok, info = check_signal_range(c, AMK_POSITIONS[pos]["av1"],
                                       "AMK_ActualVelocity", 0, 6500)
        return TestResult("", "", ok, actual=info)

    def _temp_motor(c):
        ok, info = check_signal_range(c, AMK_POSITIONS[pos]["av2"],
                                       "AMK_TempMotor", -40, 120)
        return TestResult("", "", ok, actual=info)

    def _temp_inv(c):
        ok, info = check_signal_range(c, AMK_POSITIONS[pos]["av2"],
                                       "AMK_TempInverter", -40, 100)
        return TestResult("", "", ok, actual=info)

    def _no_diag(c):
        decoded = c.get_decoded(AMK_POSITIONS[pos]["av2"])
        if decoded is None:
            return TestResult("", "", False, actual="brak AV2")
        diag = decoded.get("AMK_DiagnosisNo", 0)
        ok   = int(diag) == 0
        return TestResult("", "", ok, actual=f"DiagnosisNo={int(diag)}")

    fns = {
        "present_av1":  _present_av1,
        "present_av2":  _present_av2,
        "cycle":        _cycle,
        "no_error":     _no_error,
        "system_ready": _system_ready,
        "velocity":     _velocity,
        "temp_motor":   _temp_motor,
        "temp_inv":     _temp_inv,
        "no_diag":      _no_diag,
    }
    return fns[field]

# ─── Rearbox ─────────────────────────────────────────────────────────────────

def _rb_safety_present(c):
    ok = check_present(c, ID["RB_SAFE"])
    return TestResult("", "", ok, actual="" if ok else "brak ramki")

def _rb_all_safety_flags(c):
    decoded = c.get_decoded(ID["RB_SAFE"])
    if decoded is None:
        return TestResult("", "", False, actual="brak ramki")
    failed = [k for k, v in decoded.items() if int(v) != 1]
    ok = len(failed) == 0
    return TestResult("", "", ok, actual="OK" if ok else f"flagi=0: {failed}")

def _rb_coolant_temp(c):
    ok1, i1 = check_signal_range(c, ID["RB_TEMP"], "coolant_temperature_in",  0, 80)
    ok2, i2 = check_signal_range(c, ID["RB_TEMP"], "coolant_temperature_out", 0, 80)
    ok = ok1 and ok2
    return TestResult("", "", ok, actual=f"in: {i1}  out: {i2}")

def _rb_pressure(c):
    ok1, i1 = check_signal_range(c, ID["RB_MISC"], "coolant_pressure_in",  5, 250)
    ok2, i2 = check_signal_range(c, ID["RB_MISC"], "coolant_pressure_out", 5, 250)
    ok = ok1 and ok2
    return TestResult("", "", ok, actual=f"in: {i1}  out: {i2}")

# ─── Driver / Frontbox ────────────────────────────────────────────────────────

def _drv_present(c):
    ok = check_present(c, ID["DRV_IN"])
    return TestResult("", "", ok)

def _drv_pedal(c):
    ok, info = check_signal_range(c, ID["DRV_IN"], "pedalPosition", 0, 65535)
    return TestResult("", "", ok, actual=info)

def _drv_brake(c):
    ok1, i1 = check_signal_range(c, ID["DRV_IN"], "brakePressureFront", 0, 65535)
    ok2, i2 = check_signal_range(c, ID["DRV_IN"], "brakePressureRear",  0, 65535)
    return TestResult("", "", ok1 and ok2, actual=f"F:{i1}  R:{i2}")

def _apps_ok(c):
    decoded = c.get_decoded(ID["FRONT"])
    if decoded is None:
        return TestResult("", "", False, actual="brak ramki Front_Data")
    impl = decoded.get("apps_implausibility", 0)
    ok   = int(impl) == 0
    return TestResult("", "", ok, actual=f"implausibility={int(impl)}")

# ─── PC Main ─────────────────────────────────────────────────────────────────

def _pc_rtd(c):
    ok, info = check_bit_flag(c, ID["PC_MAIN"], "rtd", 1)
    return TestResult("", "", ok, actual=info)

def _pc_inv_ready(c):
    ok, info = check_bit_flag(c, ID["PC_MAIN"], "invertersReady", 1)
    return TestResult("", "", ok, actual=info)

def _pc_no_inv_errors(c):
    decoded = c.get_decoded(ID["PC_MAIN"])
    if decoded is None:
        return TestResult("", "", False, actual="brak ramki")
    errors = {k: v for k, v in decoded.items()
              if k.startswith("inv_") and k.endswith("_error") and int(v) == 1}
    ok = len(errors) == 0
    return TestResult("", "", ok, actual="OK" if ok else f"błędy: {list(errors.keys())}")

def _pc_motor_temps(c):
    decoded = c.get_decoded(ID["PC_TEMP"])
    if decoded is None:
        return TestResult("", "", False, actual="brak ramki PC_TemperatureData")
    over = {k: v for k, v in decoded.items()
            if "Motor" in k and float(v) > 100}
    ok = len(over) == 0
    return TestResult("", "", ok, actual="OK" if ok else f"przegrzane: {over}")

# ─── PDU ─────────────────────────────────────────────────────────────────────

def _pdu_channels_active(c):
    decoded = c.get_decoded(ID["PDU_CH"])
    if decoded is None:
        return TestResult("", "", False, actual="brak ramki Pdu_Channnel")
    critical = ["pc_status", "pump_status", "inverter_status", "sdc_status"]
    inactive = [k for k in critical if int(decoded.get(k, 0)) == 0]
    ok = len(inactive) == 0
    return TestResult("", "", ok, actual="OK" if ok else f"nieaktywne: {inactive}")

def _pdu_total_current(c):
    ok, info = check_signal_range(c, ID["PDU_DATA"], "total_current", 0, 50000)
    return TestResult("", "", ok, actual=info)


# ─── Rejestr wszystkich testów ────────────────────────────────────────────────

def build_test_suite() -> list[TestCase]:
    tc = TestCase
    suite = [
        # BMS HV
        tc("TC01", "BMS HV — ramka obecna",          _bms_hv_present,   "BMS HV"),
        tc("TC02", "BMS HV — napięcie sumaryczne",   _bms_hv_voltage,   "BMS HV"),
        tc("TC03", "BMS HV — temperatura max < 60°C",_bms_hv_temp,      "BMS HV"),
        tc("TC04", "BMS HV — SOC w zakresie",        _bms_hv_soc,       "BMS HV"),
        tc("TC05", "BMS HV — flaga ok=1",            _bms_hv_ok_flag,   "BMS HV"),
        tc("TC06", "BMS HV — precharge=1",           _bms_hv_precharge, "BMS HV"),

        # BMS LV
        tc("TC07", "BMS LV — ramka obecna",          _bms_lv_present,   "BMS LV"),
        tc("TC08", "BMS LV — napięcie w zakresie",   _bms_lv_voltage,   "BMS LV"),
        tc("TC09", "BMS LV — SOC > 20%",             _bms_lv_soc,       "BMS LV"),
        tc("TC10", "BMS LV — ramka temp. obecna",    _bms_lv_temp_present,"BMS LV"),
        tc("TC11", "BMS LV — ogniwa < 60°C",         _bms_lv_cells_temp,"BMS LV"),

        # AMK FR
        tc("TC12", "AMK FR — AV1 obecna",            _amk_factory("FR","present_av1"),  "AMK"),
        tc("TC13", "AMK FR — AV2 obecna",            _amk_factory("FR","present_av2"),  "AMK"),
        tc("TC14", "AMK FR — cykl 5ms ±2ms",         _amk_factory("FR","cycle"),        "AMK"),
        tc("TC15", "AMK FR — brak błędu",            _amk_factory("FR","no_error"),     "AMK"),
        tc("TC16", "AMK FR — SystemReady=1",          _amk_factory("FR","system_ready"), "AMK"),
        tc("TC17", "AMK FR — prędkość 0..6500 rpm",  _amk_factory("FR","velocity"),     "AMK"),
        tc("TC18", "AMK FR — temp. silnika < 120°C", _amk_factory("FR","temp_motor"),   "AMK"),
        tc("TC19", "AMK FR — temp. inwertera < 100°C",_amk_factory("FR","temp_inv"),    "AMK"),
        tc("TC20", "AMK FR — DiagnosisNo=0",         _amk_factory("FR","no_diag"),      "AMK"),

        # AMK FL
        tc("TC21", "AMK FL — AV1 obecna",            _amk_factory("FL","present_av1"),  "AMK"),
        tc("TC22", "AMK FL — cykl 5ms ±2ms",         _amk_factory("FL","cycle"),        "AMK"),
        tc("TC23", "AMK FL — brak błędu",            _amk_factory("FL","no_error"),     "AMK"),
        tc("TC24", "AMK FL — SystemReady=1",          _amk_factory("FL","system_ready"), "AMK"),
        tc("TC25", "AMK FL — temp. silnika < 120°C", _amk_factory("FL","temp_motor"),   "AMK"),

        # AMK RR
        tc("TC26", "AMK RR — AV1 obecna",            _amk_factory("RR","present_av1"),  "AMK"),
        tc("TC27", "AMK RR — cykl 5ms ±2ms",         _amk_factory("RR","cycle"),        "AMK"),
        tc("TC28", "AMK RR — brak błędu",            _amk_factory("RR","no_error"),     "AMK"),
        tc("TC29", "AMK RR — SystemReady=1",          _amk_factory("RR","system_ready"), "AMK"),
        tc("TC30", "AMK RR — temp. silnika < 120°C", _amk_factory("RR","temp_motor"),   "AMK"),

        # AMK RL
        tc("TC31", "AMK RL — AV1 obecna",            _amk_factory("RL","present_av1"),  "AMK"),
        tc("TC32", "AMK RL — cykl 5ms ±2ms",         _amk_factory("RL","cycle"),        "AMK"),
        tc("TC33", "AMK RL — brak błędu",            _amk_factory("RL","no_error"),     "AMK"),
        tc("TC34", "AMK RL — SystemReady=1",          _amk_factory("RL","system_ready"), "AMK"),
        tc("TC35", "AMK RL — temp. silnika < 120°C", _amk_factory("RL","temp_motor"),   "AMK"),

        # Rearbox
        tc("TC36", "Rearbox — safety obecny",         _rb_safety_present,  "Rearbox"),
        tc("TC37", "Rearbox — wszystkie flagi OK",    _rb_all_safety_flags,"Rearbox"),
        tc("TC38", "Rearbox — temp. cieczy < 80°C",  _rb_coolant_temp,    "Rearbox"),
        tc("TC39", "Rearbox — ciśnienie OK",          _rb_pressure,        "Rearbox"),

        # Driver / Frontbox
        tc("TC40", "Driver — pedalPosition obecny",  _drv_present,  "Frontbox"),
        tc("TC41", "Driver — pedał w zakresie",      _drv_pedal,    "Frontbox"),
        tc("TC42", "Driver — hamulce w zakresie",    _drv_brake,    "Frontbox"),
        tc("TC43", "APPS — brak implausibility",     _apps_ok,      "Frontbox"),

        # PC
        tc("TC44", "PC — RTD=1",                     _pc_rtd,           "PC"),
        tc("TC45", "PC — invertersReady=1",          _pc_inv_ready,     "PC"),
        tc("TC46", "PC — brak błędów inwerterów",    _pc_no_inv_errors, "PC"),
        tc("TC47", "PC — temp. silników OK",         _pc_motor_temps,   "PC"),

        # PDU
        tc("TC48", "PDU — kanały krytyczne aktywne", _pdu_channels_active, "PDU"),
        tc("TC49", "PDU — prąd łączny w zakresie",  _pdu_total_current,   "PDU"),
    ]
    return suite
