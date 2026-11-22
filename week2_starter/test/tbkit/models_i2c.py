"""I2C target model (open-drain), cycle-stepped. Supports write and read,
ACK/NACK by address, and optional clock stretching after each ACK."""


class I2cTarget:
    def __init__(self, scl, sda, address, read_data=None, stretch_cycles=0):
        self.scl_pin, self.sda_pin, self.address = scl, sda, address
        self.read_data = list(read_data or [])
        self.stretch = stretch_cycles
        self.transactions = []      # dicts: addr, rw, data, acked
        self.violations = []        # protocol rule breaks seen on the bus
        self._prev = None
        self._state = "idle"
        self._sda_drive, self._scl_hold = "Z", 0

    def _start(self):
        self._state, self._sr, self._n = "addr", 0, 0
        self._tr = None

    def step(self, levels):
        scl, sda = levels[self.scl_pin], levels[self.sda_pin]
        if self._prev is None:
            self._prev = (scl, sda)
        pscl, psda = self._prev
        self._prev = (scl, sda)
        if self._scl_hold:
            self._scl_hold -= 1
        if pscl == 1 and scl == 1 and psda != sda:     # SDA moved while SCL high
            if sda == 0:
                self._start()
            else:
                self._state = "idle"
                self._sda_drive = "Z"
            return self._drives()
        if self._state == "idle":
            return self._drives()
        if pscl == 0 and scl == 1:                       # rising SCL: sample
            if self._state in ("addr", "wdata"):
                self._sr = (self._sr << 1) | sda
                self._n += 1
            elif self._state == "ack_m":               # controller ACK on read
                self._master_ack = (sda == 0)
        elif pscl == 1 and scl == 0:                     # falling SCL: drive
            if self._state in ("addr", "wdata") and self._n == 8:
                byte = self._sr & 0xFF
                if self._state == "addr":
                    ok = (byte >> 1) == self.address
                    self._tr = {"addr": byte >> 1, "rw": byte & 1, "data": [], "acked": ok}
                    self.transactions.append(self._tr)
                    if not ok:
                        self._state = "idle"
                        return self._drives()
                else:
                    self._tr["data"].append(byte)
                self._sda_drive, self._state = "0", "ack_s"
            elif self._state == "ack_s":                # ACK bit finished
                self._sda_drive = "Z"
                self._scl_hold = self.stretch
                if self._tr["rw"]:
                    self._state, self._n = "rdata", 0
                    self._byte = self.read_data.pop(0) if self.read_data else 0xFF
                    self._tr["data"].append(self._byte)
                    self._drive_read_bit()
                else:
                    self._state, self._sr, self._n = "wdata", 0, 0
            elif self._state == "rdata":
                if self._n == 8:
                    self._sda_drive, self._state = "Z", "ack_m"
                else:
                    self._drive_read_bit()
            elif self._state == "ack_m":
                if self._master_ack:
                    self._state, self._n = "rdata", 0
                    self._byte = self.read_data.pop(0) if self.read_data else 0xFF
                    self._tr["data"].append(self._byte)
                    self._drive_read_bit()
                else:
                    self._state = "idle"
        return self._drives()

    def _drive_read_bit(self):
        self._sda_drive = "0" if not (self._byte >> (7 - self._n)) & 1 else "Z"
        self._n += 1

    def _drives(self):
        return {self.sda_pin: self._sda_drive, self.scl_pin: "0" if self._scl_hold else "Z"}
