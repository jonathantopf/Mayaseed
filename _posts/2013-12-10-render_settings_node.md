---
layout: default
title: Render settings node
tags:
- docs
---

The `ms_render_settings` node contains most of the information on how your scene will be translated. Most attributes are self explanatory but this page is an overview of the most important ones.

To create a render settings node chose `mayaseed > Add Render Settings Node`. 

Export Settings
---------------

![Export settings](/images/render_settings_export_settings.png)

`Output Directory`

This attribute sets where your scene will be exported to. Any occurrence of `<ProjectDir>` will be replaced with the path to your current project and `<SceneName>` will be replaced with the name of the scene being exported.

`Output File`

This attribute sets the name of the .appleseed scene file that will be created, `<SceneName>` will be replaced by the current scene name and `#` will be replaced with the frame number padded to 4 characters.

`Convert Textures to OpenExr`

When turned on, this attribute will cause mayaseed to convert any textures to OpenExr using the `imf_copy` utility that comes bundled with Maya. This is on by default as appleseed only reads .exr and .png files currently.

`Overwrite Existing Texture Files`

While this attribute is checked, all textures will be re-converted for each export. In some scenes this can be a lengthly process, so it can be desirable to turn this off when no textures have changed.

`Overwrite Existing Geometry Files`

If geometry has been deformed in your scene, it is desirable to keep this attribute checked. In some cases when geometry has only been transformed rather than deformed you can turn this off to speed up the export.

`Motion Samples`

Adding motion samples to your export will produce more accurate motion blur but will increase the export time. Your will rarely want to change this.


Output Settings
---------------

![Output Settings](/images/render_settings_output_settings.png)

`Camera`

This is where you set the camera you want to use in your export

`Frame width` and `Frame Height`

Sets the resolution of your render. It's worth noting that this attribute isn't integrated from the Maya render settings so you need to set the two individually.


Environment Settings
--------------------

![Environment Settings](/images/render_settings_environment_settings.png)

`Environment`

Use this attribute to select the Environment node you wish to use in your export.

`Render Sky`

With this check box checked, the sky will be rendered in your scene, otherwise the background will be rendered transparent black.

`Scene Index Of Refraction`

For refractive objects appleseed requires a bsdf to have an `in` index of refraction and an `out` index of refraction. Because of this, when material auto translation happens, the `in` index of refraction on the front surface will always be the `Scene Index Of Refraction` and the `out` index of refraction on the back surface will also be the `Scene Index Of Refraction`.


Camera Settings
---------------

`Export All Cameras As Thin Lens`

In appleseed, Heinlein's camera's will render slightly faster but wont show any depth of field.


Configuration Settings
----------------------

![Configuration settings](/images/render_settings_configuration.png)

`Sampler`

Here you choose whether to render using `Uniform sampling` or `Adaptive sampling`. Uniform is usually desirable.

`Pt Light Samples`

Increasing light samples will cause appleseed to spend more or less render effort on the direct lighting of a point in the scene. For scenes with little indirect light you can push this value quite high, perhaps 4 - 12.

`Pt Environment Samples`

This will cause appleseed to spend more or less render effort on the environment lighting of a point in the scene. 


`Pt Max Ray Intensity`

Some fireflies can be eliminated by telling appleseed to disregard unusually bright samples.


Advanced Settings
-----------------

![Advanced](/images/render_settings_advanced.png)

`Profile Export` 

This causes the export to run wrapped in a python `CProfile` function. Profiling information will be printed to the script editor. 

`Auto detect Alpha`

This option will cause textures to have an auto detect alpha flag set in the appleseed scene, meaning appleseed will guess whether to use the image luminance or alpha channel as an alpha value as an input for shading nodes.

`Force Linear Texture Interpretation`

Mayaseed currently does not respect Maya color management. Because of this, it's sometimes desirable to set all textures in the scene to linear space, otherwise all textures are assumed to be sRGB.

`Force Linear Color Interpretation`

Mayaseed interprets color attributes as sRGB color space by default. Cecking this box turns the default interpretation to linear.







