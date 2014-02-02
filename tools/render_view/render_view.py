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
import argparse
import time
import copy


# sys.path.append('/projects/appleseed/sandbox/bin/Ship')

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
    mid        = QtGui.QColor(50 ,50, 50 )
    mid_light  = QtGui.QColor(55 ,55 ,55 )
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
    stylesheet = open(os.path.join(current_script_path, 'style.qss'), 'r')
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
        self.render_begin_methods = []
        self.frame_end_methods = []
        self.progress_methods = []


    def __signal_handler(self, signal, frame):
        print "Ctrl+C, aborting."
        self.__abort = True


    # This method is called before rendering begins.
    def on_rendering_begin(self):
        for method in self.render_begin_methods:
            method()


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
        for method in self.frame_end_methods:
            method()


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
# AppController
#----------------------------------------------------------------------------------

class AppController(QtCore.QObject):
    def __init__(self,  main_window, app):
        QtCore.QObject.__init__(self)
        self.renderer_controller = RendererController()
        self.project = None
        self.renderer = None 
        self.main_window = main_window
        self.app = app
        self.tcp_port = 10210
        self.read_rate = 4096
        self.render_start_time = None

        # tile callback methods
        self.tile_callback = TileCallback()
        self.tile_callback.post_render_methods.append(self.update_view)
        self.tile_callback.post_render_methods.append(self.main_window.viewport.update)

        self.tile_callback.post_render_tile_methods.append(self.update_tile)
        self.tile_callback.post_render_tile_methods.append(self.main_window.viewport.update)

        # progress callback methods
        self.renderer_controller.progress_methods.append(self.on_render_progress)
        self.renderer_controller.progress_methods.append(self.app.processEvents)

        # rendering begin callback methods
        self.renderer_controller.render_begin_methods.append(self.on_render_start)

        # frame end methods
        self.renderer_controller.frame_end_methods.append(self.on_render_stop)

        # RenderView widget callbacks
        self.main_window.viewport.callbacks.append(self.app.processEvents)
        self.main_window.viewport.callbacks.append(self.on_render_progress)

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
            self.stop_render()
            reader = appleseed.ProjectFileReader()
            self.project = reader.read(str(file_path), appleseed_schema_path)

            self.main_window.console_info('Loaded project: {0}'.format(self.project.get_name()))

            frame = self.project.get_frame()

            frame_params = frame.get_parameters()

            if (not 'pixel_format' in frame_params) or (frame_params['pixel_format'] != 'float'):
                self.main_window.console_warning('Pixel format not supported, converting to float')
                frame_params['pixel_format'] = 'float'
                new_frame = appleseed.Frame('beauty', frame_params)
                self.project.set_frame(new_frame)
                frame = self.project.get_frame()



            # initialize ui
            image_properties = frame.image().properties()            
            self.main_window.viewport.set_size(image_properties.canvas_width, image_properties.canvas_height)

            render_layer_combo_list = []

            aov_images = frame.aov_images()

            for i in range(aov_images.size()):
                render_layer_combo_list.append(aov_images.get_name(i))

            self.main_window.populate_render_layer_combo(render_layer_combo_list)


        else:
            self.main_window.console_error('Path is not valid')


    def start_render(self):
        if self.project is not None:
            self.main_window.console_info('Starting render')
            self.renderer = appleseed.MasterRenderer(self.project,
                                                     self.project.configurations()['interactive'].get_inherited_parameters(),
                                                     self.renderer_controller,
                                                     self.tile_callback)

            # Render the frame.
            self.renderer.render()  
        else:
            self.main_window.console_error('No project loaded')


    def stop_render(self):
        if self.renderer is not None:
            self.main_window.console_info('Stopping render')
            self.renderer_controller.terminate = True
            self.renderer = None


    def update_tile(self, tx, ty, w, h, tile):
        frame = self.project.get_frame()
        self.main_window.viewport.update_tile(tx, ty, w, h, frame, tile, frame.image().properties().channel_count)

    def update_view(self):
        properties = self.project.get_frame().image().properties()        
        for x in range(properties.tile_count_x):
            for y in range(properties.tile_count_y):
                tile = self.project.get_frame().image().tile(x, y)
                self.update_tile(x, y, properties.tile_width, properties.tile_height, tile)


    def submit_command(self, command):
        exec command


    def update_color(self, assembly_path, color_name, values, multiplier):
        if self.project is not None:
            assembly = get_assembly(self.project.get_scene().assemblies(), assembly_path)
            if assembly is not None:
                color_container = assembly.colors()
                self.stop_render()
                update_color_entity(assembly.colors(), color_name, values, multiplier)
                self.start_render()
            else:
                self.main_window.console_error('Bad assembly path: {0}'.format(assembly_path))
        else: 
            self.main_window.console_error('No project loaded')


    def socket_connect(self):
        self.tcp_socket.connectToHost('localhost', self.tcp_port)
        self.main_window.console_info('Connecting to: {0}'.format(self.read_rate))


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
        data = self.tcp_socket.read(4098).data()
        if data:
            if not data[-1] == '\n':
                self.main_window.console_error('Received incomplete command: try increasing the tcp read rate')
            else:
                self.main_window.console_command('Received_data --------------------')
                for line in data.split('\n'):
                    if line != '':
                        self.main_window.console_command(line)
                        self.submit_command(line)


    def socket_connected(self):
        self.main_window.console_success('Connected')
        self.main_window.connection_status.status_connected()


    def socket_disconnected(self):
        self.main_window.console_info('Disconnected')
        self.main_window.connection_status.status_disconnected()

    
    def socket_error(self):
        self.main_window.console_error('Socket error')


    def on_render_start(self):
        self.render_start_time = time.time()


    def on_render_progress(self):  
        self.main_window.status_bar.showMessage('Rendering for {0:.2f} seconds'.format(time.time() - self.render_start_time))


    def on_render_stop(self):
        self.main_window.status_bar.showMessage('Rendering finised in {0:.2f} seconds'.format(time.time() - self.render_start_time))


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
        self.callbacks = []


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


    def update_tile(self, tx, ty, w, h, frame, tile, channel_count):

        # create copy of tile to color transformations dont get applied twice or not at all
        tile_copy = copy.copy(tile)

        frame.transform_tile_to_output_color_space(tile_copy) # transform tile color space

        tile_array = array.array('f', range(tile_copy.get_channel_count() * tile_copy.get_pixel_count()))
        tile_copy.copy_data_to(tile_array)

        # we must calculate the width of the current tile incase it is not a whole tile
        # this may happen if the tile is at the edge of the buffer
        real_width = tile_copy.get_width()
        real_height = tile_copy.get_height()

        tile_image = QtGui.QImage(real_width ,real_height ,QtGui.QImage.Format_RGB32)
        tile_start = QtCore.QPoint(tx * w, ty * h)

        for y in range(real_height):
            for method in self.callbacks:
                method()
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
        self.open_action.setShortcut('Ctrl+O')
        self.toolbar.addAction(self.open_action)

        self.start_interactive_render_action = QtGui.QAction('start interactive render', self)
        self.start_interactive_render_action.setShortcut('F5')
        self.toolbar.addAction(self.start_interactive_render_action)

        self.stop_render_action = QtGui.QAction('stop render', self)
        self.stop_render_action.setShortcut('Shift+F5')
        self.toolbar.addAction(self.stop_render_action)

        self.toggle_keep_window_on_top_action = QtGui.QAction('toggle keep window on top', self)
        self.toolbar.addAction(self.toggle_keep_window_on_top_action)
        self.window_is_on_top = False

        self.toggle_console_action = QtGui.QAction('toggle console', self)
        self.toggle_console_action.setShortcut('Ctrl+Return')
        self.toolbar.addAction(self.toggle_console_action)

        self.render_layer_combo_box = QtGui.QComboBox()
        self.toolbar.addWidget(self.render_layer_combo_box)

        self.quit_action = QtGui.QAction('quit', self)
        self.quit_action.setShortcut('Ctrl+q')

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
        self.console_out.setLineWrapMode(QtGui.QTextEdit.NoWrap)
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
        self.connection_layout.addWidget(QtGui.QLabel('Read rate'))
        self.read_rate = QtGui.QLineEdit('4096')
        self.read_rate.setInputMask('00000')
        self.read_rate.setMaximumWidth(50)
        self.connection_layout.addWidget(self.read_rate)
        self.connect_button = QtGui.QPushButton('Connect')
        self.connection_layout.addWidget(self.connect_button)
        self.disconnect_button = QtGui.QPushButton('Disconnect')
        self.connection_layout.addWidget(self.disconnect_button)

        # hide console
        self.console_splitter.setSizes([400, 0])

        # connections
        # toolbar
        self.open_action.triggered.connect(self.load_project)
        self.start_interactive_render_action.triggered.connect(self.interactive_render)
        self.stop_render_action.triggered.connect(self.stop_render)
        self.toggle_keep_window_on_top_action.triggered.connect(self.toggle_keep_window_on_top)
        self.toggle_console_action.triggered.connect(self.toggle_console)
        self.quit_action.triggered.connect(self.toggle_console)

        # others
        self.console_in.returnPressed.connect(self.console_submit)
        self.connect_button.pressed.connect(self.socket_connect)
        self.port_number.returnPressed.connect(self.socket_connect)
        self.port_number.editingFinished.connect(self.port_updated)
        self.read_rate.returnPressed.connect(self.socket_connect)
        self.read_rate.editingFinished.connect(self.read_rate_updated)
        self.disconnect_button.pressed.connect(self.quit)


    def load_project(self):
        dialog = QtGui.QFileDialog(self)
        dialog.setFileMode(QtGui.QFileDialog.AnyFile)
        dialog.setNameFilter("*.appleseed")
        file_name = dialog.getOpenFileName()

        if file_name[0] != '':
            self.app_controller.load_project(file_name[0])


    def interactive_render(self):
        self.app_controller.start_render()


    def stop_render(self):
        if self.app_controller is not None:
            self.app_controller.stop_render()


    def closeEvent(self, event):
        self.quit()
        event.accept()


    def quit(self):
        self.stop_render()
        self.socket_disconnect()
        QtCore.QCoreApplication.instance().quit


    def toggle_keep_window_on_top(self):
        if self.window_is_on_top:
            self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowStaysOnTopHint)
            self.window_is_on_top  = False
        else:
            self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
            self.window_is_on_top = True

        self.show()


    def toggle_console(self):
        if self.console_splitter.sizes()[1] == 0:
            self.console_splitter.setSizes([400, 50])
            self.console_in.setFocus(QtCore.Qt.OtherFocusReason)
        else:
            self.console_splitter.setSizes([400, 00])


    def populate_render_layer_combo(self, items):
        self.render_layer_combo_box.clear()
        for item in items:
            self.render_layer_combo_box.addItem(item)


    def console_submit(self):
        self.app_controller.submit_command(self.console_in.text())


    def socket_connect(self):
        self.app_controller.socket_connect()


    def port_updated(self):
        self.app_controller.tcp_port = int(self.port_number.text())
        print 'port', self.app_controller.tcp_port

    def read_rate_updated(self):

        self.app_controller.read_rate = int(self.read_rate.text())
        print 'read rate', self.app_controller.read_rate

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

    parser = argparse.ArgumentParser(description='render_view.py is a render er and viewer for .appleseed scenes')
    parser.add_argument('file', help=".appleseed file to open", nargs='?')
    parser.add_argument('-s', '--start', help='Start render on startup', action='store_true')
    parser.add_argument('-p', '--port', metavar='port number', help='Port to open on startup', type=int)
    parser.add_argument('-r', '--read-rate', metavar='read rate', help='Bytes per line to read from tcp port', type=int)
    parser.add_argument('-oc', '--openconnection', help='Open tcp connection on startup', action='store_true')
    args = parser.parse_args()

    # log_target = appleseed.ConsoleLogTarget(sys.stderr)
    # appleseed.global_logger().add_target(log_target)

    app = QtGui.QApplication(sys.argv)
    set_style(app)

    main_window = RenderViewWindow()
    app_controller = AppController(main_window, app)

    if args.port is not None:
        app_controller.tcp_port = args.port
        main_window.port_number.setText(str(args.port))

    if args.read_rate is not None:
        app_controller.read_rate = args.read_rate
        main_window.read_rate.setText(str(args.read_rate))

    main_window.app_controller = app_controller
    main_window.showMaximized()
    main_window.raise_()

    if args.openconnection:
        app_controller.socket_connect()

    if args.file is not None:
        app_controller.load_project(args.file)

    if args.start:
        app_controller.start_render()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()

