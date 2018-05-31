import serial
import struct
import time
import numpy as np

"""
  int ramp_amplitude;
  float gain_p, gain_i, gain_ff, gain_c, gain_i2;
  int output_offset_pzt, output_offset_curr;
  int c_gain_on;
  int p_gain_on;
  int c_integrator_on;
  int p_integrator_on;
  int state;
"""

params_struct_size = 4*13
params_struct_fmt = '<'+'ifffffiiiiiii'

ZEROV = 32768
V2P5 = 49512

params_default = (1600,

                  8000., 5000., .07, 8000, 0.002,
                  V2P5, ZEROV,
                  0,
                  0,
                  0,
                  0,
                  1)

class RbLock:

    def __init__(self, serialport='COM14'):
        self.serialport = serialport
        self.params = list(params_default)
        self.params_default = list(params_default)

    def connect(self, serialport='COM14'):
        self.serialport = serialport
        self.ser = serial.Serial(self.serialport, baudrate=115200)
        time.sleep(4)  # wait for microcontroller to reboot
        self.set_params()

    def idn(self):
        self.ser.write(b'i')
        return self.ser.readline()

    def get_params(self):
        write_string = b'g'
        self.ser.write(write_string)
        data = self.ser.read(params_struct_size)
        data_tuple = struct.unpack(params_struct_fmt, data)
        self.params = list(data_tuple)
        return data_tuple

    def set_params(self):
        data = struct.pack(params_struct_fmt, *self.params)
        self.ser.write(b's'+data)

    def set_scan_amplitude(self, new_amplitude):
        self.params[0] = int(new_amplitude)
        self.set_params()

    def set_p_gain(self, new_gain):
        self.params[1] = float(new_gain)
        self.set_params()

    def set_i_gain(self, new_gain):
        self.params[2] = float(new_gain)
        self.set_params()

    def set_ff_gain(self, new_gain):
        self.params[3] = float(new_gain)
        self.set_params()

    def set_c_gain(self, new_gain):
        self.params[4] = float(new_gain)
        self.set_params()

    def set_i2_gain(self, new_gain):
        self.params[5] = float(new_gain)
        self.set_params()

    def set_c_gain_state(self, state=0):
        self.params[8] = int(state)
        self.set_params()

    def set_p_gain_state(self, state=0):
        self.params[9] = int(state)
        self.set_params()

    def set_integrator_state(self, state=0):
        self.params[10] = int(state)
        self.set_params()

    def set_integrator2_state(self, state=0):
        self.params[11] = int(state)
        self.set_params()

    def set_output_offset(self, piezo_offset, curr_offset):
        self.params[6] = int(piezo_offset)
        self.params[7] = int(curr_offset)
        self.set_params()

    def set_state(self, state):
        self.params[12] = state
        self.set_params()

    def scan(self):
        self.get_params()
        self.set_integrator2_state(0)
        self.set_integrator_state(0)
        self.set_p_gain_state(0)
        self.set_c_gain_state(0)
        self.set_state(1)

    def lock(self):
        self.get_params()
        self.set_state(0)
        time.sleep(0.5)
        self.set_c_gain_state(1)
        self.set_p_gain_state(1)
        time.sleep(0.2)
        self.set_integrator_state(1)
        self.set_integrator2_state(1)

    def close(self):
        self.scan()
        self.ser.close()

if __name__ == '__main__':
    dutc = RbLock()
