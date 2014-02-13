import pymel.core as pm
import maya.cmds as cmds
from functools import partial
import ms_export


ENTITY_TYPES = ['object_instance', 'light', 'edf']


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
                self.addControl('camera')
                self.addControl('frame_width')
                self.addControl('frame_height')
                self.addControl('color_space')
                self.addControl('export_straight_alpha')
                self.endLayout()

                # environment settings
                self.beginLayout('Environment settings')
                self.addControl('environment')
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
            render_layer_label_layout = cmds.rowLayout('render_layer_label_layout', nc=5, cal=[1, 'left'])
            for i, width in enumerate(self.render_layer_layout_widths):
                cmds.rowLayout(render_layer_label_layout, e=True, cw=[i + 1, width])
            cmds.text('name')
            cmds.text('entity type')
            cmds.text('rule')
            cmds.text('order')
            cmds.text(' - ')
            cmds.setParent('..')
            self.render_layer_layout = cmds.columnLayout('render_layer_layout')
            cmds.setParent('..')
            cmds.rowLayout(nc=3)
            cmds.button(' + ', command=partial(self.add_render_layer, args))

            self.populate_render_layer_layout(args)


        def add_render_layer(self, attr, name=None, model=None, rule=None, entity_type=None, refresh=False):
            node = attr.split('.')[0]

            i = 0

            while True:
                i += 1
                if i > 50:
                    break
                layer_name = 'render_layer_{0}_name'.format(i)  
            
                if not cmds.attributeQuery(layer_name, exists=True, node=node):

                    cmds.addAttr(node, longName='render_layer_{0}_name'.format(i), dt="string")
                    if name is not None:
                        cmds.setAttr(node + '.render_layer_{0}_name'.format(i), name, type='string')
                    cmds.addAttr(node, longName='render_layer_{0}_model'.format(i), dt="string")
                    if model is not None:
                        cmds.setAttr(node + '.render_layer_{0}_model'.format(i), model, type='string')
                    cmds.addAttr(node, longName='render_layer_{0}_rule'.format(i), dt="string")
                    if rule is not None:
                        cmds.setAttr(node + '.render_layer_{0}_rule'.format(i), rule, type='string')
                    if entity_type is not None:
                        cmds.setAttr(node + '.render_layer_{0}_type'.format(i), entity_type, type='string')
                    cmds.addAttr(node, longName='render_layer_{0}_type'.format(i), dt="string")

                    cmds.addAttr(node, longName='render_layer_{0}_order'.format(i), at="short")

                    if refresh:
                        self.populate_render_layer_layout(attr)

                    break


        def populate_render_layer_layout(self, attr): # here we pass the attribute rather than the node name so we can re use this finction id the call custom menu

            node = attr.split('.')[0]  

            # delete old ui
            children = cmds.columnLayout(self.render_layer_layout, q=True, childArray=True)
            if children is not None:
                for name in children:
                    cmds.deleteUI(name)

            i = 0

            while True:
                i += 1

                if i > 50:
                    break
                layer_name = 'render_layer_{0}_name'.format(i)

                if cmds.attributeQuery(layer_name, exists=True, node=node):

                    cmds.setParent(self.render_layer_layout)

                    current_render_layer_layout = cmds.rowLayout(nc=5)
            
                    for n, width in enumerate(self.render_layer_layout_widths):
                        cmds.rowLayout(current_render_layer_layout, e=True, cw=[n + 1, width])

                    cmds.textField()
                    entity_type_menu = cmds.optionMenu()
                    for entity_type in ENTITY_TYPES:
                        cmds.menuItem(label=entity_type)
                    rule_text_field = cmds.textField()
                    cmds.intField(v=1)
                    cmds.button(' - ', height=20)


        def set_render_layer_attrs(layer_number):
            pass


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



            
