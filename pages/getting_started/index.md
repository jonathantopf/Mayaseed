---
layout: default
title: Getting started
---

The mayaseed menu
-----------------

The mayaseed menu will appear when the plug-in is correctly installed. If you can't see it, make sure the plug-in is installed correctly and is enabled from the Maya plug-in manager `Window > Settings/Preferences > PLug-in Manager`. You only need to enable `mayaseed.py` and `ms_obj_export_<your Maya version>` from the plug-in manager; the other plug-ins will be loaded automatically.

[![mayaseed in the plug-in manager](/images/plug-in_manager.png)](/images/plug-in_manager.png)


The Render Settings node
------------------------

The ms\_renderSettings (render settings) node is the workhorse of mayaseed. It contains most of the settings to control your export and is also one of the places where you can launch the export. To export your scene you only need one ms\_renderSettings node but it is also possible to have many per scene, which can be useful for making proxy resolution renders or exporting for different render passes. 

>Note: The ms_renderSettings node's attributes are organised in a way that mirrors the internal file structure, so if an attribute seems like it's in a strange place there is a good reason. By using mayaseed you are also learning about appleseed at the same time.

[![ms_render_Settings in the Attribute editor](/images/ms_render_settings.png)](/images/ms_render_settings.png)


Your first export
-----------------

To export a scene you first need to create a render settings node. To do this, choose `mayaseed > Add Render Settings Node`, then chose `mayaseed > Export > your rendersettings node`.

Your exports will be sent to a directory named *mayaseed* in your Maya project. Of course there many customisations available in the `ms_rendersettings_node`.

Materials
---------

Mayaseed will do a best guess translation of Maya Phong/Blinn/Lambert/SurfaceShader materials, so you should be able to export out of the box. You can also customise the best guess translation with *Export Modifiers* or use native mayaseed shading nodes via ms\_materials.
