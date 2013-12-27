---
layout: default
title: Code structure
tags:
- docs
---

Mayaseed is loaded as a standard module. See the [installation](/docs/Installation) instructions for more.

The mayaseed distribution consists of a few main parts:

`open_me_to_install.ma` is a simple Maya ascii file containing a script node that loads and calls `install_helper.py`. `install_helper.py` deals with creating and saving the `mayaseed.module` file to register the mayaseed module with Maya.

The `plug-ins` directory contains all the node definitions of the mayaseed nodes plus any compiled elements of the plug-in such as `ms_export_obj_<maya_version>`.

The `scripts` directory contains all the scripts and python modules that do the translating. The AETemplate.mel files for defining attribute editor layouts are also stored here.

The `tools` directory contains a few extra tools that may be useful plus the source code for the `ms_export_obj_<maya_version>` plugin.


Code entry point
----------------

After you load `mayaseed.py` in the plug-in manager a few things happen. All the mayaseed custom nodes are registered with maya and `ms_menu.py` is used to build the mayaseed menu.

Most of the user interaction with mayaseed is then done by creating nodes or adding attributes to scene elements.

Export is started be invoking `ms_export.py`'s `export()` function and passing it the name of an `ms_render_settings` node.

