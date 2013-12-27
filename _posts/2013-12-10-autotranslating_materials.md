---
layout: default
title: Auto-translating materials
tags:
- docs
---

When mayaseed encounters a Maya Phong, Blinn, Lambert or SurfaceShader it will translate the material as best as possible. Knowing a little bit about how mayaseed will interpret the material can help a lot in getting the desired result. 

Internally, mayaseed will convert the material into a temporary "generic material" in the following pattern:


    Maya material                                 Generic material attribute
    --------------------------------------------- ---------------------------

    Maya Phong.color ---|
    Maya Blinn.color ---|------------------------ color
    Maya Lambert.color -|

    Maya Phong.transparency ---|
    Maya Blinn.transparency ---|----------------- transparency
    Maya Lambert.transparency -|

    Maya SurfaceShader.outTransparency ---------- alpha

    Maya Phong.incandescence ----|
    Maya Blinn.incandescence ----|--------------- incandescence
    Maya Lambert.incandescence --|
    Maya SurfaceShader.outColor -|

    Maya Phong.cosinePower ---------------------- glossiness

    Maya Phong.reflectivity --------------------- reflectivity

    Maya Phong.bump ----|
    Maya Blinn.bump ----|------------------------ bump_map
    Maya Lambert.bump --|

    Maya Phong.bump_depth ----|
    Maya Blinn.bump_depth ----|------------------ bump_multiplier
    Maya Lambert.bump_depth --|

    Maya Phong.refractiveIndex ------------------ refractive_index

    Maya Phong.translucence ----|
    Maya Blinn.translucence ----|---------------- translucence
    Maya Lambert.translucence --|


>Note: This interpretation may be modified by export modifiers such as ms_transparency_is_alpha, which will cause Maya material transparency to be interpreted as alpha rather than transparency.


Mayaseed will then translate these attributes to an appleseed material network that looks like this:


                                                            -- specular_btdf 
    mayaseed_material.bsdf ---------------- brdf_blend_1 --|                  
                                                           |                   -- lambertian_brdf
                                                            -- brdf_blend_2 --|
                                                                               -- microfacet_brdf
    
    mayaseed_material.edf  ---------------- diffuse_edf
    
    mayaseed_material.surface_shader ------ physical_surface_shader / constant_surface_shader


Mayaseed will map the generic material attributes like this:

    Generic material                  appleseed network
    --------------------------------- --------------------

    color --------------------------- lambertian_brdf.reflectance
    alpha --------------------------- material.alpha_map
    transparency -------------------- brdf_blend_1.weight
    incandescence ------------------- diffuse_edf.radiance
    glossiness ---------------------- microfacet_brdf.glossiness
    reflectivity -------------------- brdf_blend_2.weight
    bump_map ------------------------ material.displacement_map
    bump_multiplier ----------------- material.bump_amplitude
    refractive_index ---------------- (front_material) specular_btdf.from_ior (back_material) specular_btdf.to_ior


Reference
---------

Below is a set of images I created to help when creating materials in Maya. Each image plots various attributes of a Maya Phong against another material attribute. 

[![Reflectivity x Transparency](/images/reflectivity_transparency.jpg)](/images/reflectivity_transparency.jpg)

[![Transparency x Diffuse](/images/transparency_diffuse.jpg)](/images/transparency_diffuse.jpg)

[![Cosine x Reflectivity](/images/cosine_reflectivity.jpg)](/images/cosine_reflectivity.jpg)

[![ior x Diffuse](/images/ior_diffuse.jpg)](/images/ior_diffuse.jpg)






