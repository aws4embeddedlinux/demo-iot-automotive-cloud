# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'main_frame.ui'
#
# Created by: PyQt5 UI code generator 5.10.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1034, 275)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.btnDeploy = QtWidgets.QPushButton(self.centralwidget)
        self.btnDeploy.setGeometry(QtCore.QRect(590, 110, 431, 111))
        font = QtGui.QFont()
        font.setFamily("Ubuntu")
        font.setPointSize(22)
        font.setBold(True)
        font.setWeight(75)
        self.btnDeploy.setFont(font)
        self.btnDeploy.setStyleSheet("color: rgb(32, 74, 135);")
        self.btnDeploy.setObjectName("btnDeploy")

        font = QtGui.QFont()
        font.setPointSize(24)

        self.labelVehicleID = QtWidgets.QLabel(self.centralwidget)
        self.labelVehicleID.setGeometry(QtCore.QRect(160, 20, 731, 21))
        font = QtGui.QFont()
        font.setFamily("Ubuntu")
        font.setPointSize(12)
        font.setBold(True)
        font.setWeight(75)
        self.labelVehicleID.setFont(font)
        self.labelVehicleID.setStyleSheet("color: rgb(236, 145, 45);")
        self.labelVehicleID.setObjectName("labelVehicleID")
        self.label_2 = QtWidgets.QLabel(self.centralwidget)
        self.label_2.setGeometry(QtCore.QRect(10, 70, 461, 31))
        font = QtGui.QFont()
        font.setPointSize(16)
        font.setBold(True)
        font.setWeight(75)
        self.label_2.setFont(font)
        self.label_2.setObjectName("label_2")
        self.txtVehicleStatus = QtWidgets.QPlainTextEdit(self.centralwidget)
        self.txtVehicleStatus.setEnabled(True)
        self.txtVehicleStatus.setGeometry(QtCore.QRect(30, 390, 331, 51))
        self.txtVehicleStatus.setObjectName("txtVehicleStatus")
        self.labelIcon = QtWidgets.QLabel(self.centralwidget)
        self.labelIcon.setGeometry(QtCore.QRect(0, 0, 131, 51))
        self.labelIcon.setStyleSheet("background-color: rgb(30, 43, 61);")
        self.labelIcon.setObjectName("labelIcon")
        self.labelIcon_2 = QtWidgets.QLabel(self.centralwidget)
        self.labelIcon_2.setGeometry(QtCore.QRect(30, 370, 121, 17))
        font = QtGui.QFont()
        font.setFamily("Amazon Ember")
        font.setPointSize(12)
        font.setBold(True)
        font.setWeight(75)
        self.labelIcon_2.setFont(font)
        self.labelIcon_2.setObjectName("labelIcon_2")
        self.labelIcon_3 = QtWidgets.QLabel(self.centralwidget)
        self.labelIcon_3.setGeometry(QtCore.QRect(0, 0, 3000, 60))
        self.labelIcon_3.setStyleSheet("background-color: rgb(35, 47, 63);")
        self.labelIcon_3.setObjectName("labelIcon_3")
        self.labelIcon_3.raise_()
        self.btnDeploy.raise_()

        self.labelVehicleID.raise_()
        self.label_2.raise_()
        self.txtVehicleStatus.raise_()
        self.labelIcon.raise_()
        self.labelIcon_2.raise_()
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 1034, 22))
        self.menubar.setObjectName("menubar")
        MainWindow.setMenuBar(self.menubar)
        self.statusBar = QtWidgets.QStatusBar(MainWindow)
        self.statusBar.setObjectName("statusBar")
        MainWindow.setStatusBar(self.statusBar)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "Breeze~"))
        self.btnDeploy.setText(_translate("MainWindow", "CAMPAIGN\n"
" DEPLOY"))
        self.labelVehicleID.setText(_translate("MainWindow", "Vehicle ID :"))
        self.label_2.setText(_translate("MainWindow", "Campaigns"))
        self.labelIcon.setText(_translate("MainWindow", "TextLabel"))
        self.labelIcon_2.setText(_translate("MainWindow", "Vehicle Status"))
        self.labelIcon_3.setText(_translate("MainWindow", "TextLabel"))

