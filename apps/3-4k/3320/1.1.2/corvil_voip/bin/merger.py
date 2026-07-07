#!/usr/bin/python

import itertools
import struct

class Packet(object):
    def __init__(self, handle, endianness):
        self.valid = True 
        self.data = handle.read(16)
        if len(self.data) < 16:
            self.invalid()
        else:
            ts, ts_ns, self.cap, self.pkt = struct.unpack(endianness + "IIII", self.data)
            self.time = (ts * 1000000000) + ts_ns
            body = handle.read(self.cap)
            if len(body) != self.cap:
                self.invalid()
            else:
                self.data += body

    def invalid(self):
        self.valid = False
        self.data = None

class PcapMerger(object):

    _MAGIC_NUMBER = 0xa1b2c3d4
    _MAGIC_NUMBER_NS = 0xa1b23c4d

    def __init__(self, f0, f1):
        self.data = f0.read(24)
        other = f1.read(24)

        if len(self.data) != 24 or len(other) != 24:
            raise Exception("not enough data")

        if self.data[0:4] != other[0:4]:
            raise Exception("file formats do not match")

        for endian, magic in itertools.product([">", "<"], [self._MAGIC_NUMBER, self._MAGIC_NUMBER_NS]):
            if struct.pack(endian + "I", magic) == self.data[0:4]:
                self.endian = endian
                break
        else:
            raise Exception("unrecognised")

        self.merge(f0, f1)

    def merge(self, s0, s1):
        valid0 = valid1 = True
        p0 = p1 = None

        while valid0 or valid1:
            if valid0 and not p0:
                p0 = Packet(s0, self.endian)
                valid0 = p0.valid
            if valid1 and not p1:
                p1 = Packet(s1, self.endian)
                valid1 = p1.valid

            if valid0 and not valid1:
                self.data += p0.data
                p0 = None
            elif valid1 and not valid0:
                self.data += p1.data
                p1 = None
            elif valid1 and valid0:
                if p0.time <= p1.time:
                    self.data += p0.data
                    p0 = None
                else:
                    self.data += p1.data
                    p1 = None

