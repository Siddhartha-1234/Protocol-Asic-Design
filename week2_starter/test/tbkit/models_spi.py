"""SPI target (device) model, modes 0-3, cycle-stepped."""


class SpiTarget:
    def __init__(self, sck, mosi, miso, cs, mode=0, reply=None, msb_first=True):
        self.p = dict(sck=sck, mosi=mosi, miso=miso, cs=cs)
        self.cpol, self.cpha = mode >> 1, mode & 1
        self.reply = list(reply or [])     # bytes the target sends back
        self.msb_first = msb_first
        self.frames = []                   # list of (mosi_bytes, miso_bytes)
        self._prev_sck, self._prev_cs = None, 1
        self._miso, self._loaded = "Z", False

    def _drive_bit(self):
        if self._nbit == 0 and not self._loaded:
            self._out_byte = self.reply.pop(0) if self.reply else 0xFF
            self._loaded = True
        idx = 7 - self._nbit if self.msb_first else self._nbit
        self._miso = str((self._out_byte >> idx) & 1)

    def _sample(self, bit):
        self._sr = (self._sr << 1 | bit) if self.msb_first else (self._sr | bit << self._nbit)
        self._nbit += 1
        if self._nbit == 8:
            self._mosi_bytes.append(self._sr & 0xFF)
            self._miso_bytes.append(self._out_byte)
            self._sr, self._nbit, self._loaded = 0, 0, False

    def step(self, levels):
        sck, cs = levels[self.p["sck"]], levels[self.p["cs"]]
        if self._prev_sck is None:
            self._prev_sck = sck
        if self._prev_cs == 1 and cs == 0:              # frame starts
            self._mosi_bytes, self._miso_bytes = [], []
            self._sr, self._nbit, self._loaded = 0, 0, False
            if self.cpha == 0:                          # first bit valid before first edge
                self._drive_bit()
        elif self._prev_cs == 0 and cs == 1:            # frame ends
            if self._loaded and self._nbit == 0:        # byte loaded but never clocked
                self.reply.insert(0, self._out_byte)
            self.frames.append((self._mosi_bytes, self._miso_bytes))
            self._miso, self._loaded = "Z", False
        elif cs == 0 and sck != self._prev_sck:
            leading = (sck != self.cpol)                # edge away from the idle level
            if leading == (self.cpha == 0):
                self._sample(levels[self.p["mosi"]])
            else:
                self._drive_bit()
        self._prev_sck, self._prev_cs = sck, cs
        return {self.p["miso"]: self._miso}
