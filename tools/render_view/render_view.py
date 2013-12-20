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

sys.path.append('/projects/appleseed/sandbox/bin/Ship')

scene_path = '/Users/jonathantopf/Desktop/test.appleseed'
appleseed_schema_path = '/projects/appleseed/sandbox/schemas/Project.xsd'

import appleseed


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
        print 'start render'

    # This method is called after rendering has succeeded.
    def on_rendering_success(self):
        print 'success'

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
# Controller
#----------------------------------------------------------------------------------

class AppController():
    def __init__(self, main_window):
        self.renderer_controller = RendererController()
        self.project = None
        self.renderer = None 
        self.render_thread = None
        self.main_window = main_window

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

    def update_tile(self, tx, ty, w, h, tile):
        self.main_window.viewport.update_tile(tx, ty, w, h, tile, self.project.get_frame().image().properties().channel_count)
    
    def update_view(self):

        properties = self.project.get_frame().image().properties()        
        for x in range(properties.tile_count_x):
            for y in range(properties.tile_count_y):
                tile = self.project.get_frame().image().tile(x, y)
                self.update_tile(x, y, properties.tile_width, properties.tile_height, tile)



#----------------------------------------------------------------------------------
# ViewpotWidget
#----------------------------------------------------------------------------------

class ViewportWidget(QtGui.QWidget):


    def __init__(self):      
        super(ViewportWidget, self).__init__()
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

        
def map_float_to_int(float):
    return min(255, int(float * 256))
    # return float


#----------------------------------------------------------------------------------
# MainWindow
#----------------------------------------------------------------------------------

class RenderSequenceWindow(QtGui.QWidget):
    def __init__(self):
        super(RenderSequenceWindow, self).__init__()
        self.initUI()
        self.app_controller = None

    def initUI(self):

        self.setGeometry(100, 100, 700, 500)
        self.setWindowTitle('Render View')

        main_layout = QtGui.QVBoxLayout()
        self.setLayout(main_layout)

        # toolbar 
        toolbar = QtGui.QWidget()
        toolbar.setFixedHeight(40)
        toolbar_layout = QtGui.QHBoxLayout(toolbar)
        main_layout.addWidget(toolbar)

        interactive_render_button = QtGui.QPushButton('start interactive render', self)
        toolbar_layout.addWidget(interactive_render_button)

        stop_render_button = QtGui.QPushButton('stop render', self)
        toolbar_layout.addWidget(stop_render_button)

        toolbar_layout.addStretch()

        load_button = QtGui.QPushButton('Load', self)
        toolbar_layout.addWidget(load_button)

        test_button = QtGui.QPushButton('Test', self)
        toolbar_layout.addWidget(test_button)

        # viewport 
        main_layout.addStretch()

        viewport_layout = QtGui.QHBoxLayout()
        main_layout.addLayout(viewport_layout)

        self.viewport = ViewportWidget()
        viewport_layout.addWidget(self.viewport)
        main_layout.addStretch()

        # connections
        load_button.clicked.connect(self.load_project)
        interactive_render_button.clicked.connect(self.interactive_render)
        stop_render_button.clicked.connect(self.stop_render)
        test_button.clicked.connect(self.test)

        self.show()

    def load_project(self):
        file_name = QtGui.QFileDialog.getOpenFileName(self, caption="Open .appleseed file", filter="*.appleseed")

        if file_name[0] != '':
            self.app_controller.load_project(file_name[0])

    def interactive_render(self):
        self.app_controller.start_render()

    def test(self):
        print 'test'
        if self.app_controller is not None:
            foo = self.app_controller.project.get_scene().assemblies()['assembly'].colors().get_by_name('light_radiance')

            self.app_controller.project.get_scene().assemblies()['assembly'].colors().remove(foo)

    def stop_render(self):
        self.app_controller.stop_render()

    def closeEvent(self, event):
        self.stop_render()
        event.accept()


#----------------------------------------------------------------------------------
# Main entry point
#----------------------------------------------------------------------------------

def main():

    # log_target = appleseed.ConsoleLogTarget(sys.stderr)
    # appleseed.global_logger().add_target(log_target)

    app = QtGui.QApplication(sys.argv)

    stylesheet = open('style.qss', 'r')
    style = stylesheet.read()

    style_replacement_patterns = [
        ('TEXT',               '#ccc'),
        ('BACKGROUND_COLOR',   '#222'),
        ('BACKGROUND_HILIGHT', '#333'),
        ('BACKGROUND_HOVER',   '#444'),
        ('BACKGROUND_PRESSED', '#aac4ce')
    ]

    for pattern in style_replacement_patterns:
        style = style.replace(pattern[0], pattern[1])

    app.setStyleSheet(style)

    main_window = RenderSequenceWindow()
    app_controller = AppController(main_window)
    main_window.app_controller = app_controller

    sys.exit(app.exec_())

if __name__ == '__main__':
    main()





