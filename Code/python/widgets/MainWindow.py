from PyQt5 import QtGui, QtCore, uic, QtWidgets
from pyqtgraph.dockarea import DockArea, Dock
import os
from widgets.RbLockWidget import RbLockWidget


class MainWindow(QtWidgets.QMainWindow):
    """The only window of the application."""

    def __init__(self, settings):
        super(MainWindow, self).__init__()
        self.settings = settings

        self.setupUi()

        self.dock_area = DockArea()
        self.setCentralWidget(self.dock_area)

        self.createDocks()

        self.loadSettings()
        self.setWindowTitle('Rb Lock')

    def setupUi(self):
        pass

    def createDocks(self):
        self.rb_lock_widget = RbLockWidget(self.settings, self)
        self.rb_lock_widget_dock = Dock('Rb Lock',
                                        widget=self.rb_lock_widget)
        self.dock_area.addDock(self.rb_lock_widget_dock)

    def loadSettings(self):
        """Load window state from self.settings"""

        self.settings.beginGroup('mainwindow')
        geometry = self.settings.value('geometry')
        state = self.settings.value('windowstate')
        dock_string = str(self.settings.value('dockstate').toString())
        if dock_string is not "":
            dock_state = eval(dock_string)
            self.dock_area.restoreState(dock_state)
        self.settings.endGroup()

        self.restoreGeometry(geometry)
        self.restoreState(state)

    def saveSettings(self):
        """Save window state to self.settings."""
        self.settings.beginGroup('mainwindow')
        self.settings.setValue('geometry', self.saveGeometry())
        self.settings.setValue('windowstate', self.saveState())
        dock_state = self.dock_area.saveState()
        # dock_state returned here is a python dictionary. Coundn't find a good
        # way to save dicts in QSettings, hence just using representation
        # of it.
        self.settings.setValue('dockstate', repr(dock_state))
        self.settings.endGroup()

    def closeEvent(self, event):
        self.rb_lock_widget.saveSettings()
        self.saveSettings()
