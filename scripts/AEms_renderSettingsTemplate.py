
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

import pymel.core as pm
import maya.cmds as cmds
from functools import partial
import ms_export
import ms_commands

class AEms_renderSettingsTemplate(pm.uitypes.AETemplate):
        def __init__(self, node):

                self.beginScrollLayout()

                self.callCustom(self.toolbar_create, self.toolbar_edit, 'render_toolbar')

                # export settings
                self.beginLayout('Export settings', collapse=False)
                self.callCustom(self.output_directory_create, self.populate_render_layer_layout, 'output_directory')
                self.addControl('output_file')
                self.addSeparator()
                self.addControl('convert_shading_nodes_to_textures', label='Bake shading networks')
                self.addSeparator()
                self.addControl('convert_textures_to_exr', label='Convert Textures to OpenEXR')
                self.addSeparator()
                self.addControl('overwrite_existing_textures', label='Overwrite Existing Textures Files')
                self.addSeparator()
                self.addControl('overwrite_existing_geometry', label='Overwrite Existing Geometry Files')
                self.addSeparator()
                self.addControl('export_camera_blur', label='Export Camera Transformation Motion Blur')
                self.addSeparator()
                self.addControl('export_transformation_blur', label='Export Assembly Transformation Motion Blur')
                self.addSeparator()
                self.addControl('export_deformation_blur', label='Export Object Deformation Motion Blur')
                self.addSeparator()
                self.addControl('motion_samples')
                self.addControl('shutter_open_time')
                self.addControl('shutter_close_time')
                self.addSeparator()
                self.addControl('export_animation')
                self.addControl('animation_start_frame')
                self.addControl('animation_end_frame')
                self.addControl('export_animated_textures')
                self.endLayout()

                # output settings
                self.beginLayout('Output settings')
                self.callCustom(self.camera_select_create, self.camera_select_update, 'camera')
                self.camera_select_option_menu = None
                self.addControl('frame_width')
                self.addControl('frame_height')
                self.addControl('color_space')
                self.addControl('export_straight_alpha')
                self.endLayout()

                # environment settings
                self.beginLayout('Environment settings')
                self.callCustom(self.environment_select_create, self.environment_select_update, 'environment')
                self.environment_select_option_menu = None
                self.addControl('render_sky')
                self.addControl('scene_index_of_refraction')
                self.endLayout()

                # configuration settings
                self.beginLayout('Configuration settings')
                self.addControl('sampler', changeCommand=self.configuration_settings_sampler_callback)
                self.addControl('adaptive_min_samples')
                self.addControl('adaptive_max_samples')
                self.addControl('adaptive_quality')
                self.addSeparator()
                self.addControl('uniform_samples')
                self.addControl('uniform_decorrelate_pixels', label='Decorrelate pixels')
                self.addSeparator()
                self.addControl('pt_direct_lighting')
                self.addControl('pt_ibl')
                self.addControl('pt_caustics')
                self.addSeparator()
                self.addControl('pt_next_event_estimation')
                self.addControl('pt_max_bounces')
                self.addControl('pt_light_samples')
                self.addControl('pt_environment_samples')
                self.addControl('pt_max_ray_intensity')
                self.addSeparator()
                self.addControl('enable_importance_sampling')
                self.endLayout()

                # render layers
                self.beginLayout('Render layers')
                self.callCustom(self.render_layer_create_layout, self.populate_render_layer_layout, 'render_layers')
                self.render_layer_layout = None
                self.endLayout()

                # advanced settings
                self.beginLayout('Advanced settings')
                self.addControl('profile_export')
                self.addSeparator()
                self.addControl('autodetect_alpha')
                self.addSeparator()
                self.addControl('force_linear_texture_interpretation')
                self.addSeparator()
                self.addControl('force_linear_color_interpretation')
                self.addSeparator()
                self.addControl('export_all_cameras_as_thin_lens')
                self.addSeparator()
                self.addControl('export_maya_lights')

                self.endLayout()

                self.addExtraControls()

                self.endScrollLayout()

                # suppress potential render layers
                for i in range(50):
                    for attr in ms_commands.RENDER_LAYER_ATTRS:
                        self.suppress('render_layer_{0}_{1}'.format(i, attr[0]))


        def get_file_dir(self, *attr):
            file_name = cmds.fileDialog2(fm=3, cap='Select directory', okc='Select')
            if file_name is not None:
                cmds.setAttr(attr[0], file_name[0], type='string')


        def output_directory_create(self, attr):
            cmds.rowLayout(nc=3)
            cmds.text(label='Output Directory')
            self.output_dir_text_field = cmds.textField(fileName=cmds.getAttr(attr))
            self.output_dir_button = cmds.button(' Select directory ', c=partial(self.get_file_dir, attr))


        def output_directory_update(self, attr):
            cmds.textField(self.output_dir_text_field, edit=True, fileName=cmds.getAttr(attr))
            cmds.button(self.output_dir_button, edit=True, c=partial(self.get_file_dir, attr))


        def render_layer_create_layout(self, args):
            self.render_layer_layout_widths = [130, 120, 130, 50, 30]
            self.render_layer_label_layout = cmds.rowLayout('render_layer_label_layout', nc=5, cal=[1, 'left'])
            for i, width in enumerate(self.render_layer_layout_widths):
                cmds.rowLayout(self.render_layer_label_layout, e=True, cw=[i + 1, width])
            cmds.text('name')
            cmds.text('entity type')
            cmds.text('rule')
            cmds.text('order')
            cmds.text(' - ')
            cmds.setParent('..')
            self.render_layer_layout = cmds.columnLayout('render_layer_layout')
            cmds.setParent('..')
            self.populate_render_layer_layout(args)


        def add_render_layer(self, node, refresh=True):
            for i in range(50):
                i += 1

                layer_name = 'render_layer_{0}_name'.format(i)  
            
                if not cmds.attributeQuery(layer_name, exists=True, node=node):
                    for attr in ms_commands.RENDER_LAYER_ATTRS:
                        cmds.addAttr(node, longName='render_layer_{0}_{1}'.format(i, attr[0]), dt="string", k=False, w=False)
                        cmds.setAttr('{0}.render_layer_{1}_{2}'.format(node, i, attr[0]), attr[1], type='string')
                    if refresh:
                        self.populate_render_layer_layout(attr)
                    break


        def remove_render_layer(self, node, number, args):
            for attr in ms_commands.RENDER_LAYER_ATTRS:
                cmds.deleteAttr(n=node, at='render_layer_{0}_{1}'.format(number, attr[0]))
            self.populate_render_layer_layout(node)


        def populate_render_layer_layout(self, attr):
            if self.render_layer_layout is not None:
                node = attr.split('.')[0]  
                # delete old ui
                children = cmds.columnLayout(self.render_layer_layout, q=True, childArray=True)
                if children is not None:
                    for name in children:
                        cmds.deleteUI(name)

                for i in range(50):
                    i += 1

                    layer_name = 'render_layer_{0}_name'.format(i)

                    if cmds.attributeQuery(layer_name, exists=True, node=node):
                        cmds.setParent(self.render_layer_layout)
                        current_render_layer_layout = cmds.rowLayout(nc=5)
                        for n, width in enumerate(self.render_layer_layout_widths):
                            cmds.rowLayout(current_render_layer_layout, e=True, cw=[n + 1, width])
                        cmds.textField(cc=partial(self.set_render_layer_name, node, i), text=cmds.getAttr('{0}.render_layer_{1}_name'.format(node, i)))
                        entity_type_menu = cmds.optionMenu(cc=partial(self.set_render_layer_type, node, i))
                        for entity_type in ms_commands.RENDER_LAYER_ENTITY_TYPES:
                            cmds.menuItem(label=entity_type)
                        cmds.optionMenu(entity_type_menu, e=True, v=cmds.getAttr('{0}.render_layer_{1}_type'.format(node, i)))
                        rule_text_field = cmds.textField(cc=partial(self.set_render_layer_rule, node, i), text=cmds.getAttr('{0}.render_layer_{1}_rule'.format(node, i)))
                        cmds.textField(cc=partial(self.set_render_layer_order, i), text=cmds.getAttr('{0}.render_layer_{1}_order'.format(node, i)))
                        cmds.button(' - ', height=20, command=partial(self.remove_render_layer, node, i))
                
                cmds.setParent(self.render_layer_layout)
                current_render_layer_layout = cmds.rowLayout(nc=2)
                cmds.button(' + ', command=partial(self.add_render_layer, node))


        def camera_select_create(self, attr=None):
            self.camera_select_layout = cmds.rowLayout(nc=3)
            cmds.text('Camera')
            self.camera_select_option_menu = cmds.optionMenu(cc=partial(self.camera_select_set, attr))
            self.camera_select_update(attr)


        def camera_select_update(self, attr):
            if self.camera_select_option_menu is not None:
                items = cmds.optionMenu(self.camera_select_option_menu, q=True, ill=True)
                if items is not None:
                    for item in items:
                        cmds.deleteUI(item)
                cmds.menuItem(label='<none>', p=self.camera_select_option_menu)
                for camera in cmds.ls(type='camera'):
                    if not cmds.getAttr(camera + '.orthographic'):
                        cmds.menuItem(label=camera, p=self.camera_select_option_menu)
                connection = cmds.listConnections(attr, sh=True)
                if connection is None:
                    cmds.optionMenu(self.camera_select_option_menu, e=True, v='<none>')
                else:
                    cmds.optionMenu(self.camera_select_option_menu, e=True, v=connection[0])


        def camera_select_set(self, attr, camera):
            value = cmds.optionMenu(self.camera_select_option_menu, q=True, v=True)
            connection = cmds.listConnections(attr, sh=True)
            if value == '<none>':
                if connection is not None:
                    cmds.disconnectAttr(connection[0] + '.message', attr)
            else:
                if connection is not None:
                    if connection[0] == camera:
                        return
                cmds.connectAttr(camera + '.message', attr, f=True)


        def environment_select_create(self, attr=None):
            self.environment_select_layout = cmds.rowLayout(nc=3)
            cmds.text('Environment')
            self.environment_select_option_menu = cmds.optionMenu(cc=partial(self.environment_select_set, attr))
            if attr is not None:
                self.environment_select_update(attr)


        def environment_select_update(self, attr):
            if self.environment_select_option_menu is not None:
                items = cmds.optionMenu(self.environment_select_option_menu, q=True, ill=True)
                if items is not None:
                    for item in items:
                        cmds.deleteUI(item)
                cmds.menuItem(label='<none>', p=self.environment_select_option_menu)
                for environment in cmds.ls(type='ms_environment') + cmds.ls(type='ms_physical_environment'):
                    cmds.menuItem(label=environment, p=self.environment_select_option_menu)
                connection = cmds.listConnections(attr, sh=True)
                if connection is None:
                    cmds.optionMenu(self.environment_select_option_menu, e=True, v='<none>')
                else:
                    cmds.optionMenu(self.environment_select_option_menu, e=True, v=connection[0])


        def environment_select_set(self, attr, environment):
            value = cmds.optionMenu(self.environment_select_option_menu, q=True, v=True)
            connection = cmds.listConnections(attr, sh=True)
            if value == '<none>':
                if connection is not None:
                    cmds.disconnectAttr(connection[0] + '.message', attr)
            else:
                if connection is not None:
                    if connection[0] == environment:
                        return
                cmds.connectAttr(environment + '.message', attr, f=True)


        def set_render_layer_name(self, node, layer_number, value):
            self.set_render_layer_attr(node, layer_number, 'name', value)


        def set_render_layer_type(self, node, layer_number, value):
            self.set_render_layer_attr(node, layer_number, 'type', value)


        def set_render_layer_rule(self, node, layer_number, value):
            self.set_render_layer_attr(node, layer_number, 'rule', value)


        def set_render_layer_order(self, node, layer_number, value):
            self.set_render_layer_attr(node, layer_number, 'order', value)


        def set_render_layer_attr(self, node, layer_number, name, value):
            cmds.setAttr('{0}.render_layer_{1}_{2}'.format(node, layer_number, name), value, type='string')


        def toolbar_create(self, args):
            cmds.button('Export', bgc=[0, 0.7, 1], command=self.render)         
            cmds.button('Refresh attribute editor', command=self.refresh_editor)
            

        def toolbar_edit(self, args):
            pass


        def configuration_settings_sampler_callback(self, node):
            if cmds.getAttr(node + '.sampler') == 0: # adaptive
                cmds.editorTemplate(dimControl=[node, 'adaptive_min_samples', False])
                cmds.editorTemplate(dimControl=[node, 'adaptive_max_samples', False])
                cmds.editorTemplate(dimControl=[node, 'adaptive_quality', False])
                cmds.editorTemplate(dimControl=[node, 'uniform_samples', True])
                cmds.editorTemplate(dimControl=[node, 'uniform_decorrelate_pixels', True])
            else: # uniform
                cmds.editorTemplate(dimControl=[node, 'adaptive_min_samples', True])
                cmds.editorTemplate(dimControl=[node, 'adaptive_max_samples', True])
                cmds.editorTemplate(dimControl=[node, 'adaptive_quality', True])
                cmds.editorTemplate(dimControl=[node, 'uniform_samples', False])
                cmds.editorTemplate(dimControl=[node, 'uniform_decorrelate_pixels', False])


        def refresh_editor(self, args):
            cmds.refreshEditorTemplates()


        def render(self, args):
            node = cmds.ls(sl=True)
            ms_export.export(node[0])



            
