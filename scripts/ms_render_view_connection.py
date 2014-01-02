import sys
from PySide import QtCore, QtGui, QtNetwork
import maya.cmds as cmds
import maya.OpenMaya as om
import ms_commands
import socket


#----------------------------------------------------------------------------------
# module variables
#----------------------------------------------------------------------------------

global object_mapping
object_mapping = []

global socket_connection
socket_connection = None

global client_connection
client_connection = None

global window
window = None


#----------------------------------------------------------------------------------
# tcp functions
#----------------------------------------------------------------------------------

def socket_open():
    global socket_connection
    if socket_connection is None:
        socket_connection = QtNetwork.QTcpServer()
        if socket_connection.listen():
            print 'Server opened at port:', socket_connection.serverPort()
            socket_connection.newConnection.connect(client_connected)
            return socket_connection
        else:
            print 'Error opening connection'
    else:
        print 'A connection is already open at:', socket_connection.serverPort()
        print 'Close connection before connecting again'
    return None


def socket_close():
    global socket_connection
    socket_connection = None
    print 'Connection closed'


def socket_send(data):
    global socket_connection
    global client_connection

    if client_connection is not None:
        client_connection.write(data)


def client_connected():
    global socket_connection
    global client_connection
    client_connection = socket_connection.nextPendingConnection()


def client_disconnected():
    global window
    window.client_status_no_client()
    print 'client disconnected'


#----------------------------------------------------------------------------------
# callback functions
#----------------------------------------------------------------------------------

def update_color(msg, mplug, other_mplug, client_data):
    global connection
    if connection is not None:
        # update_color(self, assembly_path, color_name, values, multiplier)

        command = 'self.update_color({0}, {1}, {2}, {3})'


def update_transform(msg, mplug, other_mplug, client_data):
    global connection
    if connection is not None:
        pass


#----------------------------------------------------------------------------------
# add/remove callbacks functions
#----------------------------------------------------------------------------------

def add_callback(object_name, callback, client_data):

    s_list = om.MSelectionList()
    s_list.add(object_name)
    m_object = om.MObject()
    s_list.getDependNode(0, m_object)    
    return om.MNodeMessage.addAttributeChangedCallback(m_object, callback, client_data)
    

def remove_callback(callback):
    om.MNodeMessage.removeCallback(callback)


def remove_callbacks():
    global object_mapping
    for callback in object_mapping:
        removeCallback(callback)

    object_mapping = []


#----------------------------------------------------------------------------------
# ConnectionStatus Widget
#----------------------------------------------------------------------------------

class ConnectionStatus(QtGui.QWidget):
    def __init__(self):      
        super(ConnectionStatus, self).__init__()
        self.m_mutex = QtCore.QMutex()
        self.initUI()

        self.open = False
        self.sending = False


    def initUI(self):
        self.width = 12
        self.height = 12
        self.setMaximumWidth(self.width)
        self.setMinimumWidth(self.width)
        self.setMaximumHeight(self.height)
        self.setMinimumHeight(self.height)


    def paintEvent(self, e):
        qp = QtGui.QPainter()
        qp.begin(self)
        qp.setRenderHint(QtGui.QPainter.Antialiasing)
        self.drawWidget(qp)
        qp.end()


    def drawWidget(self, qp):
        pen = QtGui.QPen()
        qp.setPen(QtCore.Qt.NoPen)

        if self.sending:
            brush = QtGui.QBrush(QtGui.QColor(255, 219, 18))
        elif self.open:
            brush = QtGui.QBrush(QtGui.QColor(43, 222, 8))
        else:
            brush = QtGui.QBrush(QtGui.QColor(251, 58, 58))

        qp.setBrush(brush)
        qp.drawEllipse(0, 0, self.width, self.height)


    def status_open(self):
        self.open = True
        self.update()


    def status_closed(self):
        self.open = False
        self.update()


    def status_sending_data(self):
        self.sending = True
        self.update()
        QtCore.QTimer.singleShot(10, self.status_stop_sending_data)


    def status_stop_sending_data(self):
        self.sending = False
        self.update()


#----------------------------------------------------------------------------------
# ConnectionWindow Widget
#----------------------------------------------------------------------------------

class ConnectionWindow(QtGui.QMainWindow):
    def __init__(self):
        super(ConnectionWindow, self).__init__()
        self.initUI()
        self.app_controller = None

    def initUI(self):

        global socket_connection
        self.socket_connection = socket_connection

        global window
        window = self

        # keep window on top
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)

        # set object name so maya can query the window object's existence
        self.setObjectName('ms_render_view_connection_window')

        self.setGeometry(100, 100, 310, 50)
        self.setMaximumHeight(50)
        self.setWindowTitle('Render view connection')

        self.window = QtGui.QWidget()
        self.main_layout = QtGui.QVBoxLayout()

        self.setCentralWidget(self.window)
        self.window.setLayout(self.main_layout)

        if len(object_mapping) != 0:
            self.maping_button = QtGui.QPushButton('Re-generate object mapping')
        else:
            self.maping_button = QtGui.QPushButton('Generate object mapping')

        # mapping button
        self.main_layout.addWidget(self.maping_button)

        # open close buttons
        self.line = QtGui.QFrame()
        self.line.setFrameShape(QtGui.QFrame.HLine)
        self.line.setFrameShadow(QtGui.QFrame.Sunken)

        self.main_layout.addWidget(self.line)

        self.open_close_buttons_layout = QtGui.QHBoxLayout()
        self.main_layout.addLayout(self.open_close_buttons_layout)

        self.open_button = QtGui.QPushButton('Open')
        self.open_close_buttons_layout.addWidget(self.open_button)

        self.close_button = QtGui.QPushButton('Close')
        self.open_close_buttons_layout.addWidget(self.close_button)

        # server status 
        self.server_status_layout = QtGui.QHBoxLayout()
        self.main_layout.addLayout(self.server_status_layout)

        self.server_status_label = QtGui.QLabel('Server:')
        self.server_status_label.setMinimumWidth(40)
        self.server_status_layout.addWidget(self.server_status_label)

        self.server_connection_status = ConnectionStatus()
        self.server_status_layout.addWidget(self.server_connection_status)

        self.server_status_label = QtGui.QLabel()
        self.server_status_layout.addWidget(self.server_status_label)

        if self.socket_connection is None:
            self.server_status_closed()
        else:
            self.server_status_open()

        self.server_status_layout.addStretch()

        # client status 
        self.client_status_layout = QtGui.QHBoxLayout()
        self.main_layout.addLayout(self.client_status_layout)

        self.client_status_label = QtGui.QLabel('Client:')
        self.client_status_label.setMinimumWidth(40)
        self.client_status_layout.addWidget(self.client_status_label)

        self.client_connection_status = ConnectionStatus()
        self.client_status_layout.addWidget(self.client_connection_status)

        self.client_status_label = QtGui.QLabel()
        self.client_status_layout.addWidget(self.client_status_label)
        self.client_status_no_client()
        self.client_status_layout.addStretch()

        # connections
        self.maping_button.pressed.connect(self.generate_mapping)
        self.open_button.pressed.connect(self.server_open)
        self.close_button.pressed.connect(self.server_close)


    def generate_mapping(self):
        self.maping_button.setText('Re-generate object mapping')


    def server_open(self):
        self.socket_connection = socket_open()
        if self.socket_connection is not None:
            self.server_status_open(self.socket_connection.serverPort())
            self.socket_connection.newConnection.connect(self.client_status_got_client)
        else:
            self.server_status_closed()


    def server_close(self):
        socket_close()
        self.server_status_closed()


    def server_status_open(self, port):
        self.server_status_label.setText('Connection open at port: {0}'.format(port))
        self.server_connection_status.status_open()


    def server_status_closed(self):
        self.server_status_label.setText('No connection')
        self.server_connection_status.status_closed()


    def server_status_sending_data(self):
        self.connection_status.status_sending_data()


    def client_status_no_client(self):
        self.client_status_label.setText('No client connected')
        self.client_connection_status.status_closed()

    def client_status_got_client(self):
        self.client_status_label.setText('Client connected')
        self.client_connection_status.status_open()




