import sys
import os
import json
import glob
import time
import datetime
import requests
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from PySide6 import  QtWidgets
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtCore import Qt, QDate, QThread, Signal, QTimer
from PySide6.QtWidgets import QLineEdit,QWidget,QFormLayout,QVBoxLayout,QSpacerItem,QSizePolicy,QGridLayout,QPushButton,QLabel,QDateEdit,QHBoxLayout
from backgroundfunction import loginCredValidation, registerNewUser,connectToServer, retriveDataChunk, saveCurrentTempFile, requestCalibration, startUpBlender,clearTempFolder

class ConnectThread(QThread):
    connection_result = Signal(bool) 
    def run(self):
        connectvalidation = connectToServer()
        self.connection_result.emit(connectvalidation)  

class runSim(QThread):
    def __init__(self, source,status):
        super().__init__()
        self.source = 'real_time'
        self.irt = 0
        self.status = status
        self.base_url = "http://127.0.0.1:5000"
        self.simstatepath = "/Users/ryanjewett/Documents/CPE4850/simstate.json"

    def updateData(self):
        try:
            now = datetime.datetime.now()
            current_date = now.date()
            current_time = (now + datetime.timedelta(seconds=-1)).strftime("%H:%M:%S")  
            data = None
            time.sleep(1)
            if self.source == 'real_time':
                try:
                    response = requests.get(f"{self.base_url}/ret/real_data/{current_date}/{current_time}/")
                    #response = requests.get(f"{self.base_url}/ret/real_data/2024-10-10/10:10:10/")
                    response.raise_for_status()
                    data = response.json()
                except requests.exceptions.RequestException as e:
                    print(f"Request failed: {e}")
                    return False
            elif self.source == 'saved_data':
                try:
                    with open('tempfile.json', 'r') as f:
                        saved_data = json.load(f)
                        if self.irt < len(saved_data):
                            data = saved_data[self.irt]
                        else:
                            return False
                except (FileNotFoundError, json.JSONDecodeError) as e:
                    print(f"File error: {e}")
                    return False

            if data is not None:
                try:
                    with open('tempdata.json', 'w') as f:
                        json.dump(data, f, indent=4)
                except Exception as e:
                    print(f"Failed to write data: {e}")
                    return False

            return True
        except Exception as ex:
            print(f"An unexpected error occurred: {ex}")
            return False

    def stopBlender(self):
        data = [{"isrunning": 0}, {"renderStatus": 1}]
        with open(self.simstatepath, 'w') as f:
            json.dump(data, f)

    def run(self):
        data = [{"isrunning": 1}, {"renderStatus": 1}]
        with open(self.simstatepath, 'w') as f:
            json.dump(data, f)
        self.irt = 0
        while self.status:
            val = self.updateData()
            #time.sleep(1)
            #if not val:
            #    break
            self.irt += 1
    
    def updateMode(self,source):
        self.source = source

class MatplotlibCanvas(FigureCanvas):
    def __init__(self, parent=None, max_time_range=10):
        self.fig, self.ax = plt.subplots()
       
        super().__init__(self.fig)
        self.setParent(parent)
        
        self.max_time_range = max_time_range
        self.error_data = []
        self.time_data = []
        
        self.body_parts = ['left_shoulder', 'middle_back', 'right_shoulder']
        self.y_positions = range(len(self.body_parts))  
        
        self.ax.set_ylim(-0.5, len(self.body_parts) - 0.5)
        self.ax.set_yticks(self.y_positions)
        self.ax.set_yticklabels(self.body_parts) 
        self.ax.set_xlabel("Time")
        self.ax.set_ylabel("Errors")
        self.fig.autofmt_xdate()  

        self.persistent_errors = {part: [] for part in self.body_parts}  

    def update_graph(self, error_status):
        current_time = datetime.datetime.now()
        self.error_data.append(error_status)
        self.time_data.append(current_time)

        min_time = current_time - datetime.timedelta(seconds=self.max_time_range)
        while self.time_data and self.time_data[0] < min_time:
            self.time_data.pop(0)
            self.error_data.pop(0)

        self.ax.clear()
        
        self.ax.set_ylim(-0.5, len(self.body_parts) - 0.5)
        self.ax.set_yticks(self.y_positions)
        self.ax.set_yticklabels(self.body_parts)
        self.ax.set_xlabel("Time")
        self.ax.set_ylabel("Errors")
        self.ax.set_title("Posture Error Graph")
        self.fig.autofmt_xdate()

        current_errors = error_status[0]  

        for idx, part in enumerate(self.body_parts):
            if current_errors[part] == 1:  
                self.persistent_errors[part].append(self.time_data[-1])  

        for idx, part in enumerate(self.body_parts):
            for i, error_time in enumerate(self.persistent_errors[part]):
                if error_time >= min_time:
                    # Offset the time slightly to avoid overlapping points
                    plot_time = error_time + datetime.timedelta(milliseconds=100 * i)
                    if part == 'left_shoulder':
                        self.ax.plot(plot_time, idx, 'ro', label='Left Shoulder' if i == 0 else "")
                    elif part == 'middle_back':
                        self.ax.plot(plot_time, idx, 'bs', label='Middle Back' if i == 0 else "")
                    else:
                        self.ax.plot(plot_time, idx, 'g^', label='Right Shoulder' if i == 0 else "")
                        
        self.ax.set_xlim(min_time, current_time)
        self.draw()

class MatplotRawData(FigureCanvas):
    def __init__(self):
        self.past_data = {}
        self.fig, self.axs = plt.subplots(3,1) 
        self.fig.subplots_adjust(hspace=0.4)
        super().__init__(self.fig)
        self.body_parts =  ["left_shoulder", "middle_back", "right_shoulder"]
        self.data = {} 
        for i, body_part in enumerate(self.body_parts):
            self.axs[i].set_title(f'{body_part.capitalize()}')
            #self.axs[i].set_xlabel('Time')
            self.axs[i].set_ylabel('Position (x, y, z)')
            #self.axs[i].legend(['x', 'y', 'z'])

    def update_data(self, new_data):
        time = datetime.datetime.now()
        
        if not new_data:
            if not self.past_data:
                new_data = {
                            "date": "2024-11-06",
                            "left_elbow": {
                                "x":0,
                                "y":0,
                                "z":0
                            },
                            "left_shoulder": {
                                "x": 0,
                                "y": 0,
                                "z": 0
                            },
                            "middle_back": {
                                "x": 0,
                                "y": 0,
                                "z": 0
                            },
                            "right_elbow": {
                                "x": 0,
                                "y": 0,
                                "z": 0
                            },
                            "right_shoulder": {
                                "x": 0,
                                "y": 0,
                                "z": 0
                            },
                            "time": "00:00:00"
                        }
                print("No data found")
            else:
                new_data = self.past_data
                print("setting as past data")
        else:
            print("data found")
            self.past_data = new_data
        for i, body_part in enumerate(self.body_parts):
            x = new_data[body_part]['x']
            y = new_data[body_part]['y']
            z = new_data[body_part]['z']
            
            if body_part not in self.data:
                self.data[body_part] = {'timestamp': [], 'x': [], 'y': [], 'z': []}
            
            self.data[body_part]['timestamp'].append(time)
            self.data[body_part]['x'].append(x)
            self.data[body_part]['y'].append(y)
            self.data[body_part]['z'].append(z)

            if len(self.data[body_part]['timestamp']) > 10:
                self.data[body_part]['timestamp'].pop(0)
                self.data[body_part]['x'].pop(0)
                self.data[body_part]['y'].pop(0)
                self.data[body_part]['z'].pop(0)
                    
            self.axs[i].cla()
            self.axs[i].plot(self.data[body_part]['timestamp'], self.data[body_part]['x'], label='x', color='r')
            self.axs[i].plot(self.data[body_part]['timestamp'], self.data[body_part]['y'], label='y', color='g')
            self.axs[i].plot(self.data[body_part]['timestamp'], self.data[body_part]['z'], label='z', color='b')
            self.axs[i].set_title(f'{body_part.capitalize()}')
            #self.axs[i].set_xlabel('Time')
            #self.axs[i].set_ylabel('Position')
            self.axs[i].legend()

        self.draw()

class updateUDGraph(QThread):
    error_signal = Signal(list)  
    new_raw_data = Signal(dict)

    def __init__(self, base_url="http://127.0.0.1:5000", update_interval=1, graph_type = 1):
        super().__init__()
        self.base_url = base_url
        self.update_interval = update_interval
        self.graph_type = graph_type

    def getErrorStatus(self):
        try:
            response = requests.get(f"{self.base_url}/geter")
            response.raise_for_status()
            data = response.json()  # Expecting [{'left_shoulder': 0, 'middle_back': 0, 'right_shoulder': 0}]
            if data:  
                return data 
            else:
                return None 
        except Exception as e:
            print(f"Error getting current error: {str(e)}")
            return [{'left_shoulder': 0, 'middle_back': 0, 'right_shoulder': 0}]  
    def getRawData(self):
        try:
            now = datetime.datetime.now()
            current_date = now.date()
            current_time = (now + datetime.timedelta(seconds=-1)).strftime("%H:%M:%S")  

            response = requests.get(f"{self.base_url}/ret/real_data/{current_date}/{current_time}/")
            #response = requests.get(f"{self.base_url}/ret/real_data/2024-10-10/10:10:10/")
            new_data = response.json()
            if response.status_code ==200:
                return new_data
            else:
                return 1
        except Exception as e:
            print(f"Error in getting raw data: {str(e)}")
            return 1
           
    def run(self):
        while True:
            if self.graph_type == 1:
                error_status = self.getErrorStatus()
                self.error_signal.emit(error_status)  
                self.msleep(self.update_interval * 1000)
            elif self.graph_type == 2:
                new_data = self.getRawData()
                self.new_raw_data.emit(new_data)
                self.msleep(self.update_interval *1000)
    
class connectServerWindow(QtWidgets.QTabWidget):

    def __init__(self, mainWindow):
        super().__init__()

        self.mainWindow = mainWindow
        self.conntingText = QtWidgets.QLabel("Connecting...")
        self.failedText = QtWidgets.QLabel("Failed To Connect To Server :(")

        self.retrybutton = QtWidgets.QPushButton("Retry")
        self.retrybutton.setMaximumSize(200,100)
        self.retrybutton.clicked.connect(self.retryConnect)
        self.conntingText.setVisible(True)
        self.retrybutton.setVisible(False)
        self.failedText.setVisible(False)

        flo = QFormLayout()
        flo.addRow(self.conntingText)
        flo.addRow(self.failedText)
        flo.addRow(self.retrybutton)

        centerbox = QVBoxLayout()
        centerbox.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        centerbox.addLayout(flo)
        centerbox.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        centerbox.setAlignment(flo, Qt.AlignCenter)
        self.setLayout(centerbox)

        self.connectThread = ConnectThread()
        self.connectThread.connection_result.connect(self.onConnectionResult)
        self.connectThread.start()  

    def retryConnect(self):
        self.connectingVisablity()
        self.connectThread.start()  

    def connectingVisablity(self):
        self.conntingText.setVisible(True)
        self.failedText.setVisible(False)
        self.retrybutton.setVisible(False)

    def retryConnectVisablitly(self):
        self.failedText.setVisible(True)
        self.retrybutton.setVisible(True)
        self.conntingText.setVisible(False)

    def onConnectionResult(self, connectvalidation):
        if connectvalidation:
            self.mainWindow.showLoginWindow()
        else:
            self.retryConnectVisablitly()

class loginWindow(QtWidgets.QTabWidget):

    def __init__(self,mainWindow):

        super().__init__()

        self.setWindowTitle("Login Window")
        self.mainWindow = mainWindow
        
        #self.setMaximumSize(800,600)
        #self.setMinimumSize(800,600)
        #self.resize(800,600)

        stylesheet = """
        QWidget {
            background-color: qlineargradient(x1: 0, x2: 1, stop: 0 cyan, stop: 1 magenta);
        }
        QLineEdit {
            background-color: white;
            color: black;
            border: 1px solid gray;
            border-radius: 10px;  
            padding: 5px;  
        }
        QPushButton {
            background-color: white;
            color: black;
            border: 1px solid gray;
            border-radius: 10px;  
            padding: 5px;
        }
        QLabel {
            background-color: white;
            color: black;
            border: 1px solid gray;
            border-radius: 10px; 
            padding: 5px;

        }
        """
        self.setStyleSheet(stylesheet)

        self.username = QLineEdit()
        self.username.setMaxLength(12)
        self.username.setFont(QFont("Times New Roman",20))

        self.password = QLineEdit()
        self.password.setMaxLength(12)
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setFont(QFont("Times New Roman",20))

        self.submitButton = QtWidgets.QPushButton("Login")
        self.submitButton.clicked.connect(self.loginValidation)

        self.registerButton = QtWidgets.QPushButton("Register")
        self.registerButton.clicked.connect(self.registerUser)

        self.failedtext = QtWidgets.QLabel("Failed Login or Register")
        self.failedtext.setVisible(False)

        flo = QFormLayout()
        flo.addWidget(self.failedtext)
        flo.addRow("Username",self.username)
        flo.addRow("Password",self.password)
        flo.addWidget(self.submitButton)
        flo.addWidget(self.registerButton)
        
        self.central_layout = QVBoxLayout()
        self.central_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        self.central_layout.addLayout(flo)
        self.central_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        self.central_layout.setAlignment(flo, Qt.AlignCenter)
        self.setLayout(self.central_layout)

    def loginValidation(self):
        usernameTxt = self.username.text()
        passwordTxt = self.password.text()
        validation = loginCredValidation(username=usernameTxt, password=passwordTxt)
        if validation == True:
            self.mainWindow.showUserDash()
        else:
            self.failedLogin()
    
    def registerUser(self):
        usernameTxt = self.username.text()
        passwordTxt = self.password.text()
        validation = registerNewUser(username=usernameTxt,password=passwordTxt)
        if validation == True:
            self.mainWindow.showUserDash()
        else:
            self.failedLogin()
        
    def failedLogin(self):
        self.username.clear()
        self.password.clear()

        self.failedtext.setVisible(True)
    
    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.loginValidation()

class userDash(QWidget):
    def __init__(self, mainWindow):
        super().__init__()

        self.mainWindow = mainWindow
        self.currentGraphType = 1
        stylesheet = """
        QLineEdit { background-color: white; color: black; border: 1px solid gray; border-radius: 10px; padding: 5px; }
        QPushButton { background-color: white; color: black; border: 1px solid gray; border-radius: 10px; padding: 5px; }
        QLabel { background-color: white; color: black; border: 1px solid gray; border-radius: 10px; padding: 5px; }
        """
        self.setStyleSheet(stylesheet)

        self.mainLayout = QHBoxLayout()
        self.buttonLayout = QVBoxLayout()

        self.welcomeLabel = QLabel("Welcome to the User Dashboard")
        self.welcomeLabel.setAlignment(Qt.AlignCenter)
        self.buttonLayout.addWidget(self.welcomeLabel)
        self.buttonLayout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        
        self.create_buttons()
        
        self.graphError = MatplotlibCanvas(self, max_time_range=10)
        self.mainLayout.addWidget(self.graphError)
        self.graphError.setVisible(True)

        self.graphData = MatplotRawData()
        self.mainLayout.addWidget(self.graphData)
        self.graphData.setVisible(False)

        self.graphThread = updateUDGraph(graph_type=self.currentGraphType)
        self.graphThread.error_signal.connect(self.graphError.update_graph)
        self.graphThread.new_raw_data.connect(self.graphData.update_data)
        self.graphThread.start()

        self.setLayout(self.mainLayout)

    def create_buttons(self):
        button_specs = [
           
            ("Retrieve Past Data", self.retrievePastData),
            ("Real-Time Sim", self.viewRealTimeData),
            #("Manage Alerts", self.manageAlerts),
            ("Calibrate", self.calibrate),
            ("Download Data", self.downloadData),
            ("Change Graph", self.changeGraph),
            ("Sign Out", self.signOut)
        ]

        for text, handler in button_specs:
            button = QPushButton(text)
            button.setMaximumSize(200, 100)
            button.clicked.connect(handler)
            self.buttonLayout.addWidget(button)
        
        self.buttonLayout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        self.mainLayout.addLayout(self.buttonLayout)

    def changeGraph(self):
        if self.currentGraphType == 1:
            self.graphThread.graph_type =2
            self.currentGraphType = 2
            self.graphError.setVisible(False)
            self.graphData.setVisible(True)
        else:
           self.graphThread.graph_type =1
           self.currentGraphType = 1
           self.graphError.setVisible(True)
           self.graphData.setVisible(False)
        
    def signOut(self):
        self.graphThread.terminate()
        self.mainWindow.showLoginWindow()

    def retrievePastData(self):
        self.graphThread.terminate()
        self.mainWindow.retivePastDataWindow()

    def viewRealTimeData(self):
        self.graphThread.terminate()
        self.mainWindow.showBlendWindow()

    def manageAlerts(self):
        self.graphThread.terminate()
        self.mainWindow.showManageAlertWindow()

    def calibrate(self):
        self.graphThread.terminate()
        self.mainWindow.showCalibrationWindow()

    def downloadData(self):
        self.graphThread.terminate()
        self.mainWindow.showDataDownloadWindow()

class retrievePastDataWindow(QWidget):
    def __init__(self, mainWindow):
        super().__init__()

        self.mainWindow = mainWindow

        stylesheet = """
        QWidget {
            background-color: grey;
        }
        QLineEdit {
            background-color: white;
            color: black;
            border: 1px solid gray;
            border-radius: 10px;  
            padding: 5px;  
        }
        QPushButton {
            background-color: white;
            color: black;
            border: 1px solid gray;
            border-radius: 10px;  
            padding: 5px;
        }
        QLabel {
            background-color: white;
            color: black;
            border: 1px solid gray;
            border-radius: 10px; 
            padding: 5px;

        }
        """
        self.setStyleSheet(stylesheet)

        self.mainLayout = QVBoxLayout()
        self.topLayout = QHBoxLayout()

        self.retiveSuccessText = QLabel("Data Retrieved Successfully")
        self.retiveSuccessText.setAlignment(Qt.AlignCenter)
        self.retiveSuccessText.setVisible(False)

        self.retiveFailedText = QLabel("Data Retrieval Failed")
        self.retiveFailedText.setAlignment(Qt.AlignCenter)
        self.retiveFailedText.setVisible(False)

        self.backButton = QPushButton("Back")
        self.backButton.clicked.connect(self.goBack)
        self.topLayout.addWidget(self.backButton)
        self.topLayout.addStretch()

        self.mainLayout.addLayout(self.topLayout)

        self.titleLabel = QLabel("Select Date Range to Retrieve Past Data")
        self.titleLabel.setAlignment(Qt.AlignCenter)
        self.mainLayout.addWidget(self.titleLabel)

        self.startDateLabel = QLabel("Start Date:")
        self.startDateEdit = QDateEdit()
        self.startDateEdit.setCalendarPopup(True)
        self.startDateEdit.setDate(QDate.currentDate())
        self.endDateLabel = QLabel("End Date:")
        self.endDateEdit = QDateEdit()
        self.endDateEdit.setCalendarPopup(True)
        self.endDateEdit.setDate(QDate.currentDate())

        dateLayout = QHBoxLayout()
        dateLayout.addWidget(self.startDateLabel)
        dateLayout.addWidget(self.startDateEdit)
        dateLayout.addWidget(self.endDateLabel)
        dateLayout.addWidget(self.endDateEdit)
        self.mainLayout.addLayout(dateLayout)

        self.submitButton = QPushButton("Retrieve Data")
        self.submitButton.clicked.connect(self.retrieveData)
        self.mainLayout.addWidget(self.submitButton)

        self.mainLayout.addWidget(self.retiveSuccessText)
        self.mainLayout.addWidget(self.retiveFailedText)

        #sself.mainLayout.addStretch()

        self.setLayout(self.mainLayout)

    def goBack(self):
        if  not (self.retiveFailedText.isVisible() or self.retiveSuccessText.isVisible()):
            self.mainWindow.showUserDash()
        else:
            self.backButton.setVisible(True)
            self.retiveSuccessText.setVisible(False)
            self.retiveFailedText.setVisible(False)
            self.submitButton.setVisible(True)
            self.startDateEdit.setVisible(True)
            self.endDateEdit.setVisible(True)
            self.startDateLabel.setVisible(True)
            self.endDateLabel.setVisible(True)
            self.titleLabel.setVisible(True)

    def retrieveData(self):
        startDate = self.startDateEdit.date()
        endDate = self.endDateEdit.date()

        startDateReForm = startDate.toPython()
        endDateReForm = endDate.toPython()
        print(f"startdate:{startDateReForm},enddate:{endDateReForm} ")

        val = retriveDataChunk(str(startDateReForm), str(endDateReForm))

        if val == True:
            self.successDataRet()
        else:
            self.failedDataRet()

    def successDataRet(self):
        
        self.submitButton.setVisible(False)
        self.startDateEdit.setVisible(False)
        self.endDateEdit.setVisible(False)
        self.startDateLabel.setVisible(False)
        self.endDateLabel.setVisible(False)
        self.titleLabel.setVisible(False)

        self.retiveSuccessText.setVisible(True)

    def failedDataRet(self):
        
        self.submitButton.setVisible(False)
        self.startDateEdit.setVisible(False)
        self.endDateEdit.setVisible(False)
        self.startDateLabel.setVisible(False)
        self.endDateLabel.setVisible(False)
        self.titleLabel.setVisible(False)
        self.backButton.setVisible(False)

        self.retiveFailedText.setVisible(True)

        QTimer.singleShot(3000, self.goBack)

class realTimeModelWindow(QWidget):
    def __init__(self, mainWindow):
        super().__init__()

        self.runningsim = False

        self.pathToTempFolder= "/Users/ryanjewett/Documents/CPE4850/SAVE_HERE"

        self.newestFile = "/Users/ryanjewett/Documents/CPE4850/backupimage.jpeg"
        self.fallbackImage = "/Users/ryanjewett/Documents/CPE4850/backupimage.jpeg"

        self.mode = 'real_time'
        self.currentMesh = None
        self.mainWindow = mainWindow

        stylesheet = """
    
        QLineEdit {
            background-color: white;
            color: black;
            border: 1px solid gray;
            border-radius: 10px;  
            padding: 5px;  
        }
        QPushButton {
            background-color: white;
            color: black;
            border: 1px solid gray;
            border-radius: 10px;  
            padding: 5px;
        }
        QLabel {
            background-color: white;
            color: black;
            border: 1px solid gray;
            border-radius: 10px; 
            padding: 5px;

        }
        """

        self.setStyleSheet(stylesheet)
        
        self.topLayout = QHBoxLayout()
        self.mainLayout = QVBoxLayout()

        self.backButton = QPushButton("Back")
        self.backButton.clicked.connect(self.goBack)
        self.topLayout.addWidget(self.backButton)

        #self.startModel = QPushButton("Start Blender")
        #self.startModel.clicked.connect(self.startBlenderModel)
        #self.topLayout.addWidget(self.startModel)

        self.startSimButton = QPushButton("Start Sim")
        self.startSimButton.clicked.connect(self.startSim)
        self.topLayout.addWidget(self.startSimButton)

        self.stopSimButton = QPushButton("Stop Sim")
        self.stopSimButton.clicked.connect(self.stopSim)
        self.topLayout.addWidget(self.stopSimButton)

        self.realTimeButton = QPushButton("Real-Time Mode")
        self.realTimeButton.clicked.connect(self.realTimeMode)
        self.topLayout.addWidget(self.realTimeButton)

        self.savedDataButton = QPushButton("Saved Data Mode")
        self.savedDataButton.clicked.connect(self.savedDataMode)
        self.topLayout.addWidget(self.savedDataButton)

        self.mainLayout.addLayout(self.topLayout)

        self.imageLabel = QLabel(self)
        self.mainLayout.addWidget(self.imageLabel)

        self.timer = QTimer(self)  
        self.timer.timeout.connect(self.loadJPEG)  

        self.setLayout(self.mainLayout)

    def loadJPEG(self):
        jpeg_files = glob.glob(os.path.join(self.pathToTempFolder, '*.jpeg'))
        if jpeg_files:
            self.newestFile = max(jpeg_files, key=os.path.getmtime)
            self.fallbackImage = self.newestFile
            print("Newest JPEG file:", self.newestFile)
        else:
            print("No JPEG files found.")
            self.newestFile = self.fallbackImage

        pixmap = QPixmap(self.newestFile)  
        self.imageLabel.setPixmap(pixmap)
        self.imageLabel.setScaledContents(True)  
        self.imageLabel.adjustSize()

    def goBack(self):
        if self.runningsim: self.stopSim()
        self.mainWindow.showUserDash()

    def startBlenderModel(self):
        val = startUpBlender()
        if val:
            print("blender started")
        else:
            print("blender failed")
        return
    
    def startSim(self):

        val = startUpBlender()
        if not val:
            print("blender failed")
            return
        print("blender started")
        val = clearTempFolder(self.pathToTempFolder)
        if val:
            self.simThread = runSim(self.mode,status=True)
            self.runningsim = True
            self.simThread.start()
            self.timer.start(1000)
        else:
            print("error in clearing temp folder")

    def realTimeMode(self):
        self.mode = 'real_time'
        self.simThread.updateMode(self.mode)
    def savedDataMode(self):
        self.mode = 'saved_data'
        self.simThread.updateMode(self.mode)
        
    def stopSim(self):
        self.simThread.stopBlender()
        self.runningsim = False
        self.simThread.terminate()
        self.timer.stop()

class manageAlertWindow(QWidget):
    def __init__(self,mainWindow):
        super().__init__()

        self.mainWindow = mainWindow

class calibrationWindow(QWidget):
    def __init__(self, mainWindow):
        super().__init__()

        stylesheet = """
        QLineEdit { background-color: white; color: black; border: 1px solid gray; border-radius: 10px; padding: 5px; }
        QPushButton { background-color: white; color: black; border: 1px solid gray; border-radius: 10px; padding: 5px; }
        QLabel { background-color: white; color: black; border: 1px solid gray; border-radius: 10px; padding: 5px; }
        """
        self.setStyleSheet(stylesheet)
        self.startCalibrationButton = QPushButton("Start Calibration")
        self.startCalibrationButton.pressed.connect(self.startCalibration)

       

        self.successText = QLabel("Calibration Request Success")
        self.successText.setAlignment(Qt.AlignCenter)
        self.successText.setVisible(False)

        self.failedText = QLabel("Calibration Request Failed")
        self.failedText.setAlignment(Qt.AlignCenter)
        self.failedText.setVisible(False)

        self.inProgressText = QLabel("Calibration in Progress, Please Stay Still")
        self.inProgressText.setAlignment(Qt.AlignCenter)
        self.inProgressText.setVisible(False)

        self.completedText = QLabel("Calibration Complete")
        self.completedText.setAlignment(Qt.AlignCenter)
        self.completedText.setVisible(False)

        topLayout = QGridLayout()

        centerLayout = QVBoxLayout()
        centerLayout.addWidget(self.successText)
        centerLayout.addWidget(self.failedText)
        centerLayout.addWidget(self.inProgressText)
        centerLayout.addWidget(self.completedText)
        centerLayout.addWidget(self.startCalibrationButton)
        centerLayout.setAlignment(Qt.AlignCenter)

        mainLayout = QVBoxLayout()
        mainLayout.addLayout(topLayout)
        mainLayout.addLayout(centerLayout)

        self.setLayout(mainLayout)
        self.mainWindow = mainWindow

        self.inProgressTimer = QTimer()
        self.inProgressTimer.setSingleShot(True)
        self.inProgressTimer.timeout.connect(self.showCompletedText)

        self.completedTimer = QTimer()
        self.completedTimer.setSingleShot(True)
        self.completedTimer.timeout.connect(self.goBack)

        self.startCalibration()

    def goBack(self):
        self.mainWindow.showUserDash()

    def startCalibration(self):
        self.val = requestCalibration()
        if self.val:
            self.yay()
        else:
            self.nay()

    def yay(self):
        self.successText.setVisible(True)
        self.failedText.setVisible(False)
        self.startInProgress()

    def nay(self):
        self.successText.setVisible(False)
        self.failedText.setVisible(True)

    def startInProgress(self):
        self.startCalibrationButton.setVisible(False)
        self.inProgressText.setVisible(True)
        self.inProgressTimer.start(5000)  

    def showCompletedText(self):
        #self.startCalibrationButton.setVisible(True)
        self.inProgressText.setVisible(False)
        self.completedText.setVisible(True)
        self.completedTimer.start(3000)  

    def hideCompletedText(self):
        self.completedText.setVisible(False)
        self.successText.setVisible(False)
        self.failedText.setVisible(False)

class dataDownloadWindow(QWidget):
    def __init__(self,mainWindow):
        super().__init__()

        self.successText = QLabel("Data Saved Success")
        self.successText.setAlignment(Qt.AlignCenter)
        self.successText.setVisible(False)

        self.failedText = QLabel("Data Failed to Save")
        self.failedText.setAlignment(Qt.AlignCenter)
        self.failedText.setVisible(False)

        self.runButton = QPushButton("Save Data")
        self.runButton.clicked.connect(self.saveData)
        self.runButton.setVisible(False)

        topLayout = QGridLayout()

        centerLayout = QVBoxLayout()
        centerLayout.addWidget(self.successText)
        centerLayout.addWidget(self.failedText)
        centerLayout.addWidget(self.runButton)
        centerLayout.setAlignment(Qt.AlignCenter)  

        mainLayout = QVBoxLayout()
        mainLayout.addLayout(topLayout)    
        mainLayout.addLayout(centerLayout)  
        
        self.setLayout(mainLayout)

        self.saveTimer = QTimer()
        self.saveTimer.setSingleShot(True)
        self.saveTimer.timeout.connect(self.goBack)
        self.saveTimer.start(3000)
        self.saveData()

        self.mainWindow = mainWindow
    def saveData(self):
        self.val = saveCurrentTempFile()
        if self.val:
            self.yay()
        else:
            self.nay()
    def yay(self):
        self.failedText.setVisible(False)
        self.successText.setVisible(True)
    def nay(self):
        self.successText.setVisible(False)
        self.failedText.setVisible(True)
    def goBack(self):
        self.mainWindow.showUserDash()

class mainWindow(QtWidgets.QMainWindow):      #working like a statemachine, parent class
    def __init__(self):
        super().__init__()

        self.showConnectionWindow()

    def showConnectionWindow(self):
        self.connectwindow = connectServerWindow(self)
        self.setCentralWidget(self.connectwindow)
        self.setWindowTitle("Connection Window")
        self.setMinimumSize(800, 600)

    def showLoginWindow(self):
        self.loginwindow = loginWindow(self)
        self.setCentralWidget(self.loginwindow)
        self.setWindowTitle("Login Window")
        self.setMinimumSize(1100,900)
        self.showFullScreen()
        self.loginwindow.update()
    
    def showUserDash(self):
        self.userdash = userDash(self)
        self.setCentralWidget(self.userdash)
        self.setWindowTitle("User Dash")
        self.setMinimumSize(1100,900)
        self.showFullScreen()
        self.userdash.update()

    def retivePastDataWindow(self):
        self.retivepastdataselect = retrievePastDataWindow(self)
        self.setCentralWidget(self.retivepastdataselect)
        self.setWindowTitle("Date Select")
        self.setMinimumSize(1100,900)
        self.showFullScreen()
        self.retivepastdataselect.update()

    def showBlendWindow(self):
        self.realtimewindow = realTimeModelWindow(self)
        self.setCentralWidget(self.realtimewindow)
        self.setWindowTitle("3D Model")
        self.setMinimumSize(1100,900)
        self.showFullScreen()
        self.realtimewindow.update()
    
    def showManageAlertWindow(self):
        self.managealert = manageAlertWindow(self)
        self.setCentralWidget(self.managealert)
        self.setWindowTitle("Manage Alert")
        self.setFixedSize(800,600)
        self.managealert.update()
    
    def showCalibrationWindow(self):
        self.calibrationcontrol = calibrationWindow(self)
        self.setCentralWidget(self.calibrationcontrol)
        self.setWindowTitle("Calibration Control")
        self.setMinimumSize(1100,900)
        self.showFullScreen()
        self.calibrationcontrol.update()

    def showDataDownloadWindow(self):
        self.datadownload = dataDownloadWindow(self)
        self.setCentralWidget(self.datadownload)
        self.setWindowTitle("Data Download")
        self.setMinimumSize(1100,900)
        self.showFullScreen()
        self.datadownload.update()

if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    widget = mainWindow()
    widget.show()
    sys.exit(app.exec())








"""
known issues:
- calibration not working with blender
- not saving the calibration data in db 
- the data refactor on the bldenr script beign weird
- add ajustablitly to the time scale of the graph
- add scroller to sim
- make setting page: usermode(persion vs apperaacne), time interval setting, 
- add admin mode(select differnt user database)
- add calibration db and error to db
- test server to raspi


"""
