
#
# Copyright (c) 2012-2014 Jonathan Topf
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

import maya.cmds as cmds
import maya.mel as mel
import ms_commands
import ms_export

shelf_name = 'mayaseed'
main_shelf_parent = 'MayaWindow|toolBar2|MainShelfLayout|formLayout14|ShelfLayout'
button_list = []

#--------------------------------------------------------------------------------------------------
# Buttons.
#--------------------------------------------------------------------------------------------------

# reload modules

button_list.append(['Reload mayaseed modues', 'icon_reload_modules.png', 'python', """
import ms_shelf
ms_shelf.reload_modules()
"""])

# export.

button_list.append(['Export', 'icon_export.png', 'python', """
import ms_shelf
ms_shelf.export()
"""])

# export without dependencies.

button_list.append(['Export without dependencies', 'icon_export_no_deps.png', 'python', """
import ms_shelf
ms_shelf.export_no_deps_button()
"""])

# re-export

button_list.append(['Re-export', 'icon_re_export.png', 'python', """
import ms_shelf
ms_shelf.re_export()
"""])

# re-export without dependencies

button_list.append(['Re-export without dependencies', 'icon_re_export_no_deps.png', 'python', """
import ms_shelf
ms_shelf.re_export_no_deps()
"""])

# import .appleseed scene

button_list.append(['Import .appleseed scene', 'icon_import_appleseed_scene.png', 'python', """
import ms_shelf
ms_shelf.import_appleseed_scene()
"""])


#--------------------------------------------------------------------------------------------------
# button functions.
#--------------------------------------------------------------------------------------------------

def get_export_node():
    render_settings_nodes = cmds.ls(type='ms_renderSettings')
    if len(render_settings_nodes) > 0:
        if len(render_settings_nodes) == 1:
            return render_settings_nodes[0]
        else:
            render_settings_nodes = cmds.ls(type='ms_renderSettings')
            export_node = cmds.confirmDialog(title='', message='Select a render settings node to export.', button=render_settings_nodes)
            if export_node != 'dismiss':
                return export_node
    else:
        ms_commands.error('No render settings nodes present')
        return None


def export():
    node = get_export_node()
    if node is not None:
        ms_export.export(node)


def export_no_deps_button():
    node = get_export_node()
    export_no_deps(node)


def export_no_deps(node):
    if node is not None:

        tex_export = cmds.getAttr(node + '.overwrite_existing_textures')
        geo_export = cmds.getAttr(node + '.overwrite_existing_geometry')

        cmds.setAttr(node + '.overwrite_existing_textures', 0)
        cmds.setAttr(node + '.overwrite_existing_geometry', 0)

        ms_export.export(node)

        cmds.setAttr(node + '.overwrite_existing_textures', tex_export)
        cmds.setAttr(node + '.overwrite_existing_geometry', geo_export)

    else:
        ms_commands.error('No render settings nodes present')


def re_export():
    if ms_export.previous_export is not None and cmds.objExists(ms_export.previous_export):
        ms_export.export(ms_export.previous_export)


def re_export_no_deps():
    if ms_export.previous_export is not None and cmds.objExists(ms_export.previous_export):
        export_no_deps(ms_export.previous_export)


def import_appleseed_scene():
    ms_commands.create_ms_appleseed_scene()


def reload_modules():
    import ms_export
    reload(ms_export)
    import ms_commands
    reload(ms_commands)
    import ms_menu
    reload(ms_menu)
    import ms_shelf
    reload(ms_shelf)
    import ms_export_obj
    reload(ms_export_obj)
    import ms_render_view_connection
    reload(ms_render_view_connection)


#--------------------------------------------------------------------------------------------------
# Shelf creation.
#--------------------------------------------------------------------------------------------------

def add_shelf_buton(shelf_name, button_name, icon, type, command):
    cmds.shelfButton(button_name, p=shelf_name, i=icon, c=command, stp=type, width=45, height=44)


def populate_shelf(shelf_name, button_list):
    for button in button_list:
        add_shelf_buton(shelf_name, button[0], button[1], button[2], button[3])


def create():

    if cmds.shelfLayout(shelf_name, exists=True, q=True):
        cmds.deleteUI(shelf_name)
    
    cmds.setParent(main_shelf_parent)
    cmds.shelfLayout(shelf_name)

    populate_shelf(shelf_name, button_list)

    # fix stupid maya error with shelves generated via python
    top_level_shelf = mel.eval('string $m = $gShelfTopLevel')
    shelves = cmds.shelfTabLayout(top_level_shelf, query=True, tabLabelIndex=True)
    for index, shelf in enumerate(shelves):
        cmds.optionVar(stringValue=('shelfName%d' % (index+1), str(shelf)))


def create_if_absent():

    if not cmds.shelfLayout(shelf_name, exists=True, q=True):
        create()




