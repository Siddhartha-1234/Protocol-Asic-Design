"""Measure I2C bus timing from a trace and compare with the I2C specification
(NXP UM10204, minimum values in microseconds)."""

SPEC_MIN_US = {
    "standard": {"t_low": 4.7, "t_high": 4.0, "t_hd_sta": 4.0, "t_su_sto": 4.0, "t_buf": 4.7},
    "fast":     {"t_low": 1.3, "t_high": 0.6, "t_hd_sta": 0.6, "t_su_sto": 0.6, "t_buf": 1.3},
}


def measure(trace, clk_hz):
    """trace: list of {'SCL': 0/1, 'SDA': 0/1}, one entry per clock cycle.
    Returns the shortest observed value of each interval, in microseconds."""
    us = 1e6 / clk_hz
    seen = {k: [] for k in SPEC_MIN_US["standard"]}
    scl_edge = None          # cycle of the last SCL edge
    start_at = stop_at = None
    for i in range(1, len(trace)):
        a, b = trace[i - 1], trace[i]
        if a["SCL"] != b["SCL"]:
            if scl_edge is not None:
                seen["t_low" if a["SCL"] == 0 else "t_high"].append(i - scl_edge)
            if b["SCL"] == 0 and start_at is not None:
                seen["t_hd_sta"].append(i - start_at)
                start_at = None
            scl_edge = i
        elif b["SCL"] == 1 and a["SDA"] != b["SDA"]:
            if b["SDA"] == 0:                       # START
                start_at = i
                if stop_at is not None:
                    seen["t_buf"].append(i - stop_at)
            else:                                   # STOP
                seen["t_su_sto"].append(i - scl_edge)
                stop_at = i
    return {k: min(v) * us for k, v in seen.items() if v}


def violations(trace, clk_hz, mode="standard"):
    got = measure(trace, clk_hz)
    return {k: (round(v, 3), SPEC_MIN_US[mode][k])
            for k, v in got.items() if v < SPEC_MIN_US[mode][k]}
