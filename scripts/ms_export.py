
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
import maya.utils as mu
import os
import time
import re
import subprocess
import sys
import ms_commands
import time
import inspect
import shutil
import copy

global previous_export
previous_export = None

#--------------------------------------------------------------------------------------------------
# WriteXml class.
#--------------------------------------------------------------------------------------------------

class WriteXml():
    spaces_per_indentation_level = 4

    def __init__(self, file_path):
        self.indentation_level = 0
        self.file_object = None
        try:
            self.file_object = open(file_path, 'w')
        except IOError:
            cmds.error("IO error: failed to open {0} for writing.".format(file_path))

    def start_element(self, str):
        self.append_line("<" + str + ">")
        self.indentation_level += 1

    def end_element(self, str):
        self.indentation_level -= 1
        self.append_line("</" + str + ">")

    def append_element(self, str):
        self.append_line("<" + str + "/>")

    def append_parameter(self, name, value):
        self.append_line('<parameter name="{0}" value="{1}" />'.format(name, value))

    def append_line(self, str):
        self.file_object.write(self.indentation_string() + str + "\n")

    def close(self):
        self.file_object.close()

    def indentation_string(self):
        return (self.indentation_level * self.spaces_per_indentation_level) * " "


#--------------------------------------------------------------------------------------------------
# check_export_cancelled function.
#--------------------------------------------------------------------------------------------------

def check_export_cancelled():
    if cmds.progressWindow(query=True, isCancelled=True):
        cmds.progressWindow(endProgress=1)
        ms_commands.warning("Export cancelled")
        sys.exit()
        

#--------------------------------------------------------------------------------------------------
# get_maya_params function.
#--------------------------------------------------------------------------------------------------

def get_maya_params(render_settings_node):
    ms_commands.info("Retrieving settings from UI...")

    params = {}

    params['entity_defs'] = ms_commands.get_entity_defs(os.path.join(ms_commands.ROOT_DIRECTORY, 'scripts', 'appleseedEntityDefs.xml'))

    # Main settings.
    params['output_directory'] = cmds.getAttr(render_settings_node + '.output_directory')
    params['file_name'] = cmds.getAttr(render_settings_node + '.output_file')
    params['convert_shading_nodes'] = cmds.getAttr(render_settings_node + '.convert_shading_nodes_to_textures')
    params['convert_textures_to_exr'] = cmds.getAttr(render_settings_node + '.convert_textures_to_exr')
    params['overwrite_existing_textures'] = cmds.getAttr(render_settings_node + '.overwrite_existing_textures')
    params['overwrite_existing_geometry'] = cmds.getAttr(render_settings_node + '.overwrite_existing_geometry')
    params['export_camera_blur'] = cmds.getAttr(render_settings_node + '.export_camera_blur')
    params['exportMayaLights'] = cmds.getAttr(render_settings_node + '.export_maya_lights')
    params['export_transformation_blur'] = cmds.getAttr(render_settings_node + '.export_transformation_blur')
    params['export_deformation_blur'] = cmds.getAttr(render_settings_node + '.export_deformation_blur')
    params['motion_samples'] = cmds.getAttr(render_settings_node + '.motion_samples')
    params['shutter_open_time'] = cmds.getAttr(render_settings_node + '.shutter_open_time')
    params['shutter_close_time'] = cmds.getAttr(render_settings_node + '.shutter_close_time')
    params['export_animation'] = cmds.getAttr(render_settings_node + '.export_animation')
    params['animation_start_frame'] = cmds.getAttr(render_settings_node + '.animation_start_frame')
    params['animation_end_frame'] = cmds.getAttr(render_settings_node + '.animation_end_frame')
    params['animated_textures'] = cmds.getAttr(render_settings_node + '.export_animated_textures')
    params['scene_scale'] = 1.0

    if not (params['export_transformation_blur'] or params['export_deformation_blur'] or params['export_camera_blur'] or params['export_animation']):
        params['motion_samples'] = 1
    elif params['motion_samples'] < 2:
        ms_commands.warning('Motion samples must be >= 2, using 2.')
        params['motion_samples'] = 2

    # Advanced options.
    if cmds.listConnections(render_settings_node + '.environment'):
        params['environment'] = cmds.listRelatives(cmds.listConnections(render_settings_node + '.environment')[0])[0]
    else:
        params['environment'] = False

    params['render_sky'] = cmds.getAttr(render_settings_node + '.render_sky')
    params['scene_ior'] = cmds.getAttr(render_settings_node + '.scene_index_of_refraction')

    # Cameras.
    # params['sceneCameraExportAllCameras'] = cmds.checkBox('ms_sceneCameraExportAllCameras', query=True, value=True)
    params['export_all_cameras_as_thin_lens'] = cmds.getAttr(render_settings_node + '.export_all_cameras_as_thin_lens')

    # Output.
    if cmds.listConnections(render_settings_node + '.camera'):
        connected_cameras = cmds.listConnections(render_settings_node + '.camera')
        if connected_cameras is not None:
            params['output_camera'] = cmds.listRelatives(connected_cameras[0], typ='camera', fullPath=True)[0]
    else:
        params['output_camera'] = '|persp|perspShape'
        ms_commands.warning('No camera connected to {0}, using "{1}".'.format(render_settings_node, params['output_camera']))

    if cmds.getAttr(render_settings_node + '.color_space') == 1:
        params['output_color_space'] = 'linear_rgb'
    elif cmds.getAttr(render_settings_node + '.color_space') == 2:
        params['output_color_space'] = 'spectral'
    elif cmds.getAttr(render_settings_node + '.color_space') == 3:
        params['output_color_space'] = 'ciexyz'
    else:
        params['output_color_space'] = 'srgb'

    params['output_res_width'] = cmds.getAttr(render_settings_node + '.width')
    params['output_res_height'] = cmds.getAttr(render_settings_node + '.height')
    params['export_straight_alpha'] = cmds.getAttr(render_settings_node + '.export_straight_alpha')

    # render layers
    params['render_layers'] = []
    for i in range(50):
        i += 1
        test_layer_name = 'render_layer_{0}_name'.format(i)  
        if cmds.attributeQuery(test_layer_name, exists=True, node=render_settings_node):
            layer = {}
            for attr in ms_commands.RENDER_LAYER_ATTRS:
                layer[attr[0]] = cmds.getAttr('{0}.render_layer_{1}_{2}'.format(render_settings_node, i, attr[0]))

            params['render_layers'].append(layer)

    # configuration settings.
    params['sampler'] = cmds.getAttr(render_settings_node + '.sampler')
    if params['sampler'] == 0:
        params['sampler'] = 'adaptive'
    else:
        params['sampler'] = 'uniform'

    params['uniform_samples'] = cmds.getAttr(render_settings_node + '.uniform_samples')
    params['uniform_decorrelate_pixels'] = cmds.getAttr(render_settings_node + '.uniform_decorrelate_pixels')
 
    params['adaptive_min_samples'] = cmds.getAttr(render_settings_node + '.adaptive_min_samples')
    params['adaptive_max_samples'] = cmds.getAttr(render_settings_node + '.adaptive_max_samples')
    params['adaptive_quality'] = cmds.getAttr(render_settings_node + '.adaptive_quality')
    params['pt_ibl'] = cmds.getAttr(render_settings_node + '.pt_ibl')
    params['pt_caustics'] = cmds.getAttr(render_settings_node + '.pt_caustics')
    params['pt_direct_lighting'] = cmds.getAttr(render_settings_node + '.pt_direct_lighting')
    params['pt_next_event_estimation'] = cmds.getAttr(render_settings_node + '.pt_next_event_estimation')
    params['pt_max_bounces'] = cmds.getAttr(render_settings_node + '.pt_max_bounces')
    params['pt_light_samples'] = cmds.getAttr(render_settings_node + '.pt_light_samples')
    params['pt_environment_samples'] = cmds.getAttr(render_settings_node + '.pt_environment_samples')
    params['pt_max_ray_intensity'] = cmds.getAttr(render_settings_node + '.pt_max_ray_intensity')
    params['enable_importance_sampling'] = cmds.getAttr(render_settings_node + '.enable_importance_sampling')

    # Select obj exporter.
    if cmds.pluginInfo('ms_export_obj_' + str(int(mel.eval('getApplicationVersionAsFloat()'))), query=True, r=True):
        params['obj_exporter'] = ms_commands.export_obj
    else:
        ms_commands.warning("No native obj exporter found, exporting using Python obj exporter.")
        params['obj_exporter'] = ms_export_obj.export

    params['autodetect_alpha'] = cmds.getAttr(render_settings_node + '.autodetect_alpha')
    params['force_linear_texture_interpretation'] = cmds.getAttr(render_settings_node + '.force_linear_texture_interpretation')
    params['force_linear_color_interpretation'] = cmds.getAttr(render_settings_node + '.force_linear_color_interpretation')
    params['tile_width'] = cmds.getAttr(render_settings_node + '.tile_width')
    params['tile_height'] = cmds.getAttr(render_settings_node + '.tile_height')
    params['use_long_names'] = cmds.getAttr(render_settings_node + '.use_long_names')

    return params


#--------------------------------------------------------------------------------------------------
# get_maya_scene function.
#--------------------------------------------------------------------------------------------------

def get_maya_scene(params):

    """ Parses the Maya scene and returns a list of root transforms with the relevant children """

    info_message = "Caching Maya transform data..."
    ms_commands.info(info_message)
    cmds.progressWindow(e=True, status=info_message, progress=0, max=1)
    cmds.refresh(cv=True)

    start_time = cmds.currentTime(query=True)

    # the Maya scene is stored as a list of root transforms that contain meshes/geometry/lights as children
    maya_root_transforms = []

    # find all root transforms and create Mtransforms from them
    for maya_transform in cmds.ls(tr=True, long=True):
        if not cmds.listRelatives(maya_transform, ap=True, fullPath=True):
            if ms_commands.transform_is_renderable(maya_transform):
                maya_root_transforms.append(MTransform(params, maya_transform, None))

    cmds.progressWindow(e=True, progress=1)

    start_frame = int(start_time)
    end_frame = start_frame
    sample_increment = 1.0
    if params['motion_samples'] > 1:
        sample_increment = 1.0 / (params['motion_samples'] - 1)

    if params['export_animation']:
        start_frame = params['animation_start_frame']
        end_frame = params['animation_end_frame']

    if params['export_transformation_blur'] or params['export_deformation_blur'] or params['export_camera_blur']:
        end_frame += 1

    # compute the base output directory
    scene_filepath = cmds.file(q=True, sceneName=True)
    scene_basename = os.path.splitext(os.path.basename(scene_filepath))[0]
    if len(scene_basename) == 0:
        scene_basename = "Untitled"
    project_directory = cmds.workspace(q=True, rd=True)
    params['output_directory'] = params['output_directory'].replace("<ProjectDir>", project_directory)
    params['output_directory'] = params['output_directory'].replace("<SceneName>", scene_basename)

    ms_commands.create_dir(os.path.join(params['output_directory'], ms_commands.TEXTURE_DIR))
    ms_commands.create_dir(os.path.join(params['output_directory'], ms_commands.GEO_DIR))

    # get environment
    environment = None
    if params['environment']:
        if cmds.nodeType(params['environment']) == 'ms_physical_environment':
            environment = MMsPhysicalEnvironment(params, params['environment'])
        else:
            environment = MMsEnvironment(params, params['environment'])

        environment.add_environment_sample(params['output_directory'], 0)

    # add motion samples
    current_frame = start_frame
    frame_sample_number = 1


    cmds.progressWindow(edit=True, progress=0, status='Adding motion samples', max=end_frame - start_frame + 1)
    cmds.refresh(cv=True)
    while current_frame <= end_frame:

        info_message = "Adding motion samples, frame {0}...".format(current_frame)
        ms_commands.info(info_message)

        cmds.progressWindow(e=True, status=info_message)
        cmds.refresh(cv=True)

        cmds.currentTime(current_frame)

        # determine if this is the first sample of a frame
        initial_sample = (frame_sample_number == 1)

        for transform in maya_root_transforms:
            add_scene_sample(transform, params['export_transformation_blur'], params['export_deformation_blur'], params['export_camera_blur'], current_frame, start_frame, frame_sample_number, initial_sample, params['output_directory'])

        frame_sample_number += 1
        if frame_sample_number == params['motion_samples']:
            frame_sample_number = 1

        current_frame += sample_increment

        MMesh.export_geo(params['obj_exporter'], current_frame)

        MFile.export_images(params['output_directory'], params['overwrite_existing_textures'], current_frame)

        cmds.progressWindow(e=True, progress=current_frame - start_frame)
        cmds.refresh(cv=True)

    # return to pre-export time
    cmds.currentTime(start_time)

    cmds.progressWindow(e=True, progress=end_frame - start_frame)
    cmds.refresh(cv=True)

    return maya_root_transforms, environment


#--------------------------------------------------------------------------------------------------
# add_scene_sample function.
#--------------------------------------------------------------------------------------------------

def add_scene_sample(m_transform, transform_blur, deform_blur, camera_blur, current_frame, start_frame, frame_sample_number, initial_sample, export_root):

    check_export_cancelled()

    if transform_blur or initial_sample:
        m_transform.add_transform_sample()
        if (frame_sample_number == 1) or initial_sample:
            m_transform.add_visibility_sample()

    if deform_blur or initial_sample:
        for mesh in m_transform.child_meshes:
            # Only add a sample if this is the first frame to be exported or if it has some deformation
            if mesh.has_deformation or (current_frame == start_frame):
                if initial_sample:
                    mesh.add_deform_sample(export_root, current_frame)

    for mesh in m_transform.child_meshes:
        if (frame_sample_number == 1) or initial_sample:
            for material in mesh.ms_materials:
                for texture in material.textures:
                    if texture.is_animated or initial_sample:
                        texture.add_image_sample(export_root, current_frame)
                        
            for material in mesh.generic_materials:
                for texture in material.textures:
                    if texture.is_animated or initial_sample:
                        texture.add_image_sample(export_root, current_frame) 

    for light in m_transform.child_lights:
        if light.color.__class__.__name__ == 'MFile':
            if light.color.is_animated or initial_sample:
                light.color.add_image_sample(export_root, current_frame) 

    for camera in m_transform.child_cameras:
        if camera_blur or initial_sample or (frame_sample_number == 1):
            camera.add_matrix_sample()
        if frame_sample_number == 1:
            camera.add_focal_distance_sample()
            camera.add_focal_length_sample()

    for transform in m_transform.child_transforms:
        add_scene_sample(transform, transform_blur, deform_blur, camera_blur, current_frame, start_frame, frame_sample_number, initial_sample, export_root)


#--------------------------------------------------------------------------------------------------
# m_file_from_color_connection function.
#--------------------------------------------------------------------------------------------------

def m_file_from_color_connection(params, m_color_connection):
    if m_color_connection.connected_node:
        if m_color_connection.connected_node_type == 'file':
            return MFile(params, m_color_connection.connected_node)
        else:
            node_name, attr_name = m_color_connection.name.split('.')
            return MFile(params, None, node_name, attr_name)

    return None


#--------------------------------------------------------------------------------------------------
# MTransform class.
#--------------------------------------------------------------------------------------------------

class MTransform():

    """ Lightweight class representing info for a Maya transform node """

    def __init__(self, params, maya_transform_name, parent):
        self.params = params
        self.name = maya_transform_name
        self.safe_name = ms_commands.legalize_name(self.name)
        self.parent = parent

        # child attributes
        self.child_cameras = []
        self.child_meshes = []
        self.child_lights = []
        self.child_ms_appleseed_scenes = []
        self.child_ms_appleseed_scene_instances = []
        self.child_transforms = []

        self.has_children = False

        # sample attributes
        self.matrices = []
        self.visibility_states = []

        #check for incoming connections to transform attributes and set the is_animated var
        self.is_animated = False
        maya_transform_attribute_list = ['translate', 'translateX', 'translateY', 'translateZ',
                                         'rotate', 'rotateX', 'rotateY', 'rotateZ',
                                         'scale','scaleX','scaleY','scaleZ', 'visibility']

        for attribute in maya_transform_attribute_list:
            if cmds.listConnections(self.name + '.' + attribute) is not None:
                self.is_animated = True
                break

        # get children
        mesh_names = cmds.listRelatives(self.name, type='mesh', fullPath=True)
        if mesh_names is not None:
            self.has_children = True
            for mesh_name in mesh_names:
                if ms_commands.mesh_is_renderable(mesh_name):
                    self.child_meshes.append(MMesh(params, mesh_name, self))

        light_names = cmds.listRelatives(self.name, type='light', fullPath=True)
        if light_names is not None:
            self.has_children = True
            for light_name in light_names:
                if cmds.nodeType(light_name) == 'pointLight' or cmds.nodeType(light_name) == 'spotLight' or cmds.nodeType(light_name) == 'areaLight':
                    self.child_lights.append(MLight(params, light_name, self))

        camera_names = cmds.listRelatives(self.name, type='camera', fullPath=True)
        if camera_names is not None:
            self.has_children = True
            for camera_name in camera_names:
                self.child_cameras.append(MCamera(params, camera_name, self))

        ms_appleseed_scene_names = cmds.listRelatives(self.name, type='ms_appleseed_scene', fullPath=True)
        if ms_appleseed_scene_names is not None:
            self.has_children = True
            for ms_appleseed_scene_name in ms_appleseed_scene_names:
                self.child_ms_appleseed_scenes.append(MMsAppleseedScene(params, ms_appleseed_scene_name, self))

        transform_names = cmds.listRelatives(self.name, type='transform', fullPath=True)
        if transform_names is not None:
            self.has_children = True
            for transform_name in transform_names:
                if ms_commands.transform_is_renderable(transform_name):
                    if ms_commands.transform_is_visible(transform_name):
                        self.child_transforms.append(MTransform(params, transform_name, self))

    def add_transform_sample(self):
        self.matrices.append(cmds.xform(self.name, query=True, matrix=True))

    def add_visibility_sample(self):
        self.visibility_states.append(cmds.getAttr(self.name + '.visibility'))


#--------------------------------------------------------------------------------------------------
# get_ms_appleseed_scene_from_heirarchy function.
#--------------------------------------------------------------------------------------------------

def get_ms_appleseed_scene_from_heirarchy(ms_appleseed_scene_name, transform):
    for ms_appleseed_scene in transform.child_ms_appleseed_scenes:
        if ms_appleseed_scene.name == ms_appleseed_scene_name:
            return ms_appleseed_scene

    for chlid_tranform in transform.child_transforms:
        ms_appleseed_scene_in_heirarchy = get_ms_appleseed_scene_from_heirarchy()
        if ms_appleseed_scene_in_heirarchy is not None:
            return ms_appleseed_scene_in_heirarchy

    return None


#--------------------------------------------------------------------------------------------------
# MTransformChild class.
#--------------------------------------------------------------------------------------------------

class MTransformChild():

    """ Base class for all classes representing Maya scene entities """

    current_id = 0

    def __init__(self, params, maya_entity_name, MTransform_object):
        
        # incrememnt transform child id counter
        self.id = MTransformChild.current_id
        MTransformChild.current_id += 1

        self.params = params
        self.name = maya_entity_name
        self.short_name = self.name.split('|')[-1]
        self.safe_short_name = ms_commands.legalize_name(self.short_name)

        if params['use_long_names']:
            self.safe_name = ms_commands.legalize_name(self.name)
        else:
            self.safe_name = '{0}_{1}'.format(self.safe_short_name, self.id)

        self.transform = MTransform_object

        self.export_modifiers = {}

        for attribute in ms_commands.LIGHT_EXPORT_MODIFIERS:
            if cmds.attributeQuery(attribute[0], n=self.name, ex=True):
                self.export_modifiers[attribute[0]] = cmds.getAttr('{0}.{1}'.format(self.name, attribute[0]))


#--------------------------------------------------------------------------------------------------
# MMesh class.
#--------------------------------------------------------------------------------------------------

class MMesh(MTransformChild):

    """ Lightweight class representing Maya mesh data """

    # because fill path names of geo can be too long for a file name we use the short name plus a counter
    object_counter = 1
    export_queue = []

    def __init__(self, params, maya_mesh_name, MTransform_object):
        MTransformChild.__init__(self, params, maya_mesh_name, MTransform_object)

        # increment class counter so each instance of the class gets a unique id
        self.id = MMesh.object_counter
        MMesh.object_counter += 1

        self.mesh_file_names = []
        self.ms_materials = []
        self.generic_materials = []
        self.has_deformation = False

        if cmds.listConnections(self.name + '.inMesh') is not None:
            ms_commands.info("{0} has deformation.".format(self.name))
            self.has_deformation = True

        attached_material_names = ms_commands.get_attached_materials(self.name)

        if attached_material_names is not None:
            for material_name in attached_material_names:
                if cmds.nodeType(material_name) == 'ms_appleseed_material':
                    self.ms_materials.append(MMsMaterial(self.params, material_name))
                else:
                    self.generic_materials.append(MGenericMaterial(self.params, material_name))

    def add_deform_sample(self, export_root, time):
        # if the shape current transform is visible, export;
        # otherwise skip export and just append a null
        if ms_commands.visible_in_hierarchy(self.transform.name):
            file_name = '%s_%i_%i.obj' % (self.safe_short_name, self.id, time)
            output_file_path = os.path.join(ms_commands.GEO_DIR, file_name)

            # set file path as relative value
            self.mesh_file_names.append(output_file_path)

            # export mesh using absolute file path
            absolute_file_path = os.path.join(export_root, output_file_path)
            if not os.path.exists(absolute_file_path) or self.params['overwrite_existing_geometry']:
                MMesh.export_queue.append([self.name, absolute_file_path])
        else:
            self.mesh_file_names.append(None)

    @classmethod
    def export_geo(cls_obj, exporter, frame_no):
        queue_len = len(cls_obj.export_queue)
        if queue_len > 0:
            cmds.progressWindow(e=True, status='Exporting geo for frame {0}'.format(frame_no), progress=0, max=queue_len)
            cmds.refresh(cv=True)
            for i, geo in enumerate(cls_obj.export_queue):
                cmds.progressWindow(e=True, progress=i)            
                exporter(geo[0], geo[1], overwrite=True)
            cls_obj.export_queue = []


#--------------------------------------------------------------------------------------------------
# MLight class.
#--------------------------------------------------------------------------------------------------

class MLight(MTransformChild):

    """ Lightweight class representing Maya light data """

    def __init__(self, params, maya_light_name, MTransform_object):
        MTransformChild.__init__(self, params, maya_light_name, MTransform_object)
        self.color = MColorConnection(self.params, self.name + '.color')
        if self.color.connected_node is not None:
            self.color = MFile(self.params, self.color.connected_node)
        self.multiplier = cmds.getAttr(self.name+'.intensity')
        self.decay = cmds.getAttr(self.name+'.decayRate')
        self.model = cmds.nodeType(self.name)
        if self.model == 'spotLight':
            self.inner_angle = cmds.getAttr(self.name + '.coneAngle')
            self.outer_angle = cmds.getAttr(self.name + '.coneAngle') +  (2 * cmds.getAttr(self.name + '.penumbraAngle'))


#--------------------------------------------------------------------------------------------------
# MCamera class.
#--------------------------------------------------------------------------------------------------

class MCamera(MTransformChild):

    """ Lightweight class representing Maya camera data """

    def __init__(self, params, maya_camera_name, MTransform_object):
        MTransformChild.__init__(self, params, maya_camera_name, MTransform_object)

        # In Maya cameras are descendents of transforms like other objects but in appleseed they exist outside
        # of the main assembly. For this reason we include the world space matrix as an attribute of the camera's
        # transform even though it's not a 'correct' representation of the Maya scene.

        self.world_space_matrices = []
        self.dof = cmds.getAttr(self.name + '.depthOfField')
        self.focal_distance_values = []
        self.focal_length_values = []
        self.focus_region_scale = cmds.getAttr(self.name + '.focusRegionScale')
        self.f_stop = self.focus_region_scale * cmds.getAttr(self.name + '.fStop')

        maya_resolution_aspect = float(self.params['output_res_width']) / float(self.params['output_res_height'])
        maya_film_aspect = cmds.getAttr(self.name + '.horizontalFilmAperture') / cmds.getAttr(self.name + '.verticalFilmAperture')

        if maya_resolution_aspect > maya_film_aspect:
            self.film_width = float(cmds.getAttr(self.name + '.horizontalFilmAperture')) * ms_commands.INCH_TO_METER * 100
            self.film_height = self.film_width / maya_resolution_aspect
        else:
            self.film_height = float(cmds.getAttr(self.name + '.verticalFilmAperture')) * ms_commands.INCH_TO_METER * 100
            self.film_width = self.film_height * maya_resolution_aspect

    def add_matrix_sample(self):
        world_space_matrix = cmds.xform(self.transform.name, query=True, matrix=True, ws=True)
        self.world_space_matrices.append(ms_commands.matrix_remove_scale(world_space_matrix))

    def add_focal_distance_sample(self):
        self.focal_distance_values.append(cmds.getAttr(self.name + '.focusDistance'))

    def add_focal_length_sample(self):
        self.focal_length_values.append(float(cmds.getAttr(self.name + '.focalLength')) / 10)


#--------------------------------------------------------------------------------------------------
# MMsAppleseedScene class.
#--------------------------------------------------------------------------------------------------

class MMsAppleseedScene(MTransformChild):

    """ Lightweight class representing Maya ms_appleseed_scene nodes """

    def __init__(self, params, ms_appleseed_scene_node_name, MTransform_object):
        MTransformChild.__init__(self, params, ms_appleseed_scene_node_name, MTransform_object)

        self.scene_filepath = cmds.getAttr(self.name + '.appleseed_file')


#--------------------------------------------------------------------------------------------------
# MMsAppleseedSceneInstance class.
#--------------------------------------------------------------------------------------------------

class MMsAppleseedSceneInstance(MTransformChild):

    """ Lightweight class representing an instance of a Maya ms_appleseed_scene node """

    def __init__(self, params, ms_appleseed_scene_node_name, MTransform_object, original):
        MTransformChild.__init__(self, params, ms_appleseed_scene_node_name, MTransform_object)

        self.original = original


#--------------------------------------------------------------------------------------------------
# MFile class.
#--------------------------------------------------------------------------------------------------

class MFile():

    """ Lightweight class representing Maya file nodes """

    export_queue = set()

    def __init__(self, params, maya_file_node, source_node=False, attribute=False):
        self.params = params
        self.image_file_names = []
        self.converted_images = set()
        self.node_type = cmds.nodeType(maya_file_node)
        self.autodetect_alpha = params['autodetect_alpha']        

        if self.node_type == 'file':
            self.name = maya_file_node
            self.safe_name = ms_commands.legalize_name(self.name)
            self.image_name = cmds.getAttr(self.name + '.fileTextureName')
            self.is_animated = cmds.getAttr(self.name + '.useFrameExtension')
            self.alpha_is_luminance = cmds.getAttr(self.name + '.alphaIsLuminance')
            self.filtering_mode = cmds.getAttr((self.name + '.filterType'), asString=True)

            # Off, Mipmap, Box, Quadratic, Quartic, Gaussian 

            texture_placement_node = ms_commands.get_connected_node(self.name + '.uvCoord')
            if texture_placement_node is not None:
                self.has_uv_placement = True
                self.repeat_u = cmds.getAttr(texture_placement_node + '.repeatU')
                self.repeat_v = cmds.getAttr(texture_placement_node + '.repeatV')
            else:
                self.has_uv_placement = False

        else:
            self.source_node = source_node
            self.attribute = attribute
            self.filtering_mode = 'Quadratic'
            self.name = 'baked_' + self.source_node + '_' + self.attribute
            self.safe_name = ms_commands.legalize_name(self.name)
            self.is_animated = False
            self.alpha_is_luminance = False
            self.has_uv_placement = False

    def add_image_sample(self, export_root, time):
        if self.node_type == 'file':
            image_name = ms_commands.get_file_texture_name(self.name, time)
        else:
            image_name = ms_commands.convert_connection_to_image(self.source_node, self.attribute, os.path.join(export_root, ms_commands.TEXTURE_DIR, ('{0}_{1}.iff'.format(self.name, time))), self.params['overwrite_existing_textures'])

        if self.params['convert_textures_to_exr']:
            if image_name not in self.converted_images:
                MFile.export_queue.add(image_name)
                file_name = os.path.join(ms_commands.TEXTURE_DIR, os.path.split(image_name)[1])
                self.image_file_names.append(file_name)
        else:
            self.image_file_names.append(image_name)

    @classmethod
    def export_images(cls_obj, export_root, overwrite, frame_no):
        queue_len = len(cls_obj.export_queue)
        if queue_len > 0:
            cmds.progressWindow(e=True, status='Exporting textures for frame {0}'.format(frame_no), progress=0, max=queue_len)
            cmds.refresh(cv=True)
            for i, tex in enumerate(cls_obj.export_queue):
                cmds.progressWindow(e=True, progress=i)  

                dest = os.path.join(export_root, ms_commands.TEXTURE_DIR, os.path.split(tex)[1])

                ms_commands.convert_texture_to_exr(tex, dest , overwrite=overwrite)


            cls_obj.export_queue = set()


#--------------------------------------------------------------------------------------------------
# MMsEnvironment class.
#--------------------------------------------------------------------------------------------------

class MMsEnvironment():

    """ Lightweight class representing Maya ms_environment nodes """

    def __init__(self, params, maya_ms_environment_node):
        self.params = params
        self.name = maya_ms_environment_node
        self.safe_name = ms_commands.legalize_name(self.name)

        self.model = cmds.getAttr(self.name + '.model')

        # ********** key *************
        # Constant Environment = 0
        # Gradient Environment = 1
        # Latitude Longitude Map = 2
        # Mirrorball Map = 3

        if self.model == 0:
            self.model = "constant_environment_edf"
        elif self.model == 1:
            self.model = "gradient_environment_edf"
        elif self.model == 2:
            self.model = "latlong_map_environment_edf"
        elif self.model == 3:
            self.model = "mirrorball_map_environment_edf"

        self.constant_exitance = MColorConnection(self.params, self.name + '.constant_exitance')
        self.gradient_horizon_exitance = MColorConnection(self.params, self.name + '.gradient_horizon_exitance')
        self.gradient_zenith_exitance = MColorConnection(self.params, self.name + '.gradient_zenith_exitance')
        
        self.latitude_longitude_exitance = self.get_connections(self.name + '.latitude_longitude_exitance')
        self.mirrorball_exitance = self.get_connections(self.name + '.mirror_ball_exitance')

        self.exitance_multiplier = cmds.getAttr(self.name + '.exitance_multiplier')

    def get_connections(self, attr_name):
        connection = MColorConnection(self.params, attr_name)
        if connection.connected_node is not None:
            return m_file_from_color_connection(self.params, connection)
        
        return None

    def add_environment_sample(self, export_root, time):
        if self.latitude_longitude_exitance is not None:
            self.latitude_longitude_exitance.add_image_sample(export_root, time)
        if self.mirrorball_exitance is not None:
            self.mirrorball_exitance.add_image_sample(export_root, time)

#--------------------------------------------------------------------------------------------------
# MMsPhysicalEnvironment class.
#--------------------------------------------------------------------------------------------------

class MMsPhysicalEnvironment():

    """ Lightweight class representing Maya ms_physical_environment nodes """

    def __init__(self, params, maya_ms_environment_node):
        self.params = params
        self.name = maya_ms_environment_node
        self.safe_name = ms_commands.legalize_name(self.name)

        self.model = cmds.getAttr(self.name + '.model')

        # ********** key *************
        # hosek_environment_edf    = 0
        # preetham_environment_edf = 1

        if self.model == 0:
            self.model = "hosek_environment_edf"
        elif self.model == 1:
            self.model = "preetham_environment_edf"

        self.ground_albedo           = cmds.getAttr(self.name + '.ground_albedo')
        self.horizon_shift           = cmds.getAttr(self.name + '.horizon_shift')
        self.luminance_multiplier    = cmds.getAttr(self.name + '.luminance_multiplier')
        self.saturation_multiplier   = cmds.getAttr(self.name + '.saturation_multiplier')
        self.luminance_gamma         = cmds.getAttr(self.name + '.luminance_gamma')
        self.sun_phi                 = cmds.getAttr(self.name + '.sun_phi')
        self.sun_theta               = cmds.getAttr(self.name + '.sun_theta')
        self.turbidity               = self.get_connections(self.name + '.turbidity')
        self.turbidity_multiplier    = cmds.getAttr(self.name + '.turbidity_multiplier')
        self.create_physical_sun     = cmds.getAttr(self.name + '.create_physical_sun') 
        self.physical_sun_multiplier = cmds.getAttr(self.name + '.physical_sun_multiplier')

    def get_connections(self, attr_name):
        connection = MColorConnection(self.params, attr_name)
        if connection.connected_node is not None:
            return m_file_from_color_connection(self.params, connection)

        return connection

    def add_environment_sample(self, export_root, time):
        if self.turbidity is not None:
            if self.turbidity.__class__.__name__ == 'MFile':
                self.turbidity.add_image_sample(export_root, time)


#--------------------------------------------------------------------------------------------------
# MColorConnection class.
#--------------------------------------------------------------------------------------------------

class MColorConnection():

        """ Lightweight class representing Maya color connections, although these are not Maya nodes we define an M class for ease of use"""

        def __init__(self, params, color_connection):
            self.name = color_connection
            self.safe_name = ms_commands.legalize_name(self.name)
            self.color_value = cmds.getAttr(self.name)

            if self.color_value.__class__.__name__ == 'float':
                self.color_value = (self.color_value, self.color_value, self.color_value)
            else:
                self.color_value = self.color_value[0]

            self.normalized_color = ms_commands.normalizeRGB(self.color_value)[:3]
            self.multiplier = ms_commands.normalizeRGB(self.color_value)[3]

            self.is_black = self.normalized_color == (0,0,0)
            self.connected_node = ms_commands.get_connected_node(self.name)

            if (self.normalized_color[0] == self.normalized_color[1]) and (self.normalized_color[0] == self.normalized_color[2]):
                self.is_grey = True
            else:
                self.is_grey = False

            if self.connected_node is not None:
                self.connected_node_type = cmds.nodeType(self.connected_node)


#--------------------------------------------------------------------------------------------------
# MMsMaterial class.
#--------------------------------------------------------------------------------------------------

class MMsMaterial():

    """ Lightweight class representing Maya material nodes """

    def __init__(self, params, maya_ms_material_name):
        self.params = params
        self.name = maya_ms_material_name
        self.safe_name = ms_commands.legalize_name(self.name)

        self.shading_nodes = []
        self.colors = []
        self.textures = []

        self.duplicate_shaders = cmds.getAttr(self.name + '.duplicate_front_attributes_on_back')

        self.enable_front = cmds.getAttr(self.name + '.enable_front_material')
        self.enable_back = cmds.getAttr(self.name + '.enable_back_material')

        self.bsdf_front = self.get_connections(self.name + '.BSDF_front_color')
        self.edf_front = self.get_connections(self.name + '.EDF_front_color')
        self.surface_shader_front = self.get_connections(self.name + '.surface_shader_front_color')
        self.displacement_map_front = self.get_connections(self.name + '.displacement_map_front_color')
        self.alpha_map = self.get_connections(self.name + '.alpha_map_color')
        self.displacement_mode = cmds.getAttr(self.name + '.displacement_mode')
        self.bump_amplitude = cmds.getAttr(self.name + '.bump_amplitude')
        self.normal_map_up = cmds.getAttr(self.name + '.normal_map_up')

        # only use front shaders on back if box is checked
        if not self.duplicate_shaders:
            self.bsdf_back = self.get_connections(self.name + '.BSDF_back_color')
            self.edf_back = self.get_connections(self.name + '.EDF_back_color')
            self.surface_shader_back = self.get_connections(self.name + '.surface_shader_back_color')
            self.displacement_map_back = self.get_connections(self.name + '.displacement_map_back_color')

            self.shading_nodes += [self.bsdf_front,
                                   self.bsdf_back,
                                   self.edf_front,
                                   self.edf_back,
                                   self.surface_shader_front,
                                   self.surface_shader_back]

            for texture in [self.displacement_map_front, self.displacement_map_back, self.alpha_map]:
                if texture is not None:
                    self.textures.append(texture)


        else:
            self.bsdf_back, self.edf_back, self.surface_shader_back, self.displacement_map_back = self.bsdf_front, self.edf_front, self.surface_shader_front, self.displacement_map_front

            self.shading_nodes += [self.bsdf_front,
                                   self.edf_front,
                                   self.surface_shader_front]

            if self.displacement_map_front is not None:
                  self.textures.append(self.displacement_map_front)
            if self.alpha_map is not None:
                self.textures.append(self.alpha_map)


    def get_connections(self, attr_name):
        connection = MColorConnection(self.params, attr_name)

        if connection.connected_node is None:
            return None

        if connection.connected_node_type == 'ms_appleseed_shading_node':
            shading_node = MMsShadingNode(self.params, connection.connected_node)
            self.shading_nodes = self.shading_nodes + [shading_node] + shading_node.child_shading_nodes
            self.colors += shading_node.colors
            self.textures += shading_node.textures
            return shading_node

        elif connection.connected_node_type == 'file':
            texture_node = MFile(self.params, connection.connected_node)
            self.textures += [texture_node]
            return texture_node


#--------------------------------------------------------------------------------------------------
# MGenericMaterial class.
#--------------------------------------------------------------------------------------------------

class MGenericMaterial():

    """Generic material class representing all non ms_material materials in the maya scene"""

    def __init__(self, params, maya_material_name):
        self.params = params
        self.name = maya_material_name
        self.safe_name = ms_commands.legalize_name(self.name)
        self.type = cmds.nodeType(maya_material_name)

        self.color = None
        self.alpha = None # translated to material alpha
        self.transparency = None # translated to mix between reflectivity and transmission
        self.incandescence = None
        self.glossiness = None
        self.reflectivity = None
        self.bump_map = None
        self.bump_multiplier = None
        self.refractive_index = None
        self.translucence = None

        self.textures = []

        self.export_modifiers = {}

        for attribute in ms_commands.MATERIAL_EXPORT_MODIFIERS:
            if cmds.attributeQuery(attribute[0], n=self.name, ex=True):
                if attribute[0] is not 'ms_secondary_surface_shader':
                    self.export_modifiers[attribute[0]] = cmds.getAttr('{0}.{1}'.format(self.name, attribute[0]))
                else:
                    attribute_connections = cmds.listConnections(self.name + '.ms_secondary_surface_shader')
                    if attribute_connections is not None:
                        self.export_modifiers[attribute[0]] = attribute_connections[0]

        self.secondary_surface_shader = None

        if 'ms_secondary_surface_shader' in self.export_modifiers:
            if cmds.nodeType(self.export_modifiers['ms_secondary_surface_shader']) == 'ms_appleseed_shading_node':
                if cmds.getAttr(self.export_modifiers['ms_secondary_surface_shader'] + '.node_type') is not 'surface_shader':
                    self.secondary_surface_shader = MMsShadingNode(params, self.export_modifiers['ms_secondary_surface_shader'])
                    self.textures += self.secondary_surface_shader.textures
                else:
                    ms_commands.warning('{0} is not a surface_shader'.format(self.export_modifiers['ms_secondary_surface_shader']))
            else:
                ms_commands.warning('{0} is not an ms_appleseed_shading_node'.format(self.export_modifiers['ms_secondary_surface_shader']))

        # work out color component
        if cmds.attributeQuery('color', node=self.name, exists=True):
            self.color = MColorConnection(self.params, self.name + '.color')
            if self.color.connected_node is not None:
                self.color = m_file_from_color_connection(self.params, self.color)
                self.textures.append(self.color)

        elif cmds.attributeQuery('outColor', node=self.name, exists=True):
            self.color = MColorConnection(self.params, self.name + '.outColor')
            if self.color.connected_node is not None:
                self.color = m_file_from_color_connection(self.params, self.color)
                self.textures.append(self.color)

        # work out specular components
        if cmds.attributeQuery('cosinePower', node=self.name, exists=True):
            self.glossiness = MColorConnection(self.params, self.name + '.cosinePower')
            self.glossiness.multiplier = self.glossiness.multiplier * 0.01

            if self.glossiness.connected_node is not None:
                self.glossiness = m_file_from_color_connection(self.params, self.glossiness)
                self.textures.append(self.glossiness)
            elif self.glossiness.is_black:
                self.glossiness = None

        if cmds.attributeQuery('reflectivity', node=self.name, exists=True):
            self.reflectivity = MColorConnection(self.params, self.name + '.reflectivity')
            if self.reflectivity.connected_node is not None:
                self.reflectivity = m_file_from_color_connection(self.params, self.reflectivity)
                self.textures.append(self.reflectivity)
            elif self.reflectivity.is_black:
                self.reflectivity = None

        # work out alpha / transparrency component
        if cmds.attributeQuery('transparency', node=self.name, exists=True):
            self.transparency = MColorConnection(self.params, self.name + '.transparency')
            if self.transparency.connected_node is not None:
                self.transparency = m_file_from_color_connection(self.params, self.transparency)
                self.textures.append(self.transparency)
            elif self.transparency.is_black:
                self.transparency = None

            if 'ms_transparency_is_material_alpha' in self.export_modifiers:
                if self.export_modifiers['ms_transparency_is_material_alpha']:
                    self.alpha = self.transparency
                    self.transparency = None

        # work out incandescence component
        emit_light = True

        if 'ms_emit_light' in self.export_modifiers:
            if self.export_modifiers['ms_emit_light'] == False:
                emit_light = False

        if emit_light:
            if cmds.attributeQuery('incandescence', node=self.name, exists=True):
                self.incandescence = MColorConnection(self.params, self.name + '.incandescence')
            elif cmds.attributeQuery('outColor', node=self.name, exists=True):
                self.incandescence = MColorConnection(self.params, self.name + '.outColor')

            if self.incandescence.connected_node is not None:
                self.incandescence = m_file_from_color_connection(self.params, self.incandescence)
                self.textures.append(self.incandescence)
            elif self.incandescence.is_black:
                self.incandescence = None

        # work out bump component
        if cmds.attributeQuery('normalCamera', node=self.name, exists=True):
            connected_bump_node = cmds.listConnections(self.name + '.normalCamera', s=True, type='bump2d')

            if connected_bump_node is not None:
                bump_node = connected_bump_node[0]
                bump_tex_connected_node = cmds.listConnections(bump_node + '.bumpValue', s=True, type='file')
                
                if bump_tex_connected_node is not None:
                    self.bump_multiplier = cmds.getAttr(bump_node + '.bumpDepth')
                    self.bump_map = MFile(params, bump_tex_connected_node[0])
                    self.textures.append(self.bump_map)

        # work out refractive index component
        if cmds.attributeQuery('refractiveIndex', node=self.name, exists=True):
            self.refractive_index = cmds.getAttr(self.name + '.refractiveIndex')

        # work out translucense component
        if cmds.attributeQuery('translucence', node=self.name, exists=True):
            self.translucence = MColorConnection(self.params, self.name + '.translucence')
            if self.translucence.connected_node is not None:
                self.translucence = m_file_from_color_connection(self.params, self.translucence)
                self.textures.append(self.reflectivity)
            elif self.translucence.is_black:
                self.translucence = None

#--------------------------------------------------------------------------------------------------
# MMsShadingNode class.
#--------------------------------------------------------------------------------------------------

class MMsShadingNode():

    """ Lightweight class representing Maya shading nodes """

    def __init__(self, params, maya_ms_shading_node_name):
        self.params = params
        self.name = maya_ms_shading_node_name
        self.safe_name = ms_commands.legalize_name(self.name)

        self.type = cmds.getAttr(self.name + '.node_type')    # diffuse_component, edf etc.
        self.model = cmds.getAttr(self.name + '.node_model')  # lambertian etc.

        self.child_shading_nodes = []
        self.attributes = dict()
        self.colors = []
        self.textures = []

        # add the correct attributes based on the entity defs xml
        for attribute_key in params['entity_defs'][self.model].attributes.keys():
            self.attributes[attribute_key] = ''

        for attribute_key in self.attributes.keys():
            maya_attribute = self.name + '.' + attribute_key

            # if the attribute is a color/entity
            entity_type = params['entity_defs'][self.model].attributes[attribute_key].type
            if (entity_type == 'colormap') or (entity_type == 'entity'):
                color_connection = MColorConnection(self.params, maya_attribute)

                if color_connection.connected_node:
                    # if the node is an appleseed shading node
                    if color_connection.connected_node_type == 'ms_appleseed_shading_node':
                        shading_node = MMsShadingNode(self.params, color_connection.connected_node)
                        self.attributes[attribute_key] = shading_node
                        self.child_shading_nodes += [shading_node] + shading_node.child_shading_nodes
                        self.colors += shading_node.colors
                        self.textures += shading_node.textures

                    # else if it's a Maya texture node
                    elif color_connection.connected_node_type == 'file':
                        texture_node = MFile(self.params, color_connection.connected_node)
                        self.attributes[attribute_key] = texture_node
                        self.textures += [texture_node]

                # no node is connected, just use the color value
                else:
                    self.attributes[attribute_key] = color_connection

            # the attribute is a string or an item from a drop-down list
            else:
                self.attributes[attribute_key] = str(cmds.getAttr(maya_attribute))


#--------------------------------------------------------------------------------------------------
# AsParameter class.
#--------------------------------------------------------------------------------------------------

class AsParameter():

    """ Class representing an appleseed Parameter entity """

    def __init__(self, name=None, value=None):
        self.name = name
        self.value = value

    def as_normalized_path(self):
        return AsParameter(self.name, ms_commands.normalize_path(self.value))

    def emit_xml(self, doc):
        if self.value is not None:
            value_string = str(self.value)
            if len(value_string) > 0:
                doc.append_parameter(self.name, value_string)


#--------------------------------------------------------------------------------------------------
# AsParameters class.
#--------------------------------------------------------------------------------------------------

class AsParameters():

    """ Class representing an appleseed Parameters entity """

    def __init__(self, name=None):
        self.name = name
        self.parameters = []

    def as_normalized_path(self):
        result = AsParameters(self.name)
        for parameter in self.parameters:
            result.parameters.append(parameter.as_normalized_path())
        return result

    def emit_xml(self, doc):
        doc.start_element('parameters name="%s"' % self.name)
        for parameter in self.parameters:
            parameter.emit_xml(doc)
        doc.end_element('parameters')


#--------------------------------------------------------------------------------------------------
# AsColor class.
#--------------------------------------------------------------------------------------------------

class AsColor():

    """ Class representing an appleseed Color entity """

    def __init__(self):
        self.name = None
        self.RGB_color = [0.5, 0.5, 0.5]
        self.alpha = 1.0
        self.multiplier = AsParameter('multiplier', '1.0')
        self.color_space = AsParameter('color_space', 'srgb')

    def emit_xml(self, doc):
        doc.start_element('color name="%s"' % self.name)
        self.color_space.emit_xml(doc)
        self.multiplier.emit_xml(doc)

        doc.start_element('values')
        doc.append_line('%.6f %.6f %.6f' % (self.RGB_color[0], self.RGB_color[1], self.RGB_color[2]))
        doc.end_element('values')

        doc.start_element('alpha')
        doc.append_line('%.6f' % self.alpha)
        doc.end_element('alpha')

        doc.end_element('color')


#--------------------------------------------------------------------------------------------------
# AsTransform class.
#--------------------------------------------------------------------------------------------------

class AsTransform():

    """ Class representing an appleseed Transform entity """

    def __init__(self):
        self.time = 0.0
        self.scaling_value = 1.0
        self.matrices = []

    def emit_xml(self, doc):
        doc.start_element('transform time="%f"' % self.time)

        if self.scaling_value != 1.0:
            doc.append_element('scaling value="%s"' % self.scaling_value)

        for matrix in reversed(self.matrices):
            doc.start_element('matrix')
            doc.append_line('%.15f %.15f %.15f %.15f' % (matrix[0], matrix[4], matrix[8],  matrix[12]))
            doc.append_line('%.15f %.15f %.15f %.15f' % (matrix[1], matrix[5], matrix[9],  matrix[13]))
            doc.append_line('%.15f %.15f %.15f %.15f' % (matrix[2], matrix[6], matrix[10], matrix[14]))
            doc.append_line('%.15f %.15f %.15f %.15f' % (matrix[3], matrix[7], matrix[11], matrix[15]))
            doc.end_element('matrix')

        doc.end_element('transform')


#--------------------------------------------------------------------------------------------------
# AsTexture class.
#--------------------------------------------------------------------------------------------------

class AsTexture():

    """ Class representing an appleseed Texture entity """

    def __init__(self):
        self.name = None
        self.model = 'disk_texture_2d'
        self.color_space = AsParameter('color_space', 'srgb')
        self.file_name = None
        self.instances = []

    def instantiate(self):
        texture_instance = AsTextureInstance(self)
        self.instances.append(texture_instance)
        return texture_instance

    def emit_xml(self, doc):
        doc.start_element('texture name="%s" model="%s"' % (self.name, self.model))
        self.color_space.emit_xml(doc)
        self.file_name.as_normalized_path().emit_xml(doc)
        doc.end_element('texture')


#--------------------------------------------------------------------------------------------------
# AsTextureInstance class.
#--------------------------------------------------------------------------------------------------

class AsTextureInstance():

    """ Class representing an appleseed Texture Instance entity """

    def __init__(self, as_texture):
        self.name = '%s_instance_%i' % (as_texture.name, len(as_texture.instances))
        self.texture = as_texture
        self.addressing_mode = AsParameter('addressing_mode', 'wrap')
        self.filtering_mode = AsParameter('filtering_mode', 'bilinear')
        self.alpha_mode = AsParameter('alpha_mode', 'alpha_channel')

    def emit_xml(self, doc):
        doc.start_element('texture_instance name="%s" texture="%s"' % (self.name, self.texture.name))
        self.addressing_mode.emit_xml(doc)
        self.filtering_mode.emit_xml(doc)
        self.alpha_mode.emit_xml(doc)
        doc.end_element('texture_instance')


#--------------------------------------------------------------------------------------------------
# AsObject class.
#--------------------------------------------------------------------------------------------------

class AsObject():

    """ Class representing appleseed Object entity """

    def __init__(self):
        self.name = None
        self.name_in_obj = None
        self.model = 'mesh_object'
        self.file_names = None
        self.instances = []
        self.has_deformation = False

    def instantiate(self):
        object_instance = AsObjectInstance(self)
        self.instances.append(object_instance)
        return object_instance

    def emit_xml(self, doc):
        doc.start_element('object name="%s" model="%s"' % (self.name, self.model))
        self.file_names.as_normalized_path().emit_xml(doc)
        doc.end_element('object')


#--------------------------------------------------------------------------------------------------
# AsObjectInstanceMaterialAssignment class.
#--------------------------------------------------------------------------------------------------

class AsObjectInstanceMaterialAssignment():

    """ Class representing appleseed Object Instance Material Assignment entity """

    def __init__(self, slot=None, side=None, material=None):
        self.slot = slot
        self.side = side
        self.material = material

    def emit_xml(self, doc):
        doc.append_element('assign_material slot="%s" side="%s" material="%s"' % (self.slot, self.side, self.material))


#--------------------------------------------------------------------------------------------------
# AsObjectInstance class.
#--------------------------------------------------------------------------------------------------

class AsObjectInstance():

    """ Class representing appleseed Object Instance entity """

    def __init__(self, as_object):
        self.name = self.name = '%s_instance_%i' % (as_object.name, len(as_object.instances))
        self.object = as_object
        self.transforms = []
        self.material_assignments = []

    def emit_xml(self, doc):
        doc.start_element('object_instance name="%s" object="%s.0"' % (self.name, self.object.name))
        for transform in self.transforms:
            transform.emit_xml(doc)
        for material_assignment in self.material_assignments:
            material_assignment.emit_xml(doc)
        doc.end_element('object_instance')


#--------------------------------------------------------------------------------------------------
# AsCamera class.
#--------------------------------------------------------------------------------------------------

class AsCamera():

    """ Class representing appleseed Camera entity """

    def __init__(self):
        self.name = None
        self.model = None
        self.film_dimensions = None
        self.focal_length = None
        self.focal_distance = None
        self.f_stop = None
        self.diaphragm_blades = AsParameter('diaphragm_blades', '0')
        self.diaphragm_tilt_angle = AsParameter('diaphragm_tilt_angle', '0.0')
        self.shutter_open_time = AsParameter('shutter_open_time', '0.0')
        self.shutter_close_time = AsParameter('shutter_close_time', '1.0')
        self.controller_target = AsParameter('controller_target', '0 0 0')
        self.transforms = []

    def emit_xml(self, doc):
        doc.start_element('camera name="%s" model="%s"' % (self.name, self.model))

        self.film_dimensions.emit_xml(doc)
        self.focal_length.emit_xml(doc)
        self.shutter_open_time.emit_xml(doc)
        self.shutter_close_time.emit_xml(doc)
        self.controller_target.emit_xml(doc)

        if self.model == 'thinlens_camera':
            self.focal_distance.emit_xml(doc)
            self.diaphragm_blades.emit_xml(doc)
            self.diaphragm_tilt_angle.emit_xml(doc)
            self.f_stop.emit_xml(doc)

        for transform in self.transforms:
            transform.emit_xml(doc)

        doc.end_element('camera')


#--------------------------------------------------------------------------------------------------
# AsEnvironment class.
#--------------------------------------------------------------------------------------------------

class AsEnvironment():

    """ Class representing appleseed Environment entity """

    def __init__(self):
        self.name = None
        self.environment_shader = None
        self.environment_edf = None

    def emit_xml(self, doc):
        doc.start_element('environment name="%s" model="generic_environment"' % self.name)
        if self.environment_shader is not None:
            self.environment_shader.emit_xml(doc)
        self.environment_edf.emit_xml(doc)
        doc.end_element('environment')


#--------------------------------------------------------------------------------------------------
# AsEnvironmentShader class.
#--------------------------------------------------------------------------------------------------

class AsEnvironmentShader():

    """ Class representing appleseed Environment Shader entity """

    def __init__(self):
        self.name = None
        self.edf = None
        self.parameters = []

    def emit_xml(self, doc):
        doc.start_element('environment_shader name="%s" model="edf_environment_shader"' % self.name)
        self.edf.emit_xml(doc)
        for parameter in self.parameters:
            parameter.emit_xml(doc)
        doc.end_element('environment_shader')


#--------------------------------------------------------------------------------------------------
# AsEnvironmentEdf class.
#--------------------------------------------------------------------------------------------------

class AsEnvironmentEdf():

    """ Class representing appleseed Environment EDF entity """

    def __init__(self):
        self.name = None
        self.model = None
        self.parameters = []

    def emit_xml(self, doc):
        doc.start_element('environment_edf name="%s" model="%s"' % (self.name, self.model))
        for parameter in self.parameters:
            parameter.emit_xml(doc)
        doc.end_element('environment_edf')


#--------------------------------------------------------------------------------------------------
# AsMaterial class.
#--------------------------------------------------------------------------------------------------

class AsMaterial():

    """ Class representing appleseed Material entity """

    def __init__(self):
        self.name = None
        self.model = 'generic_material'
        self.bsdf = None
        self.edf = None
        self.surface_shader = None
        self.alpha_map = None
        self.displacement_map = None
        self.displacement_mode = None
        self.bump_amplitude = None
        self.normal_map_up = None

    def emit_xml(self, doc):
        doc.start_element('material name="%s" model="%s"' % (self.name, self.model))

        if self.bsdf is not None:
            self.bsdf.emit_xml(doc)

        if self.edf is not None:
            self.edf.emit_xml(doc)

        if self.surface_shader is not None:
            self.surface_shader.emit_xml(doc)

        if self.alpha_map is not None:
            self.alpha_map.emit_xml(doc)

        if self.displacement_map is not None:
            self.displacement_map.emit_xml(doc)

        if self.displacement_mode is not None:
            self.displacement_mode.emit_xml(doc)

        if self.bump_amplitude is not None:
            self.bump_amplitude.emit_xml(doc)

        if self.normal_map_up is not None:
            self.normal_map_up.emit_xml(doc)

        doc.end_element('material')


#--------------------------------------------------------------------------------------------------
# AsBsdf class.
#--------------------------------------------------------------------------------------------------

class AsBsdf():

    """ Class representing appleseed BSDF entity """

    def __init__(self):
        self.name = None
        self.model = None
        self.parameters = []

    def emit_xml(self, doc):
        doc.start_element('bsdf name="%s" model="%s"' % (self.name, self.model))
        for parameter in self.parameters:
            parameter.emit_xml(doc)
        doc.end_element('bsdf')


#--------------------------------------------------------------------------------------------------
# AsEdf class.
#--------------------------------------------------------------------------------------------------

class AsEdf():

    """ Class representing appleseed EDF entity """

    def __init__(self):
        self.name = None
        self.model = None
        self.parameters = []

    def emit_xml(self, doc):
        doc.start_element('edf name="%s" model="%s"' % (self.name, self.model))
        for parameter in self.parameters:
            parameter.emit_xml(doc)
        doc.end_element('edf')


#--------------------------------------------------------------------------------------------------
# AsSurfaceShader class.
#--------------------------------------------------------------------------------------------------

class AsSurfaceShader():

    """ Class representing appleseed Surface Shader entity """

    def __init__(self):
        self.name = None
        self.model = None
        self.parameters = []

    def emit_xml(self, doc):
        doc.start_element('surface_shader name="%s" model="%s"' % (self.name, self.model))
        for parameter in self.parameters:
            parameter.emit_xml(doc)
        doc.end_element('surface_shader')


#--------------------------------------------------------------------------------------------------
# AsLight class.
#--------------------------------------------------------------------------------------------------

class AsLight():

    """ Class representing appleseed Light entity """

    def __init__(self):
        self.name = None
        self.model = None
        self.exitance = None
        self.exitance_multiplier = AsParameter('exitance_multiplier', 1)
        self.inner_angle = None
        self.outer_angle = None
        self.transform = None
        self.parameters = []

    def emit_xml(self, doc):
        doc.start_element('light name="%s" model="%s"' % (self.name, self.model))
        if self.exitance is not None:
            self.exitance.emit_xml(doc)
        self.exitance_multiplier.emit_xml(doc)
        if self.model == 'spot_light':
            self.inner_angle.emit_xml(doc)
            self.outer_angle.emit_xml(doc)
        for param in self.parameters:
            param.emit_xml(doc)
        if self.transform is not None:
            self.transform.emit_xml(doc)
        doc.end_element('light')


#--------------------------------------------------------------------------------------------------
# AsAssembly class.
#--------------------------------------------------------------------------------------------------

class AsAssembly():

    """ Class representing appleseed Assembly entity """

    def __init__(self, parent_assembly):
        self.parent_assembly = parent_assembly
        self.name = None
        self.colors = []
        self.textures = []
        self.texture_instances = []
        self.materials = []
        self.bsdfs = []
        self.edfs = []
        self.surface_shaders = []
        self.lights = []
        self.objects = []
        self.object_instances = []
        self.assemblies = []
        self.assembly_instances = []

        self.raw_xml = ''

        self.instances = []

    def instantiate(self):
        assembly_instance = AsAssemblyInstance(self)
        self.instances.append(assembly_instance)
        return assembly_instance

    def emit_xml(self, doc):
        doc.start_element('assembly name="%s"' % self.name)

        for color in self.colors:
            color.emit_xml(doc)

        for texture in self.textures:
            texture.emit_xml(doc)

        for texture_instance in self.texture_instances:
            texture_instance.emit_xml(doc)

        for bsdf in self.bsdfs:
            bsdf.emit_xml(doc)

        for edf in self.edfs:
            edf.emit_xml(doc)

        for surface_shader in self.surface_shaders:
            surface_shader.emit_xml(doc)

        for light in self.lights:
            light.emit_xml(doc)

        for material in self.materials:
            material.emit_xml(doc)

        for object in self.objects:
            object.emit_xml(doc)

        for assembly in self.assemblies:
            assembly.emit_xml(doc)

        for object_instance in self.object_instances:
            object_instance.emit_xml(doc)

        for assembly_instance in self.assembly_instances:
            assembly_instance.emit_xml(doc)

        if not self.raw_xml == '':
            for line in self.raw_xml.split('\n'):
                doc.append_line(line)

        doc.end_element('assembly')


#--------------------------------------------------------------------------------------------------
# AsAssemblyInstance class.
#--------------------------------------------------------------------------------------------------

class AsAssemblyInstance():

    """ Class representing appleseed Assembly Instance entity """

    def __init__(self, as_assembly):
        self.name = '%s_instance_%i' % (as_assembly.name, len(as_assembly.instances))
        self.assembly = as_assembly
        self.transforms = []

    def emit_xml(self, doc):
        doc.start_element('assembly_instance name="%s" assembly="%s"' % (self.name, self.assembly.name))
        for transform in self.transforms:
            transform.emit_xml(doc)
        doc.end_element('assembly_instance')


#--------------------------------------------------------------------------------------------------
# AsRules class.
#--------------------------------------------------------------------------------------------------

class AsRules():

    """ Class representing appleseed Rules entity """

    def __init__(self):
        self.rules = []

    def emit_xml(self, doc):
        doc.start_element('rules')
        for rule in self.rules:
            rule.emit_xml(doc)
        doc.end_element('rules')


#--------------------------------------------------------------------------------------------------
# AsRenderLayerAssignment class.
#--------------------------------------------------------------------------------------------------

class AsRenderLayerAssignment():

    """ Class representing appleseed RenderLayerAssignment entity """

    def __init__(self, name, model):
        self.name = name
        self.model = model
        self.parameters = []

    def emit_xml(self, doc):
        doc.start_element('render_layer_assignment name="{0}" model="{1}"'.format(self.name, self.model))
        for param in self.parameters:
            param.emit_xml(doc)
        doc.end_element('render_layer_assignment')


#--------------------------------------------------------------------------------------------------
# AsFrame class.
#--------------------------------------------------------------------------------------------------

class AsFrame():

    """ Class representing appleseed Frame entity """

    def __init__(self):
        self.name = 'beauty'
        self.camera = None
        self.color_space = AsParameter('color_space', 'linear_rgb')
        self.resolution = None
        self.premultiplied_alpha = AsParameter('premultiplied_alpha', 'true')
        self.tile_size = None

    def emit_xml(self, doc):
        doc.start_element('frame name="%s"' % self.name)
        self.camera.emit_xml(doc)
        self.color_space.emit_xml(doc)
        self.resolution.emit_xml(doc)
        self.premultiplied_alpha.emit_xml(doc)
        self.tile_size.emit_xml(doc)
        doc.end_element('frame')


#--------------------------------------------------------------------------------------------------
# AsOutput class.
#--------------------------------------------------------------------------------------------------

class AsOutput():

    """ Class representing appleseed Output entity """

    def __init__(self):
        self.frames = []

    def emit_xml(self, doc):
        doc.start_element('output')
        for frame in self.frames:
            frame.emit_xml(doc)
        doc.end_element('output')


#--------------------------------------------------------------------------------------------------
# AsConfiguration class.
#--------------------------------------------------------------------------------------------------

class AsConfiguration():

    """ Class representing appleseed Configuration entity """

    def  __init__(self):
        self.name = None
        self.base = None
        self.parameters = []

    def emit_xml(self, doc):
        doc.start_element('configuration name="%s" base="%s"' % (self.name, self.base))
        for parameter in self.parameters:
            parameter.emit_xml(doc)
        doc.end_element('configuration')


#--------------------------------------------------------------------------------------------------
# AsConfigurations class.
#--------------------------------------------------------------------------------------------------

class AsConfigurations():

    """ Class representing appleseed Configurations entity """

    def __init__(self):
        self.configurations = []

    def emit_xml(self, doc):
        doc.start_element('configurations')
        for configuration in self.configurations:
            configuration.emit_xml(doc)
        doc.end_element('configurations')


#--------------------------------------------------------------------------------------------------
# AsScene class.
#--------------------------------------------------------------------------------------------------

class AsScene():

    """ Class representing appleseed Scene entity """

    def __init__(self):
        self.cameras = None
        self.colors = []
        self.textures = []
        self.texture_instances = []
        self.environment_edfs = []
        self.environment_shaders = []
        self.environment = None
        self.output = None
        self.configurations = None
        self.assemblies = []
        self.assembly_instances = []
        self.parameters = []

    def emit_xml(self, doc):
        doc.start_element('scene')

        for parameter in self.parameters:
            parameter.emit_xml(doc)

        self.camera.emit_xml(doc)

        for color in self.colors:
            color.emit_xml(doc)

        for texture in self.textures:
            texture.emit_xml(doc)

        for texture_instance in self.texture_instances:
            texture_instance.emit_xml(doc)

        for environment_edf in self.environment_edfs:
            environment_edf.emit_xml(doc)

        for environment_shader in self.environment_shaders:
            environment_shader.emit_xml(doc)

        if self.environment is not None:
            self.environment.emit_xml(doc)

        if self.output is not None:
            self.output.emit_xml(doc)

        if self.configurations is not None:
            self.configurations.emit_xml(doc)

        for assembly in self.assemblies:
            assembly.emit_xml(doc)

        for assembly_instance in self.assembly_instances:
            assembly_instance.emit_xml(doc)

        doc.end_element('scene')


#--------------------------------------------------------------------------------------------------
# AsProject class.
#--------------------------------------------------------------------------------------------------

class AsProject():

    """ Class representing appleseed Project entity """

    def __init__(self):
        self.scene = None
        self.output = None
        self.rules = None
        self.configurations = None

    def emit_xml(self, doc):
        doc.start_element('project')
        self.scene.emit_xml(doc)
        self.output.emit_xml(doc)
        self.rules.emit_xml(doc)
        self.configurations.emit_xml(doc)
        doc.end_element('project')


#--------------------------------------------------------------------------------------------------
# fetch_m_camera function.
#--------------------------------------------------------------------------------------------------

def fetch_m_camera(m_transform, maya_camera_name):

    # check if any direct children are the camera were looking for
    for camera in m_transform.child_cameras:
        if camera.name == maya_camera_name:
            return camera

    # if not found recursively check any child transform to see if they own the camera
    for transform in m_transform.child_transforms:
        camera = fetch_m_camera(transform, maya_camera_name)
        if camera is not None:
            return camera

    return None


#--------------------------------------------------------------------------------------------------
# m_color_connection_to_as_color function.
#--------------------------------------------------------------------------------------------------

def m_color_connection_to_as_color(m_color_connection, postfix=''):

    as_color = AsColor()
    as_color.name = m_color_connection.safe_name + postfix
    as_color.RGB_color = m_color_connection.normalized_color
    as_color.multiplier.value = m_color_connection.multiplier

    return as_color


#--------------------------------------------------------------------------------------------------
# m_file_to_as_texture function.
#--------------------------------------------------------------------------------------------------

def m_file_to_as_texture(params, m_file, postfix='', file_number=0):

    as_texture = AsTexture()
    as_texture.name = m_file.safe_name + postfix
    if m_file.is_animated:
        as_texture.file_name = AsParameter('filename', m_file.image_file_names[file_number])
    else:
        as_texture.file_name = AsParameter('filename', m_file.image_file_names[0])

    as_texture_instance = as_texture.instantiate()
    if m_file.autodetect_alpha:
        as_texture_instance.alpha_mode.value = 'detect'
    else:
        if m_file.alpha_is_luminance:
            as_texture_instance.alpha_mode.value = 'luminance'

    if params['force_linear_texture_interpretation']:
        as_texture.color_space.value = 'linear_rgb'

    if m_file.filtering_mode == 'Off':
        as_texture_instance.filtering_mode.value = 'nearest'

    return as_texture, as_texture_instance


#--------------------------------------------------------------------------------------------------
# traslate_maya_scene function.
#--------------------------------------------------------------------------------------------------

def translate_maya_scene(params, maya_scene, maya_environment):

    """ Main function for converting a cached Maya scene into an appleseed object hierarchy """

    # create dict for storing appleseed object models into
    # the key will be the file path to save the project too
    as_object_models = []

    # initialize frame list with single default value
    frame_list = [int(cmds.currentTime(query=True))]

    # compute the base output directory
    scene_filepath = cmds.file(q=True, sceneName=True)
    scene_basename = os.path.splitext(os.path.basename(scene_filepath))[0]
    if len(scene_basename) == 0:
        scene_basename = "Untitled"
    project_directory = cmds.workspace(q=True, rd=True)
    params['output_directory'] = params['output_directory'].replace("<ProjectDir>", project_directory)
    params['output_directory'] = params['output_directory'].replace("<SceneName>", scene_basename)

    # compute the output file path
    base_file_name = params['file_name']
    base_file_name = params['file_name'].replace("<SceneName>", scene_basename)

    # if animation export is on populate frame list with correct frame numbers
    if params['export_animation']:
        frame_list = range(params['animation_start_frame'], params['animation_end_frame'] + 1)

    cmds.progressWindow(e=True, status='Translating maya scene', progress=0, max=len(frame_list))
    cmds.refresh(cv=True)

    for i, frame_number in enumerate(frame_list):

        check_export_cancelled()

        ms_commands.info("Exporting frame %i..." % frame_number)

        # mb_sample_number is list of indices that should be iterated over in the cached Maya scene for objects with motion blur
        # if animation export is turned off it should be initialised to the first sample
        mb_sample_number_list = range(params['motion_samples'])

        non_mb_sample_number = None
        if params['export_animation']:
            non_mb_sample_number = frame_number - params['animation_start_frame']
        else:
            non_mb_sample_number = 0

        # if animation export is turned on set the sample list according to the current frame and the sample count
        if params['export_animation']:
            mb_sample_number_list = range(params['motion_samples'])
            for i in range(params['motion_samples']):
                mb_sample_number_list[i] += (frame_number - params['animation_start_frame']) * (params['motion_samples'] - 1)

        # begin construction of as object hierarchy *************************************************

        as_project = AsProject()

        # create output and frame objects
        as_output = AsOutput()
        as_project.output = as_output
        as_frame = AsFrame()
        as_output.frames.append(as_frame)
        # note: frame camera is set when the camera is retrieved for the scene element
        as_frame.resolution = AsParameter('resolution', '%i %i' % (params['output_res_width'], params['output_res_height']))
        as_frame.color_space.value = params['output_color_space']

        if params['export_straight_alpha']:
            as_frame.premultiplied_alpha.value = 'false'

        as_frame.tile_size = AsParameter('tile_size', '{0} {1}'.format(params['tile_width'], params['tile_height']))

        # create render layers

        as_rules = AsRules()
        as_project.rules = as_rules

        for i, layer in enumerate(params['render_layers']):
            render_layer_assignment = AsRenderLayerAssignment('{0}_{1}'.format(layer['name'], i), layer['model'])
            render_layer_assignment.parameters.append(AsParameter('render_layer', layer['name']))
            render_layer_assignment.parameters.append(AsParameter('entity_type', layer['type']))
            render_layer_assignment.parameters.append(AsParameter('pattern', layer['pattern']))
            render_layer_assignment.parameters.append(AsParameter('order', layer['order']))
            as_rules.rules.append(render_layer_assignment)

        # create configurations object
        as_configurations = AsConfigurations()
        as_project.configurations = as_configurations

        # create interactive config
        interactive_config = AsConfiguration()
        as_configurations.configurations.append(interactive_config)
        interactive_config.name = 'interactive'
        interactive_config.base = 'base_interactive'

        # create final config
        final_config = AsConfiguration()
        as_configurations.configurations.append(final_config)
        final_config.name = 'final'
        final_config.base = 'base_final'

        for config in [interactive_config, final_config]:
            enable_importance_sampling_parameters = AsParameters('light_sampler')
            enable_importance_sampling_parameters.parameters.append(AsParameter('enable_importance_sampling', params['enable_importance_sampling']))
            config.parameters.append(enable_importance_sampling_parameters)

            config.parameters.append(AsParameter('lighting_engine', 'pt'))
            config.parameters.append(AsParameter('pixel_renderer', params['sampler']))

            adaptive_pixel_renderer_params = AsParameters('adaptive_pixel_renderer')
            adaptive_pixel_renderer_params.parameters.append(AsParameter('min_samples', params['adaptive_min_samples']))
            adaptive_pixel_renderer_params.parameters.append(AsParameter('max_samples', params['adaptive_max_samples']))
            adaptive_pixel_renderer_params.parameters.append(AsParameter('quality', params['adaptive_quality']))
            config.parameters.append(adaptive_pixel_renderer_params)

            uniform_pixel_renderer_params = AsParameters('uniform_pixel_renderer')
            uniform_pixel_renderer_params.parameters.append(AsParameter('samples', params['uniform_samples']))
            uniform_pixel_renderer_params.parameters.append(AsParameter('decorrelate_pixels', params['uniform_decorrelate_pixels']))
            config.parameters.append(uniform_pixel_renderer_params)

            pt_params = AsParameters('pt')
            pt_params.parameters.append(AsParameter('dl_light_samples', params['pt_light_samples']))
            pt_params.parameters.append(AsParameter('enable_caustics', params['pt_caustics']))
            pt_params.parameters.append(AsParameter('enable_dl', params['pt_direct_lighting']))
            pt_params.parameters.append(AsParameter('enable_ibl', params['pt_ibl']))
            pt_params.parameters.append(AsParameter('ibl_env_samples', params['pt_environment_samples']))
            pt_params.parameters.append(AsParameter('max_path_length', params['pt_max_bounces']))
            pt_params.parameters.append(AsParameter('next_event_estimation', params['pt_next_event_estimation']))

            if params['pt_max_ray_intensity'] > 0:
                pt_params.parameters.append(AsParameter('max_ray_intensity', params['pt_max_ray_intensity']))                

            config.parameters.append(pt_params)

        # begin scene object
        as_project.scene = AsScene()

        # create bouding box scene parameter

        bb = cmds.ls(type='mesh')
        if len(bb) > 0:
            bounding_box = cmds.exactWorldBoundingBox(bb)
            bounding_box_string = str(bounding_box[0])
            for item in bounding_box[1:]:
                bounding_box_string += ' %.15f' % item

            as_project.scene.parameters.append(AsParameter('bounding_box', bounding_box_string))

        # define root assembly
        root_assembly = AsAssembly(None)

        # if present add the environment
        if maya_environment is not None:

            environment = AsEnvironment()
            environment.name = maya_environment.safe_name

            environment_edf = AsEnvironmentEdf()
            environment_edf.name = maya_environment.safe_name + '_edf'
            environment_edf.model = maya_environment.model
            environment.environment_edf = AsParameter('environment_edf', environment_edf.name)

            if maya_environment.__class__.__name__ == 'MMsPhysicalEnvironment':
                environment_edf.model = maya_environment.model
                environment_edf.parameters.append(AsParameter('ground_albedo' , maya_environment.ground_albedo))
                environment_edf.parameters.append(AsParameter('horizon_shift' , maya_environment.horizon_shift))
                environment_edf.parameters.append(AsParameter('luminance_multiplier' , maya_environment.luminance_multiplier))
                environment_edf.parameters.append(AsParameter('saturation_multiplier' , maya_environment.saturation_multiplier))
                environment_edf.parameters.append(AsParameter('luminance_gamma' , maya_environment.luminance_gamma))
                environment_edf.parameters.append(AsParameter('sun_phi' , maya_environment.sun_phi))
                environment_edf.parameters.append(AsParameter('sun_theta' , maya_environment.sun_theta))
                environment_edf.parameters.append(AsParameter('turbidity_multiplier' , maya_environment.turbidity_multiplier))

                if maya_environment.turbidity.__class__.__name__ == 'MFile':
                    turbidity_file, turbidity_file_instance = m_file_to_as_texture(params, maya_environment.turbidity, '_texture', non_mb_sample_number)
                    as_project.scene.textures.append(turbidity_file)
                    as_project.scene.texture_instances.append(turbidity_file_instance)
                    turbidity_param = AsParameter('exitance', turbidity_file_instance.name)
                    environment_edf.parameters.append(turbidity_param)
                else:
                    turbidity_color = m_color_connection_to_as_color(maya_environment.turbidity, '_turbidity')
                    turbidity_param = AsParameter('turbidity', turbidity_color.name)
                    environment_edf.parameters.append(turbidity_param)
                    as_project.scene.colors.append(turbidity_color)

                if maya_environment.create_physical_sun:
                    light = AsLight()
                    light.name = 'physical_sun_light'
                    light.model = 'sun_light'
                    light.parameters.append(AsParameter('environment_edf', environment_edf.name))
                    light.parameters.append(AsParameter('radiance_multiplier', maya_environment.physical_sun_multiplier))
                    light.parameters.append(turbidity_param)
                    root_assembly.lights.append(light)

            else:
                # environment must be generic
                if environment_edf.model == 'constant_environment_edf':
                    constant_environment_color = m_color_connection_to_as_color(maya_environment.constant_exitance, '_constant_exitance')
                    environment_edf.parameters.append(AsParameter('exitance', constant_environment_color.name))
                    as_project.scene.colors.append(constant_environment_color)

                elif environment_edf.model == 'gradient_environment_edf':
                    gradient_horizon_exitance = m_color_connection_to_as_color(maya_environment.gradient_horizon_exitance, '_horizon_exitance')
                    environment_edf.parameters.append(AsParameter('horizon_exitance', gradient_horizon_exitance.name))
                    as_project.scene.colors.append(gradient_horizon_exitance)

                    zenith_horizon_exitance = m_color_connection_to_as_color(maya_environment.gradient_zenith_exitance, '_zenith_exitance')
                    environment_edf.parameters.append(AsParameter('zenith_exitance', zenith_horizon_exitance.name))
                    as_project.scene.colors.append(zenith_horizon_exitance)

                elif environment_edf.model == 'latlong_map_environment_edf':
                    lat_long_map, lat_long_map_instance = m_file_to_as_texture(params, maya_environment.latitude_longitude_exitance, '_texture', non_mb_sample_number)                
                    
                    as_project.scene.textures.append(lat_long_map)
                    as_project.scene.texture_instances.append(lat_long_map_instance)

                    environment_edf.parameters.append(AsParameter('exitance', lat_long_map_instance.name))

                elif environment_edf.model == 'mirrorball_map_environment_edf':
                    mirror_ball_map, mirror_ball_map_instance = m_file_to_as_texture(params, maya_environment.mirrorball_exitance, '_texture', non_mb_sample_number)
                    
                    as_project.scene.textures.append(mirror_ball_map)
                    as_project.scene.texture_instances.append(mirror_ball_map_instance)

                    environment_edf.parameters.append(AsParameter('exitance', mirror_ball_map_instance.name))

                environment_edf.parameters.append(AsParameter('exitance_multiplier', str(maya_environment.exitance_multiplier)))

            if params['render_sky']:
                environment_shader = AsEnvironmentShader()
                environment_shader.name = maya_environment.safe_name + '_shader'
                environment_shader.edf = AsParameter('environment_edf', environment_edf.name)
                environment.environment_shader = AsParameter('environment_shader', environment_shader.name)
                as_project.scene.environment_shaders.append(environment_shader)

            as_project.scene.environment = environment
            as_project.scene.environment_edfs.append(environment_edf)

        # retrieve camera from Maya scene cache and create as camera
        camera = None
        for transform in maya_scene:
            camera = fetch_m_camera(transform, params['output_camera'])
            if camera is not None:
                break
        if camera == None:
            ms_commands.error('Camera not found: ' +  params['output_camera'])

        # set camera parameter in as frame
        as_frame.camera = AsParameter('camera', camera.safe_name)

        # generic camera settings
        as_camera = AsCamera()
        as_camera.name = camera.safe_name
        as_camera.film_dimensions = AsParameter('film_dimensions', '%f %f' % (camera.film_width, camera.film_height))
        as_camera.focal_length = AsParameter('focal_length', camera.focal_length_values[non_mb_sample_number])
        as_camera.shutter_open_time.value = params['shutter_open_time']
        as_camera.shutter_close_time.value = params['shutter_close_time']

        # dof specific camera settings
        if camera.dof or params['export_all_cameras_as_thin_lens']:
            as_camera.model = 'thinlens_camera'
            as_camera.focal_distance = AsParameter('focal_distance', camera.focal_distance_values[non_mb_sample_number])
            as_camera.f_stop = AsParameter('f_stop', camera.f_stop)
        else:
            as_camera.model = 'pinhole_camera'

        # create sample number list
        if params['export_camera_blur']:
            camera_sample_number_list = mb_sample_number_list
        else:
            camera_sample_number_list = [non_mb_sample_number]

        # add transforms
        sample_index = 0
        sample_count = len(camera_sample_number_list)
        time_increment = 1.0 / (sample_count - 1) if sample_count > 1 else 1.0
        for sample_number in camera_sample_number_list:
            as_transform = AsTransform()
            as_transform.time = sample_index * time_increment
            as_transform.matrices.append(camera.world_space_matrices[sample_number])
            as_camera.transforms.append(as_transform)
            sample_index += 1

        as_project.scene.camera = as_camera

        # construct assembly hierarchy
        # root assembly is defined earlier to let the environment sun light have access to it
        root_assembly.name = 'root_assembly'
        as_project.scene.assemblies.append(root_assembly)
        root_assembly_instance = root_assembly.instantiate()
        root_assembly_instance.transforms.append(AsTransform())
        as_project.scene.assembly_instances.append(root_assembly_instance)

        # create default materials
        default_material = AsMaterial()
        default_material.name = 'as_default_material'
        default_material.alpha_map = AsParameter('alpha_map', '0')

        # clear surface shader
        default_clear_surface_shader = AsSurfaceShader()
        default_clear_surface_shader.name = 'as_default_clear_surface_shader'
        default_clear_surface_shader.model = 'constant_surface_shader'
        default_clear_surface_shader.parameters.append(AsParameter('color', '0'))
        default_clear_surface_shader.parameters.append(AsParameter('alpha_multiplier', '0'))
        root_assembly.surface_shaders.append(default_clear_surface_shader)

        # physical surface_shader
        default_physical_surface_shader = AsSurfaceShader()
        default_physical_surface_shader.name = 'as_default_physical_surface_shader'
        default_physical_surface_shader.model = 'physical_surface_shader'
        root_assembly.surface_shaders.append(default_physical_surface_shader)

        # default material
        default_material.surface_shader = AsParameter('surface_shader', default_clear_surface_shader.name)
        root_assembly.materials.append(default_material)

        # create default invisible material 
        default_invisible_surface_shader = AsSurfaceShader()
        default_invisible_material = AsMaterial()
        default_invisible_material.name = 'as_default_invisible_material'
        default_invisible_material.alpha_map = AsParameter('alpha_map', '0')
        default_invisible_material.surface_shader = AsParameter('surface_shader', default_clear_surface_shader.name)

        root_assembly.materials.append(default_invisible_material)

        for transform in maya_scene:
            construct_transform_descendents(params, root_assembly, root_assembly, [], transform, mb_sample_number_list, non_mb_sample_number, params['export_camera_blur'], params['export_transformation_blur'], params['export_deformation_blur'])

        # end construction of as project hierarchy ************************************************

        # add project to dict with the project file path as the key
        file_name = base_file_name.replace("#", str(frame_number).zfill(4))
        project_file_path = os.path.join(params['output_directory'], file_name)

        as_object_models.append((project_file_path, as_project))

        cmds.progressWindow(e=True, progress=i)

    return as_object_models


#--------------------------------------------------------------------------------------------------
# construct_transform_descendents function.
#--------------------------------------------------------------------------------------------------

def construct_transform_descendents(params, root_assembly, parent_assembly, matrix_stack, maya_transform, mb_sample_number_list, non_mb_sample_number, camera_blur, transformation_blur, object_blur):

    """ this function recursively builds an appleseed object hierarchy from a MTransform """

    current_assembly = parent_assembly
    current_matrix_stack = matrix_stack + [maya_transform.matrices[non_mb_sample_number]]

    if maya_transform.has_children and maya_transform.visibility_states[non_mb_sample_number]:

        if maya_transform.is_animated and transformation_blur:
            current_assembly = AsAssembly(parent_assembly)
            current_assembly.name = maya_transform.safe_name
            parent_assembly.assemblies.append(current_assembly)
            current_assembly_instance = current_assembly.instantiate()
            parent_assembly.assembly_instances.append(current_assembly_instance)
            current_matrix_stack = []

            sample_index = 0
            sample_count = len(mb_sample_number_list)
            time_increment = 1.0 / (sample_count - 1) if sample_count > 1 else 1.0
            for sample_number in mb_sample_number_list:
                new_transform = AsTransform()
                new_transform.time = sample_index * time_increment
                new_transform.matrices = [maya_transform.matrices[sample_number]] + matrix_stack
                current_assembly_instance.transforms.append(new_transform)
                sample_index += 1

        for transform in maya_transform.child_transforms:
            construct_transform_descendents(params, root_assembly, current_assembly, current_matrix_stack, transform, mb_sample_number_list, non_mb_sample_number, camera_blur, transformation_blur, object_blur)

        for light in maya_transform.child_lights:

            if light.multiplier > 0:

                # create colour entites
                if light.color.__class__.__name__ == 'MFile':
                    light_color_file, light_color =  m_file_to_as_texture(params, light.color, '_light_color', non_mb_sample_number)
                    current_assembly.textures.append(light_color_file)
                    current_assembly.texture_instances.append(light_color)
                else:
                    light_color = m_color_connection_to_as_color(light.color, '_light_color')
                    current_assembly.colors.append(light_color)

                if light.model == 'areaLight':
                    
                    # create new light mesh instance and material
                    light_mesh = AsObject()
                    light_mesh.name = light.safe_name
                    light_mesh.file_names = AsParameter('filename', ms_commands.GEO_DIR + '/maya_area_light.obj')

                    light_mesh_transform = AsTransform()
                    if current_matrix_stack is not []:
                        light_mesh_transform.matrices = current_matrix_stack

                    light_mesh_instance = light_mesh.instantiate()
                    light_mesh_instance.transforms.append(light_mesh_transform)

                    light_material = AsMaterial()
                    light_material.name = light.safe_name + '_material'

                    light_edf = AsEdf()
                    light_edf.name = light.safe_name + '_edf'
                    light_edf.model = 'diffuse_edf'
                    light_edf.parameters.append(AsParameter('radiance', light_color.name))
                    light_edf.parameters.append(AsParameter('radiance_multiplier', light.multiplier))

                    if 'ms_cast_indirect_light' in light.export_modifiers:
                        if light.export_modifiers['ms_cast_indirect_light'] is False:
                            light_edf.parameters.append(AsParameter('cast_indirect_light', 'false'))

                    if 'ms_importance_multiplier' in light.export_modifiers:
                        light_edf.parameters.append(AsParameter('importance_multiplier', light.export_modifiers['ms_importance_multiplier']))

                    current_assembly.edfs.append(light_edf)

                    light_material.surface_shader = AsParameter('surface_shader', 'as_default_clear_surface_shader')
                    light_material.alpha_map = AsParameter('alpha_map', '0')

                    # in this case simpler to set the surface shader and reset it as its not a simple if else situation
                    if 'ms_area_light_visibility' in light.export_modifiers:
                        if light.export_modifiers['ms_area_light_visibility'] is True:
                            light_material.surface_shader = AsParameter('surface_shader', 'as_default_physical_surface_shader')
                            light_material.alpha_map = None

                    light_material.edf = AsParameter('edf', light_edf.name)
                    current_assembly.materials.append(light_material)

                    light_mesh_instance.material_assignments.append(AsObjectInstanceMaterialAssignment('0', 'front', light_material.name))
                    light_mesh_instance.material_assignments.append(AsObjectInstanceMaterialAssignment('0', 'back', 'as_default_invisible_material'))

                    current_assembly.objects.append(light_mesh)
                    current_assembly.object_instances.append(light_mesh_instance)

                else:
                    new_light = AsLight()
                    new_light.name = light.safe_name
                    
                    new_light.exitance_multiplier.value = light.multiplier

                    new_light.exitance = AsParameter('exitance', light_color.name)
                    new_light.transform = AsTransform()
                    if current_matrix_stack is not []:
                        new_light.transform.matrices = current_matrix_stack

                    if light.model == 'spotLight':
                        new_light.model = 'spot_light'
                        new_light.inner_angle = AsParameter('inner_angle', light.inner_angle)
                        new_light.outer_angle = AsParameter('outer_angle', light.outer_angle)
                    else:
                        new_light.model = 'point_light'

                    current_assembly.lights.append(new_light)

        for mesh in maya_transform.child_meshes:
            # For now we won't be supporting instantiating objects. When the time comes I will add a function call here
            # to find if the mesh has been defined somewhere in the assembly hierarchy already and instantiate it if so.
            new_mesh = AsObject()
            new_mesh.name = mesh.safe_name
            new_mesh.name_in_obj = mesh.short_name
            new_mesh.has_deformation = mesh.has_deformation

            if not object_blur or not new_mesh.has_deformation:
                # If the mesh has no deformation there will only be one sample so always take the first sample.
                if new_mesh.has_deformation:
                    new_mesh.file_names = AsParameter('filename', mesh.mesh_file_names[non_mb_sample_number])
                else:
                    new_mesh.file_names = AsParameter('filename', mesh.mesh_file_names[0])
            else:
                file_names = AsParameters('filename')
                for i in mb_sample_number_list:
                    file_names.parameters.append(AsParameter(i - mb_sample_number_list[0], mesh.mesh_file_names[i]))
                new_mesh.file_names = file_names

            current_assembly.objects.append(new_mesh)
            mesh_instance = new_mesh.instantiate()
            mesh_transform = AsTransform()
            if current_matrix_stack is not []:
                mesh_transform.matrices = current_matrix_stack
            mesh_instance.transforms.append(mesh_transform)

            # translate materials and assign
            for maya_ms_material in mesh.ms_materials:
                as_materials = convert_maya_ms_material_network(params, root_assembly, maya_ms_material, non_mb_sample_number)

                if as_materials is not None:
                    
                    if as_materials[0] is not None:
                        mesh_instance.material_assignments.append(AsObjectInstanceMaterialAssignment(maya_ms_material.name, 'front', as_materials[0].name))
                    else:
                        mesh_instance.material_assignments.append(AsObjectInstanceMaterialAssignment('0', 'front', 'as_default_material'))
                    
                    if as_materials[1] is not None:
                        mesh_instance.material_assignments.append(AsObjectInstanceMaterialAssignment(maya_ms_material.name, 'back', as_materials[1].name))
                    else:
                        mesh_instance.material_assignments.append(AsObjectInstanceMaterialAssignment('0', 'back', 'as_default_material'))

            for maya_generic_material in mesh.generic_materials:

                front_as_material, back_as_material = convert_maya_generic_material(params, root_assembly, maya_generic_material, non_mb_sample_number)

                mesh_instance.material_assignments.append(AsObjectInstanceMaterialAssignment(maya_generic_material.name, 'front', front_as_material.name))

                if back_as_material is not None:
                    mesh_instance.material_assignments.append(AsObjectInstanceMaterialAssignment(maya_generic_material.name, 'back', back_as_material.name))

            current_assembly.object_instances.append(mesh_instance)


        for ms_appleseed_scene in maya_transform.child_ms_appleseed_scenes:

            scene_file_name = os.path.split(ms_appleseed_scene.scene_filepath)[1]

            ms_commands.info('Embedding scene: {0}'.format(scene_file_name))

            assembly = get_ms_appleseed_scene_from_heirarchy(scene_file_name, current_assembly)


            if assembly is None:
                assembly = AsAssembly(parent_assembly)
                assembly.name = scene_file_name
                current_assembly.assemblies.append(assembly)

                if os.path.exists(ms_appleseed_scene.scene_filepath):
                    path = ms_appleseed_scene.scene_filepath
                elif os.path.exists(os.path.join(cmds.workspace(q=True, rd=True), ms_appleseed_scene.scene_filepath)):
                    path = os.path.join(cmds.workspace(q=True, rd=True), ms_appleseed_scene.scene_filepath)
                else:
                    path = None

                if path is None:
                    ms_commands.warning('{0} does not exist, skipping archive output'.format(ms_appleseed_scene.scene_filepath))
                else:
                    assembly.raw_xml += ms_commands.strip_scene_xml(path, params['output_directory'])

            assembly_instance = assembly.instantiate()

            assembly_transform = AsTransform()
            if current_matrix_stack is not []:
                assembly_transform.matrices = current_matrix_stack
            assembly_instance.transforms.append(assembly_transform)

            current_assembly.assembly_instances.append(assembly_instance)


def get_ms_appleseed_scene_from_heirarchy(scene_name, current_assembly):
    for child_assembly in current_assembly.assemblies:
        if child_assembly.name == scene_name:
            return child_assembly

    if current_assembly.parent_assembly is not None:
        child_in_parent_assembly = get_ms_appleseed_scene_from_heirarchy(scene_name, current_assembly.parent_assembly)
        if child_child_assembly is not None:
            return child_child_assembly
            
    return None    


#--------------------------------------------------------------------------------------------------
# convert_maya_generic_material function.
#--------------------------------------------------------------------------------------------------

def convert_maya_generic_material(params, root_assembly, generic_material, non_mb_sample_number):

    front_material = None
    back_material = None

    double_sided = True
    single_material = True

    # determin if the material is double sided and if it uses the same material on front and back
    if generic_material.type == 'surfaceShader':
        double_sided = False

    if 'ms_double_sided_material' in generic_material.export_modifiers:
        double_sided = generic_material.export_modifiers['ms_double_sided_material']

    if (generic_material.transparency is not None) and double_sided:
        single_material = False

    # check if material already exists in the root
    if not double_sided:
        front_material = get_from_list(root_assembly.materials, generic_material.safe_name)
    elif single_material:
        front_material = get_from_list(root_assembly.materials, generic_material.safe_name)
        back_material = get_from_list(root_assembly.materials, generic_material.safe_name)
    else:
        front_material = get_from_list(root_assembly.materials, generic_material.safe_name + '_front')
        back_material = get_from_list(root_assembly.materials, generic_material.safe_name + '_back')

    if front_material is not None:
        return front_material, back_material


    # conver relevant as entities from generic material attributes to as attributes
    material_attribs = {'color'            : generic_material.color,
                        'alpha'            : generic_material.alpha,
                        'transparrency'    : generic_material.transparency,
                        'incandescence'    : generic_material.incandescence,
                        'glossiness'       : generic_material.glossiness,
                        'reflectivity'     : generic_material.reflectivity,
                        'bump_map'         : generic_material.bump_map,
                        'bump_multiplier'  : generic_material.bump_multiplier,
                        'translucence'     : generic_material.translucence}

    for key in material_attribs.keys():
        if material_attribs[key] is not None:
            if material_attribs[key].__class__.__name__ == 'MFile':
                texture, texture_instance = m_file_to_as_texture(params, material_attribs[key], '_' + key + '_file', non_mb_sample_number)
                material_attribs[key] = texture_instance.name
                if not get_from_list(root_assembly.textures, texture.name):
                    root_assembly.textures.append(texture)
                    root_assembly.texture_instances.append(texture_instance)
                
            else:
                if isinstance(material_attribs[key], (int, long, float, complex)):
                    pass
                elif material_attribs[key].is_grey:
                    material_attribs[key] = material_attribs[key].normalized_color[0] * material_attribs[key].multiplier

                else:
                    color = m_color_connection_to_as_color(material_attribs[key], '_' + key + '_color')    
                    if not get_from_list(root_assembly.colors, color.name):
                        material_attribs[key] = color.name
                        root_assembly.colors.append(color)


    # create front and back materials
    front_material = AsMaterial()
    front_material.name = generic_material.safe_name
    root_assembly.materials.append(front_material)

    if double_sided and single_material:
        back_material = front_material

    elif double_sided:
        front_material.name = front_material.name + '_front'

        back_material = AsMaterial()
        back_material.name = generic_material.safe_name + '_back'
        root_assembly.materials.append(back_material)


    # material alpha component
    if 'ms_material_visibility' in generic_material.export_modifiers:
        if generic_material.export_modifiers['ms_material_visibility']:
            if material_attribs['alpha'] is not None:
                if isinstance(material_attribs['alpha'], (int, long, float, complex)):
                    front_material.alpha_map = AsParameter('alpha_map', 1 - material_attribs['alpha'])
                else:
                    front_material.alpha_map = AsParameter('alpha_map', material_attribs['alpha'])
        else:
            front_material.alpha_map = AsParameter('alpha_map', 0)
    if double_sided and (single_material == False):
        back_material.alpha_map = front_material.alpha_map


    # material displacement component
    if generic_material.bump_multiplier is not None:
        front_material.displacement_mode = AsParameter('displacement_method', 'bump')
        front_material.bump_amplitude = AsParameter('bump_amplitude', material_attribs['bump_multiplier'])
        front_material.displacement_map = AsParameter('displacement_map', material_attribs['bump_map'])
        if double_sided and (single_material == False):
            back_material.displacement_map = front_material.displacement_map


    # surface shader component
    if generic_material.incandescence is not None:
        # add a constant surface shader
        primary_surface_shader = AsSurfaceShader()
        primary_surface_shader.name = generic_material.safe_name + '_surface_shader'
        primary_surface_shader.model = 'constant_surface_shader'
        primary_surface_shader.parameters.append(AsParameter('color', material_attribs['incandescence']))
        primary_surface_shader.parameters.append(AsParameter('color', material_attribs['incandescence']))

    else:
        # add a physical surface shader
        primary_surface_shader = AsSurfaceShader()
        primary_surface_shader.name = generic_material.safe_name + '_surface_shader'
        primary_surface_shader.model = 'physical_surface_shader'

    # surface shader alpha multiplier
    if 'ms_surface_shader_visibility' in generic_material.export_modifiers:
        if not generic_material.export_modifiers['ms_surface_shader_visibility']:
            primary_surface_shader.parameters.append(AsParameter('alpha_multiplier', 0))


    # secondary surface shader component
    if generic_material.secondary_surface_shader is not None:
        main_surface_shader = AsSurfaceShader()
        main_surface_shader.name = generic_material.safe_name + '_main_surface_shader'
        main_surface_shader.model = 'surface_shader_collection'
        secondary_surface_shader = get_from_list(root_assembly.surface_shaders, generic_material.secondary_surface_shader.name + '_secondary')

        if secondary_surface_shader is None:
            secondary_surface_shader = build_as_shading_nodes(params, root_assembly,  generic_material.secondary_surface_shader, non_mb_sample_number)
        else:
            secondary_surface_shader.name += '_secondary'

        # secondary surface shader alpha multiplier
        if 'ms_surface_shader_visibility' in generic_material.export_modifiers:
            if not generic_material.export_modifiers['ms_surface_shader_visibility']:
                secondary_surface_shader.parameters.append(AsParameter('alpha_multiplier', 0))

        primary_surface_shader.name += '_primary'
        main_surface_shader.parameters.append(AsParameter('surface_shader1', primary_surface_shader.name))
        main_surface_shader.parameters.append(AsParameter('surface_shader2', secondary_surface_shader.name))
        
        root_assembly.surface_shaders.append(primary_surface_shader)

    else:
        main_surface_shader = primary_surface_shader

    root_assembly.surface_shaders.append(main_surface_shader)

    # connect main surface shader to material
    front_material.surface_shader = AsParameter('surface_shader', main_surface_shader.name)

    if double_sided and (single_material == False):
        back_material.surface_shader = front_material.surface_shader


    # edf component
    if generic_material.incandescence is not None:
        edf = AsEdf()
        edf.name = generic_material.safe_name + '_edf'
        edf.model = 'diffuse_edf'
        edf.parameters.append(AsParameter('radiance', material_attribs['incandescence']))
        root_assembly.edfs.append(edf)

        if 'ms_cast_indirect_light' in generic_material.export_modifiers:
            if generic_material.export_modifiers['ms_cast_indirect_light'] is False:
                edf.parameters.append(AsParameter('cast_indirect_light', 'false'))

        if 'ms_importance_multiplier' in generic_material.export_modifiers:
            edf.parameters.append(AsParameter('importance_multiplier', generic_material.export_modifiers['ms_importance_multiplier']))

        front_material.edf = AsParameter('edf', edf.name)

    # color_component component
    if (generic_material.incandescence is None) and (generic_material.color is not None):

        color_component = None
        reflective_component = None
        diffuse_component = None
        specular_component = None
        front_transmission_component = None
        back_transmission_component = None
        front_bsdf = None
        back_bsdf = None

        # reflective component
        if generic_material.color:

            # 'diffuse' component
            if generic_material.color is not None:
                diffuse_component = AsBsdf()
                diffuse_component.name = generic_material.safe_name + '_diffuse_component'
                diffuse_component.model = 'lambertian_brdf'
                root_assembly.bsdfs.append(diffuse_component)
                diffuse_component.parameters.append(AsParameter('reflectance', material_attribs['color']))

            # 'specular' component
            if generic_material.glossiness:
                specular_component = AsBsdf()
                specular_component.name = generic_material.safe_name + '_specular_component'
                specular_component.model = 'microfacet_brdf'
                specular_component.parameters.append(AsParameter('mdf', 'blinn'))
                root_assembly.bsdfs.append(specular_component)
                specular_component.parameters.append(AsParameter('glossiness', material_attribs['glossiness']))
                if generic_material.reflectivity:
                    specular_component.parameters.append(AsParameter('reflectance', material_attribs['reflectivity']))
                else:
                    specular_component.parameters.append(AsParameter('reflectance', 0))

        # transmission component
        if generic_material.transparency and (not generic_material.alpha):
            front_transmission_component = AsBsdf()
            front_transmission_component.name = generic_material.safe_name + '_front_transmission_component'
            front_transmission_component.model = 'specular_btdf'
            root_assembly.bsdfs.append(front_transmission_component)

            # reflectance parameter
            if generic_material.reflectivity:
                front_transmission_component.parameters.append(AsParameter('reflectance', material_attribs['reflectivity']))
            else:
                front_transmission_component.parameters.append(AsParameter('reflectance', 0))

            # transmittance parameter
            if generic_material.color:
                front_transmission_component.parameters.append(AsParameter('transmittance', material_attribs['color']))

            if generic_material.refractive_index:
                front_transmission_component.parameters.append(AsParameter('from_ior', params['scene_ior']))
                front_transmission_component.parameters.append(AsParameter('to_ior', generic_material.refractive_index))
            else:
                front_transmission_component.parameters.append(AsParameter('from_ior', params['scene_ior']))
                front_transmission_component.parameters.append(AsParameter('to_ior', params['scene_ior']))

            if double_sided and (single_material == False):
                back_transmission_component = AsBsdf()
                back_transmission_component.name = generic_material.safe_name + '_back_transmission_component'
                back_transmission_component.model = 'specular_btdf'
                root_assembly.bsdfs.append(back_transmission_component)

                # reflectance parameter
                if generic_material.reflectivity:
                    back_transmission_component.parameters.append(AsParameter('reflectance', material_attribs['reflectivity']))
                else:
                    back_transmission_component.parameters.append(AsParameter('reflectance', 0))

                # transmittance parameter
                if generic_material.color:
                    back_transmission_component.parameters.append(AsParameter('transmittance', material_attribs['color']))

                if generic_material.refractive_index:
                    back_transmission_component.parameters.append(AsParameter('from_ior', generic_material.refractive_index))
                    back_transmission_component.parameters.append(AsParameter('to_ior', params['scene_ior']))
                else:
                    back_transmission_component.parameters.append(AsParameter('from_ior', params['scene_ior']))
                    back_transmission_component.parameters.append(AsParameter('to_ior', params['scene_ior']))


        # connect up the appleseed shading networks
        # reflective component
        if (diffuse_component is not None) and (specular_component is not None) and (not material_attribs['reflectivity'] is None):
            reflective_component = AsBsdf()
            reflective_component.name = generic_material.safe_name + '_reflective_component'
            reflective_component.model = 'bsdf_blend'
            root_assembly.bsdfs.append(reflective_component)

            reflective_component.parameters.append(AsParameter('bsdf0', specular_component.name))
            reflective_component.parameters.append(AsParameter('bsdf1', diffuse_component.name))

            reflective_component.parameters.append(AsParameter('weight', material_attribs['reflectivity']))


        elif diffuse_component is not None:
            reflective_component = diffuse_component

        elif specular_component is not None:
            reflective_component = specular_component

        # main bsdf component
        # create bsdf mix if reflective component and transmission component are present
        if (reflective_component is not None) and (front_transmission_component is not None):
            front_bsdf = AsBsdf()
            front_bsdf.name = generic_material.safe_name + '_front_bsdf'
            front_bsdf.model = 'bsdf_blend'
            root_assembly.bsdfs.append(front_bsdf)

            if isinstance(material_attribs['transparrency'], (int, long, float, complex)):
                front_bsdf.parameters.append(AsParameter('weight', (material_attribs['transparrency'] * -1 )+ 1))
            else:
                front_bsdf.parameters.append(AsParameter('weight', material_attribs['transparrency']))

            front_bsdf.parameters.append(AsParameter('bsdf0', reflective_component.name))
            front_bsdf.parameters.append(AsParameter('bsdf1', front_transmission_component.name))

            # before the ior is defined duplicate the parts that should be identical
            if double_sided and (single_material == False):
                back_bsdf = AsBsdf()
                back_bsdf.name = generic_material.safe_name + '_back_bsdf'
                back_bsdf.model = 'bsdf_blend'
                root_assembly.bsdfs.append(back_bsdf)

                if isinstance(material_attribs['transparrency'], (int, long, float, complex)):
                    back_bsdf.parameters.append(AsParameter('weight', (material_attribs['transparrency'] * -1 )+ 1))
                else:
                    back_bsdf.parameters.append(AsParameter('weight', material_attribs['transparrency']))

                back_bsdf.parameters.append(AsParameter('bsdf0', reflective_component.name))
                back_bsdf.parameters.append(AsParameter('bsdf1', back_transmission_component.name))


        if front_bsdf is None:
            if reflective_component is not None:
                front_bsdf = reflective_component
            else:
                front_bsdf = front_transmission_component

        if front_bsdf is not None:
            front_material.bsdf = AsParameter('bsdf', front_bsdf.name)

        if double_sided and (single_material == False):
            if back_bsdf is None:
                if reflective_component is not None:
                    back_bsdf = reflective_component
                else:
                    back_bsdf = back_transmission_component

            if back_bsdf is not None:
                back_material.bsdf = AsParameter('bsdf', back_bsdf.name)

    # return relevent combination of front and back materials
    if double_sided and (single_material == False):
        return front_material, back_material

    elif double_sided:
        return front_material, front_material

    else: 
        return front_material, None


#--------------------------------------------------------------------------------------------------
# convert_maya_ms_material_network function.
#--------------------------------------------------------------------------------------------------

def convert_maya_ms_material_network(params, root_assembly, ms_material, non_mb_sample_number):

    """ constructs a AsMaterial from an MMsMaterial """

    materials = [None, None]

    # check if material already exists in root_assembly
    for material in root_assembly.materials:
        if material.name == (ms_material.safe_name + '_front') and ms_material.enable_front:
            materials[0] = material
        if material.name == (ms_material.safe_name + '_back') and ms_material.enable_back and ms_material.duplicate_shaders:
            materials[1] = material

    if materials[0] is None and materials[1] is None:
        if ms_material.alpha_map is not None:
            alpha_texture, alpha_texture_instance = m_file_to_as_texture(params, ms_material.alpha_map, '_alpha', non_mb_sample_number)
            root_assembly.textures.append(alpha_texture)
            root_assembly.texture_instances.append(alpha_texture_instance)

        normal_map_up = None
        displacement_mode = None
        bump_amplitude = None
        # create displacement attributes
        if ms_material.displacement_mode == 0:
            displacement_mode = AsParameter('displacement_method', 'bump')
            bump_amplitude = AsParameter('bump_amplitude', str(ms_material.bump_amplitude))
        else:
            displacement_mode = AsParameter('displacement_method', 'normal')
            if ms_material.normal_map_up == '0':
                normal_map_up = AsParameter('normal_map_up', 'y')
            else:
                normal_map_up = AsParameter('normal_map_up', 'z')

        # if the materials are not yet defined construct them
        if ms_material.enable_front:
            front_material = AsMaterial()
            front_material.name = ms_material.safe_name + '_front'
            if ms_material.bsdf_front is not None:
                new_bsdf = build_as_shading_nodes(params, root_assembly, ms_material.bsdf_front, non_mb_sample_number)
                front_material.bsdf = AsParameter('bsdf', new_bsdf.name)
            if ms_material.edf_front is not None:
                new_edf = build_as_shading_nodes(params, root_assembly, ms_material.edf_front, non_mb_sample_number)
                front_material.edf = AsParameter('edf', new_edf.name)
            if ms_material.surface_shader_front is not None:
                new_surface_shader = build_as_shading_nodes(params, root_assembly, ms_material.surface_shader_front, non_mb_sample_number)
                front_material.surface_shader = AsParameter('surface_shader', new_surface_shader.name)
            if ms_material.displacement_map_front is not None:

                texture, texture_instance = m_file_to_as_texture(params, ms_material.displacement_map_front, '_displacement_back', non_mb_sample_number)
                existing_texture = get_from_list(root_assembly.textures, texture.name)
                existing_texture_instance = get_from_list(root_assembly.texture_instances, texture_instance.name)

                if existing_texture is None:
                    root_assembly.textures.append(texture)
                    root_assembly.texture_instances.append(texture_instance)
                else:
                    texture = existing_texture
                    texture_instance = existing_texture_instance

                front_material.displacement_map = AsParameter('displacement_map', texture_instance.name)
                front_material.displacement_mode = displacement_mode
                front_material.bump_amplitude = bump_amplitude
                front_material.normal_map_up = normal_map_up

            if ms_material.alpha_map is not None:
                front_material.alpha_map = AsParameter('alpha_map', alpha_texture_instance.name)

            root_assembly.materials.append(front_material)
            materials[0] = front_material

        if ms_material.enable_back:
            back_material = AsMaterial()
            back_material.name = ms_material.safe_name + '_back'
            if ms_material.bsdf_back is not None:
                new_bsdf = build_as_shading_nodes(params, root_assembly, ms_material.bsdf_back, non_mb_sample_number)
                back_material.bsdf = AsParameter('bsdf', new_bsdf.name)
            if ms_material.edf_back is not None:
                new_edf = build_as_shading_nodes(params, root_assembly, ms_material.edf_back, non_mb_sample_number)
                back_material.edf = AsParameter('edf', new_edf.name)
            if ms_material.surface_shader_back is not None:
                new_surface_shader = build_as_shading_nodes(params, root_assembly, ms_material.surface_shader_back, non_mb_sample_number)
                back_material.surface_shader = AsParameter('surface_shader', new_surface_shader.name)
            if ms_material.displacement_map_back is not None:

                texture, texture_instance = m_file_to_as_texture(params, ms_material.displacement_map_back, '_displacement_back', non_mb_sample_number)
                existing_texture = get_from_list(root_assembly.textures, texture.name)
                existing_texture_instance = get_from_list(root_assembly.texture_instances, texture_instance.name)

                if existing_texture is None:
                    root_assembly.textures.append(texture)
                    root_assembly.texture_instances.append(texture_instance)
                else:
                    texture = existing_texture
                    texture_instance = existing_texture_instance

                back_material.displacement_map = AsParameter('displacement_map', texture_instance.name)

                back_material.displacement_mode = displacement_mode
                back_material.bump_amplitude = bump_amplitude
                back_material.normal_map_up = normal_map_up


            if ms_material.alpha_map is not None:
                back_material.alpha_map = AsParameter('alpha_map', alpha_texture_instance.name)

            root_assembly.materials.append(back_material)
            materials[1] = back_material

    return materials


#--------------------------------------------------------------------------------------------------
# get_from_list function.
#--------------------------------------------------------------------------------------------------

def get_from_list(list, name):

    """ searches through list of objects with a .name attribute or surface_shaders and returns the object if it exists or None if not """

    for item in list:
        if item.name == name:
            return item

    return None


#--------------------------------------------------------------------------------------------------
# build_as_shading_nodes function.
#--------------------------------------------------------------------------------------------------

def build_as_shading_nodes(params, root_assembly, current_maya_shading_node, non_mb_sample_number):

    """ takes a Maya MMsShading node and returns a AsEdf, AsBsdf or AsSurfaceShader"""

    # the connection is an edf, bsdf or surface_shader
    current_shading_node = None
    if current_maya_shading_node.type == 'bsdf':
        current_shading_node = get_from_list(root_assembly.bsdfs, current_maya_shading_node.safe_name)
        if current_shading_node is None:
            current_shading_node = AsBsdf()
            root_assembly.bsdfs.append(current_shading_node)
        else:
            return current_shading_node

    elif current_maya_shading_node.type == 'edf':
        current_shading_node = get_from_list(root_assembly.edfs, current_maya_shading_node.safe_name)
        if current_shading_node is None:
            current_shading_node = AsEdf()
            root_assembly.edfs.append(current_shading_node)
        else:
            return current_shading_node

    elif current_maya_shading_node.type == 'surface_shader':
        current_shading_node = get_from_list(root_assembly.surface_shaders, current_maya_shading_node.safe_name)
        if current_shading_node is None:
            current_shading_node = AsSurfaceShader()
            root_assembly.surface_shaders.append(current_shading_node)
        else:
            return current_shading_node

    current_shading_node.name = current_maya_shading_node.safe_name
    current_shading_node.model = current_maya_shading_node.model

    for attrib_key in current_maya_shading_node.attributes:
        if current_maya_shading_node.attributes[attrib_key].__class__.__name__ == 'MMsShadingNode':
            new_shading_node = get_from_list(root_assembly.edfs, current_maya_shading_node.attributes[attrib_key].safe_name)

            if new_shading_node is None:
                new_shading_node = get_from_list(root_assembly.bsdfs, current_maya_shading_node.attributes[attrib_key].safe_name)

            if new_shading_node is None:
                new_shading_node = get_from_list(root_assembly.surface_shaders, current_maya_shading_node.attributes[attrib_key].safe_name)

            if new_shading_node is None:
                new_shading_node = build_as_shading_nodes(params, root_assembly, current_maya_shading_node.attributes[attrib_key], non_mb_sample_number)

            new_shading_node_parameter = AsParameter(attrib_key, new_shading_node.name)
            current_shading_node.parameters.append(new_shading_node_parameter)

        elif current_maya_shading_node.attributes[attrib_key].__class__.__name__ == 'MFile':
            texture_entity = get_from_list(root_assembly.textures, current_maya_shading_node.attributes[attrib_key].safe_name)

            if texture_entity is None:
                texture_entity, texture_instance = m_file_to_as_texture(params, current_maya_shading_node.attributes[attrib_key], '', non_mb_sample_number)

                root_assembly.textures.append(texture_entity)
                root_assembly.texture_instances.append(texture_instance)
            else:
                texture_instance = texture_entity.instantiate()
                root_assembly.texture_instances.append(texture_instance)
            
            new_shading_node_parameter = AsParameter(attrib_key, texture_instance.name)
            current_shading_node.parameters.append(new_shading_node_parameter)

        elif current_maya_shading_node.attributes[attrib_key].__class__.__name__ == 'MColorConnection':

            if current_maya_shading_node.attributes[attrib_key].is_grey is True:
                current_shading_node.parameters.append(AsParameter(attrib_key, current_maya_shading_node.attributes[attrib_key].normalized_color[0]))
            else:

                new_color_entity = get_from_list(root_assembly.colors, current_maya_shading_node.attributes[attrib_key].safe_name)

                if new_color_entity is None:
                    new_color_entity = AsColor()
                    new_color_entity.name = current_maya_shading_node.attributes[attrib_key].safe_name
                    new_color_entity.RGB_color = current_maya_shading_node.attributes[attrib_key].normalized_color
                    new_color_entity.multiplier.value = current_maya_shading_node.attributes[attrib_key].multiplier
                    if params['force_linear_color_interpretation']:
                        new_color_entity.color_space.value = 'linear_rgb'

                root_assembly.colors.append(new_color_entity)
                current_shading_node.parameters.append(AsParameter(attrib_key, new_color_entity.name))

        elif current_maya_shading_node.attributes[attrib_key].__class__.__name__ == 'str':
            new_shading_node_parameter = AsParameter(attrib_key, current_maya_shading_node.attributes[attrib_key])
            current_shading_node.parameters.append(new_shading_node_parameter)

    return current_shading_node


#--------------------------------------------------------------------------------------------------
# export_container function.
#--------------------------------------------------------------------------------------------------

def export_container(render_settings_node):

    """ This function triggers the 3 main processes in exporting, scene caching, translation and saving """

    export_start_time = time.time()

    cmds.progressWindow(title='Exporting ...',
                        min=0,
                        max=100,
                        progress=0,
                        status='Beginning export',
                        isInterruptable=True)

    # reset object counter so there is a higher chance of avoiding duplicate mesh exports
    MMesh.object_counter = 1

    # cache maya scene
    params = get_maya_params(render_settings_node)
    maya_scene, maya_environment = get_maya_scene(params)
    scene_cache_finish_time = time.time()

    ms_commands.info('Scene cached for translation in %.2f seconds.' % (scene_cache_finish_time - export_start_time))

    # copy area light primitives into export directory
    current_script_path = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
    obj_file_name = 'maya_area_light.obj'
    obj_source_path = os.path.join(current_script_path, obj_file_name)
    obj_dest_path = os.path.join(params['output_directory'], ms_commands.GEO_DIR, obj_file_name)
    shutil.copy(obj_source_path, obj_dest_path)

    # translate maya scene
    as_object_models = translate_maya_scene(params, maya_scene, maya_environment)
    scene_translation_finish_time = time.time()

    ms_commands.info('Scene translated in %.2f seconds.' % (scene_translation_finish_time - scene_cache_finish_time))

    cmds.progressWindow(e=True, status='Writing scene files', progress=0, max=len(as_object_models))
    cmds.refresh(cv=True)

    for i, as_object in enumerate(as_object_models):
        ms_commands.info('Saving %s...' % as_object[0])
        doc = WriteXml(as_object[0])
        doc.append_line('<?xml version="1.0" encoding="UTF-8"?>')
        doc.append_line('<!-- File generated by Mayaseed version {0} -->'.format(ms_commands.MAYASEED_VERSION))
        as_object[1].emit_xml(doc)
        doc.close()

        cmds.progressWindow(e=True, progress=i)
        cmds.refresh(cv=True)

    export_finish_time = time.time()

    cmds.progressWindow(endProgress=1)

    appleseed_version_notice = 'This version of mayaseed is designed to work with {0}. Other versions of appleseed may work but have not been tested.'.format(ms_commands.RECCOMENDED_APPLESEED_VERSION)

    ms_commands.info(appleseed_version_notice)

    completed_message = 'Export completed in %.2f seconds, see the script editor for details.' % (export_finish_time - export_start_time)

    ms_commands.info(completed_message)

    cmds.confirmDialog(message=completed_message, button='ok')


#--------------------------------------------------------------------------------------------------
# export function.
#--------------------------------------------------------------------------------------------------

def export(render_settings_node=None):

    """ This function is a wrapper for export_container so that we can profile the export easily """
    
    global previous_export

    if render_settings_node is None:
        if previous_export is not None:
            resolved_render_settings_node = previous_export
        else:
            ms_commands.error('No previous export')
    else:
        resolved_render_settings_node = render_settings_node

    previous_export = resolved_render_settings_node

    if cmds.getAttr(resolved_render_settings_node + '.profile_export'):
        import cProfile
        command = 'import ms_export\nms_export.export_container("' + resolved_render_settings_node + '")'
        cProfile.run(command)
    else:
        export_container(resolved_render_settings_node)
