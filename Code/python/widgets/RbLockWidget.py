from PyQt5 import QtGui, QtCore, uic, QtWidgets
from widgets.CommonWidgets import BoolBox, SliderSpinBox, MyDoubleSpinBox, MySpinBox
import os
import numpy as np
import zmq
import time
from arduino_serial import RbLock
import datetime
import sys

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

class RbLockWidget(QtWidgets.QWidget):

    def __init__(self, settings, parent=None):
        super(RbLockWidget, self).__init__(parent)
        self.settings = settings
        self.rblock = RbLock()
        self.setupUi()
        self.loadSettings()
        self.setGUIParams()
        self.connect_slots()

    def connect_slots(self):
        self.connect_button.myValueChanged.connect(self.handleConnectClicked)
        self.ramp_amplitude_spinbox.valueChanged.connect(self.handleRampAmplitudeChanged)
        for sb in self.double_spin_boxes_list:
            sb.valueChanged.connect(self.handleParamsChanged)
        for sb in self.bool_spin_boxes_list:
            sb.myValueChanged.connect(self.handleParamsChanged)

        self.piezo_offset_spinbox.myValueChanged.connect(self.handleParamsChanged)
        self.current_offset_spinbox.myValueChanged.connect(self.handleParamsChanged)

    def disconnect_slots(self):
        self.connect_button.myValueChanged.disconnect(self.handleConnectClicked)
        self.ramp_amplitude_spinbox.valueChanged.disconnect(self.handleRampAmplitudeChanged)
        for sb in self.double_spin_boxes_list:
            sb.valueChanged.disconnect(self.handleParamsChanged)
        for sb in self.bool_spin_boxes_list:
            sb.myValueChanged.disconnect(self.handleParamsChanged)

        self.piezo_offset_spinbox.myValueChanged.disconnect(self.handleParamsChanged)
        self.current_offset_spinbox.myValueChanged.disconnect(self.handleParamsChanged)


    def setupUi(self):
        self.grid = QtWidgets.QGridLayout(self)
        self.setLayout(self.grid)

        self.log_display = QtWidgets.QTextEdit(self)
        self.log_display.setReadOnly(True)
        self.label_com = QtWidgets.QLabel('Port')
        self.lineedit_com = QtWidgets.QLineEdit()

        self.connect_button = BoolBox(value=False, parent=self,
                                      ontext='Connected',
                                      offtext='Disconnected')


        self.pz_offset_label = QtWidgets.QLabel('Piezo Output Offset')
        self.curr_offset_label = QtWidgets.QLabel('Current Output Offset')

        self.piezo_offset_spinbox = SliderSpinBox(0, valrange=(32768, 2*32768), step_size=20, parent=self)
        self.current_offset_spinbox = SliderSpinBox(0, valrange=(0, 2*32768), step_size=100, parent=self)

        self.ramp_amplitude_spinbox = MySpinBox(self)
        self.ramp_amplitude_spinbox.setRange(0, 32768)
        self.ramp_amplitude_label = QtWidgets.QLabel('Ramp Amplitude')

        self.grid.addWidget(self.label_com, 0, 0)
        self.grid.addWidget(self.lineedit_com, 0, 1)

        self.grid.addWidget(self.connect_button, 1, 0, 1, 2)



        self.grid.addWidget(self.ramp_amplitude_label, 2, 0, 1, 1)
        self.grid.addWidget(self.ramp_amplitude_spinbox, 2, 1, 1, 1)

        double_labels = ['Piezo Prop. Gain',
                         'Curr Integral gain',
                         'Feedforward gain',
                         'Curr. Prop. gain',
                         'Piezo Integral^2 gain']

        start_index = 3
        self.double_spin_boxes_list = []
        for index, label_string in enumerate(double_labels):
            self.grid.addWidget(QtWidgets.QLabel(label_string), start_index+index, 0)
            sb = MyDoubleSpinBox(self)
            sb.setRange(0.0, 5e5)
            sb.setDecimals(3)
            self.double_spin_boxes_list.append(sb)
            self.grid.addWidget(sb, start_index+index, 1)

        bool_labels = ['Current Prop Gain',
                       'Piezo Prop Gain',
                       'Current Integrator',
                       'Piezo I^2',
                       'Scanning']

        start_index += len(double_labels)
        self.bool_spin_boxes_list = []
        for index, label_string in enumerate(bool_labels):
            self.grid.addWidget(QtWidgets.QLabel(label_string), start_index+index, 0)
            sb = BoolBox(value=False, parent=self, ontext='Enabled',
                                offtext='Disabled')
            self.bool_spin_boxes_list.append(sb)
            self.grid.addWidget(sb, start_index+index, 1)


        start_index += len(bool_labels)
        self.grid.addWidget(self.pz_offset_label, start_index, 0, 1, 1)
        self.grid.addWidget(self.piezo_offset_spinbox, start_index, 1, 1, 1)


        self.grid.addWidget(self.curr_offset_label, start_index+1, 0, 1, 1)
        self.grid.addWidget(self.current_offset_spinbox, start_index+1, 1, 1, 1)

        self.lockbutton = BoolBox(value=False, parent=self, ontext='Locked',
                                offtext='Unlocked')
        self.lockbutton.myValueChanged.connect(self.handleLockClicked)

        self.resetbutton = QtWidgets.QPushButton('Reset to defaults')
        self.resetbutton.clicked.connect(self.handleResetButtonClicked)
        self.grid.addWidget(self.resetbutton, start_index+3, 0, 1, 2)

        self.grid.addWidget(self.lockbutton, start_index+4, 0, 1, 2)
        self.grid.addWidget(self.log_display, 0, 2, 20, 1)
        self.grid.setColumnStretch(2, 2)  # stretch the log column

    def handleLockClicked(self, value):
        if value is True:
            new_text = 'Locking:'
            try:
                self.rblock.lock()
                new_text += 'Success\n'
            except Exception as e:
                new_text += 'Error' + str(e) + '\n'
        else:
            new_text = 'Scanning:'
            try:
                
                self.rblock.scan()
            except Exception as e:
                new_text += 'Error' + str(e) + '\n'
        self.disconnect_slots()
        self.setGUIParams()
        self.connect_slots()


    def LogParams(self):
        keepLogging = True
        MaxLogHours = 12.0
        StartTime = time.time()
        Data = []
        while keepLogging:
            currentParams = self.RbLock.get_params()
            output_offset_pzt = currentParams[7]
            state = currentParams[6]
            TimeDelta = StartTime - time.time()
            data.append([TimeDelta,output_offset_pzt,state])
            if TimeDelta/3600.0 >= MaxLogHours:
                keepLogging = False
            time.sleep(0.5)
        data = np.asarray(data)
        np.savetxt('DataLog.csv',data,delimiter=',')


    def handleResetButtonClicked(self):
        self.rblock.params = list(self.rblock.params_default)
        self.setParamsOnArduino()
        self.disconnect_slots()
        self.setGUIParams()
        self.connect_slots()

    def handleRampAmplitudeChanged(self):
        self.setAllParams()
        print('amp changed')

    def handleParamsChanged(self):
        self.setAllParams()
        print('params changed')

    def setAllParams(self):
        ra = self.ramp_amplitude_spinbox.value()
        ra = ra - ra % 800  # HACK!!! Change this if you change N_STEPS
        pnew = self.getAllParams()
        pnew[0] = ra
        self.rblock.params = pnew
        self.setParamsOnArduino()
        print(self.rblock.get_params())

    def setParamsOnArduino(self):
        new_text = str(datetime.datetime.now())
        new_text += ' Setting Params on Arduino:'
        try:
            self.rblock.set_params()
            new_text += 'Success\n'
        except Exception as e:
            new_text += ' Error : ' + str(e) + '\n'
        self.append_to_log(new_text)

    def getAllParams(self):
        float_list = [float(i.value()) for i in self.double_spin_boxes_list]
        toggle_list = [int(i.isChecked()) for i in self.bool_spin_boxes_list]

        all_list = float_list + toggle_list
        ra = self.ramp_amplitude_spinbox.value()
        p_offset = self.piezo_offset_spinbox.value()
        c_offset = self.current_offset_spinbox.value()

        return [ra] + float_list + [p_offset, c_offset] + toggle_list

    def setGUIParams(self):
        self.ramp_amplitude_spinbox.setValue(self.rblock.params[0])
        for i, sb in enumerate(self.double_spin_boxes_list):
            sb.setValue(self.rblock.params[i+1])

        for i, sb in enumerate(self.bool_spin_boxes_list):
            sb.mySetValue(self.rblock.params[i+8])

        self.piezo_offset_spinbox.setValue(self.rblock.params[6])
        self.current_offset_spinbox.setValue(self.rblock.params[7])

    def handleConnectClicked(self, click_val):
        new_text = str(datetime.datetime.now())
        if click_val is True:
            # we should connect
            try:
                self.rblock.connect(str(self.lineedit_com.text()))
                new_text += ' Connected\n'
            except Exception as e:
                # e = sys.exc_info()[0]
                new_text += ' Error connecting: ' + str(e) + '\n'
                self.connect_button.mySetValue(0)
        elif click_val is False:
            new_text += ' Disconnected\n'
            self.rblock.close()
        self.append_to_log(new_text)

    def append_to_log(self, new_string):
        old_text = self.log_display.toPlainText()
        self.log_display.setPlainText(old_text + new_string)

    def loadSettings(self):
        self.settings.beginGroup('RbLockWidget')
        self.lineedit_com.setText(str(self.settings.value('com_port', 'COM14')))
        params_default_str = repr(self.rblock.params_default)
        self.rblock.params = eval(str(self.settings.value('params', params_default_str)))
        self.settings.endGroup()

    def saveSettings(self):
        self.settings.beginGroup('RbLockWidget')
        self.settings.setValue('com_port', str(self.lineedit_com.text()))
        self.settings.setValue('params', repr(self.rblock.params))
        self.settings.endGroup()

