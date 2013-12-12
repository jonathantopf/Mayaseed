---
layout: default
title: Tuning a scene
tags:
- docs
---

This page is a summery of tips and tricks to get the most out of your export & render time.


Increase light/environment samples
----------------------------------

When tuning a scene my first point of call is usually to increase the `pt_light_samples` and/or `pt_environment_samples` attribute in the ms_render_settings node configurations section. If most of the light in your scene is direct this can dramatically decrease the perceived amount of noise in the your render. 


Tweak Max ray intensity
-----------------------

In some scenes you may find that the scene converges quickly apart from a few fireflies here and there. One trick you can try is to turn down the `pt_max_ray_intensity` attribute in your ms_render_settings node's configurations section. 

In the images below the left has a max ray intensity of `0` (infinity) and the right has a max ray intensity of `1`.

![Fireflies](/images/fireflies.png)


Combine objects
---------------

When a scene has  a lot of objects parsing the Maya scene and exporting geometry files file for each object can become a bottleneck. For these scenes it can be advantageous to merge any non transforming or deforming objects into a single mesh.


Fake displacement
-----------------

Displacement is not yet supported in appleseed and even if it were it would be likely to slow down the scene. You'd be surprised how many scenes can be rendered with a fairly high resolution mesh containing low-mid frequency details and a high frequency bump/normal map. 


Only export what you need
-------------------------

When you are fine tuning a scene you are likely to find yourself doing a lot of exports just to test the effect of tweaking a light value or a shader attribute. In this case re-exporting all geometry and textures makes no sense as none of them will have changed so you can tall mayaseed not to re-export textures and geometry that already exist on disk.

![Render settings overwriting files](/images/render_settings_overwrite_files.png)


Tweak a light's importance
--------------------------

appleseed does quite a good job of tweaking a lights importance in the scene automatically but there are often cases when one light might be noisier than the others. In these cases its useful to add an `ms_importance_multiplier` export modifier to your noisy light and increase the multiplier accordingly. As a rule of thumb your scene should be uniformly noise so that increasing sampling rates will increase the render quality over the whole image with as little wasted effort as possible.


Windows
-------

appleseed can sometimes have a hard time rendering indoor scene's lit by an exterior light source like the sun. The problem is that there is a low change of a ray from the sun making it through the window and into the camera so noise is inevitable. Unfortunately for truly accurate scenes there is nothing you can do about it but if you don't mind giving up a small amount of accuracy you can sometimes cheat a little.

In the image below notice how much noisier the reflected light on the walls looks compared to the light directly hitting the floor. This is due to the fact that the light has a very low chance of hitting the wall as it first has to go through the window, bunch of the floor and onto the wall. 

![Window optimisation - before](/images/window_optimisation_before.png)

As a cheat one thing you can do is add an `ms_cast_indirect_light` export modifier to the light and make sure indirect light is turned off. This will make the light behave non physically and stop it casting any indirect light into the scene. To account for the lack of bounce light you can then place another area light where the light would be hitting the floor to fake the indirect light in the scene. Doing this can mess with the light's importance so you may want to add an `ms_importance_multiplier` export modifier to the main light to tweak the importance up. Once you balance the main light and fake indirect light you can usually get a nice uniformly noisy scene that is ready to render at a higher quality as below. 

![Window optimisation - after](/images/window_optimisation_after.png)





