"""Main module for exporting texture animation blocks."""

# ***** BEGIN LICENSE BLOCK *****
#
# Copyright © 2025 NIF File Format Library and Tools contributors.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#
#    * Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials provided
#      with the distribution.
#
#    * Neither the name of the NIF File Format Library and Tools
#      project nor the names of its contributors may be used to endorse
#      or promote products derived from this software without specific
#      prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# ***** END LICENSE BLOCK *****


import bpy
from io_scene_niftools.modules.nif_export.animation.common import AnimationCommon
from io_scene_niftools.modules.nif_export.block_registry import block_store
from io_scene_niftools.modules.nif_export.object import DICT_NAMES
from io_scene_niftools.modules.nif_export.property.texture.common import TextureWriter
from io_scene_niftools.utils.logging import NifLog
from io_scene_niftools.utils.singleton import NifData
from nifgen.formats.nif import classes as NifClasses


class TextureAnimation(AnimationCommon):
    """
    Main interface class for exporting texture animation blocks
    (i.e., NiTextureTransformController, NiFlipController, NiUVController) and keyframe data.
    Texture animations for Bethesda shader properties (only for Skyrim and above)
    are handled by the shader animation class.
    """
    # TODO: Test NiFlipController and NiUVController export methods

    def __init__(self):
        super().__init__()

        # Map operations to their respective FCurve data paths
        self.operation_to_fcurve = {
            "TT_TRANSLATE_U": "shader_nodes[\"Mapping\"].translation[0]",
            "TT_TRANSLATE_V": "shader_nodes[\"Mapping\"].translation[1]",
            "TT_ROTATE": "shader_nodes[\"Mapping\"].rotation[2]",
            "TT_SCALE_U": "shader_nodes[\"Mapping\"].scale[0]",
            "TT_SCALE_V": "shader_nodes[\"Mapping\"].scale[1]",
        }

    def export_texture_animations(self, b_controlled_blocks, n_ni_controller_sequence=None):
        for b_controlled_block in b_controlled_blocks:
            b_strip, b_obj = b_controlled_block
            b_action = b_strip.action
            b_mat = b_obj.active_material.node_tree

            if not b_action.id_root == 'NODE_TREE':
                continue

            n_ni_geometry = DICT_NAMES[b_obj.name]

            n_ni_texturing_property = None
            for n_ni_property in n_ni_geometry.properties:
                if isinstance(n_ni_property, NifClasses.NiTexturingProperty):
                    n_ni_texturing_property = n_ni_property

            if not n_ni_texturing_property:
                NifLog.warn(f"Object {b_obj.name} has no NiTexturingProperty!"
                            f"Texture animation for {b_action.name} will not be exported."
                            f"(Ensure that an unsupported shader property is not applied).")
                continue



            for operation, fcurve_path in self.operation_to_fcurve.items():
                # Check if the operation is animated
                fcurve = next((fcu for fcu in b_action.fcurves if fcu.data_path == fcurve_path), None)
                if not fcurve:
                    continue

                # Create the NiTextureTransformController for this operation
                n_ni_texture_transform_controller = (
                    self.export_ni_texture_transform_controller(n_ni_texturing_property, b_action,
                                                                n_ni_controller_sequence, operation))

                if n_ni_controller_sequence:
                    n_controlled_block = n_ni_controller_sequence.add_block
                    n_controlled_block.controller = n_ni_texture_transform_controller
                    n_controlled_block.node_name = n_ni_geometry.name
                    n_controlled_block.property_type = "NiTexturingProperty"
                    n_controlled_block.controller_type = "NiTextureTransformController"
                    n_controlled_block.controller_id = f"0-0-{operation}"

        return

    def export_ni_texture_transform_controller(self, n_ni_texturing_property, b_action,
                                               n_ni_controller_sequence=None, operation=None):
        """Export a NiTextureTransformController block."""
        n_ni_texture_transform_controller = block_store.create_block("NiTextureTransformController")

        n_ni_texturing_property.controller = n_ni_texture_transform_controller
        n_ni_texture_transform_controller.target = n_ni_texturing_property

        n_ni_texture_transform_controller.texture_slot = NifClasses.TexType['BASE_MAP']
        n_ni_texture_transform_controller.operation = operation

        n_ni_texture_transform_controller.start_time = b_action.frame_start / self.fps
        n_ni_texture_transform_controller.stop_time = b_action.frame_end / self.fps

        if n_ni_controller_sequence:
            # Create a NiBlendFloatInterpolator
            n_ni_float_interpolator = block_store.create_block("NiBlendFloatInterpolator")
            n_ni_float_interpolator.flags = 0x1
        else:
            n_ni_float_interpolator = block_store.create_block("NiFloatInterpolator")

        n_ni_texture_transform_controller.interpolator = n_ni_float_interpolator

        n_ni_float_data = block_store.create_block("NiFloatData")
        n_ni_float_interpolator.data = n_ni_float_data

        # Export keys from the corresponding FCurve
        fcurve = next((fcu for fcu in b_action.fcurves if fcu.data_path == self.operation_to_fcurve[operation]), None)
        if fcurve:
            self.export_fcurve_to_nif_keys(fcurve, n_ni_float_data)

        return n_ni_texture_transform_controller

    def export_fcurve_to_nif_keys(self, fcurve, n_ni_float_data):
        """Export FCurve keyframes to NiFloatData."""
        keys = []
        for keyframe in fcurve.keyframe_points:
            time = keyframe.co[0] / self.fps
            value = keyframe.co[1]
            interpolation = keyframe.interpolation

            nif_key = NifClasses.NiFloatKey()
            nif_key.time = time
            nif_key.value = value
            nif_key.interpolation = self.get_nif_interpolation(interpolation)

            keys.append(nif_key)

        n_ni_float_data.keys = keys

    def get_nif_interpolation(self, blender_interpolation):
        """Map Blender interpolation to NIF interpolation types."""
        interpolation_map = {
            'LINEAR': NifClasses.KeyType.LINEAR_KEY,
            'CONSTANT': NifClasses.KeyType.CONSTANT_KEY,
            'BEZIER': NifClasses.KeyType.QUADRATIC_KEY,
        }
        return interpolation_map.get(blender_interpolation, NifClasses.KeyType.LINEAR_KEY)

    def export_ni_uv_controller(self, n_ni_geometry, b_action):
        """Export a NiUVController block."""

        # Get F-curves - a bit more elaborate here so we can zip with the NiUVData later
        # nb. these are actually specific to the texture slot in blender
        # here we don't care and just take the first F-curve that matches
        b_f_curves = []
        for dp, ind in (("offset", 0), ("offset", 1), ("scale", 0), ("scale", 1)):
            for fcu in b_action.fcurves:
                if dp in fcu.data_path and fcu.array_index == ind:
                    b_f_curves.append(fcu)
                    break
            else:
                b_f_curves.append(None)

        # continue if at least one fcurve exists
        if not any(b_f_curves):
            return

        # get the uv curves and translate them into nif data
        n_uv_data = NifClasses.NiUVData(NifData.data)
        for fcu, n_uv_group in zip(b_f_curves, n_uv_data.uv_groups):
            if fcu:
                NifLog.debug(f"Exporting {fcu} as NiUVData")
                n_uv_group.num_keys = len(fcu.keyframe_points)
                n_uv_group.interpolation = NifClasses.KeyType.LINEAR_KEY
                n_uv_group.reset_field("keys")
                for b_point, n_key in zip(fcu.keyframe_points, n_uv_group.keys):
                    # add each point of the curve
                    b_frame, b_value = b_point.co
                    if "offset" in fcu.data_path:
                        # offsets are negated in blender
                        b_value = -b_value
                    n_key.arg = n_uv_group.interpolation
                    n_key.time = b_frame / self.fps
                    n_key.value = b_value

        # if uv data is present then add the controller so it is exported
        if b_f_curves[0].keyframe_points:
            n_ni_uv_controller = NifClasses.NiUVController(NifData.data)
            self.set_flags_and_timing(n_ni_uv_controller, b_f_curves)
            n_ni_uv_controller.data = n_uv_data
            # attach block to geometry
            n_ni_geometry.add_controller(n_ni_uv_controller)

    def export_ni_flip_controller(self, fliptxt, texture, target, target_tex):
        # TODO [animation] port code to use native Blender image strip system
        #                  despite its name a NiFlipController does not flip / mirror a texture
        #                  instead it swaps through a list of textures for a sprite animation
        #
        # fliptxt is a blender text object containing the n_flip definitions
        # texture is the texture object in blender ( texture is used to checked for pack and mipmap flags )
        # target is the NiTexturingProperty
        # target_tex is the texture to n_flip ( 0 = base texture, 4 = glow texture )
        #
        # returns exported NiFlipController

        tlist = fliptxt.asLines()

        # create a NiFlipController
        n_flip = block_store.create_block("NiFlipController", fliptxt)
        target.add_controller(n_flip)

        # fill in NiFlipController's values
        n_flip.flags = 8  # active
        n_flip.frequency = 1.0
        start = bpy.context.scene.frame_start

        n_flip.start_time = (start - 1) * self.fps
        n_flip.stop_time = (bpy.context.scene.frame_end - start) * self.fps
        n_flip.texture_slot = target_tex

        count = 0
        for t in tlist:
            if len(t) == 0:
                continue  # skip empty lines
            # create a NiSourceTexture for each n_flip
            tex = TextureWriter.export_source_texture(texture, t)
            n_flip.num_sources += 1
            n_flip.sources.append(tex)
            count += 1
        if count < 2:
            raise NifLog.warn(f"Error in Texture Flip buffer '{fliptxt.name}': must define at least two textures")
        n_flip.delta = (n_flip.stop_time - n_flip.start_time) / count
