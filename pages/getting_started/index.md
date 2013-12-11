---
layout: default
title: Getting started
---

The Mayaseed menu
-----------------

The Mayaseed menu will appear when the plugin is correctly installed, if you can't see it make sure the plugin installed correctly and is enabled from the Maya plug-in manager `Window > Settings/Preferences > PLug-in Manager`. You only need to enable `mayaseed.py` and `ms_obj_export_<your maya version>` from the plugin-manager, ther other plugins will be loaded automatically.

[![Mayaseed in the plug-in manager](/images/plug-in_manager.png)](/images/plug-in_manager.png)


The Render Settings node
------------------------

The ms\_renderSettings (render settings) node is the workhorse of Mayaseed, it contains most of the settings to control your export and is also one of the places where you can launch the export. To export your scene you only need one ms\_renderSettings node but it is also possible to have many per scene, this can be useful for making proxy resolution renders or exporting for different render passes. 

>Note: The ms_renderSettings node's attributes are organised in a way that mirrors the internal file structure, so if an attribute seems like its in a strange place there is a good reason. By using Mayaseed you are also learning about appleseed at the same time.

[![ms_render_Settings in the Attribute editor](/images/ms_render_settings.png)](/images/ms_render_settings.png)


Your first export
-----------------

To export a scene you first need to create a render settings node, to do this choose `mayaseed > Add Render Settings Node`.

With the latest release of Mayaseed this is all you need to do, your exports will be sent to a directory named *Mayaseed* in your Maya project. Of course there many customizations available in the *ms\_rendersettings\_node* but I'll leave you to explore them…

Materials
---------

Mayaseed will do a buest guess translation of Maya Phong/Blinn/Lambert/SurfaceShader materials so you should be able to export out of the box. You can also customise the buest guess translation with Export Modifiers or use native mayaseed shading nodes via ms\_materials.
