# **********************************************************************
# Copyright 2020 Advanced Micro Devices, Inc
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#********************************************************************
import traceback

import MaterialX as mx

import bpy

from . import HdUSD_Panel, HdUSD_Operator
from ..mx_nodes.node_tree import MxNodeTree
from ..utils import mx as mx_utils
from .. import config

from ..utils import logging
log = logging.Log(tag='ui.matlib')


class HDUSD_MATERIAL_OP_matlib_clear_search(bpy.types.Operator):
    """Create new MaterialX node tree for selected material"""
    bl_idname = "hdusd.matlib_clear_search"
    bl_label = ""

    def execute(self, context):
        context.window_manager.hdusd.matlib.search = ''
        return {"FINISHED"}


class HDUSD_MATLIB_OP_import_material(HdUSD_Operator):
    """Import Material"""
    bl_idname = "hdusd.matlib_import_material"
    bl_label = "Import Material"

    def execute(self, context):
        matlib_prop = context.window_manager.hdusd.matlib
        material = matlib_prop.pcoll.materials[matlib_prop.material]

        # unzipping package
        package = next(package for package in material.packages
                       if package.id == matlib_prop.package_id)

        package.get_info()
        package.get_file()
        mtlx_file = package.unzip()

        # getting/creating MxNodeTree
        bl_material = context.material
        mx_node_tree = bl_material.hdusd.mx_node_tree
        if not bl_material.hdusd.mx_node_tree:
            mx_node_tree = bpy.data.node_groups.new(f"MX_{bl_material.name}",
                                                    type=MxNodeTree.bl_idname)
            bl_material.hdusd.mx_node_tree = mx_node_tree

        log("Reading", mtlx_file)
        doc = mx.createDocument()
        search_path = mx.FileSearchPath(str(mtlx_file.parent))
        search_path.append(str(mx_utils.MX_LIBS_DIR))
        try:
            mx.readFromXmlFile(doc, str(mtlx_file), searchPath=search_path)
            mx_node_tree.import_(doc, mtlx_file)

        except Exception as e:
            log.error(traceback.format_exc(), mtlx_file)
            return {'CANCELLED'}

        return {"FINISHED"}


class HDUSD_MATLIB_OP_load_package(HdUSD_Operator):
    """Reload Material"""
    bl_idname = "hdusd.matlib_load_package"
    bl_label = "Load package"

    def execute(self, context):
        matlib_prop = context.window_manager.hdusd.matlib
        material = matlib_prop.pcoll.materials[matlib_prop.material]

        # unzipping package
        package = next(package for package in material.packages
                       if package.id == matlib_prop.package_id)

        package.get_info(False)
        package.get_file(False)
        package.unzip(False)

        return {"FINISHED"}


class HDUSD_MATLIB_PT_matlib(HdUSD_Panel):
    bl_label = "Material Library"
    bl_context = "material"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        return super().poll(context) and config.matlib_enabled

    def draw(self, context):
        layout = self.layout
        matlib_prop = context.window_manager.hdusd.matlib

        # status
        if matlib_prop.pcoll.materials is None:
            layout.label(text="No materials loaded")
            matlib_prop.load_data()
            return

        # category
        layout.prop(matlib_prop, 'category_id')

        # search
        row = layout.row(align=True)
        row.prop(matlib_prop, 'search', text="", icon='VIEWZOOM')
        if matlib_prop.search:
            row.operator(HDUSD_MATERIAL_OP_matlib_clear_search.bl_idname, icon='X')

        # materials
        col = layout.column(align=True)
        materials = matlib_prop.get_materials()
        if not materials:
            col.label(text="No materials found")
            return

        col.template_icon_view(matlib_prop, 'material_id', show_labels=True)

        mat = materials.get(matlib_prop.material_id)
        if not mat:
            return

        # other material renders
        if len(mat.renders) > 1:
            grid = col.grid_flow(align=True)
            for i, render in enumerate(mat.renders):
                if i % 6 == 0:
                    row = grid.row()
                    row.alignment = 'CENTER'

                row.template_icon(render.thumbnail_icon_id, scale=5)

        # material description
        row = col.row()
        row.alignment = 'CENTER'
        row.label(text=mat.title)

        if mat.description:
            col.label(text=mat.description)
        col.label(text=f"Category: {mat.category.title}")

        # packages
        row = layout.row(align=True)
        row.prop(matlib_prop, 'package_id', icon='DOCUMENTS')
        package = next(p for p in mat.packages if p.id == matlib_prop.package_id)
        row.operator(HDUSD_MATLIB_OP_load_package.bl_idname, text="",
                     icon='FILE_REFRESH' if package.has_file else 'IMPORT')

        row = layout.row()
        row.enabled = bool(context.material)
        row.operator(HDUSD_MATLIB_OP_import_material.bl_idname, text="Import Material Package",
                     icon='IMPORT')


class HDUSD_MATLIB_MT_package_menu(bpy.types.Menu):
    bl_label = "Package"
    bl_idname = "HDUSD_MATLIB_MT_package_menu"

    def draw(self, context):
        layout = self.layout
        op_idname = HDUSD_MATLIB_OP_select_package.bl_idname

        matlib_prop = context.window_manager.hdusd.matlib
        packages = matlib_prop.pcoll.materials[matlib_prop.material].packages

        for package in packages:
            if package.file is None:
                package.get_info()

            row = layout.row()
            op = row.operator(op_idname, text=f"{package.label} ({package.size})",
                              icon='DOCUMENTS')
            op.matlib_package_id = package.id


class HDUSD_MATLIB_OP_select_package(bpy.types.Operator):
    """Select Package"""
    bl_label = "Select Package"
    bl_idname = "hdusd.matlib_select_package"

    matlib_package_id: bpy.props.StringProperty(default="")

    def execute(self, context):
        context.window_manager.hdusd.matlib.package_id = self.matlib_package_id
        return {"FINISHED"}
