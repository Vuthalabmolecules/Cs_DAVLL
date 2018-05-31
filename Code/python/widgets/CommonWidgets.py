from PyQt4 import QtGui, QtCore
import sys


class BoolBox(QtGui.QPushButton):
    myValueChanged = QtCore.pyqtSignal(bool)

    def __init__(self, value, parent=None, ontext='ON', offtext='OFF'):
        super(BoolBox, self).__init__(parent)
        self.ontext = ontext
        self.offtext = offtext
        self.setCheckable(True)
        self.state = value
        self.setChecked(self.state)
        if self.state:
            text = self.ontext
        else:
            text = self.offtext
        self.setText(text)
        self.clicked.connect(self.handleBoolButtonClicked)
        stylesheet = ('QPushButton:checked { background-color:'
                      'rgb(100,255,125); }'
                      'QPushButton { background-color:'
                      'rgb(255,125,100); }')
        self.setStyleSheet(stylesheet)

    def handleBoolButtonClicked(self, checked):
        self.state = bool(checked)
        if self.state:
            text = self.ontext
        else:
            text = self.offtext
        self.setText(text)
        self.myValueChanged.emit(self.state)

    def mySetValue(self, val):
        self.state = bool(val)
        self.setChecked(self.state)
        if self.state:
            text = self.ontext
        else:
            text = self.offtext
        self.setText(text)


class MyDoubleSpinBox(QtGui.QDoubleSpinBox):

    """Selects all text once it receives a focusInEvent.
    Use this widget instead of the usual QDoubleSpinBox for quick editing.
    """

    def __init__(self, parent):
        super(MyDoubleSpinBox, self).__init__()
        self.setDecimals(3)
        self.setKeyboardTracking(False)

    def focusInEvent(self, e):
        super(MyDoubleSpinBox, self).focusInEvent(e)
        QtCore.QTimer.singleShot(100, self.afterFocus)

    def afterFocus(self):
        self.selectAll()


class MySpinBox(QtGui.QSpinBox):

    """Selects all text once it receives a focusInEvent.
    Use this widget instead of the usual QDoubleSpinBox for quick editing.
    """

    def __init__(self, parent):
        super(MySpinBox, self).__init__()
        self.setKeyboardTracking(False)

    def focusInEvent(self, e):
        super(MySpinBox, self).focusInEvent(e)
        QtCore.QTimer.singleShot(100, self.afterFocus)

    def afterFocus(self):
        self.selectAll()

class SliderSpinBox(QtGui.QWidget):
    myValueChanged = QtCore.pyqtSignal(int)


    def __init__(self, value=0, valrange=(0, 1000), step_size=100, parent=None):
        super(SliderSpinBox, self).__init__(parent)
        self.qhboxlayout = QtGui.QVBoxLayout(self)
        self.setLayout(self.qhboxlayout)

        self.spinbox = QtGui.QSpinBox(self)
        self.spinbox.setSingleStep(step_size)
        print(step_size)
        print('single step:', self.spinbox.singleStep())
        self.slider = QtGui.QSlider(1, self)  # 1 == horizontal
        self.slider.setSingleStep(step_size)

        self.spinbox.setRange(valrange[0], valrange[1])
        self.slider.setRange(valrange[0], valrange[1])

        self.spinbox.valueChanged.connect(self.slider.setValue)
        self.slider.valueChanged.connect(self.spinbox.setValue)

        self.spinbox.valueChanged.connect(self.myValueChanged)
        self.slider.valueChanged.connect(self.myValueChanged)

        self.qhboxlayout.addWidget(self.spinbox)
        self.qhboxlayout.addWidget(self.slider)

    def setValue(self, newValue):
        self.spinbox.setValue(newValue)

    def value(self):
        return self.spinbox.value()
