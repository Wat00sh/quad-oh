import serial
import struct
import math

ESC_HW_POLES = 1


class ESCTelemetryData:
    def __init__(self):
        self.voltage = 0
        self.current = 0
        self.temperature_cdeg = 0

    def update(self, voltage, current, temperature_cdeg):
        self.voltage = voltage
        self.current = current
        self.temperature_cdeg = temperature_cdeg


try:
    ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)
except serial.SerialException as e:
    print(f"Failed to open serial port: {e}")


telem_data = ESCTelemetryData()


def read_bytes(ser, n):
    return ser.read(n)

def discard_pending(ser):
    ser.reset_input_buffer()



XMODEM_CRC16_LOOKUP = [
    0x0000, 0x1021, 0x2042, 0x3063, 0x4084, 0x50A5, 0x60C6, 0x70E7,
    0x8108, 0x9129, 0xA14A, 0xB16B, 0xC18C, 0xD1AD, 0xE1CE, 0xF1EF,
    0x1231, 0x0210, 0x3273, 0x2252, 0x52B5, 0x4294, 0x72F7, 0x62D6,
    0x9339, 0x8318, 0xB37B, 0xA35A, 0xD3BD, 0xC39C, 0xF3FF, 0xE3DE,
    0x2462, 0x3443, 0x0420, 0x1401, 0x64E6, 0x74C7, 0x44A4, 0x5485,
    0xA56A, 0xB54B, 0x8528, 0x9509, 0xE5EE, 0xF5CF, 0xC5AC, 0xD58D,
    0x3653, 0x2672, 0x1611, 0x0630, 0x76D7, 0x66F6, 0x5695, 0x46B4,
    0xB75B, 0xA77A, 0x9719, 0x8738, 0xF7DF, 0xE7FE, 0xD79D, 0xC7BC,
    0x48C4, 0x58E5, 0x6886, 0x78A7, 0x0840, 0x1861, 0x2802, 0x3823,
    0xC9CC, 0xD9ED, 0xE98E, 0xF9AF, 0x8948, 0x9969, 0xA90A, 0xB92B,
    0x5AF5, 0x4AD4, 0x7AB7, 0x6A96, 0x1A71, 0x0A50, 0x3A33, 0x2A12,
    0xDBFD, 0xCBDC, 0xFBBF, 0xEB9E, 0x9B79, 0x8B58, 0xBB3B, 0xAB1A,
    0x6CA6, 0x7C87, 0x4CE4, 0x5CC5, 0x2C22, 0x3C03, 0x0C60, 0x1C41,
    0xEDAE, 0xFD8F, 0xCDEC, 0xDDCD, 0xAD2A, 0xBD0B, 0x8D68, 0x9D49,
    0x7E97, 0x6EB6, 0x5ED5, 0x4EF4, 0x3E13, 0x2E32, 0x1E51, 0x0E70,
    0xFF9F, 0xEFBE, 0xDFDD, 0xCFFC, 0xBF1B, 0xAF3A, 0x9F59, 0x8F78,
    0x9188, 0x81A9, 0xB1CA, 0xA1EB, 0xD10C, 0xC12D, 0xF14E, 0xE16F,
    0x1080, 0x00A1, 0x30C2, 0x20E3, 0x5004, 0x4025, 0x7046, 0x6067,
    0x83B9, 0x9398, 0xA3FB, 0xB3DA, 0xC33D, 0xD31C, 0xE37F, 0xF35E,
    0x02B1, 0x1290, 0x22F3, 0x32D2, 0x4235, 0x5214, 0x6277, 0x7256,
    0xB5EA, 0xA5CB, 0x95A8, 0x8589, 0xF56E, 0xE54F, 0xD52C, 0xC50D,
    0x34E2, 0x24C3, 0x14A0, 0x0481, 0x7466, 0x6447, 0x5424, 0x4405,
    0xA7DB, 0xB7FA, 0x8799, 0x97B8, 0xE75F, 0xF77E, 0xC71D, 0xD73C,
    0x26D3, 0x36F2, 0x0691, 0x16B0, 0x6657, 0x7676, 0x4615, 0x5634,
    0xD94C, 0xC96D, 0xF90E, 0xE92F, 0x99C8, 0x89E9, 0xB98A, 0xA9AB,
    0x5844, 0x4865, 0x7806, 0x6827, 0x18C0, 0x08E1, 0x3882, 0x28A3,
    0xCB7D, 0xDB5C, 0xEB3F, 0xFB1E, 0x8BF9, 0x9BD8, 0xABBB, 0xBB9A,
    0x4A75, 0x5A54, 0x6A37, 0x7A16, 0x0AF1, 0x1AD0, 0x2AB3, 0x3A92,
    0xFD2E, 0xED0F, 0xDD6C, 0xCD4D, 0xBDAA, 0xAD8B, 0x9DE8, 0x8DC9,
    0x7C26, 0x6C07, 0x5C64, 0x4C45, 0x3CA2, 0x2C83, 0x1CE0, 0x0CC1,
    0xEF1F, 0xFF3E, 0xCF5D, 0xDF7C, 0xAF9B, 0xBFBA, 0x8FD9, 0x9FF8,
    0x6E17, 0x7E36, 0x4E55, 0x5E74, 0x2E93, 0x3EB2, 0x0ED1, 0x1EF0
]


def crc_xmodem(data):
    crc = 0
    for b in data:
        index = ((crc >> 8) ^ b) & 0xFF
        crc = ((crc << 8) ^ XMODEM_CRC16_LOOKUP[index]) & 0xFFFF
    return crc

temp_table = [
    (241, 0), (240, 1), (239, 2), (238, 3), (237, 4), (236, 5), (235, 6), (234, 7), (233, 8), (232, 9),
    (231, 10), (230, 11), (229, 12), (228, 13), (227, 14), (226, 15), (224, 16), (223, 17), (222, 18), (220, 19),
    (219, 20), (217, 21), (216, 22), (214, 23), (213, 24), (211, 25), (209, 26), (208, 27), (206, 28), (204, 29),
    (202, 30), (201, 31), (199, 32), (197, 33), (195, 34), (193, 35), (191, 36), (189, 37), (187, 38), (185, 39),
    (183, 40), (181, 41), (179, 42), (177, 43), (174, 44), (172, 45), (170, 46), (168, 47), (166, 48), (164, 49),
    (161, 50), (159, 51), (157, 52), (154, 53), (152, 54), (150, 55), (148, 56), (146, 57), (143, 58), (141, 59),
    (139, 60), (136, 61), (134, 62), (132, 63), (130, 64), (128, 65), (125, 66), (123, 67), (121, 68), (119, 69),
    (117, 70), (115, 71), (113, 72), (111, 73), (109, 74), (106, 75), (105, 76), (103, 77), (101, 78), (99, 79),
    (97, 80), (95, 81), (93, 82), (91, 83), (90, 84), (88, 85), (85, 86), (84, 87), (82, 88), (81, 89),
    (79, 90), (77, 91), (76, 92), (74, 93), (73, 94), (72, 95), (69, 96), (68, 97), (66, 98), (65, 99),
    (64, 100), (62, 101), (62, 102), (61, 103), (59, 104), (58, 105), (56, 106), (54, 107), (54, 108), (53, 109),
    (51, 110), (51, 111), (50, 112), (48, 113), (48, 114), (46, 115), (46, 116), (44, 117), (43, 118), (43, 119),
    (41, 120), (41, 121), (39, 122), (39, 123), (39, 124), (37, 125), (37, 126), (35, 127), (35, 128), (33, 129)
]


def temperature_decode(temp_raw):
    if temp_raw == 0:
        return 0
    for temp_value, decoded_value in temp_table:
        if temp_value <= temp_raw:
            return decoded_value
    return 130


def decode_current(curr):
    return curr / 64.0

FRAME_HEAD_EXPECTED = 0x9B
FRAME_LENGTH_EXPECTED = 158
CMD_EXPECTED = 2
VERSION_EXPECTED = 1
FRAME_OVERHEAD = 6  # Size of the header and footer in the frame
FRAME_SIZE = FRAME_LENGTH_EXPECTED + FRAME_OVERHEAD

def check_input():
    n_bytes = ser.in_waiting
    if n_bytes < FRAME_SIZE:
        return  # Not enough data for a complete frame
    if n_bytes > FRAME_SIZE:
        discard_pending(ser)  # Discards buffer if data is more than one frame size, adjust strategy as needed

    s = read_bytes(ser, FRAME_SIZE)  # Read exactly one frame size
    head, frame_len, ver, cmd, _ = struct.unpack(">BBBBH", s[:6])
    if head != FRAME_HEAD_EXPECTED or frame_len != FRAME_LENGTH_EXPECTED or ver != VERSION_EXPECTED or cmd != CMD_EXPECTED:
        print(f"Bad frame header: {head}, length: {frame_len}, version: {ver}, cmd: {cmd}")
        return

    crc_expected, = struct.unpack("<H", s[-2:])
    crc_calculated = crc_xmodem(s[1:-2])  # Calculate CRC from the content excluding the CRC field itself
    if crc_expected != crc_calculated:
        print(f"Bad CRC: expected {crc_expected}, calculated {crc_calculated}")
        return

    # Continue processing if all checks pass


    for i in range(8):
        offset = 7 + i * 19
        e = s[offset:offset+19]
        _, pnum, in_thr, out_thr, eRPM, volt, curr, pcurr, mos_temp, cap_temp, status = struct.unpack(">BHHHHHhhBBH", e)
        RPM = math.floor(eRPM * 10.0 / ESC_HW_POLES)
        if volt > 0 or curr > 0 or RPM > 0 or pnum > 1:
            curr = decode_current(curr)
            pcurr = decode_current(pcurr)
            volt = volt * 0.1
            in_thr = in_thr / 32768.0
            out_thr = out_thr / 32768.0
            mos_temp = temperature_decode(mos_temp)
            cap_temp = temperature_decode(cap_temp)
            telem_data.update(volt, curr, mos_temp*100)
            # Log or handle updated telemetry data as needed
            print(f"Data: Motor {pnum}, RPM: {RPM}, Current: {curr}, Voltage: {volt}, MosTemp: {mos_temp}, CapTemp: {cap_temp}")


def main_loop():
    try:
        while True:
            check_input()
    except KeyboardInterrupt:
        print("Program interrupted")
    finally:
        ser.close()

if __name__ == "__main__":
    main_loop()
