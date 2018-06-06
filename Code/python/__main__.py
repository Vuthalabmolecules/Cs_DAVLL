#!/usr/bin/env python

import sys
import os
from PyQt5 import QtGui, QtCore
from widgets.MainWindow import MainWindow


main_dir = os.path.dirname(os.path.abspath(__file__))

def main():
    # see if we can write to main_dir
    if os.access(main_dir, os.W_OK):
        # if yes, then put all settings in an ini file there
        path_to_settings = os.path.join(main_dir, 'settings.ini')
        settings = QtCore.QSettings(path_to_settings,
                                    QtCore.QSettings.IniFormat)
    else:
        # else use Qt settings system
        settings = QtCore.QSettings('rb_lock', 'Shreyas Potnis')
    w = MainWindow(settings)
    w.show()
    return app.exec_()

if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    sys.exit(main())
