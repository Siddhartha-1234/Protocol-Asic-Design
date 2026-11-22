"""Pure-Python co-simulation: one engine lane + protocol device models on shared nets."""
from tbkit.bus import resolve


def simulate(lane, devices, cycles, stop=None, trace=None):
    """Run `cycles` clock cycles. Nets are named by the program's .pin lines.
    devices: list of model objects with step(levels) -> {net: '0'|'1'|'Z'}.
    stop(lane): optional predicate; returns early when it is true.
    trace: optional list; each cycle appends the dict of net levels."""
    pins = lane.cfg["pins"]                       # {'p0': 'TX', ...}
    dev_drives = [dict() for _ in devices]
    for _ in range(cycles):
        out = lane.pins_out()
        levels = {}
        for p, net in pins.items():
            drivers = [out[int(p[1])]] + [d.get(net, "Z") for d in dev_drives]
            levels[net] = resolve(drivers, pullup=True, net=net)
        if trace is not None:
            trace.append(levels)
        lane.step([levels.get(pins.get(f"p{i}"), 1) for i in range(4)])
        dev_drives = [dev.step(levels) for dev in devices]
        if stop and stop(lane):
            return True
    return False
