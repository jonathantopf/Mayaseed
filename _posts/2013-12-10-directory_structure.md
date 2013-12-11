---
layout: default
title: Directory structure
tags:
- docs
---

When exporting mayaseed will output files to a to a specific directory structure. Paths in the .appleseed file are relative so you can move the outputted files wherever you like as long as any dependencies stay in the same relative location to the .appleseed scene file.

    shot_directory/geometry/geometry_files ...
               |
               -- /textures/texture_files ...
               |
               -- /scene_file.appleseed