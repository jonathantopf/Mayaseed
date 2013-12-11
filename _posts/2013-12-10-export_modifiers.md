---
layout: default
title: Export modifiers
tags:
- docs
---

Export modifiers are attributes you can add to Maya geometry, lights and materials that modify the way that mayaseed interprets your scene. You can add or remove export modifiers to an object by selecting it and going to one of the export modifier menus.

![Export Modifier menu](/images/export_modifier_menu.png)

The export modifiers will be added to an object as an attribute under the `Extra Attributes` section.

![Export Modifiers in the attribute editor](/images/export_modifiers_in_the_attribute_editor.png)

Currently the following export modifiers are available:

Lights
------

+ ***ms_area_light_visibility*** - lets you set whether an area light has a transparent alpha causing the light to appear invisible
+ ***ms_cast_indirect_light*** - lets you turn off indirect light for a specific light
+ ***ms_importance_multiplier*** - lets you raise or decrease a lights importance causing the renderer to spend more or less effort on that light

Materials (Only Auto translated materials)
----------------------------------------

+ ***ms_cast_indirect_light*** - for light emitting materials, lets you turn off indirect light for a specific light
+ ***ms_importance_multiplier*** - for light emitting materials, lets you raise or decrease a lights importance causing the renderer to spend more or less effort on that light
+ ***ms_front_light_samples*** - lets you increase the light samples for the front surface of a material
+ ***ms_back_light_samples*** - lets you increase the light samples for the back surface of a material
+ ***ms_double_sided_material*** - lets you specify whether mayaseed should create front and back materials from or only front
+ ***ms_transparency_is_material_alpha*** - use this to switch materiel translation from interpreting Maya material transparency as a blend value between a transparent btdf and a reflective brdf or material alpha, material alpha is faster to render but will have no refraction
+ ***ms_secondary_surface_shader*** - connect any output of an ms surface shader (create by choosing `mayaseed > Create Surface Shader`) to this attribute to have that shader attached as a secondary surface shader of a material, useful for adding mattes for a particular object.
+ ***ms_emit_light*** - if this is unchecked a material will not emit light

