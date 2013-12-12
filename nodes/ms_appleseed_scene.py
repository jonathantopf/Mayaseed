
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

#--------------------------------------------------------------------------------------------------
# ms_appleseed_scene node.
#--------------------------------------------------------------------------------------------------


ms_appleseed_scene_nodeTypeName = "ms_appleseed_scene"

ms_appleseed_scene_nodeTypeId = OpenMaya.MTypeId(0x00339)

glRenderer = OpenMayaRender.MHardwareRenderer.theRenderer()
glFT = glRenderer.glFunctionTable()


class ms_appleseed_scene(OpenMayaMPx.MPxLocatorNode):
        def __init__(self):
            OpenMayaMPx.MPxLocatorNode.__init__(self)


        def draw(self, view, path, style, status):


            # get input values
            this_node = self.thisMObject()

            x_min_plug = OpenMaya.MPlug(this_node, ms_appleseed_scene.x_min)
            x_min = x_min_plug.asFloat()
            x_max_plug = OpenMaya.MPlug(this_node, ms_appleseed_scene.x_max)
            x_max = x_max_plug.asFloat()

            y_min_plug = OpenMaya.MPlug(this_node, ms_appleseed_scene.y_min)
            y_min = y_min_plug.asFloat()
            y_max_plug = OpenMaya.MPlug(this_node, ms_appleseed_scene.y_max)
            y_max = y_max_plug.asFloat()

            z_min_plug = OpenMaya.MPlug(this_node, ms_appleseed_scene.z_min)
            z_min = z_min_plug.asFloat()
            z_max_plug = OpenMaya.MPlug(this_node, ms_appleseed_scene.z_max)
            z_max = z_max_plug.asFloat()


            # draw bounding box
            view.beginGL()

            glFT.glEnable(OpenMayaRender.MGL_BLEND)
            
            # bounding box
            glFT.glBegin(OpenMayaRender.MGL_LINE_STRIP) 
            glFT.glVertex3f(x_min, y_min, z_min)
            glFT.glVertex3f(x_max, y_min, z_min)
            glFT.glVertex3f(x_max, y_max, z_min)
            glFT.glVertex3f(x_min, y_max, z_min)
            glFT.glVertex3f(x_min, y_min, z_min)
            glFT.glEnd()

            glFT.glBegin(OpenMayaRender.MGL_LINE_STRIP) 
            glFT.glVertex3f(x_min, y_min, z_max)
            glFT.glVertex3f(x_max, y_min, z_max)
            glFT.glVertex3f(x_max, y_max, z_max)
            glFT.glVertex3f(x_min, y_max, z_max)
            glFT.glVertex3f(x_min, y_min, z_max)
            glFT.glEnd()
            
            glFT.glBegin(OpenMayaRender.MGL_LINE_STRIP) 
            glFT.glVertex3f(x_min, y_min, z_min)
            glFT.glVertex3f(x_min, y_min, z_max)
            glFT.glEnd()
            
            glFT.glBegin(OpenMayaRender.MGL_LINE_STRIP) 
            glFT.glVertex3f(x_max, y_min, z_min)
            glFT.glVertex3f(x_max, y_min, z_max)
            glFT.glEnd()
            
            glFT.glBegin(OpenMayaRender.MGL_LINE_STRIP) 
            glFT.glVertex3f(x_max, y_max, z_min)
            glFT.glVertex3f(x_max, y_max, z_max)
            glFT.glEnd()
            
            glFT.glBegin(OpenMayaRender.MGL_LINE_STRIP) 
            glFT.glVertex3f(x_min, y_max, z_min)
            glFT.glVertex3f(x_min, y_max, z_max)
            glFT.glEnd()

            glFT.glDisable(OpenMayaRender.MGL_BLEND)

            view.endGL()

def ms_appleseed_scene_nodeCreator():
    return OpenMayaMPx.asMPxPtr(ms_appleseed_scene())
 
def ms_appleseed_scene_nodeInitializer():

    # appleseed_file
    appleseed_file_string = OpenMaya.MFnStringData().create("")
    appleseed_file_Attr = OpenMaya.MFnTypedAttribute()
    ms_appleseed_scene.appleseed_file = appleseed_file_Attr.create("appleseed_file", "as_scene", OpenMaya.MFnData.kString, appleseed_file_string)
    ms_appleseed_scene.addAttribute(ms_appleseed_scene.appleseed_file)

    # bounding box
    x_min_AttrFloat = OpenMaya.MFnNumericAttribute()
    ms_appleseed_scene.x_min = x_min_AttrFloat.create("x_min", "x_min", OpenMaya.MFnNumericData.kFloat, -1)
    x_min_AttrFloat.setHidden(False)
    x_min_AttrFloat.setKeyable(False)
    ms_appleseed_scene.addAttribute(ms_appleseed_scene.x_min)

    x_max_AttrFloat = OpenMaya.MFnNumericAttribute()
    ms_appleseed_scene.x_max = x_max_AttrFloat.create("x_max", "x_max", OpenMaya.MFnNumericData.kFloat, 1)
    x_max_AttrFloat.setHidden(False)
    x_max_AttrFloat.setKeyable(False)
    ms_appleseed_scene.addAttribute(ms_appleseed_scene.x_max)

    y_min_AttrFloat = OpenMaya.MFnNumericAttribute()
    ms_appleseed_scene.y_min = y_min_AttrFloat.create("y_min", "y_min", OpenMaya.MFnNumericData.kFloat, -1)
    y_min_AttrFloat.setHidden(False)
    y_min_AttrFloat.setKeyable(False)
    ms_appleseed_scene.addAttribute(ms_appleseed_scene.y_min)

    y_max_AttrFloat = OpenMaya.MFnNumericAttribute()
    ms_appleseed_scene.y_max = y_max_AttrFloat.create("y_max", "y_max", OpenMaya.MFnNumericData.kFloat, 1)
    y_max_AttrFloat.setHidden(False)
    y_max_AttrFloat.setKeyable(False)
    ms_appleseed_scene.addAttribute(ms_appleseed_scene.y_max)

    z_min_AttrFloat = OpenMaya.MFnNumericAttribute()
    ms_appleseed_scene.z_min = z_min_AttrFloat.create("z_min", "z_min", OpenMaya.MFnNumericData.kFloat, -1)
    z_min_AttrFloat.setHidden(False)
    z_min_AttrFloat.setKeyable(False)
    ms_appleseed_scene.addAttribute(ms_appleseed_scene.z_min)

    z_max_AttrFloat = OpenMaya.MFnNumericAttribute()
    ms_appleseed_scene.z_max = z_max_AttrFloat.create("z_max", "z_max", OpenMaya.MFnNumericData.kFloat, 1)
    z_max_AttrFloat.setHidden(False)
    z_max_AttrFloat.setKeyable(False)
    ms_appleseed_scene.addAttribute(ms_appleseed_scene.z_max)


#--------------------------------------------------------------------------------------------------
# node initialization .
#--------------------------------------------------------------------------------------------------

def initializePlugin(obj):
    plugin = OpenMayaMPx.MFnPlugin(obj)

    try:
        plugin.registerNode(ms_appleseed_scene_nodeTypeName, 
        ms_appleseed_scene_nodeTypeId, 
        ms_appleseed_scene_nodeCreator, 
        ms_appleseed_scene_nodeInitializer, OpenMayaMPx.MPxNode.kLocatorNode)
    except:
        sys.stderr.write("Failed to register node: %s" % ms_appleseed_scene_nodeTypeName)

def uninitializePlugin(obj):
    plugin = OpenMayaMPx.MFnPlugin(obj)

    try:
        plugin.deregisterNode(ms_appleseed_scene_nodeTypeId)
    except:
        sys.stderr.write("Failed to deregister node: %s" % ms_appleseed_scene_nodeTypeName)
