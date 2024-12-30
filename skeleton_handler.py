import bpy
import xml.etree.ElementTree as ET
from mathutils import Matrix, Vector, Euler
import tempfile


def import_collada_skeleton(context, filepath):
    empties = {}
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
        namespace = {'collada': root.tag.split('}')[0].strip('{')}
        print(f"Namespace detected: {namespace}")

        visual_scene = root.find(".//collada:library_visual_scenes/collada:visual_scene", namespace)
        if not visual_scene:
            print({'ERROR'}, "No skeleton found in the COLLADA file.")
            return {'CANCELLED'}

        import_hierarchy(visual_scene, namespace, empties, None)

        armature_object = create_armature(context, empties)

        cleanup_scene(context, armature_object, empties)

    except Exception as e:
        print({'ERROR'}, f"Failed to parse COLLADA file: {e}")
        print(f"Error: {e}")
        return {'CANCELLED'}

    print({'INFO'}, "Skeleton imported as empties and armature.")
    print("Import completed successfully.")
    return armature_object


def import_hierarchy(node, namespace, empties, parent_empty):
    for child_node in node.findall("collada:node", namespace):
        if child_node.get("type") == "JOINT":
            empty_object = create_empty_from_joint(child_node, namespace)
            if parent_empty:
                empty_object.parent = parent_empty

            empties[empty_object.name] = empty_object

            import_hierarchy(child_node, namespace, empties, empty_object)


def create_empty_from_joint(node, namespace):
    name = node.get("name", "Unnamed")
    matrix_element = node.find("collada:matrix", namespace)
    transform_matrix = Matrix.Identity(4)  # Default to identity matrix if not found

    if matrix_element is not None:
        matrix_values = list(map(float, matrix_element.text.split()))
        transform_matrix = Matrix([matrix_values[i:i + 4] for i in range(0, 16, 4)])

    empty = bpy.data.objects.new(name, None)
    empty.matrix_world = transform_matrix
    bpy.context.collection.objects.link(empty)
    return empty

def create_armature(context, empties):
    armature = bpy.data.armatures.new("Armature")
    armature_object = bpy.data.objects.new("Armature", armature)
    bpy.context.collection.objects.link(armature_object)
    bpy.context.view_layer.objects.active = armature_object
    bpy.ops.object.mode_set(mode='EDIT')

    edit_bones = armature.edit_bones
    for empty_name, empty in empties.items():
        bone = edit_bones.new(empty_name)
        bone.head = empty.matrix_world.translation
        boneLength = 5

        local_tail = Vector((0, boneLength, 0))
        if empty.parent:
            parent_matrix = empty.matrix_world.to_3x3()  # Only rotation part
            rotated_tail = parent_matrix @ local_tail
            bone.tail = empty.matrix_world.translation + rotated_tail
        else:
            bone.tail = bone.head + local_tail

        if empty.parent and empty.parent.name in edit_bones:
            bone.parent = edit_bones[empty.parent.name]
        
        local_matrix = empty.matrix_world
        loc, rot, sca = local_matrix.decompose()
        local_x = rot @ Vector((0, 0, 1))
        bone.align_roll(local_x)

    bpy.ops.object.mode_set(mode='OBJECT')
    return armature_object

def cleanup_scene(context, armature_object, empties):

    for empty_name, empty in empties.items():
        bpy.data.objects.remove(empty, do_unlink=True)

    context.scene.render.fps = 60
    armature_object.data.relation_line_position = 'HEAD'


def export_collada_skeleton(context, armature):
    if bpy.context.view_layer.objects.active and bpy.context.view_layer.objects.active.type == 'ARMATURE':
        temp_file = tempfile.NamedTemporaryFile(suffix=".dae", delete=False)
        temp_filepath = temp_file.name
        temp_file.close()

        bpy.ops.wm.collada_export(
            filepath = temp_filepath,
            apply_modifiers = False,
            export_mesh_type = 0,
            export_mesh_type_selection = 'view',
            export_global_forward_selection = 'Y',
            export_global_up_selection = 'Z',
            apply_global_orientation = False,
            selected = True,
            include_children = False,
            include_armatures = False,
            include_shapekeys = False,
            deform_bones_only = False,
            include_animations = True,
            include_all_actions = False,
            export_animation_type_selection = 'sample',
            sampling_rate = 1,
            keep_smooth_curves = False,
            keep_keyframes = False,
            keep_flat_curves = False,
            active_uv_only = False,
            use_texture_copies = True,
            triangulate = True,
            use_object_instantiation = True,
            use_blender_profile = True,
            sort_by_name = False,
            export_object_transformation_type = 0,
            export_object_transformation_type_selection = 'matrix',
            export_animation_transformation_type = 0,
            export_animation_transformation_type_selection = 'matrix',
            open_sim = False,
            limit_precision = False,
            keep_bind_info = False
        )
        print(f"Armature exported to {temp_filepath}")
        return temp_filepath
    else:
        print("No armature is selected or active.")