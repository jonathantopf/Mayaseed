---
layout: default
title: appleseed scene files
tags:
- docs
---

Because mayaseed creates appleseed scene files it's useful to know a little bit about them. appleseed scene files are simple plain text XML documents with a .appleseed file extension that contain information about your render settings, objects transforms, links to external textures and geometry and a whole bunch more.

Some of the more important entities defined in the appleseed scene file are as follows:

`<project>`

The project element contains all information on the appleseed project, surprisingly.

`<scene>`

The scene element contains all information about the 3D scene itself, lights, cameras, textures, geometry etc.

Inside the scene element you have, amongst other things, `<assembly>` and `<assembly_instance>` elements. Assemblies let you group and instantiate scene elements and can be thought of as a kind of group.

`<output>`

The output element contains info on the output format of your render, such as color space, resolution etc.

`<configurations>`

The configurations element contains the main parameters that affect how the renderer performs: sample count, lighting engine etc.

You can find a much more detailed overview of the appleseed scene file structure on the [appleseedhq site](https://github.com/appleseedhq/appleseed/wiki/Project-File-Format).
