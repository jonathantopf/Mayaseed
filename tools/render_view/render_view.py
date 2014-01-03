#!/usr/bin/python

#
# Copyright (c) 2012 Jonathan Topf
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#

#
# You will need PySide to run this script.
# Download it here: http://qt-project.org/wiki/PySideDownloads
#

import sys
from PySide import QtGui, QtCore, QtNetwork
import os
import subprocess
import re
import signal
import array
import inspect


sys.path.append('/projects/appleseed/sandbox/bin/Ship')

current_script_path = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))

appleseed_schema_path = os.path.join(current_script_path, 'project.xsd')

import appleseed

#----------------------------------------------------------------------------------
# Utilities
#----------------------------------------------------------------------------------

def map_float_to_int(float):
    # return min(255, int(float * 256))
    return min(255, float * 255)


def get_assembly(assembly_container, assembly_path):
    assembly = assembly_container.get_by_name(assembly_path[0])
    if not len(assembly_path) > 1:
        return assembly
    else:
        return get_assembly(assembly.assemblies() ,assembly_path[1:])


#----------------------------------------------------------------------------------
# Appleseed scene edition functions
#----------------------------------------------------------------------------------

def update_color_entity(color_container, color_name, values, multiplier):
    color = color_container.get_by_name(color_name)
    params = color.get_parameters()
    params['multiplier'] = multiplier
    color_container.remove(color)
    color_container.insert(appleseed.ColorEntity(color_name, params, values))


#----------------------------------------------------------------------------------
# Set style function
#----------------------------------------------------------------------------------

def set_style(app):
    # set base style
    
    palette = QtGui.QPalette()

    # set palette
    shadow     = QtGui.QColor(30, 30, 30 )
    background = QtGui.QColor(40, 40, 40 )
    mid        = QtGui.QColor(45 ,45, 45 )
    mid_light  = QtGui.QColor(50 ,50 ,50 )
    light      = QtGui.QColor(90,90,90)
    highlight  = QtGui.QColor(120,180,200)
    text       = QtGui.QColor(220,220,220)

    palette.setBrush(QtGui.QPalette.Window, background)
    palette.setBrush(QtGui.QPalette.WindowText, text)
    palette.setBrush(QtGui.QPalette.Base, background)
    palette.setBrush(QtGui.QPalette.AlternateBase, mid)  
    palette.setBrush(QtGui.QPalette.ToolTipBase, light)  
    palette.setBrush(QtGui.QPalette.ToolTipText, text)  
    palette.setBrush(QtGui.QPalette.Text, text)
    palette.setBrush(QtGui.QPalette.Button, background)
    palette.setBrush(QtGui.QPalette.ButtonText, text)
    palette.setBrush(QtGui.QPalette.BrightText, background)
    palette.setBrush(QtGui.QPalette.Light, background)
    palette.setBrush(QtGui.QPalette.Midlight, light)
    palette.setBrush(QtGui.QPalette.Dark, background)
    palette.setBrush(QtGui.QPalette.Mid, light)
    palette.setBrush(QtGui.QPalette.Shadow, background)

    app.setPalette(palette)

    # set stylesheet
    stylesheet = open('style.qss', 'r')
    style = stylesheet.read()

    style_replacement_patterns = [
        ('TEXT',       text.name()),
        ('SHADOW',     shadow.name()),
        ('BACKGROUND', background.name()),
        ('MID_LIGHT',  mid_light.name()),
        ('MID',        mid.name()),
        ('HIGHLIGHT',  highlight.name()),
        ('LIGHT',      light.name())
    ]

    for pattern in style_replacement_patterns:
        style = style.replace(pattern[0], pattern[1])

    app.setStyleSheet(style)


#----------------------------------------------------------------------------------
# Appleseed Classes
#----------------------------------------------------------------------------------

class TileCallback(appleseed.ITileCallback):
    def __init__(self):
        super(TileCallback, self).__init__()

        self.post_render_tile_methods = []
        self.post_render_methods = []


    def pre_render(self, x, y, width, height):
        pass


    def post_render_tile(self, frame, tile_x, tile_y):
        for method in self.post_render_tile_methods:
            method()

    def post_render(self, frame):
        for method in self.post_render_methods:
            method()


class RendererController(appleseed.IRendererController):
    def __init__(self):
        super(RendererController, self).__init__()

        # catch Control-C
        signal.signal(signal.SIGINT, lambda signal, frame: self.__signal_handler(signal, frame))
        self.__abort = False
        self.terminate = False
        self.progress_methods = []


    def __signal_handler(self, signal, frame):
        print "Ctrl+C, aborting."
        self.__abort = True


    # This method is called before rendering begins.
    def on_rendering_begin(self):
        pass


    # This method is called after rendering has succeeded.
    def on_rendering_success(self):
        pass


    # This method is called after rendering was aborted.
    def on_rendering_abort(self):
        pass


    # This method is called before rendering a single frame.
    def on_frame_begin(self):
        pass


    # This method is called after rendering a single frame.
    def on_frame_end(self):
        pass


    def on_progress(self):
        
        for method in self.progress_methods:
            method()

        if self.__abort:
            return appleseed.IRenderControllerStatus.AbortRendering

        if self.terminate == True:
            self.terminate = False
            return appleseed.IRenderControllerStatus.TerminateRendering

        return appleseed.IRenderControllerStatus.ContinueRendering


#----------------------------------------------------------------------------------
# TcpTonnectionThread
#----------------------------------------------------------------------------------

class TcpTonnectionThread (QtCore.QThread):
    def __init__(self, parent, port):
        QtCore.QThread.__init__(self, parent)
        self.exiting = False

        self.app_controller = parent
        host_name = 'localhost'
        socket_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        socket_connection.bind((host_name, port))
        socket_connection.listen(1)
        socket_connection.setblocking(0)
        self.socket_connection, self.addr = socket_connection.accept()


    def run(self):
        while(True):
            # check for shutdown flag
            if self.exiting:
                break

            # listen for commands
            data = self.socket_connection.recv(4096)
            if data:
                self.app_controller.main_window.console_info('Received_data --------------------')
                for line in data.split('\n'):
                    if line != '':
                        self.app_controller.main_window.console_info(line)
                        self.app_controller.submit_command(line)

            print 'looping'

        print 'cleanup'


#----------------------------------------------------------------------------------
# AppController
#----------------------------------------------------------------------------------

class AppController(QtCore.QObject):
    def __init__(self, main_window):
        QtCore.QObject.__init__(self)
        self.renderer_controller = RendererController()
        self.project = None
        self.renderer = None 
        self.render_thread = None
        self.main_window = main_window

        # tile callback methods
        self.tile_callback = TileCallback()
        self.tile_callback.post_render_methods.append(self.update_view)
        self.tile_callback.post_render_methods.append(self.main_window.viewport.update)

        self.tile_callback.post_render_tile_methods.append(self.update_tile)
        self.tile_callback.post_render_tile_methods.append(self.main_window.viewport.update)

        # socket
        self.tcp_socket = QtNetwork.QTcpSocket(self)
        self.block_size = 0
        self.tcp_socket = QtNetwork.QTcpSocket(self)

        # connections
        self.tcp_socket.readyRead.connect(self.socket_read_command)
        self.tcp_socket.connected.connect(self.socket_connected)
        self.tcp_socket.disconnected.connect(self.socket_disconnected)
        self.tcp_socket.error.connect(self.socket_error)
        self.tcp_socket.error.connect(self.socket_connection_error)


    def load_project(self, file_path):
        if os.path.exists(file_path):
            reader = appleseed.ProjectFileReader()
            self.project = reader.read(str(file_path), appleseed_schema_path)

            self.main_window.console_info('Loaded project: {0}'.format(self.project.get_name()))

            frame_params = self.project.get_frame().get_parameters()

            if (not 'pixel_format' in frame_params) or (frame_params['pixel_format'] != 'float'):
                self.main_window.console_warning('Pixel format not supported, converting to float')
                frame_params['pixel_format'] = 'float'
                new_frame = appleseed.Frame('beauty', frame_params)
                self.project.set_frame(new_frame)

            self.main_window.viewport.set_size(self.project.get_frame().image().properties().canvas_width,
                  self.project.get_frame().image().properties().canvas_height)
        else:
            self.main_window.console_error('Path is not valid')


    def start_render(self):
        if self.project is not None:
            self.renderer = appleseed.MasterRenderer(self.project,
                                                     self.project.configurations()['interactive'].get_inherited_parameters(),
                                                     self.renderer_controller,
                                                     self.tile_callback)

            # Render the frame.
            self.render_thread = appleseed.RenderThread(self.renderer)
            self.render_thread.start()      
        else:
            self.main_window.console_error('No project loaded')


    def stop_render(self):
        self.main_window.console_info('Stopping render')
        self.renderer_controller.terminate = True
        if self.render_thread is not None:
            self.render_thread.join()


    def update_tile(self, tx, ty, w, h, tile):
        self.main_window.viewport.update_tile(tx, ty, w, h, tile, self.project.get_frame().image().properties().channel_count)
    

    def update_view(self):
        properties = self.project.get_frame().image().properties()        
        for x in range(properties.tile_count_x):
            for y in range(properties.tile_count_y):
                tile = self.project.get_frame().image().tile(x, y)
                self.update_tile(x, y, properties.tile_width, properties.tile_height, tile)


    def submit_command(self, command):
        # try:
        self.main_window.console_command('Received command: {0}'.format(command))
        exec command
        # except:
        #     self.main_window.console_error('There was an error processing the command')


    def update_color(self, assembly_path, color_name, values, multiplier):
        if self.project is not None:
            assembly = get_assembly(self.project.get_scene().assemblies(), assembly_path)
            if assembly is not None:
                color_container = assembly.colors()
                self.stop_render()
                update_color_entity(assembly.colors(), color_name, values, multiplier)
                self.start_render()
            else:
                self.main_window.console_error('Bad assembly path')
        else: 
           
            self.main_window.console_error('No project loaded')


    def socket_connect(self, port):
        self.tcp_socket.connectToHost('localhost', port)
        self.main_window.console_info('Connecting to: {0}'.format(port))


    def socket_connection_error(self, socket_error):
        if socket_error == QtNetwork.QAbstractSocket.RemoteHostClosedError:
            pass
        elif socket_error == QtNetwork.QAbstractSocket.HostNotFoundError:
            self.main_window.console_error('Host not found. Please check the host name and port settings.')

        elif socket_error == QtNetwork.QAbstractSocket.ConnectionRefusedError:
            self.main_window.console_error('Connection refused by the peer.')

        else:
            self.main_window.console_error('The following error occurred: {0}.'.format(self.tcp_socket.errorString()))

        self.main_window.connection_status.status_disconnected()


    def socket_disconnect(self):
        self.tcp_socket.disconnectFromHost()


    def socket_read_command(self):
        data = self.tcp_socket.read(1024).data()
        self.submit_command(data)


    def socket_connected(self):
        self.main_window.console_success('Connecetd')
        self.main_window.connection_status.status_connected()


    def socket_disconnected(self):
        self.main_window.console_info('Disconnecetd')
        self.main_window.connection_status.status_disconnected()

    def socket_error(self):
        self.main_window.console_error('Socket error')



#----------------------------------------------------------------------------------
# RenderView Widget
#----------------------------------------------------------------------------------

class RenderView(QtGui.QWidget):
    def __init__(self):      
        super(RenderView, self).__init__()
        self.initUI()


    def initUI(self):
        self.width = 300
        self.height = 200
        self.set_size(self.width, self.height)
        self.image = QtGui.QImage(self.width, self.height, QtGui.QImage.Format_RGB32)


    def set_size(self, width, height):
        self.width = width
        self.height = height
        self.image = QtGui.QImage(width, self.height, QtGui.QImage.Format_RGB32)

        self.setMaximumWidth(width)
        self.setMinimumWidth(width)
        self.setMaximumHeight(height)
        self.setMinimumHeight(height)


    def paintEvent(self, e):
        qp = QtGui.QPainter()
        qp.begin(self)
        self.drawWidget(qp)
        qp.end()


    def drawWidget(self, qp):
        qp.drawImage(QtCore.QPoint(0,0), self.image)


    def update_tile(self, tx, ty, w, h, tile, channel_count):

        tile_array = array.array('f', range(tile.get_channel_count() * tile.get_pixel_count()))
        tile.copy_data_to(tile_array)

        # we must calculate the width of the current tile incase it is not a whole tile
        # this may happen if the tile is at the edge of the buffer
        real_width = tile.get_width()
        real_height = tile.get_height()

        tile_image = QtGui.QImage(real_width ,real_height ,QtGui.QImage.Format_RGB32)
        tile_start = QtCore.QPoint(tx * w, ty * h)

        for y in range(real_height):
            for x in range(real_width):

                pixel_start = ((y * real_width) + x) * channel_count

                pixel = QtGui.qRgb(map_float_to_int(tile_array[pixel_start    ]), 
                                   map_float_to_int(tile_array[pixel_start + 1]), 
                                   map_float_to_int(tile_array[pixel_start + 2]))

                tile_image.setPixel(x,y,pixel)

        painter = QtGui.QPainter(self.image)
        painter.drawImage(tile_start, tile_image)


#----------------------------------------------------------------------------------
# ConnectionStatus
#----------------------------------------------------------------------------------

class ConnectionStatus(QtGui.QWidget):
    def __init__(self):      
        super(ConnectionStatus, self).__init__()
        self.m_mutex = QtCore.QMutex()
        self.initUI()

        self.connected = False
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
        elif self.connected:
            brush = QtGui.QBrush(QtGui.QColor(43, 222, 8))
        else:
            brush = QtGui.QBrush(QtGui.QColor(251, 58, 58))

        qp.setBrush(brush)
        qp.drawEllipse(0, 0, self.width, self.height)


    def status_connected(self):
        self.connected = True
        self.update()


    def status_disconnected(self):
        self.connected = False
        self.update()


    def status_receiving_data(self):
        self.sending = True
        self.update()
        QtCore.QTimer.singleShot(10, self.status_stop_sending_data)


#----------------------------------------------------------------------------------
# MainWindow
#----------------------------------------------------------------------------------

class RenderViewWindow(QtGui.QMainWindow):
    def __init__(self):
        super(RenderViewWindow, self).__init__()
        self.initUI()
        self.app_controller = None


    def initUI(self):
        # keep window on top
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)

        self.setGeometry(100, 100, 700, 500)
        self.setWindowTitle('Render View')

        window = QtGui.QWidget()
        self.setCentralWidget(window)

        self.main_layout = QtGui.QVBoxLayout()
        self.main_layout.setContentsMargins(0,0,0,0)
        window.setLayout(self.main_layout)


        # toolbar
        self.toolbar = QtGui.QToolBar(self)
        self.addToolBar(self.toolbar)
        self.open_action = QtGui.QAction('open', self)
        self.toolbar.addAction(self.open_action)

        self.start_interactive_render_action = QtGui.QAction('start interactive render', self)
        self.toolbar.addAction(self.start_interactive_render_action)

        self.stop_render_action = QtGui.QAction('stop render', self)
        self.toolbar.addAction(self.stop_render_action)

        # status bar
        self.status_bar = self.statusBar()
        self.connection_status = ConnectionStatus()
        self.status_bar.addPermanentWidget(self.connection_status)

        # splitter
        self.console_splitter = QtGui.QSplitter(QtCore.Qt.Vertical)
        self.main_layout.addWidget(self.console_splitter)

        # viewport
        self.viewport_widget = QtGui.QWidget()
        self.viewport_layout = QtGui.QHBoxLayout()
        self.viewport_layout.setContentsMargins(0,0,0,0)
        self.viewport_scroll_area = QtGui.QScrollArea()
        self.viewport_scroll_area.setObjectName('viewport_scroll_area')
        self.viewport_scroll_area.setWidgetResizable(True)
        self.viewport_scroll_area_widget = QtGui.QWidget()
        self.viewport_scroll_area_layout = QtGui.QHBoxLayout()
        self.viewport = RenderView()

        self.console_splitter.addWidget(self.viewport_widget)
        self.viewport_widget.setLayout(self.viewport_layout)
        self.viewport_layout.addWidget(self.viewport_scroll_area)
        self.viewport_scroll_area.setWidget(self.viewport_scroll_area_widget)
        self.viewport_scroll_area_widget.setLayout(self.viewport_scroll_area_layout)
        self.viewport_scroll_area_layout.addStretch()
        self.viewport_scroll_area_layout.addWidget(self.viewport)
        self.viewport_scroll_area_layout.addStretch()

        # console
        self.console_widget = QtGui.QWidget()
        self.console_layout = QtGui.QVBoxLayout()
        self.console_widget.setLayout(self.console_layout)
        self.console_in = QtGui.QLineEdit()
        self.console_out = QtGui.QTextEdit()
        self.console_layout.addWidget(self.console_in)
        self.console_layout.addWidget(self.console_out)
        self.console_splitter.addWidget(self.console_widget)

        self.connection_layout = QtGui.QHBoxLayout()
        self.console_layout.addLayout(self.connection_layout)
        self.connection_layout.addStretch()
        self.connection_layout.addWidget(QtGui.QLabel('Port'))
        self.port_number = QtGui.QLineEdit('10210')
        self.port_number.setInputMask('99999')
        self.port_number.setMaximumWidth(50)
        self.connection_layout.addWidget(self.port_number)
        self.connect_button = QtGui.QPushButton('Connect')
        self.connection_layout.addWidget(self.connect_button)
        self.disconnect_button = QtGui.QPushButton('Disconnect')
        self.connection_layout.addWidget(self.disconnect_button)

        # hide console
        self.console_splitter.setSizes([400, 0])

        # connections
        self.open_action.triggered.connect(self.load_project)
        self.start_interactive_render_action.triggered.connect(self.interactive_render)
        self.stop_render_action.triggered.connect(self.stop_render)
        self.console_in.returnPressed.connect(self.console_submit)
        self.connect_button.pressed.connect(self.socket_connect)
        self.disconnect_button.pressed.connect(self.socket_disconnect)


    def load_project(self):
        file_name = QtGui.QFileDialog.getOpenFileName(self, caption="Open .appleseed file", filter="*.appleseed")

        if file_name[0] != '':
            self.app_controller.load_project(file_name[0])


    def interactive_render(self):
        self.app_controller.start_render()


    def stop_render(self):
        if self.app_controller is not None:
            self.app_controller.stop_render()


    def closeEvent(self, event):
        self.stop_render()
        self.socket_disconnect()
        event.accept()


    def console_submit(self):
        self.app_controller.submit_command(self.console_in.text())


    def socket_connect(self):
        self.app_controller.socket_connect(int(self.port_number.text()))


    def socket_disconnect(self):
        self.app_controller.socket_disconnect()
        self.connection_status.status_disconnected()

    
    def console_info(self, msg):
        self.console_out.append('<font color=#f9f9f9>{0}</font>'.format(msg))


    def console_success(self, msg):
        self.console_out.append('<font color=#0fce52>{0}</font>'.format(msg))


    def console_warning(self, msg):
        self.console_out.append('<font color=#ffec1c>{0}</font>'.format(msg))


    def console_error(self, msg):
        self.console_out.append('<font color=#ff5757>{0}</font>'.format(msg))


    def console_command(self, msg):
        self.console_out.append('<font color=#00c6ff>{0}</font>'.format(msg))


#----------------------------------------------------------------------------------
# Main entry point
#----------------------------------------------------------------------------------

def main():

    # log_target = appleseed.ConsoleLogTarget(sys.stderr)
    # appleseed.global_logger().add_target(log_target)

    app = QtGui.QApplication(sys.argv)
    set_style(app)

    main_window = RenderViewWindow()
    app_controller = AppController(main_window)
    main_window.app_controller = app_controller
    main_window.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()

