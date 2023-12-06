from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication, QLabel, QFrame
import sys
import subprocess
import main_frame
import json
import logging
import boto3
from botocore.exceptions import ClientError
import os

INITIAL_TIMER_DELAY = 5000
TIMER_DELAY = 5000

log = logging.getLogger('app_logger')
logging.basicConfig(format='[%(asctime)s %(levelname)s] %(message)s', level=logging.DEBUG)


with open("./setup_config.json", "r") as c:
    conf = json.load(c)

isGamma = conf.get('gamma', "false")

if isGamma == "true":
    session = boto3.Session()
    session._loader.search_paths.extend([os.path.dirname(os.path.abspath(__file__)) + "/models"])
    fleetwise = session.client("iotfleetwise", region_name='us-west-2', endpoint_url='https://controlplane.us-west-2.gamma.kaleidoscope.iot.aws.dev')

else:
    fleetwise = boto3.client(
        'iotfleetwise'
    )

with open("./config.json", "r") as f:
    campaigns = json.load(f)

vehicle_id = campaigns["vehicleName"]

class VLine(QFrame):
    # a simple VLine, like the one you get from designer
    def __init__(self):
        super(VLine, self).__init__()
        self.setFrameShape(self.VLine|self.Sunken)

class BreezeApp(QtWidgets.QMainWindow, main_frame.Ui_MainWindow):
    def __init__(self, logger, parent=None):
        super(BreezeApp, self).__init__(parent)
        self.setupUi(self)
        self.labelVehicleID.setText("Vehicle ID :  " + vehicle_id)

        self.checkBoxes = []

        for i, e in enumerate(campaigns["campaigns"]):
            checkBox = QtWidgets.QCheckBox(e["name"], self.centralwidget)
            checkBox.setGeometry(QtCore.QRect(10, 110 + i*40, 400, 30))
            self.checkBoxes.append(checkBox)
        self.btnDeploy.clicked.connect(self.btnDeploy_clicked)

        self.my_logger = logger
        self.timer=QTimer()
        self.timer.timeout.connect(self.timer_timeout)
        self.pixmap = QPixmap('./resources/aws_icon.png')

        self.labelIcon.setPixmap(self.pixmap)

        # Optional, resize label to image size
        self.labelIcon.resize(self.pixmap.width(), self.pixmap.height())
        self.statusBar.showMessage("Initialized. Please, deploy a campaign.")

        self.lbl1 = QLabel("Label: ")
        self.lbl1.setStyleSheet('border: 0; color:  blue;')
        self.lbl2 = QLabel("Data : ")
        self.lbl2.setStyleSheet('border: 0; color:  red;')

        self.statusBar.reformat()
        self.statusBar.setStyleSheet('border: 0; background-color: #FFF8DC;')
        self.statusBar.setStyleSheet("QStatusBar::item {border: none;}")

        self.statusBar.addPermanentWidget(VLine())    # <---
        self.statusBar.addPermanentWidget(self.lbl1)
        self.statusBar.addPermanentWidget(VLine())    # <---
        self.statusBar.addPermanentWidget(self.lbl2)

        self.lbl1.setText("  Vehicle Status : __________________   ")
        self.lbl2.setText("  Campaign Status : __________________   ")
        self.active_campaign = []

    def timer_timeout(self):
        self.timer.stop()
        if not self.active_campaign:
            self.statusBar.showMessage("No active campaigns.")
            return

        for campaign_name in self.active_campaign:
            self.statusBar.showMessage(f"Checking campaign status... {campaign_name}")
            campaign_status = fleetwise.get_campaign(name=campaign_name)
            # Assuming you want to update lbl2 with the status of each campaign
            self.lbl2.setText(f"Campaign Status for {campaign_name}: {campaign_status['status']}")

            if campaign_status["status"] == "WAITING_FOR_APPROVAL":
                print(f"Approving campaign: {campaign_name}")
                fleetwise.update_campaign(name=campaign_name, action="APPROVE")
                campaign_status = fleetwise.get_campaign(name=campaign_name)
                self.lbl2.setText(f"Campaign Status for {campaign_name}: {campaign_status['status']}")

        # Vehicle status handling remains the same
        self.statusBar.showMessage("Checking vehicle status... " + vehicle_id)
        vehicle_status = fleetwise.get_vehicle_status(vehicleName=vehicle_id)
        status = vehicle_status["campaigns"][0]["status"] if len(vehicle_status["campaigns"]) > 0 else ""
        self.lbl1.setText("  Vehicle Status : " + status)
        self.statusBar.showMessage("")
        self.timer.start(TIMER_DELAY)


    def btnDeploy_clicked(self):
        self.btnDeploy.setEnabled(False)
        for checkBox in self.checkBoxes:
            checkBox.setEnabled(False)
        self.timer.stop()
        self.statusBar.showMessage("Preparing to deploy campaigns...")
        self.my_logger.debug("Deploy Clicked")

        # Suspending all campaigns
        self.my_logger.debug("Suspending all campaigns first")
        for campaign_data in campaigns["campaigns"]:
            campaign_name = campaign_data["name"]
            self.my_logger.debug("<<<<< Suspend campaign: " + campaign_name)
            self.statusBar.showMessage("Suspending a campaign: " + campaign_name)
            fleetwise.update_campaign(name=campaign_name, action='SUSPEND')

        # Handling selected campaigns
        selected_campaigns = [checkBox.text() for checkBox in self.checkBoxes if checkBox.isChecked()]
        if not selected_campaigns:
            self.statusBar.showMessage("No campaigns selected.")
            self.btnDeploy.setEnabled(True)
            for checkBox in self.checkBoxes:
                checkBox.setEnabled(True)
            return

        for campaign in selected_campaigns:
            self.my_logger.debug(f"Processing campaign: {campaign}")
            self.active_campaign = campaign
            self.lbl2.setText("  Campaign Status : __________________   ")

            # Updating and resuming the selected campaign
            print("Update campaign : " + campaign)
            self.statusBar.showMessage("Updating the campaign: " + campaign)
            fleetwise.update_campaign(name=campaign, action='RESUME')
            campaign_status = fleetwise.get_campaign(name=self.active_campaign)
            self.lbl2.setText("  Campaign Status : " + campaign_status["status"])
            self.statusBar.showMessage("Campaign resumed: " + campaign)

        self.btnDeploy.setEnabled(True)
        for checkBox in self.checkBoxes:
            checkBox.setEnabled(True)
        self.timer.start(1000)


def main():
    app = QApplication(sys.argv)
    screen = app.primaryScreen()
    print('Screen: %s' % screen.name())
    size = screen.size()
    print('Size: %d x %d' % (size.width(), size.height()))
    rect = screen.availableGeometry()
    print('Available: %d x %d' % (rect.width(), rect.height()))
    form = BreezeApp(log)
    form.show()
    app.exec_()

if __name__ == '__main__':
    main()


