"""Resolve one net from several drivers. Each driver says '0', '1' or 'Z'."""


class Contention(Exception):
    pass


def resolve(drives, pullup=True, net="net"):
    d = [x for x in drives if x != "Z"]
    if "0" in d and "1" in d:
        raise Contention(f"{net}: one driver drives 0 while another drives 1")
    if "0" in d:
        return 0
    if "1" in d:
        return 1
    if pullup:
        return 1
    raise Contention(f"{net}: floating (no driver, no pull-up)")
