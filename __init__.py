bl_info = {
    "name": "Hades II Blender Utility",
    "author": "Lune",
    "version": (1, 0, 0),
    "blender": (4, 1, 0),
    "location": "File > Import > Hades Model (.lz4)",
    "description": "Import Models from Hades II",
    "category": "Import-Export",
}

import bpy
import math
import os
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty
from .lz4_handler import *
from .divine_handler import gr2_to_dae, dae_to_gr2
from .skeleton_handler import import_collada_skeleton, export_collada_skeleton
from .mesh_handler import import_collada_meshes

class ImportHadesFile(bpy.types.Operator, ImportHelper):
    """Import Hades Model File"""
    bl_idname = "import_scene.hades_model"
    bl_label = "Import Hades Model"
    bl_options = {'REGISTER', 'UNDO'}

    filename_ext = ".lz4"
    filter_glob: StringProperty(default="*.lz4", options={'HIDDEN'}, maxlen=255)

    def execute(self, context):
        if bpy.context.space_data.type == 'VIEW_3D':
            bpy.context.space_data.shading.show_backface_culling = True

        lz4_model_path = self.filepath

        try:
            self.report({'INFO'}, "Decompressing LZ4 file...")
            # gr2_model_path = decompress_lz4(lz4_model_path)
            gr2_model_path = decompress_lz4(lz4_model_path)
            if not gr2_model_path:
                raise Exception("Failed to decompress LZ4 file.")

            self.report({'INFO'}, "Converting GR2 to DAE...")
            dae_model_path = gr2_to_dae(gr2_model_path)
            if not dae_model_path:
                raise Exception("Failed to convert GR2 to DAE.")

            self.report({'INFO'}, "Importing COLLADA skeleton...")
            armature = import_collada_skeleton(context, dae_model_path)

            import_collada_meshes(context, dae_model_path, armature)

            armature.rotation_euler = (math.radians(90), 0, 0)  

            self.report({'INFO'}, "Model imported successfully.")

        except Exception as e:
            self.report({'ERROR'}, f"Import failed: {e}")
            return {'CANCELLED'}

        return {'FINISHED'}

class ExportHadesAnimation(bpy.types.Operator, ImportHelper):
    """Export Hades Animation"""
    bl_idname = "export_scene.hades_animation"
    bl_label = "Export Hades Animation"
    bl_options = {'REGISTER', 'UNDO'}

    filename_ext = ".gr2.lz4"
    filter_glob: StringProperty(default="*.gr2.lz4", options={'HIDDEN'}, maxlen=255)

    def execute(self, context):
        if not self.filepath.lower().endswith(".gr2.lz4"):
            export_path = os.path.splitext(self.filepath)[0] + self.filename_ext
        else:
            export_path = self.filepath
        
        try:
            self.report({'INFO'}, f"Exporting animation to {export_path}...")

            #first get the armature
            if bpy.context.active_object and bpy.context.active_object.type == 'ARMATURE':
                armature = bpy.context.active_object
            else:
                armature = next((obj for obj in bpy.data.objects if obj.type == 'ARMATURE'), None)
            
            if armature:
                bpy.ops.object.select_all(action='DESELECT')
                armature.select_set(True)
                bpy.context.view_layer.objects.active = armature

            #then export to .dae using the default exporter. use a temp file
            dae_model_path = export_collada_skeleton(context, armature)

            #then convert to gr2 with divine.exe
            gr2_model_path = dae_to_gr2(dae_model_path, export_path)
            if not gr2_model_path:
                raise Exception("Failed to convert DAE to GR2.")

            #finally compress to lz4
            compress_gr2(gr2_model_path, export_path)

            self.report({'INFO'}, "Animation exported successfully.")
        except Exception as e:
            self.report({'ERROR'}, f"Export failed: {e}")
            return {'CANCELLED'}

        return {'FINISHED'}


def menu_func_import(self, context):
    """Add the importer to the File > Import menu"""
    self.layout.operator(ImportHadesFile.bl_idname, text="Hades II Model (.lz4)")

def menu_func_export(self, context):
    """Add the exporter to the File > Export menu"""
    self.layout.operator(ExportHadesAnimation.bl_idname, text="Hades II Animation (.lz4)")


classes = [ImportHadesFile, ExportHadesAnimation]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)



if __name__ == "__main__":
    register()