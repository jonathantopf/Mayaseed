---
layout: default
title: Installation
tags:
- docs
---

Installing mayaseed is simple; simply move the downloaded files to your preferred location on your disk or network and open the `open_me_to_install.ma` file included with the mayaseed distribution. 

Once you have installed mayaseed, you just need to give maya a restart and enable it from the plug-in manager `Window > Settings/Preferences > Plug-in manager`

[![Mayaseed in the plug-in manager](/images/plug-in_manager.png)](/images/plug-in_manager.png)

During export, mayaseed exports geometry as obj files. Mayaseed includes two .obj exporters, one cross-platform and cross-version exporter built using pyhton and one faster compiled version that is specific to your OS and maya version. If you have a version of maya with a compatable compiled exporter you'll want to enable that also; it will be called `ms_export_obj_<maya_version>`.

If something goes wrong or you prefer to install mayaseed manually, create a file called `mayaseed.module` with the following contents, replacing `<version_number>` and `<install_directory>` with the correct values.

    mayaseed <version_number> <install_directory>
    icons: graphics
    scripts: scripts

You then want to put that file in one of the following locations:

    Mac: /Users/<username\>/Library/Preferences/Autodesk/maya/<maya version>/scripts
    Windows Vista and higher: C:\Users\<username>\Documents\maya\<maya version>\scripts (you may have My Documents instead of Documents)
    Windows XP and lower: C:\Documents and Settings\username\My Documents\maya\<maya version>\scripts
    Linux: /usr/aw/userconfig/maya/<maya version>/scripts
    