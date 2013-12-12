
#
# Copyright (c) 2012-2013 Jonathan Topf
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

import sys
import maya.OpenMaya as OpenMaya
import maya.OpenMayaMPx as OpenMayaMPx
import maya.OpenMayaRender as OpenMayaRender
import maya.OpenMayaUI as OpenMayaUI
import maya.cmds as cmds
import inspect
import os
import os.path

ROOT_DIRECTORY = os.path.split((os.path.dirname(inspect.getfile(inspect.currentframe()))))[0]
sys.path.append(os.path.join(ROOT_DIRECTORY, 'scripts'))
sys.path.append(os.path.join(ROOT_DIRECTORY, 'graphics'))
sys.path.append(os.path.join(ROOT_DIRECTORY, 'nodes'))

import ms_menu

#--------------------------------------------------------------------------------------------------
# mayaseed plugin.
#--------------------------------------------------------------------------------------------------


def initializePlugin(obj):
    try:
        import ms_appleseed_material
        ms_appleseed_material.initializePlugin(obj)

        import ms_appleseed_shading_node
        ms_appleseed_shading_node.initializePlugin(obj)
        
        import ms_environment_node
        ms_environment_node.initializePlugin(obj)
        
        import ms_physical_environment_node
        ms_physical_environment_node.initializePlugin(obj)

        import ms_render_settings
        ms_render_settings.initializePlugin(obj)
    
    except: 
        print 'Failed to register mayaseed plug-in'

    ms_menu.createMenu()
    ms_menu.buildMenu()


def uninitializePlugin(obj):
    try:
        import ms_appleseed_material
        ms_appleseed_material.uninitializePlugin(obj)

        import ms_appleseed_shading_node
        ms_appleseed_shading_node.uninitializePlugin(obj)
        
        import ms_environment_node
        ms_environment_node.uninitializePlugin(obj)
        
        import ms_physical_environment_node
        ms_physical_environment_node.uninitializePlugin(obj)

        import ms_render_settings
        ms_render_settings.uninitializePlugin(obj)

    except: 
        print 'Failed to deregister mayaseed plug-in'

    ms_menu.deleteMenu()
