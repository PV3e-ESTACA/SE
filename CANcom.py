import math

import can


class VESC:

    # Les calculs à effectuer sont à mettre dans updateData()

    def __init__(self, i0, kv, kq=-1, pole=1, C=16.6, can_interface='can0'):
        self.id = 0x79
        self.pole = pole
        self.bus = can.interface.Bus(can_interface, bustype='socketcan', bitrate=500000)
        self.stop = False
        self.i0 = i0
        self.Kv = kv
        self.rpm = 0

        self.torque = 0
        self.temp_mot = 0
        self.temp_fet = 0
        self.current = 0
        self.vin = 0
        self.wath = 0
        self.C = C
        self.energy = 0

        if kq == -1:
            self.Kq = 30 / (math.pi * self.Kv)

    #
    def write(self, id, data, extended=True):
        msg = can.Message(arbitration_id=id, data=data, extended_id=extended)
        self.bus.send(msg)

    # envoi une commande pour changer le duty cycle
    def set_duty_cycle(self, dutyc):
        b1 = int(dutyc * 100000) & 0xFF
        b2 = (int(dutyc * 100000) & 0xFF00) >> 8
        b3 = (int(dutyc * 100000) & 0xFF0000) >> 16
        b4 = (int(dutyc * 100000) & 0xFF000000) >> 24
        self.write((self.id | 0x000), [b4, b3, b2, b1])

    # envoi une commande en couple
    def set_torque(self, torque):
        amp = (torque / self.Kq) + self.i0
        self.set_current(amp)

    # envoi une commande en courant
    def set_current(self, curr):
        b1 = int(curr * 1000) & 0xFF
        b2 = (int(curr * 1000) & 0xFF00) >> 8
        b3 = (int(curr * 1000) & 0xFF0000) >> 16
        b4 = (int(curr * 1000) & 0xFF000000) >> 24
        self.write((self.id | 0x100), [b4, b3, b2, b1])

    # je suis pas sur de ce que ça fait
    def set_current_brake(self, curr):
        b1 = int(curr * 1000) & 0xFF
        b2 = (int(curr * 1000) & 0xFF00) >> 8
        b3 = (int(curr * 1000) & 0xFF0000) >> 16
        b4 = (int(curr * 1000) & 0xFF000000) >> 24
        self.write((self.id | 0x200), [b4, b3, b2, b1])

    # envoi une commande en tours/min (RPM doit etre en veritable tours/min, pas ERPM
    def set_RPM(self, RPM):
        RPM = RPM * self.pole
        b1 = int(RPM) & 0xFF
        b2 = (int(RPM) & 0xFF00) >> 8
        b3 = (int(RPM) & 0xFF0000) >> 16
        b4 = (int(RPM) & 0xFF000000) >> 24
        self.write((self.id | 0x300), [b4, b3, b2, b1])

    # passur non plus de ce que ça fait
    def set_pos(self, pos):
        b1 = int(pos * 1000000) & 0xFF
        b2 = (int(pos * 1000000) & 0xFF00) >> 8
        b3 = (int(pos * 1000000) & 0xFF0000) >> 16
        b4 = (int(pos * 1000000) & 0xFF000000) >> 24
        self.write((self.id | 0x400), [b4, b3, b2, b1])

    def toInt16(self, value):
        vint = int(value)
        if vint >> 15 == 1:
            toadd = int(-1)
            toadd = toadd - pow(2, 16) + 1
            vint |= toadd
        return vint

    def toInt32(self, value):
        vint = int(value)
        if vint >> 31 == 1:
            toadd = int(-1)
            toadd = toadd - pow(2, 32) + 1
            vint |= toadd
        return vint

    def decode(self, msg):
        id = msg.arbitration_id
        array = msg.data
        array.reverse()
        dlc = msg.dlc
        if id & 0xFF00 == 0x900:
            # print("PACKET 1")
            self.rpm = self.toInt32(array[7] << 24 | array[6] << 16 | array[5] << 8 | array[4])
            self.rpm = self.rpm / self.pole
            print("RPM : " + str(self.rpm))
            self.current = self.toInt16(array[3] << 8 | array[2])
            print("current : " + str(self.current))
            self.dutyc = self.toInt16(array[1] << 8 | array[0]) / 1000.0
            print("duty Cycle : " + str(self.dutyc))
        elif id & 0xFF00 == 0xe00:
            # print("PACKET 2")
            self.amph = array[7] << 24 | array[6] << 16 | array[5] << 8 | array[4]
            self.amph = self.amph / 1000
            print("AMP_H : " + str(self.amph))
            self.amphc = array[3] << 24 | array[2] << 16 | array[1] << 8 | array[0]
            self.amphc = self.amphc / 1000
            print("AMP_HC : " + str(self.amphc))
        elif id & 0xFF00 == 0xf00:
            # print("PACKET 3")
            self.wath = array[7] << 24 | array[6] << 16 | array[5] << 8 | array[4]
            self.wath = self.wath / 1000
            print("WATT_H : " + str(self.wath))
            self.wathc = array[3] << 24 | array[2] << 16 | array[1] << 8 | array[0]
            self.wathc = self.wathc / 1000
            print("WATT_HC : " + str(self.wathc))
        elif id & 0xFF00 == 0x1000:
            # print("PACKET 4")
            self.temp_fet = self.toInt16(array[7] << 8 | array[6]) * 0.1
            print("Temp fet : " + str(self.temp_fet))
            self.temp_mot = self.toInt16(array[5] << 8 | array[4]) * 0.1
            print("Temp motor : " + str(self.temp_mot))
            self.curr_in = self.toInt16(array[3] << 8 | array[2]) * 0.1
            print("Current in : " + str(self.curr_in))
            self.pid_pos = self.toInt16(array[1] << 8 | array[0]) * 0.5
            print("pid pos : " + str(self.pid_pos))
        elif id & 0xFF00 == 0x1b00:
            # print("PACKET 5")
            self.tacho = array[7] << 24 | array[6] << 16 | array[5] << 8 | array[4]
            print("TACHO : " + str(self.tacho))
            self.vin = self.toInt16(array[3] << 8 | array[2]) * 0.1
            print("VIN : " + str(self.vin))

        self.updateData()
        # print("\n")

    # calcul des valeurs
    def updateData(self):
        self.torque = (self.current - self.i0) * self.Kq
        self.soc = math.pow(self.vin / 48, 2) * 100
        self.energy = 0.5 * self.C * math.pow(self.vin, 2)

    def listen_can_thread(self):
        while not self.stop:
            message = self.bus.recv(1.0)  # Timeout in seconds.
            if message is None:
                pass
            else:
                self.decode(message)
