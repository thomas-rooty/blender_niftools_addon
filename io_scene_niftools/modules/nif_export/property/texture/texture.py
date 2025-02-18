"""Main module for exporting NetImmerse texture properties."""

# ***** BEGIN LICENSE BLOCK *****
#
# Copyright © 2025 NIF File Format Library and Tools contributors.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# * Redistributions of source code must retain the above copyright
#   notice, this list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above
#   copyright notice, this list of conditions and the following
#   disclaimer in the documentation and/or other materials provided
#   with the distribution.
#
# * Neither the name of the NIF File Format Library and Tools
#   project nor the names of its contributors may be used to endorse
#   or promote products derived from this software without specific
#   prior written permission.
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
from io_scene_niftools.modules.nif_export.block_registry import block_store
from io_scene_niftools.modules.nif_export.property.texture.common import TextureCommon
from io_scene_niftools.utils.consts import TEX_SLOTS
from io_scene_niftools.utils.logging import NifLog, NifError
from io_scene_niftools.utils.singleton import NifData
from nifgen.formats.nif import classes as NifClasses


class NiTexturingProperty(TextureCommon):

    # TODO Common for import/export
    """Names (ordered by default index) of shader texture slots for Sid Meier's Railroads and similar games."""
    EXTRA_SHADER_TEXTURES = [
        "EnvironmentMapIndex",
        "NormalMapIndex",
        "SpecularIntensityIndex",
        "EnvironmentIntensityIndex",
        "LightCubeMapIndex",
        "ShadowTextureIndex"]

    # Default ordering of Extra data blocks for different games
    USED_EXTRA_SHADER_TEXTURES = {
        'SID_MEIER_S_RAILROADS': (3, 0, 4, 1, 5, 2),
        'CIVILIZATION_IV': (3, 0, 1, 2)
    }

    __instance = None

    def __init__(self):
        """ Virtually private constructor. """
        if NiTexturingProperty.__instance:
            raise Exception("This class is a singleton!")
        else:
            super().__init__()
            NiTexturingProperty.__instance = self

    @staticmethod
    def get():
        """ Static access method. """
        if not NiTexturingProperty.__instance:
            NiTexturingProperty()
        return NiTexturingProperty.__instance

    def export_ni_texturing_property(self, b_mat, n_ni_geometry, n_bs_shader_property=None, applymode=None):
        """Export and return a NiTexturingProperty block."""

        self.determine_texture_types(b_mat)

        n_ni_texturing_property = NifClasses.NiTexturingProperty(NifData.data)

        n_ni_texturing_property.flags = b_mat.nif_material.texture_flags
        n_ni_texturing_property.apply_mode = applymode
        n_ni_texturing_property.texture_count = 7

        self.export_texture_shader_effect(n_ni_texturing_property)
        self.export_nitextureprop_tex_descs(n_ni_texturing_property)

        # Search for duplicate
        for n_block in block_store.block_to_obj:
            if isinstance(n_block, NifClasses.NiTexturingProperty) and n_block.get_hash() == n_ni_texturing_property.get_hash():
                n_ni_texturing_property = n_block

        block_store.register_block(n_ni_texturing_property)
        n_ni_geometry.add_property(n_ni_texturing_property)
        if n_bs_shader_property and isinstance(n_bs_shader_property, NifClasses.BSShaderNoLightingProperty):
            n_bs_shader_property.file_name = n_ni_texturing_property.base_texture.source.file_name

    def export_nitextureprop_tex_descs(self, texprop):
        # go over all valid texture slots
        for slot_name, b_texture_node in self.slots.items():
            if b_texture_node:
                # get the field name used by nif xml for this texture
                field_name = f"{slot_name.lower().replace(' ', '_')}_texture"
                NifLog.debug(f"Activating {field_name} for {b_texture_node.name}")
                setattr(texprop, "has_" + field_name, True)
                # get the tex desc link
                texdesc = getattr(texprop, field_name)
                uv_index = self.get_uv_node(b_texture_node)
                # set uv index and source texture to the texdesc
                texdesc.uv_set = uv_index
                texdesc.source = TextureCommon.export_source_texture(b_texture_node)

        # TODO [animation] FIXME Heirarchy
        # self.texture_anim.export_flip_controller(fliptxt, self.base_mtex.texture, texprop, 0)

        # todo [texture] support extra shader textures again
        # if self.slots["Bump Map"]:
        #     if bpy.context.scene.niftools_scene.game not in self.USED_EXTRA_SHADER_TEXTURES:
        #         texprop.has_bump_map_texture = True
        #         self.texture_writer.export_tex_desc(texdesc=texprop.bump_map_texture,
        #                                             uv_set=uv_index,
        #                                             b_texture_node=self.slots["Bump Map"])
        #         texprop.bump_map_luma_scale = 1.0
        #         texprop.bump_map_luma_offset = 0.0
        #         texprop.bump_map_matrix.m_11 = 1.0
        #         texprop.bump_map_matrix.m_12 = 0.0
        #         texprop.bump_map_matrix.m_21 = 0.0
        #         texprop.bump_map_matrix.m_22 = 1.0
        #
        # if self.slots["Normal"]:
        #     shadertexdesc = texprop.shader_textures[1]
        #     shadertexdesc.is_used = True
        #     shadertexdesc.texture_data.source = TextureWriter.export_source_texture(n_texture=self.slots["Bump Map"])
        #
        # if self.slots["Gloss"]:
        #     if bpy.context.scene.niftools_scene.game not in self.USED_EXTRA_SHADER_TEXTURES:
        #         texprop.has_gloss_texture = True
        #         self.texture_writer.export_tex_desc(texdesc=texprop.gloss_texture,
        #                                             uv_set=uv_index,
        #                                             b_texture_node=self.slots["Gloss"])
        #     else:
        #         shadertexdesc = texprop.shader_textures[2]
        #         shadertexdesc.is_used = True
        #         shadertexdesc.texture_data.source = TextureWriter.export_source_texture(n_texture=self.slots["Gloss"])

        # if self.b_ref_slot:
        #     if bpy.context.scene.niftools_scene.game not in self.USED_EXTRA_SHADER_TEXTURES:
        #         NifLog.warn("Cannot export reflection texture for this game.")
        #         # tex_prop.hasRefTexture = True
        #         # self.export_tex_desc(texdesc=tex_prop.refTexture, uv_set=uv_set, mtex=refmtex)
        #     else:
        #         shadertexdesc = texprop.shader_textures[3]
        #         shadertexdesc.is_used = True
        #         shadertexdesc.texture_data.source = TextureWriter.export_source_texture(n_texture=self.b_ref_slot.texture)

    def export_texture_effect(self, b_texture_node=None):
        """Export a texture effect block from material texture mtex (MTex, not Texture)."""
        texeff = NifClasses.NiTextureEffect(NifData.data)
        texeff.flags = 4
        texeff.rotation.set_identity()
        texeff.scale = 1.0
        texeff.model_projection_matrix.set_identity()
        texeff.texture_filtering = NifClasses.TexFilterMode.FILTER_TRILERP
        texeff.texture_clamping = NifClasses.TexClampMode.WRAP_S_WRAP_T
        texeff.texture_type = NifClasses.EffectType.EFFECT_ENVIRONMENT_MAP
        texeff.coordinate_generation_type = NifClasses.CoordGenType.CG_SPHERE_MAP
        if b_texture_node:
            texeff.source_texture = TextureCommon.export_source_texture(b_texture_node.texture)
            if bpy.context.scene.niftools_scene.game == 'MORROWIND':
                texeff.num_affected_node_list_pointers += 1
                # added value doesn't matter since it apparently gets automagically updated in engine
                texeff.affected_node_list_pointers.append(0)
        texeff.unknown_vector.x = 1.0
        return block_store.register_block(texeff)

    def export_texture_shader_effect(self, tex_prop):
        # disable
        return
        # export extra shader textures
        if bpy.context.scene.niftools_scene.game == 'SID_MEIER_S_RAILROADS':
            # sid meier's railroads:
            # some textures end up in the shader texture list there are 5 slots available, so set them up
            tex_prop.num_shader_textures = 5
            tex_prop.reset_field("shader_textures")
            for mapindex, shadertexdesc in enumerate(tex_prop.shader_textures):
                # set default values
                shadertexdesc.is_used = False
                shadertexdesc.map_index = mapindex

            # some texture slots required by the engine
            shadertexdesc_envmap = tex_prop.shader_textures[0]
            shadertexdesc_envmap.is_used = True
            shadertexdesc_envmap.texture_data.source = TextureCommon.export_source_texture(
                filename="RRT_Engine_Env_map.dds")

            shadertexdesc_cubelightmap = tex_prop.shader_textures[4]
            shadertexdesc_cubelightmap.is_used = True
            shadertexdesc_cubelightmap.texture_data.source = TextureCommon.export_source_texture(
                filename="RRT_Cube_Light_map_128.dds")

        elif bpy.context.scene.niftools_scene.game == 'CIVILIZATION_IV':
            # some textures end up in the shader texture list there are 4 slots available, so set them up
            tex_prop.num_shader_textures = 4
            tex_prop.reset_field("shader_textures")
            for mapindex, shadertexdesc in enumerate(tex_prop.shader_textures):
                # set default values
                shadertexdesc.is_used = False
                shadertexdesc.map_index = mapindex

    def add_shader_integer_extra_datas(self, trishape):
        """Add extra data blocks for shader indices."""
        for shaderindex in self.USED_EXTRA_SHADER_TEXTURES[bpy.context.scene.niftools_scene.game]:
            shader_name = self.EXTRA_SHADER_TEXTURES[shaderindex]
            trishape.add_integer_extra_data(shader_name, shaderindex)

    @staticmethod
    def get_n_apply_mode_from_b_blend_type(b_blend_type):
        if b_blend_type == "LIGHTEN":
            return NifClasses.ApplyMode.APPLY_HILIGHT
        elif b_blend_type == "MULTIPLY":
            return NifClasses.ApplyMode.APPLY_HILIGHT2
        elif b_blend_type == "MIX":
            return NifClasses.ApplyMode.APPLY_MODULATE

        NifLog.warn(f"Unsupported blend type ({b_blend_type}) in material, using apply mode APPLY_MODULATE")
        return NifClasses.ApplyMode.APPLY_MODULATE

    def get_uv_node(self, b_texture_node):
        uv_node = self.get_input_node_of_type(b_texture_node.inputs[0],
                                              (bpy.types.ShaderNodeUVMap, bpy.types.ShaderNodeTexCoord))
        if uv_node is None:
            links = b_texture_node.inputs[0].links
            if not links:
                # nothing is plugged in, so it will use the first UV map
                return 0
        if isinstance(uv_node, bpy.types.ShaderNodeUVMap):
            uv_name = uv_node.uv_map
            try:
                # ignore the "UV" prefix
                return int(uv_name[2:])
            except:
                return 0
        elif isinstance(uv_node, bpy.types.ShaderNodeTexCoord):
            return "REFLECT"
        else:
            raise NifError(f"Unsupported vector input for {b_texture_node.name} in material '{self.b_mat.name}''.\n"
                           f"Expected 'UV Map' or 'Texture Coordinate' nodes")

    def get_global_uv_transform_clip(self):
        # get the values from the nodes, find the nodes by name, or search back in the node tree
        x_scale = y_scale = x_offset = y_offset = clamp_x = clamp_y = None
        # first check if there are any of the preset name - much more time efficient
        try:
            combine_node = self.b_mat.node_tree.nodes["Combine UV0"]
            if not isinstance(combine_node, bpy.types.ShaderNodeCombineXYZ):
                combine_node = None
                NifLog.warn(f"Found node with name 'Combine UV0', but it was of the wrong type.")
        except:
            # if there is a combine node, it does not have the standard name
            combine_node = None
            NifLog.warn(f"Did not find node with 'Combine UV0' name.")

        if combine_node is None:
            # did not find a (correct) combine node, search through the first existing texture node vector input
            b_texture_node = None
            for slot_name, slot_node in self.slots.items():
                if slot_node is not None:
                    break
            if slot_node is not None:
                combine_node = self.get_input_node_of_type(slot_node.inputs[0], bpy.types.ShaderNodeCombineXYZ)
                NifLog.warn(f"Searching through vector input of {slot_name} texture gave {combine_node}")

        if combine_node:
            x_link = combine_node.inputs[0].links
            if x_link:
                x_node = x_link[0].from_node
                x_scale = x_node.inputs[1].default_value
                x_offset = x_node.inputs[2].default_value
                clamp_x = x_node.use_clamp
            y_link = combine_node.inputs[1].links
            if y_link:
                y_node = y_link[0].from_node
                y_scale = y_node.inputs[1].default_value
                y_offset = y_node.inputs[2].default_value
                clamp_y = y_node.use_clamp
        return x_scale, y_scale, x_offset, y_offset, clamp_x, clamp_y

    def get_uv_layers(self, b_mat):
        used_uvlayers = set()
        texture_slots = self.get_used_textslots(b_mat)
        for slot in texture_slots:
            used_uvlayers.add(slot.uv_layer)
        return used_uvlayers

    def get_used_textslots(self, b_mat):
        used_slots = []
        if b_mat is not None and b_mat.use_nodes:
            used_slots = [node for node in b_mat.node_tree.nodes if isinstance(node, bpy.types.ShaderNodeTexImage)]
        return used_slots
