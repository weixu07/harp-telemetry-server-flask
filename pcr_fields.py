import time
from typing import List, Optional,Tuple
from dataclasses import dataclass

class PcrField():
    rean_id: int
    '''The Reanimate ID for this PCR field'''
    harp_id: int
    '''The Harp ID for this PCR field'''
    name: str
    '''Human readable name for this PCR field'''
    data: bytes
    '''Copy of the data for this field'''

    def __init__(self, rean_id: int, harp_id: int, name: str):
        self.rean_id = rean_id
        self.harp_id = harp_id
        self.name = name
        self.data = b''
        self.packet_id = -1

    def from_buf(self, data: bytes) -> int:
        '''
        Parse this PCRs data from a buffer, returning the number of bytes
        consumed.
        '''
        return 0

    def to_human_readable(self) -> str:
        return f'{self.name.ljust(25, " ")}: {self.data.hex()}'



class IntPcrField(PcrField):
    '''Signed integer PCR field'''
    int_sz: int
    '''Integer size in bytes'''
    int_val: int
    '''Parsed integer value'''

    def __init__(self, rean_id: int, harp_id: int, name: str, int_sz: int):
        super().__init__(rean_id, harp_id, name)
        self.int_sz = int_sz
        self.int_val = 0

    def from_buf(self, data: bytes) -> int:
        if len(data) < self.int_sz:
            raise ValueError('Data too short')
        self.data = data[0:self.int_sz]
        self.int_val = int.from_bytes(self.data, byteorder='big', signed=True)
        return self.int_sz

    def to_human_readable(self) -> str:
        return f'{self.name.ljust(25, " ")}: {self.int_val}'



class UintPcrField(IntPcrField):
    '''Unsigned Integer PCR field'''
    def from_buf(self, data: bytes) -> int:
        if len(data) < self.int_sz:
            raise ValueError('Data too short')
        self.data = data[0:self.int_sz]
        self.int_val = int.from_bytes(self.data, byteorder='big', signed=False)
        return self.int_sz

    def to_human_readable(self) -> str:
        return f'{self.name.ljust(25, " ")}: {self.int_val} ({hex(self.int_val)})'



class DateTimePcrField(UintPcrField):
    '''Date time PCR field derived from epoch in seconds'''
    def __init__(self, rean_id: int, harp_id: int, name: str):
        super().__init__(rean_id, harp_id, name, 4)

    def to_human_readable(self) -> str:
        '''Epoch converted to machine local datetime'''
        datestr = time.strftime('%H:%M:%S %Z %m/%d/%Y', time.localtime(self.int_val))
        return f'{self.name.ljust(25, " ")}: {datestr} ({self.int_val})'

@dataclass
class BeaconData():
    mac_address: bytes
    rssi: int
    tx_power: int
    eye_flags: int
    temperature: Optional[int] = None
    humidity: Optional[int] = None
    movement_count: Optional[int] = None
    movement_angle: Optional[Tuple[int, int, int]] = None
    battery_voltage: Optional[int] = None


class BeaconPcrField(PcrField):
    def __init__(self, rean_id: int, harp_id: int, name: str):
        super().__init__(rean_id, harp_id, name)
        self.beacons = []
        self.count = 0
    
    def from_buf(self, data: bytes) -> int:
        self.count = data[0]
        pos = 1
        for i in range(self.count):
            beacon= BeaconData(None, None, None, None)
            if len(data) >= pos + 9:
                beacon.mac_address = data[pos:pos+6]
                pos = pos + 6
                beacon.rssi = data[pos]
                pos = pos + 1
                beacon.tx_power = data[pos]
                pos = pos + 1
                beacon.eye_flags = data[pos]
                pos = pos + 1
                #check bitwise setting
                if (beacon.eye_flags & (1<<0)) and len(data) >= pos + 2:
                    beacon.temperature = int.from_bytes(data[pos:pos+2], byteorder='big', signed=True)
                    pos = pos + 2
                else:
                    raise ValueError('Temperature Data too short')
                if (beacon.eye_flags & (1<<1)) and len(data) >= pos + 1:
                    beacon.humidity = data[pos]
                    pos = pos + 1
                else:
                    raise ValueError('Humidity Data too short')
                if (beacon.eye_flags & (1<<4)) and len(data) >= pos + 2:
                    beacon.movement_count = int.from_bytes(data[pos:pos+2], byteorder='big', signed=False)
                    pos = pos + 2
                else:
                    raise ValueError('Movement_Count Data too short')
                if (beacon.eye_flags & (1<<5)) and len(data) >= pos + 3:
                    beacon.movement_angle[0] = data[pos]
                    pos = pos + 1
                    beacon.movement_angle[1] = data[pos]
                    pos = pos + 1
                    beacon.movement_angle[2] = data[pos]
                    pos = pos + 1
                else:
                    raise ValueError('Movement_Angle Data too short')
                if (beacon.eye_flags & (1<<7)) and len(data) >= pos + 1:
                    beacon.battery_voltage = data[pos]
                    pos = pos + 1
                else:
                    raise ValueError('Battery_Voltage Data too short')
            else:
                raise ValueError('Header Data too short')
            
            self.beacons.append(beacon)
        return pos
    
    def to_human_readable(self) -> str:
        ret = self.name.ljust(25) + "\r\n"
        ret += "  Count".ljust(25) + f": {self.count}\r\n"
        for i in range(len(self.beacons)):
            ret += f"  Beacon[{i}]\r\n"
            ret += "    MAC Address".ljust(25, " ") + f": {self.beacons[i].mac_address.hex()}\r\n"
            ret += "    RSSI".ljust(25, " ") + f": {self.beacons[i].rssi} ({hex(self.beacons[i].rssi)})"
            ret += "    Tx Poser".ljust(25, " ") + f": {self.beacons[i].tx_power} ({hex(self.beacons[i].tx_power)})"
            ret += "    EYE Flags".ljust(25, " ") + f": {self.beacons[i].eye_flags} ({hex(self.beacons[i].eye_flags)})"
            if self.beacons[i].temperature != None:
                ret += "    Temperature".ljust(25, " ") + f": {self.beacons[i].temperature} ({hex(self.beacons[i].temperature)})"
            if self.beacons[i].humidity != None:
                ret += "    Humidity".ljust(25, " ") + f": {self.beacons[i].humidity} ({hex(self.beacons[i].humidity)})"
            if self.beacons[i].movement_count != None:
                ret += "    Movement Sensor Counter".ljust(25, " ") + f": ({hex(self.beacons[i].movement_count)})"
            if self.beacons[i].movement_angle[0] != None and self.beacons[i].movement_angle[1] != None and self.beacons[i].movement_angle[2] != None:
                ret += "    Movement Angle".ljust(25, " ") + f": ({hex(self.beacons[i].movement_angle[0])}, \
                                                                  {hex(self.beacons[i].movement_angle[1])}, \
                                                                  {hex(self.beacons[i].movement_angle[2])})"
            if self.beacons[i].battery_voltage != None:
                ret += "    Battery Voltage".ljust(25, " ") + f": {2000 + self.beacons[i].battery_voltage * 10}mV ({hex(self.beacons[i].battery_voltage)})"

        return ret
        


class BufferPcrField(PcrField):
    '''Variable length buffer PCR field'''
    harp_buf_id: int
    '''Harp ID if the actual buffer field, since legacy split the size and buffer'''
    sz_len: int
    '''Size in bytes of the length that is always prepended to the buffer'''
    buffer_data: bytes
    '''Buffer data without the prepended size'''

    def __init__(self, rean_id: int, harp_id: int, name: str, harp_buf_id: int, sz_len: int):
        super().__init__(rean_id, harp_id, name)
        self.sz_len = sz_len
        self.buffer_data = b''
        self.harp_buf_id = harp_buf_id

    def from_buf(self, data: bytes) -> int:
        if len(data) < self.sz_len:
            raise ValueError('Data toot short')
        bufsz = int.from_bytes(data[0:self.sz_len], byteorder='big', signed=False)

        if len(data) < (self.sz_len + bufsz):
            raise ValueError('Insufficient buffer data')
        self.data = data[0:self.sz_len + bufsz]
        self.buffer_data = data[self.sz_len:self.sz_len + bufsz]

        return (self.sz_len + bufsz)

    def to_human_readable(self) -> str:
        return f'{self.name.ljust(25, " ")}: {self.buffer_data.hex()}'



class FixStrPcrField(PcrField):
    '''NULL terminated string PCR field with a fixed total length'''
    str_len: int
    '''Fixed length of the string field'''
    str_val: str
    '''Parse string value'''

    def __init__(self, rean_id: int, harp_id: int, name: str, str_len: int):
        super().__init__(rean_id, harp_id, name)
        self.str_len = str_len
        self.str_val = ''

    def from_buf(self, data: bytes) -> int:
        if len(data) < self.str_len:
            raise ValueError('Data too short')

        self.data = data[0:self.str_len]
        self.str_val = ''
        for i in self.data:
            if i == 0:
                break
            self.str_val += chr(i)

        return self.str_len

    def to_human_readable(self) -> str:
        return f'{self.name.ljust(25, " ")}: "{self.str_val}"'



class BitfieldPcrField(PcrField):
    '''Bitfield PCR with each bit parsed'''
    bits: List[bool]
    '''All bits parsed out, least to most significant order'''
    byte_len: int
    '''Length in bytes of the bitfield'''
    data_int: int
    '''Bitfield data parsed as a big endian unsigned integer'''

    def __init__(self, rean_id: int, harp_id: int, name: str, byte_len: str):
        super().__init__(rean_id, harp_id, name)
        self.byte_len = byte_len
        self.bits = []

    def from_buf(self, data: bytes) -> int:
        if len(data) < self.byte_len:
            raise ValueError('Data too short')

        self.data = data[0:self.byte_len]
        self.data_int = int.from_bytes(self.data, byteorder='big', signed=False)
        self.bits = []

        for bit in range(self.byte_len * 8):
            if (self.data_int & (1 << bit)):
                self.bits.append(True)
            else:
                self.bits.append(False)

        return self.byte_len

    def to_human_readable(self) -> str:
        return f'{self.name.ljust(25, " ")}: {bin(self.data_int)}'



# PCR Fields with special meanings for program flow
class PacketIdPcrField(UintPcrField):
    def __init__(self):
        super().__init__(0x578, 0x01, 'PacketID', 1)

class ReasonCodePcrField(UintPcrField):
    def __init__(self):
        super().__init__(0x579, 0x04, 'ReasonCode', 1)

class SequenceNumberPcrField(UintPcrField):
    '''Packet sequence number, used to ACK messages'''
    def __init__(self):
        super().__init__(0x5a8, 0x05, 'SequenceNumber', 2)

class DsnPcrField(UintPcrField):
    '''Device serial number, used to categorize log data'''
    def __init__(self):
        super().__init__(0x73, 0x03, 'DSN', 4)

class LatitudePcrField(IntPcrField):
    '''Device latitude PCR field, can be used for plotting'''
    def __init__(self, rean_id: int, harp_id: int):
        super().__init__(rean_id, harp_id, 'Latitude', 4)

class LongitudePcrField(IntPcrField):
    '''Device longitude PCR field, can be used for plotting'''
    def __init__(self, rean_id: int, harp_id: int):
        super().__init__(rean_id, harp_id, 'Longitude', 4)



PCR_FIELDS: List[PcrField] = [
    PacketIdPcrField(),
    UintPcrField(-1, 0x02, 'FMHeader', 1),
    DsnPcrField(),
    ReasonCodePcrField(), #    'B',        ''],
    SequenceNumberPcrField(), #    'H',        'ak'],
    DateTimePcrField(0x32, 0x06, 'UnixTime'), #    'L',        'dt'],
    LatitudePcrField(0x04, 0x07), #    'l',        ''],
    LongitudePcrField(0x05, 0x08), #    'l',        ''],
    IntPcrField(0x06, 0x09, 'Altitude', 2), #    'h',        ''],
    IntPcrField(0x09, 0x0a, 'Heading', 2), #    'h',        ''],
    UintPcrField(0x08, 0x0b, 'GPSSpeed', 1), #    'B',        ''],
    BitfieldPcrField(0x560, 0x0c, 'InputStates', 1), #    'B',        'bf'],
    BitfieldPcrField(0xe5, 0x0d, 'OutputStates', 1), #    'B',        'bf'],
    UintPcrField(0x76, 0x0e, 'DriverId1', 4), #    'L',        ''],
    UintPcrField(0x102, 0x0f, 'DriverId2', 4), #    'L',        ''],
    UintPcrField(0xeb, 0x10, 'GPSTripOdom', 4), #    'L',        ''],
    BitfieldPcrField(0x5c0, 0x11, 'Flags', 4), #    'L',        ''],
    UintPcrField(0x0b, 0x12, 'HDOP', 1), #    'B',        ''],
    UintPcrField(0x0a, 0x13, 'NumSats', 1), #    'B',        ''],
    IntPcrField(0x0d, 0x14, 'RcvrSigStr', 2), #    'h',        ''],
    UintPcrField(0xa7, 0x15, 'CellCarrId', 2), #    'H',        ''],
    UintPcrField(0xa9, 0x16, 'IntBattVolt', 1), #    'B',        ''],
    UintPcrField(0x0c, 0x17, 'VehBattVolt', 1), #    'B',        ''],
    UintPcrField(0x0e, 0x18, 'GPSLifeOdom', 4), #    'L',        ''],
    DateTimePcrField(0x5dc, 0x19, 'AccelStartDT'), #    'L',        'dt'],
    IntPcrField(0x5d8, 0x1a, 'AccelStartLt', 4), #    'l',        ''],
    IntPcrField(0x5d9, 0x1b, 'AccelStartLn', 4), #    'l',        ''],
    UintPcrField(0x57b, 0x1c, 'AccelStartSp', 1), #    'B',        ''],
    UintPcrField(0x5a9, 0x1d, 'AccelStartHd', 2), #    'H',        ''],
    UintPcrField(0x5ab, 0x1e, 'MaxAccel', 2), #    'H',        ''],
    UintPcrField(0x57a, 0x1f, 'AccelDur', 1), #    'B',        ''],
    DateTimePcrField(0x5dd, 0x20, 'AccelEndDT'), #    'L',        'dt'],
    IntPcrField(0x5da, 0x21, 'AccelEndLt', 4), #    'l',        ''],
    IntPcrField(0x5db, 0x22, 'AccelEndLn', 4), #    'l',        ''],
    UintPcrField(0x57c, 0x23, 'AccelEndSp', 1), #    'B',        ''],
    UintPcrField(0x5aa, 0x24, 'AccelEndHd', 2), #    'H',        ''],
    UintPcrField(-1, 0x25, 'PCBRev', 1), #    'B',        ''],
    BufferPcrField(0x105, 0x26, 'GarminPkt', 0x27, 2), #    'H',        ''],
    BufferPcrField(-1, 0x28, 'BTPayload', 0x29, 2), #    'H',        ''],
    BufferPcrField(-1, 0x2a, 'CmdPayload', 0x2b, 2), #    'H',        ''],
    BitfieldPcrField(0xe2, 0x2c, 'OBDRunStates', 1), #    'B',        ''],
    UintPcrField(0xe3, 0x2d, 'OBDComStates', 1), #    'B',        ''],
    UintPcrField(0xfa, 0x2e, 'OBDTripOdom', 4), #    'L',        ''],
    UintPcrField(0x2d, 0x2f, 'OBDLifeOdom', 4), #    'L',        ''],
    UintPcrField(0xbb, 0x30, 'TempSensor0', 1), #    'B',        ''],
    UintPcrField(0x10a, 0x31, 'TempSensor1', 1), #    'B',        ''],
    IntPcrField(0x400, 0x32, 'UserVar8[0]', 1), #    'b',        ''],
    IntPcrField(0x401, 0x33, 'UserVar8[1]', 1), #    'b',        ''],
    IntPcrField(0x402, 0x34, 'UserVar8[2]', 1), #    'b',        ''],
    IntPcrField(0x403, 0x35, 'UserVar8[3]', 1), #    'b',        ''],
    IntPcrField(0x404, 0x36, 'UserVar8[4]', 1), #    'b',        ''],
    IntPcrField(0x405, 0x37, 'UserVar8[5]', 1), #    'b',        ''],
    IntPcrField(0x406, 0x38, 'UserVar8[6]', 1), #    'b',        ''],
    IntPcrField(0x407, 0x39, 'UserVar8[7]', 1), #    'b',        ''],
    IntPcrField(0x408, 0x3a, 'UserVar8[8]', 1), #    'b',        ''],
    IntPcrField(0x409, 0x3b, 'UserVar8[9]', 1), #    'b',        ''],
    IntPcrField(0x40a, 0x3c, 'UserVar8[10]', 1), #    'b',        ''],
    IntPcrField(0x40b, 0x3d, 'UserVar8[11]', 1), #    'b',        ''],
    IntPcrField(0x40c, 0x3e, 'UserVar8[12]', 1), #    'b',        ''],
    IntPcrField(0x40d, 0x3f, 'UserVar8[13]', 1), #    'b',        ''],
    IntPcrField(0x40e, 0x40, 'UserVar8[14]', 1), #    'b',        ''],
    IntPcrField(0x40f, 0x41, 'UserVar8[15]', 1), #    'b',        ''],
    IntPcrField(0x440, 0x42, 'UserVar16[0]' , 2), #    'h',        ''],
    IntPcrField(0x441, 0x43, 'UserVar16[1]' , 2), #    'h',        ''],
    IntPcrField(0x442, 0x44, 'UserVar16[2]' , 2), #    'h',        ''],
    IntPcrField(0x443, 0x45, 'UserVar16[3]' , 2), #    'h',        ''],
    IntPcrField(0x444, 0x46, 'UserVar16[4]' , 2), #    'h',        ''],
    IntPcrField(0x445, 0x47, 'UserVar16[5]' , 2), #    'h',        ''],
    IntPcrField(0x446, 0x48, 'UserVar16[6]' , 2), #    'h',        ''],
    IntPcrField(0x447, 0x49, 'UserVar16[7]' , 2), #    'h',        ''],
    IntPcrField(0x460, 0x4a, 'UserVar32[0]', 4), #    'l',        ''],
    IntPcrField(0x461, 0x4b, 'UserVar32[1]', 4), #    'l',        ''],
    IntPcrField(0x462, 0x4c, 'UserVar32[2]', 4), #    'l',        ''],
    IntPcrField(0x463, 0x4d, 'UserVar32[3]', 4), #    'l',        ''],
    IntPcrField(0x464, 0x4e, 'UserVar32[4]', 4), #    'l',        ''],
    IntPcrField(0x465, 0x4f, 'UserVar32[5]', 4), #    'l',        ''],
    IntPcrField(0x466, 0x50, 'UserVar32[6]', 4), #    'l',        ''],
    IntPcrField(0x467, 0x51, 'UserVar32[7]', 4), #    'l',        ''],
    BitfieldPcrField(0x5de, 0x52, 'SystemStates', 4), #    'L',        'bf'],
    BitfieldPcrField(0x6e, 0x53, 'WakeReason', 1), #    'B',        'bf'],
    UintPcrField(0x78, 0x54, 'OBDTrueOdom', 4), #    'L',        ''],
    UintPcrField(0x1012, 0x55, 'OBDTotFuelUs', 4), #    'L',        ''],
    UintPcrField(0xf7, 0x56, 'OBDTotEngHrs', 4), #    'L',        ''],
    UintPcrField(0x07, 0x57, 'OBDVehSpeed', 2), #    'H',        ''],
    UintPcrField(0x1f, 0x58, 'OBDEngRPM', 2), #    'H',        ''],
    IntPcrField(0x1004, 0x59, 'OBDCoolTemp', 2), #    'h',        ''],
    UintPcrField(0x70, 0x5a, 'OBDFuelLvl%', 2), #    'H',        ''],
    UintPcrField(0x1015, 0x5b, 'OBDTotDrvSec', 2), #    'L',        ''],
    UintPcrField(0x1013, 0x5c, 'OBDTotCrsSec', 4), #    'L',        ''],
    UintPcrField(0x1008, 0x5d, 'OBDTotIdlSec', 4), #    'L',        ''],
    UintPcrField(0x1016, 0x5e, 'OBDTotIdlFul', 4), #    'L',        ''],
    UintPcrField(0xf9, 0x5f, 'OBDHrshBrkCt', 4), #    'L',        ''],
    UintPcrField(0x108, 0x60, 'OBDSpdExcCt', 4), #    'L',        ''],
    UintPcrField(0x109, 0x61, 'OBDRPMExcCt', 4), #    'L',        ''],
    UintPcrField(0xf8, 0x62, 'OBDHrshXclCt', 4), #    'L',        ''],
    BitfieldPcrField(0x33, 0x63, 'IgnitionSrc', 2), #    'H',        ''],
    # Harp ID 0x64 was never implemented
    FixStrPcrField(0x19, 0x65, 'OBDVin', 17), #    'V',        ''],    
    UintPcrField(0xaa, 0x66, 'ExternADC0', 1), #    'B',        ''],
    # Harp ID 0x67 is hardfault track data, TODO on implementation
    UintPcrField(-1, 0x68, 'AccelMetrics', 4), #    'L',        ''],
    UintPcrField(0x27, 0x69, 'BootStatus', 1), #    'B',        'bf'],
    UintPcrField(-1, 0x6a, 'APNIndex', 1), #    'B',        ''],
    BufferPcrField(0xc2, 0x6c, 'OBDDTCPkt', 0x6c, 2), #    'H',        ''],
    UintPcrField(0xee, 0x6d, 'OBDBackoff', 1), #    'B',        ''],
    BitfieldPcrField(0xf0, 0x6e, 'OBDProtocols', 4), #    'L',        ''],    
    BufferPcrField(-1, 0x6f, 'CrashPktSz', 0x70, 1), #    'H',        ''],
    UintPcrField(0x1007, 0x71, 'OBDTotPTOTm', 4), #    'L',        ''],
    UintPcrField(0x1014, 0x72, 'OBDTotPTOFul', 4), #    'L',        ''],
    FixStrPcrField(0x14, 0x73, 'FwRev', 16), #    'F',        ''],   
    UintPcrField(0x1096, 0x74, 'OBDPidRsrvd1', 4), #    'L',        ''],
    UintPcrField(0x1098, 0x75, 'OBDPidRsrvd2', 4), #    'L',        ''],
    UintPcrField(0x1099, 0x76, 'OBDPidRsrvd3', 4), #    'L',        ''],
    UintPcrField(0x109a, 0x77, 'OBDPidRsrvd4', 4), #    'L',        ''],
    UintPcrField(0x109b, 0x78, 'OBDPidRsrvd5', 4), #    'L',        ''],
    UintPcrField(0x5ac, 0x79, 'OBDTransGear', 2), #    'H',        ''],
    IntPcrField(0x101d, 0x7a, 'OBDFuelTemp', 2), #    'h',        ''],
    IntPcrField(0x100f, 0x7b, 'OBDOilTemp', 2), #    'h',        ''],
    UintPcrField(0x1009, 0x7c, 'OBDThrotPos', 2), #    'H',        ''],
    UintPcrField(0x0f, 0x7d, 'OBDMPG', 2), #    'H',        ''],
    UintPcrField(0x100b, 0x7e, 'OBDAccelPos', 2), #    'H',        ''],
    UintPcrField(0x100a, 0x7f, 'OBDEngLoad', 2), #    'H',        ''],
    IntPcrField(0x100c, 0x80, 'OBDEngTorque', 2), #    'h',        ''],
    UintPcrField(0x1019, 0x81, 'OBDOilLevel', 2), #    'H',        ''],
    UintPcrField(0x101a, 0x82, 'OBDOilPress', 2), #    'H',        ''],
    UintPcrField(0x101b, 0x83, 'OBDCoolPress', 2), #    'H',        ''],
    IntPcrField(0x100e, 0x84, 'OBDItkAirTmp', 2), #    'h',        ''],
    IntPcrField(0x100d, 0x85, 'OBDMfldTemp', 2), #    'h',        ''],
    UintPcrField(0x101c, 0x86, 'OBDCoolLevel', 2), #    'H',        ''],
    UintPcrField(-1, 0x87, 'LinkageVers', 4), #    'L',        ''],
    UintPcrField(-1, 0x88, 'GPSTripOdom2', 4), #    'L',        ''],
    UintPcrField(0x4c0, 0x89, 'GenCfgValue0', 4), #    'L',        ''],
    UintPcrField(0x4c1, 0x8a, 'GenCfgValue1', 4), #    'L',        ''],
    UintPcrField(0x4c2, 0x8b, 'GenCfgValue2', 4), #    'L',        ''],
    UintPcrField(0x4c3, 0x8c, 'GenCfgValue3', 4), #    'L',        ''],
    UintPcrField(0x4c4, 0x8d, 'GenCfgValue4', 4), #    'L',        ''],
    UintPcrField(0x109c, 0x8e, 'OBDPidRsrvd6', 4), #    'L',        ''],
    UintPcrField(0x109d, 0x8f, 'OBDPidRsrvd', 4), #    'L',        ''],
    UintPcrField(0x109e, 0x90, 'OBDPidRsrvd', 4), #    'L',        ''],
    UintPcrField(0x109f, 0x91, 'OBDPidRsrvd', 4), #    'L',        ''],
    UintPcrField(0x10a1, 0x92, 'OBDPidRsrvd10', 4), #,    'L',        ''],
    UintPcrField(0x34, 0x93, 'OBDHrshAcVal', 1), #    'B',        ''],
    UintPcrField(0x36, 0x94, 'OBDHrshBkVal', 1), #    'B',        ''],
    FixStrPcrField(0x29, 0x95, 'CellSerialID', 24), #    'M',        ''],
    UintPcrField(-1, 0x96, 'PktCheckSum', 1), #    'B',        ''],
    # TPS Fields (0x97 to 0x9b) not supported
    UintPcrField(0x10a2, 0x9c, 'OBDPidRsvd11', 4), #      'L',      ''],
    UintPcrField(0x10a3, 0x9d, 'OBDPidRsvd12', 4), #      'L',      ''],
    UintPcrField(0x1017, 0x9e, 'OBDPidRsvd13', 4), #      'L',      ''],
    UintPcrField(0x1010, 0x9f, 'OBDPidRsvd14', 4), #      'L',      ''],
    UintPcrField(0x10a0, 0xa0, 'OBDPidRsvd15', 4), #    'L',        ''],
    BufferPcrField(-1, 0xa1, 'DensoDgPkt', 0xa2, 2), #    'H',        ''],
    IntPcrField(0x410, 0xa3, 'UserVar8[16]', 1), #    'b',        ''],
    IntPcrField(0x411, 0xa4, 'UserVar8[17]', 1), #    'b',        ''],
    IntPcrField(0x412, 0xa5, 'UserVar8[18]', 1), #    'b',        ''],
    IntPcrField(0x413, 0xa6, 'UserVar8[19]', 1), #    'b',        ''],
    IntPcrField(0x414, 0xa7, 'UserVar8[20]', 1), #    'b',        ''],
    IntPcrField(0x415, 0xa8, 'UserVar8[21]', 1), #    'b',        ''],
    IntPcrField(0x416, 0xa9, 'UserVar8[22]', 1), #    'b',        ''],
    IntPcrField(0x417, 0xaa, 'UserVar8[23]', 1), #    'b',        ''],
    IntPcrField(0x418, 0xab, 'UserVar8[24]', 1), #    'b',        ''],
    IntPcrField(0x419, 0xac, 'UserVar8[25]', 1), #    'b',        ''],
    IntPcrField(0x41a, 0xad, 'UserVar8[26]', 1), #    'b',        ''],
    IntPcrField(0x41b, 0xae, 'UserVar8[27]', 1), #    'b',        ''],
    IntPcrField(0x41c, 0xaf, 'UserVar8[28]', 1), #    'b',        ''],
    IntPcrField(0x41d, 0xb0, 'UserVar8[29]', 1), #    'b',        ''],
    IntPcrField(0x41e, 0xb1, 'UserVar8[30]', 1), #    'b',        ''],
    IntPcrField(0x41f, 0xb2, 'UserVar8[31]', 1), #    'b',        ''],
    IntPcrField(0x448, 0xb3, 'UserVar16[8]', 2), #    'h',        ''],
    IntPcrField(0x449, 0xb4, 'UserVar16[9]', 2), #    'h',        ''],
    IntPcrField(0x44a, 0xb5, 'UserVar16[10]', 2), #,'h',''],
    IntPcrField(0x44b, 0xb6, 'UserVar16[11]', 2), #,'h',''],
    IntPcrField(0x44c, 0xb7, 'UserVar16[12]', 2), #,'h',''],
    IntPcrField(0x44d, 0xb8, 'UserVar16[13]', 2), #,'h',''],
    IntPcrField(0x44e, 0xb9, 'UserVar16[14]', 2), #,'h',''],
    IntPcrField(0x44f, 0xba, 'UserVar16[15]', 2), #,'h',''],
    IntPcrField(0x468, 0xbb, 'UserVar32[8]', 4), #    'l',        ''],
    IntPcrField(0x469, 0xbc, 'UserVar32[9]', 4), #    'l',        ''],
    IntPcrField(0x46a, 0xbd, 'UserVar32[10]', 4), #,'l',''],
    IntPcrField(0x46b, 0xbe, 'UserVar32[11]', 4), #,'l',''],
    IntPcrField(0x46c, 0xbf, 'UserVar32[12]', 4), #,'l',''],
    IntPcrField(0x46d, 0xc0, 'UserVar32[13]', 4), #,'l',''],
    IntPcrField(0x46e, 0xc1, 'UserVar32[14]', 4), #,'l',''],
    IntPcrField(0x46f, 0xc2, 'UserVar32[15]', 4), #,'l',''],
    BitfieldPcrField(-1, 0xc3, 'OBDStartRsn', 2), #    'h',        'bf'],
    BitfieldPcrField(-1, 0xc4, 'OBDStopRsn', 4), #    'l',        'bf'],
    BufferPcrField(-1, 0xc5, 'TpsTagPayload', 0xc6, 2), #,'H',''],
    UintPcrField(0x10a1, 0xc7, 'SeatbeltStatus', 1), #,'B',''],
    UintPcrField(-1, 0xc8, '2bytebattVolt', 2), #,'H',''],
    UintPcrField(-1, 0xc9, '2byteADC0Volt', 2), #,'H',''],
    BufferPcrField(0x105, 0xca, 'AuxPassSize', 0xcb, 2), #    'H',        ''],
    BitfieldPcrField(-1, 0xcc, 'Geobitfield1', 4), #    'L',        'bf'],
    BitfieldPcrField(-1, 0xcd, 'Geobitfield2', 4), #    'L',        'bf'],
    UintPcrField(0xed, 0xce, 'ScriptVer', 4), #    'L',        ''],
    UintPcrField(0xec, 0xcf, 'ParamVer', 4), #    'L',        ''],
    FixStrPcrField(0x21, 0xd0, 'Cell ICCID', 21), #    'U',        ''],
    FixStrPcrField(0xbf, 0xd1, 'Cell MDN', 20), #    'T',        ''],
    BufferPcrField(-1, 0xd2, 'OBDdebugpck', 0xd3, 2), #,'H',''],
    UintPcrField(0x74, 0xd4, 'CellAccessTec', 1), #',  'B',        ''],
    UintPcrField(0x6d, 0xd5, 'DerivedEngSec', 4), #,'L',''],
    UintPcrField(0x1006, 0xd6, 'ECUEngineSec', 4), #    'L',        ''],
    BitfieldPcrField(0xe4, 0xd7, 'InpActiveStates', 1), #s', 'B',        'bf'],
    UintPcrField(-1, 0xd8, 'CellEnvironment', 4), #t', 'L',        ''],
    UintPcrField(0xfc, 0xd9, 'OBDHarshAcclV', 2), #l', 'H',        ''],
    UintPcrField(0xfd, 0xda, 'OBDHarshBrake', 2), #al','H',        ''],
    UintPcrField(0xa6, 0xdb, 'Cell MCC', 2), #    'H',        ''],
    FixStrPcrField(0xcc, 0xdc, 'Cell Model/Version', 58), #s', 'X',        'st'],
    UintPcrField(-1, 0xde, 'ObdMpgAvg', 2),
    UintPcrField(0xf4, 0xdf, 'GPSHarshAcclCnt', 4), #t', 'L',        ''],
    UintPcrField(0x25, 0xe0, 'GPSHarshAcclV', 2), #l', 'H',        ''],
    UintPcrField(0xf5, 0xe1, 'GPSHarshDcclCnt', 4), #t', 'L',        ''],
    UintPcrField(0x26, 0xe2, 'GPSHarshDcclV', 2), #l', 'H',        ''],
    UintPcrField(-1, 0xe3, 'TotFuelUsedHR', 4), #,'H',''],
    UintPcrField(0x1024, 0xe4, 'HybBattRemain', 1), #,'B',''],
    BitfieldPcrField(0xe7, 0xe5, 'EVChargeState', 4), #,'L','bf'],
    UintPcrField(0x1025, 0xe6, 'EVBatt_V', 2), #,'H',''],
    IntPcrField(0x1026, 0xe7, 'EVBatt_A', 2), #,'h',''],
    UintPcrField(0x1022, 0xe8, 'DieselExVol', 1), #    'B',        ''],
    UintPcrField(0x1023, 0xe9, 'DieselExLow', 1), #    'B',        ''],
    UintPcrField(0x103, 0xea, 'UpDriverId1', 2), #1', 'H',        ''],
    UintPcrField(0x104, 0xeb, 'UpDriverId2', 2), #1', 'H',        ''],
    UintPcrField(0x1027, -1, 'EV Charger Status', 1),
    UintPcrField(0x1028, -1, 'EV Charger Type', 1),
    UintPcrField(0x1029, -1, 'EV Charger State AC', 1),
    UintPcrField(0x102a, -1, 'EV Charger State DC', 1),
    BitfieldPcrField(0x10f, -1, 'Smog Status', 4),
    UintPcrField(0x110, -1, 'Smog Seq Num', 4),
    DateTimePcrField(0x5df, -1, 'Smog Timestamp'),
    UintPcrField(0xc3, -1, 'Beacon Count', 2), #    'h',        'bf'],
    BeaconPcrField(0x5f0, -1, 'Beacon List 0'), #    'H',        '']
    BeaconPcrField(0x5f1, -1, 'Beacon List 1'), #    'H',        '']
]

@dataclass
class PacketMetadata():
    recv_epoch: int
    packet_id: Optional[int]
    reason_code: Optional[int]
    dsn: Optional[int]
    seq_num: Optional[int]
    latitude: Optional[int]
    longitude: Optional[int]
    validated: bool
    human_readable: str

class PacketRecipe():
    fields: List[PcrField]
    '''Ordered list of fields in this packet recipe'''
    packet_id: int
    '''Packet ID as determined from device configuration'''
    isharp: bool
    '''Flag to determine rean/legacy harp recipe'''
    def __init__(self, index: int, packet_id: int, isharp: bool):
        self.fields = []
        self.index = index
        self.packet_id = packet_id
        self.isharp = isharp

    def to_config(self) -> str:
        if self.isharp:
            # :wycfg pcr[0] 00      11  010304060708090b0a5813122e17145205
                            #pktid  len fields
            ret = f':wycfg pcr[{self.index}] {self.packet_id:02x}{len(self.fields):02x}'
            for field in self.fields:
                ret += f'{field.harp_id:02x}'
        else:
            #!cs:95,0,      0,     20,          578,ee,579,5a8,73,32,04,05,08,09,560,e5,0a,0b,0c,a9,eb,466,5c0,467
                    #idx,   pckid, len          fields
            ret = f'!cs:95,{self.index},{self.packet_id},{len(self.fields)}'
            for field in self.fields:
                ret += f',{field.rean_id:04x}'
        
        return ret


    def packet_is_this(self, packet: bytes) -> bool:
        if (len(self.fields) == 0) or (type(self.fields[0]) != PacketIdPcrField):
            return False

        tmp = PacketIdPcrField()
        try:
            tmp.from_buf(packet)
        except ValueError:
            return False

        return (tmp.int_val == self.packet_id)

    def validate_packet(self, packet: bytes, print_me: bool = True) -> PacketMetadata:
        ret = PacketMetadata(int(time.time()), None, None, None, None, None, None, True, '')

        pos = 0
        for field in self.fields:
            try:
                pos += field.from_buf(packet[pos:])
                human_readable = field.to_human_readable()
                ret.human_readable += human_readable + '\r\n'
                if print_me:
                    print(human_readable)
            except ValueError as e:
                if print_me:
                    print(f'Failed to complete parsing of PCR {self.packet_id}, exception info:')
                    print(e)
                ret.validated = False
                break

            if type(field) is DsnPcrField:
                ret.dsn = field.int_val
            elif type(field) is SequenceNumberPcrField:
                ret.seq_num = field.int_val
            elif type(field) is LatitudePcrField:
                ret.latitude = field.int_val
            elif type(field) is LongitudePcrField:
                ret.longitude = field.int_val
            elif type(field) is PacketIdPcrField:
                ret.packet_id = field.int_val
            elif type(field) is ReasonCodePcrField:
                ret.reason_code = field.int_val

        return ret
