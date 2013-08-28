"""
@project MP4 Stream
@author Young Kim (shadowing71@gmail.com)

Helper.py - Helper functions used to parse MP4 files
"""
import struct

### File Handling Helper Functions Below

# EndOfFile - Exception to throw when end of file is reached
class EndOfFile(Exception):
    def __init_(self):
        Exception.__init__(self)
    

# read64 - Reads 64 bits from MP4 in BigEndian
def read64(file):
    data = file.read(8)
    if (data is None or len(data) <> 8):
        raise EndOfFile()
    return struct.unpack(">Q", data)[0]

# read32 - Reads 32 bits from MP4 in BigEndian
def read32(file):
    data = file.read(4)
    if (data is None or len(data) <> 4):
        raise EndOfFile()
    return struct.unpack(">I", data)[0]

# read24 - Reads 24 bits from MP4 in BigEndian
def read24(file):
    data = file.read(3)
    if (data is None or len(data) <> 3):
        raise EndOfFile()
    return struct.unpack(">I", '\x00' + data)[0]

# read16 - Reads 16 bits from MP4 in BigEndian
def read16(file):
    data = file.read(2)
    if (data is None or len(data) <> 2):
        raise EndOfFile()
    return struct.unpack(">H", data)[0]

# read8 - Reads 8 bits from MP4 in BigEndian
def read8(file):
    data = file.read(1)
    if (data is None or len(data) <> 1):
        raise EndofFile()
    return struct.unpack(">B", data)[0]

# type_to_str - Converts MP4 type to Python string
def type_to_str(data):
    a = (data >> 0) & 0xff
    b = (data >> 8) & 0xff
    c = (data >> 16) & 0xff
    d = (data >> 24) & 0xff
    return '%c%c%c%c' % (d, c, b, a)

