import bpy
import os
import xml.etree.ElementTree as ET
from collections import defaultdict

def import_collada_meshes(context, filepath, armature):
    if not os.path.isfile(filepath):
        print(f"File not found: {filepath}")
        return

    tree = ET.parse(filepath)
    root = tree.getroot()
    namespace = {'c': 'http://www.collada.org/2005/11/COLLADASchema'}

    controller_data = parse_controllers(root, namespace)
    library_geoms = root.find('c:library_geometries', namespace)

    if library_geoms is None:
        return
    
    geometry_list = library_geoms.findall('c:geometry', namespace)
    if not geometry_list:
        return


    for geometry_elem in geometry_list:
        geom_id = geometry_elem.get('id')
        
        result = parse_geometry(geometry_elem, namespace)
        if not result:
            continue
        
        mesh_name, final_verts, faces, pos_map = result
        obj, _ = build_blender_mesh(mesh_name, final_verts, faces)
        
        if geom_id in controller_data:
            skin_data = controller_data[geom_id]
            apply_vertex_weights(obj, skin_data, pos_map, armature)
        else:
            pass


def parse_controllers(root, namespace):
    controllers_map = {}
    
    lib_controllers = root.find('c:library_controllers', namespace)
    if lib_controllers is None:
        return controllers_map
    
    for ctrl_elem in lib_controllers.findall('c:controller', namespace):
        skin_elem = ctrl_elem.find('c:skin', namespace)
        if skin_elem is None:
            continue
        
        geom_ref = skin_elem.get('source')
        if not geom_ref:
            continue
        geom_id = strip_hash(geom_ref)

        skin_data = parse_skin_data(skin_elem, namespace)
        if skin_data:
            controllers_map[geom_id] = skin_data
    
    return controllers_map


def parse_skin_data(skin_elem, namespace):
    joints_elem = skin_elem.find('c:joints', namespace)
    if joints_elem is None:
        print("No <joints> in <skin>.")
        return None

    joint_input = joints_elem.find("c:input[@semantic='JOINT']", namespace)
    if joint_input is None:
        print("No <input semantic='JOINT'> in <joints>.")
        return None
    
    joint_source_id = strip_hash(joint_input.get('source'))
    joint_source = skin_elem.find(f".//c:source[@id='{joint_source_id}']", namespace)
    if joint_source is None:
        print(f"No joint source found for {joint_source_id}")
        return None
    
    name_array = joint_source.find('c:Name_array', namespace)
    if name_array is None:
        print("No <Name_array> in joint source.")
        return None
    joint_names = name_array.text.strip().split()

    vw_elem = skin_elem.find('c:vertex_weights', namespace)
    if vw_elem is None:
        print("No <vertex_weights> in <skin>.")
        return None

    weight_input = vw_elem.find("c:input[@semantic='WEIGHT']", namespace)
    if weight_input is None:
        print("No <input semantic='WEIGHT'> in <vertex_weights>.")
        return None
    weight_source_id = strip_hash(weight_input.get('source'))

    weight_source = skin_elem.find(f".//c:source[@id='{weight_source_id}']/c:float_array", namespace)
    if weight_source is None:
        print(f"No weight float_array for {weight_source_id}")
        return None
    all_weights = [float(x) for x in weight_source.text.strip().split()]

    vcount_elem = vw_elem.find('c:vcount', namespace)
    v_elem = vw_elem.find('c:v', namespace)
    if vcount_elem is None or v_elem is None:
        print("Missing <vcount> or <v> in <vertex_weights>.")
        return None

    vcount_list = [int(x) for x in vcount_elem.text.strip().split()]
    v_list = [int(x) for x in v_elem.text.strip().split()]

    return {
        'joint_names': joint_names,
        'weights': all_weights,
        'vcount': vcount_list,
        'v': v_list,
    }

def strip_hash(s):
    return s[1:] if s.startswith('#') else s


def get_floats_from_source(mesh_elem, source_id, namespace):
    float_array = mesh_elem.find(f".//c:source[@id='{source_id}']/c:float_array", namespace)
    if float_array is None:
        return []
    text_data = float_array.text.strip().split()
    return [float(x) for x in text_data]


def parse_geometry(geometry_elem, namespace):
    mesh_elem = geometry_elem.find('c:mesh', namespace)
    if mesh_elem is None:
        print("No <mesh> child found under <geometry>.")
        return None

    vertices_elem = mesh_elem.find('c:vertices', namespace)
    if vertices_elem is None:
        print("No <vertices> element.")
        return None

    pos_input = vertices_elem.find("c:input[@semantic='POSITION']", namespace)
    if pos_input is None:
        print("No input semantic='POSITION' in <vertices>.")
        return None
    pos_source_id = strip_hash(pos_input.get('source'))
    
    triangles_elem = mesh_elem.find('c:triangles', namespace)
    if triangles_elem is None:
        print("No <triangles> element found.")
        return None

    normal_input = triangles_elem.find("c:input[@semantic='NORMAL']", namespace)
    uv_input = triangles_elem.find("c:input[@semantic='TEXCOORD']", namespace)
    if normal_input is None or uv_input is None:
        print("Missing NORMAL or TEXCOORD inputs in <triangles>.")
        return None
    
    normal_source_id = strip_hash(normal_input.get('source'))
    uv_source_id = strip_hash(uv_input.get('source'))

    pos_floats = get_floats_from_source(mesh_elem, pos_source_id, namespace)
    norm_floats = get_floats_from_source(mesh_elem, normal_source_id, namespace)
    uv_floats = get_floats_from_source(mesh_elem, uv_source_id, namespace)

    positions = list(zip(pos_floats[0::3],  pos_floats[1::3],  pos_floats[2::3]))
    normals   = list(zip(norm_floats[0::3], norm_floats[1::3], norm_floats[2::3]))
    uvs       = list(zip(uv_floats[0::2],   uv_floats[1::2]))
    
    p_elem = triangles_elem.find('c:p', namespace)
    if p_elem is None:
        print("No <p> element inside <triangles>.")
        return None

    all_indices = [int(x) for x in p_elem.text.strip().split()]
    stride = 3
    triangle_count = int(triangles_elem.get('count'))

    expected_len = triangle_count * 3 * stride
    if len(all_indices) != expected_len:
        print(f"Warning: expected {expected_len} indices, found {len(all_indices)}.")

    vertex_map = {}
    final_verts = []
    faces = []

    pos_map = defaultdict(list)

    for tri_idx in range(triangle_count):
        face_indices = []
        for corner in range(3):
            base_idx = (tri_idx * 3 * stride) + (corner * stride)
            pos_i  = all_indices[base_idx + 0]
            norm_i = all_indices[base_idx + 1]
            uv_i   = all_indices[base_idx + 2]

            key = (pos_i, norm_i, uv_i)
            if key not in vertex_map:
                blender_vert_idx = len(final_verts)

                vpos  = positions[pos_i] if pos_i  < len(positions) else (0.0, 0.0, 0.0)
                vnorm = normals[norm_i]  if norm_i < len(normals)   else (0.0, 0.0, 1.0)
                vuv   = uvs[uv_i]        if uv_i   < len(uvs)       else (0.0, 0.0)

                final_verts.append((vpos, vuv, vnorm))
                vertex_map[key] = blender_vert_idx

            blender_vert_index = vertex_map[key]
            face_indices.append(blender_vert_index)

            pos_map[pos_i].append(blender_vert_index)

        faces.append(face_indices)

    mesh_name = geometry_elem.get('name', geometry_elem.get('id', 'Mesh'))
    return (mesh_name, final_verts, faces, pos_map)


def build_blender_mesh(mesh_name, final_verts, faces):
    mesh_data = bpy.data.meshes.new(mesh_name)

    verts_coords = [v[0] for v in final_verts]

    mesh_data.from_pydata(verts_coords, [], faces)
    mesh_data.update()

    uv_layer = mesh_data.uv_layers.new(name='UVMap')
    for poly in mesh_data.polygons:
        for loop_idx, vert_idx in zip(poly.loop_indices, poly.vertices):
            uv_layer.data[loop_idx].uv = final_verts[vert_idx][1]

    loop_normals = [None] * len(mesh_data.loops)
    for poly in mesh_data.polygons:
        for loop_idx in poly.loop_indices:
            v_idx = mesh_data.loops[loop_idx].vertex_index
            loop_normals[loop_idx] = final_verts[v_idx][2]

    obj = bpy.data.objects.new(mesh_data.name, mesh_data)
    bpy.context.scene.collection.objects.link(obj)
    
    for poly in obj.data.polygons:
        poly.use_smooth = True

    collada_to_blender_map = {}

    return obj, collada_to_blender_map


def apply_vertex_weights(obj, skin_data, pos_map, armature):
    # mesh_data = obj.data

    joint_names = skin_data['joint_names']
    all_weights = skin_data['weights']
    vcount_list = skin_data['vcount']
    v_list      = skin_data['v']

    for jname in joint_names:
        obj.vertex_groups.new(name=jname)

    idx_v = 0
    for collada_vert_idx, num_influences in enumerate(vcount_list):
        if num_influences == 0:
            continue

        for _ in range(num_influences):
            j_idx = v_list[idx_v]
            w_idx = v_list[idx_v + 1]
            idx_v += 2

            if j_idx < len(joint_names) and w_idx < len(all_weights):
                group_name = joint_names[j_idx]
                raw_weight_val = all_weights[w_idx]

                weight_val = raw_weight_val / num_influences

                if collada_vert_idx in pos_map:
                    for blender_vert_idx in pos_map[collada_vert_idx]:
                        vg = obj.vertex_groups.get(group_name)
                        if vg:
                            vg.add([blender_vert_idx], weight_val, 'ADD')
                            
    parent_mesh_to_armature(obj, armature)
    replace_colon_in_vertex_groups(obj)

    
def parent_mesh_to_armature(obj, armature):
    obj.parent = armature
    if not any(mod.type == 'ARMATURE' and mod.object == armature for mod in obj.modifiers):
        armature_mod = obj.modifiers.new(name="Armature", type='ARMATURE')
        armature_mod.object = armature

    
def replace_colon_in_vertex_groups(obj):
    if obj.type == 'MESH':
        for vgroup in obj.vertex_groups:
            if ':' in vgroup.name:
                new_name = vgroup.name.replace(':', '_x003A_')
                vgroup.name = new_name
