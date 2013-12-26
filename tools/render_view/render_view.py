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
from PySide import QtGui, QtCore
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
    return min(255, int(float * 256))


#----------------------------------------------------------------------------------
# Set style function
#----------------------------------------------------------------------------------

def set_style(app):
    # set base style
    app.setStyle('cleanlooks')
    
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
    palette.setBrush(QtGui.QPalette.Light, light)
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
# Appleseed scene edition functions
#----------------------------------------------------------------------------------

def update_color_entity(color_container, color_name, values, multiplier):

    color = color_container.get_by_name(color_name)

    params = color.get_parameters()
    params['multiplier'] = multiplier

    color_container.remove(color)

    color_container.insert(appleseed.ColorEntity(color_name, params, values))


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
        print 'starting render'


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
# AppController
#----------------------------------------------------------------------------------

class AppController():
    def __init__(self, main_window):
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


    def load_project(self, file_path):
        if os.path.exists(file_path):
            reader = appleseed.ProjectFileReader()
            self.project = reader.read(str(file_path), appleseed_schema_path)

            print 'Loaded project:', self.project.get_name()

            self.main_window.viewport.set_size(self.project.get_frame().image().properties().canvas_width,
                  self.project.get_frame().image().properties().canvas_height)
        else:
            print 'Path is not valid'


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
            print 'No project loaded'


    def stop_render(self):
        print 'Stopping render'
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
# Initialize UI
#----------------------------------------------------------------------------------

def init_ui(window, console):

    gui = {}
    # get UI objects
    # toolbar
    giu['tool_bar']            = window.findChildren(QtGui.QWidget, 'tool_bar')[0]
    giu['action_open_project'] = window.findChildren(QtGui.QAction, 'action_open_project')[0]
    giu['action_start_render'] = window.findChildren(QtGui.QAction, 'action_start_render')[0]
    giu['action_stop_render']  = window.findChildren(QtGui.QAction, 'action_stop_render')[0]
    giu['action_quit']         = window.findChildren(QtGui.QAction, 'action_quit')[0]
    giu['action_test_button']  = window.findChildren(QtGui.QAction, 'action_test')[0]
    # render view
    giu['render_view_layout']  = window.findChildren(QtGui.QVBoxLayout, 'render_view_layout')[0]
    # console
    giu['console_dock']        = window.findChildren(QtGui.QDockWidget, 'console_dock')[0]
    giu['console_splitter']    = console.findChildren(QtGui.QSplitter, 'console_splitter')[0]
    giu['console_in']          = console_splitter.findChildren(QtGui.QPlainTextEdit, 'console_in')[0]
    giu['console_out']         = console_splitter.findChildren(QtGui.QTextEdit, 'console_out')[0]

    # construct render_view
    render_view_layout.addStretch()
    giu['render_view'] = RenderView()
    render_view_layout.addWidget(giu['render_view'])
    render_view_layout.addStretch()

    return gui

#----------------------------------------------------------------------------------
# MainWindow
#----------------------------------------------------------------------------------

class RenderSequenceWindow(QtGui.QMainWindow):
    def __init__(self):
        super(RenderSequenceWindow, self).__init__()
        self.initUI()
        self.app_controller = None


    def initUI(self):

        self.setGeometry(100, 100, 700, 500)
        self.setWindowTitle('Render View')


        window = QtGui.QWidget()
        self.setCentralWidget(window)

        self.main_layout = QtGui.QVBoxLayout()
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

        self.test_action = QtGui.QAction('test', self)
        self.toolbar.addAction(self.test_action)

        # splitter
        self.console_splitter = QtGui.QSplitter(QtCore.Qt.Vertical)
        self.main_layout.addWidget(self.console_splitter)

        # viewport
        self.viewport_widget = QtGui.QWidget()
        self.viewport_layout = QtGui.QHBoxLayout()
        self.viewport_scroll_area = QtGui.QScrollArea()
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

        # connections
        self.open_action.triggered.connect(self.load_project)
        self.start_interactive_render_action.triggered.connect(self.interactive_render)
        self.stop_render_action.triggered.connect(self.stop_render)
        self.test_action.triggered.connect(self.test)
        self.console_in.returnPressed.connect(self.console_submit)


    def load_project(self):
        file_name = QtGui.QFileDialog.getOpenFileName(self, caption="Open .appleseed file", filter="*.appleseed")

        if file_name[0] != '':
            self.app_controller.load_project(file_name[0])


    def interactive_render(self):
        self.app_controller.start_render()


    def test(self):
        print 'Test'
        if self.app_controller is not None:
            color_container = self.app_controller.project.get_scene().assemblies()['assembly'].colors()
            self.stop_render()
            update_color_entity(color_container, 'light_radiance', [1,0,0], 30)
            self.interactive_render()


    def stop_render(self):
        if self.app_controller is not None:
            self.app_controller.stop_render()


    def closeEvent(self, event):
        self.stop_render()
        event.accept()


    def console_submit(self):
        self.app_controller.submit_command(self.console_in.text())

    
    def console_info(self, msg):
        self.console_out.append('<font color=#f9f9f9>{0}</font>'.format(msg))


    def console_warning(self, msg):
        self.console_out.append('<font color=#ffec1c>{0}</font>'.format(msg))


    def console_error(self, msg):
        self.console_out.append('<font color=#ff5757>{0}</font>'.format(msg))


#----------------------------------------------------------------------------------
# Main entry point
#----------------------------------------------------------------------------------

def main():

    # log_target = appleseed.ConsoleLogTarget(sys.stderr)
    # appleseed.global_logger().add_target(log_target)

    app = QtGui.QApplication(sys.argv)
    set_style(app)

    main_window = RenderSequenceWindow()
    app_controller = AppController(main_window)
    main_window.app_controller = app_controller
    main_window.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()

