---
layout: default
title: Render layers
tags:
- docs
---

appleseed can output environments, lights, geometry, materials and surface shaders to separate render layers. By default mayaseed will generate a render layer for each light, and the environment. ms_appleseed_shading_node's can also be assigned to render layers by adding a name to the render_layer attribute.

![Render layers](/images/ms_shadin_node_render_layer.png)