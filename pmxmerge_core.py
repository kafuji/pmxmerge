"""
pmxmerge.py - A script to merge PMX models by patching bones, materials and morphs.
Version 1.0.0

This script merges two PMX models: a base model and a patch model.

The main purpose is to update existing model with partially edited model which is exported from DCC tools like Blender, Maya, etc.
Or you can use it to make an chimera model by merging multiple models together (e.g. combining a character model with a prop model).
The patch model can contain new bones, materials, morphs, and physics, which are merged into the base model.

These features are replaced/merged or appended:
    - Bones: Patch bones are appended to the base model, existing bones are left unchanged by default.
    - Materials: Patch materials(and it's textures, faces, and vertices) are merged into the base model, replacing existing ones with the same name.
    - Morphs: Patch morphs are merged into the base model, replacing existing ones with the same name while keeping their order.
    - Rigid Bodies and Joints: Patch rigid bodies and joints are merged into the base model, replacing existing ones with the same name.

These features are left unchanged:
    - Existing Bones, Materials, Morphs, Rigid Bodies and Joints sort order
    - Display Settings: Not implemented yet, but can be merged in the future.

Unsupported features (Removed from the model when loading):
    - Soft Body Settings (no one uses it anyway)

Copyright (c) 2025 Kafuji Sato

LICENCE: GPL-3.0-or-later (https://www.gnu.org/licenses/gpl-3.0.en.html)
"""

from typing import Dict, List, Tuple

import pmx


def detect_duplicate_elements(model: pmx.Model) -> bool:
    """Check for duplicate bones, materials, and morphs in the model."""

    def check(collection: list) -> bool:
        """Check if there are duplicate items in the list."""
        seen = set()
        duplicate_found = False
        for item in collection:
            if item.name in seen:
                print(f"Duplicate item found: {item.name} (type: {type(item)}, index: {collection.index(item)})")
                duplicate_found = True
                continue
            seen.add(item.name)
        return duplicate_found

    ret = False
    ret |= check(model.bones)
    ret |= check(model.materials)
    ret |= check(model.morphs)

    return ret


def merge_bones(base: pmx.Model, patch: pmx.Model, replace_bones: bool=False) -> None:
    """Append patch model's bones to base model, skip existing bones(same as PMX Editor behavior)."""

    print(f"* Replace bone settings: {replace_bones}")

    if not patch.bones:
        # print("No bones in patch model, skipping bone merge.")
        return

    # Create a mapping of patch bone names to their indices in the base model, and append new bones
    # We must consider base bones and patch bones have different order
    patch_to_base_bone_map: Dict[int, int] = {}
    bones_appended = set()  # Track already appended bones
    bones_modified = set()  # Track modified bones
    for i, patch_bone in enumerate(patch.bones):
        # Find the corresponding bone in the base model
        base_index = next((j for j, b in enumerate(base.bones) if b.name == patch_bone.name), None)
        if base_index is not None: # already exists in base model
            patch_to_base_bone_map[i] = base_index
            if replace_bones:
                # Update bone settings from patch to base
                b: pmx.Bone = base.bones[base_index]
                b.name_e = patch_bone.name_e
                b.location = patch_bone.location
                b.parent = patch_bone.parent
                b.transform_order = patch_bone.transform_order
                b.displayConnection = patch_bone.displayConnection

                b.isRotatable = patch_bone.isRotatable
                b.isMovable = patch_bone.isMovable
                b.visible = patch_bone.visible
                b.isControllable = patch_bone.isControllable

                b.isIK = patch_bone.isIK

                b.hasAdditionalRotate = patch_bone.hasAdditionalRotate
                b.hasAdditionalLocation = patch_bone.hasAdditionalLocation
                if b.hasAdditionalRotate or b.hasAdditionalLocation:
                    b.additionalTransform = patch_bone.additionalTransform
                else:
                    b.additionalTransform = None

                b.axis = patch_bone.axis
                b.localCoordinate = patch_bone.localCoordinate
                b.transAfterPhis = patch_bone.transAfterPhis
                b.externalTransKey = patch_bone.externalTransKey

                if b.isIK:
                    b.target = patch_bone.target
                    b.ik_links = patch_bone.ik_links.copy()

                # Bone references above may need to be updated later
                bones_modified.add((i, b))  # Track modified bones

        else: # not found in base model, append it
            patch_to_base_bone_map[i] = len(base.bones)
            base.bones.append(patch_bone)
            print(f"🦴➕️ Appending new bone '{patch_bone.name}' at index {patch_to_base_bone_map[i]}")
            bones_appended.add((i, patch_bone))

    # If bone order is identical, we can skip remapping
    # This is a common case when patch model has only material or morph changes
    need_remap = any(patch_to_base_bone_map[i] != i for i in range(len(patch.bones)))

    if not need_remap:
        # print("No new bones to append or re-order, skipping bone merge.")
        return

    # Update bone references in patch model
    # We need to update bone indices in patch model to match base model's bone indices
    # If patch model has proper bone references, we can find them in the base model.
    # But if patch model has incorrect bone references, we just set them to -1 (unset).
    # It is better than leaving them as is, because it may cause issues later.

    # print("Updating bone references in patch model...")

    # Update appended/modified bone's refrerences (parent, displayConnection, addtitionalTransform, IK target, IKLink.target which are all bone indices)
    for i, patch_bone in bones_modified.union(bones_appended):
        base_index = patch_to_base_bone_map[i]
        b: pmx.Bone = base.bones[base_index]

        # Update parent index
        if b.parent is not None:
            b.parent = patch_to_base_bone_map.get(b.parent, -1)

        # Update displayConnection
        if isinstance(b.displayConnection, int) and b.displayConnection != -1:  # -1 means unset
            b.displayConnection = patch_to_base_bone_map.get(b.displayConnection, -1)

        # Update additionalTransform
        if b.additionalTransform is not None: # Tuple(bone_index, value) or None
            b.additionalTransform = (patch_to_base_bone_map.get(b.additionalTransform[0], -1), b.additionalTransform[1])

        # Update IK target
        if b.isIK:
            if b.target > -1:  # -1 means unset
                b.target = patch_to_base_bone_map.get(b.target, -1)

            # Update IK links
            for link in b.ik_links:
                link: pmx.IKLink
                link.target = patch_to_base_bone_map.get(link.target, -1)

    # Update bone references in patch models vertices (Vertex.weights[BoneWeight])
    for vertex in patch.vertices:
        vertex: pmx.Vertex
        weight = vertex.weight # BoneWeight
        if not weight:
            continue
    
        for i, bone_index in enumerate(weight.bones):
            weight.bones[i] = patch_to_base_bone_map.get(bone_index, -1)  # -1 means unset

    # Update bone indices in patch bone morphs
    for morph in (m for m in patch.morphs if isinstance(m, pmx.BoneMorph)):
        for offset in morph.offsets:
            offset.index = patch_to_base_bone_map.get(offset.index, -1)  # -1 means unset

    return


def compute_face_segments(vertex_counts: List[int]) -> List[Tuple[int, int]]:
    """Compute face index ranges (start, end) for each material."""
    segments = []
    offset = 0
    for count in vertex_counts:
        face_count = count // 3
        segments.append((offset, offset + face_count))
        offset += face_count
    return segments


def remove_material(model: pmx.Model, mat_name:str) -> None:
    """Remove a material and its associated faces, vertices, and vertex morphs."""

    idx = next((i for i, m in enumerate(model.materials) if m.name == mat_name), None)
    if idx is None:
        print(f"Material '{mat_name}' not found in the model.")
        return

    # Original counts and segments
    orig_counts = [m.vertex_count for m in model.materials]
    segments = compute_face_segments(orig_counts)

    # Remove faces for the material
    start, end = segments[idx]
    new_faces = model.faces[:start] + model.faces[end:]
    model.faces = new_faces

    # Remove material and its count
    del model.materials[idx]

    # Recalculate vertex_count for remaining materials
    remaining_segs = [seg for i, seg in enumerate(segments) if i != idx]
    for m, seg in zip(model.materials, remaining_segs):
        m.vertex_count = (seg[1] - seg[0]) * 3

    # Identify used vertex indices
    used = {v for face in model.faces for v in face}

    # Rebuild vertex list and index map
    old_vertices = model.vertices
    new_vertices = []
    index_map: Dict[int, int] = {}
    for old_idx, vert in enumerate(old_vertices):
        if old_idx in used:
            index_map[old_idx] = len(new_vertices)
            new_vertices.append(vert)
    model.vertices = new_vertices

    # Remap face indices
    model.faces = [(index_map[a], index_map[b], index_map[c]) for (a, b, c) in model.faces]

    # Update vertex morphs, remove those that reference removed vertices
    for morph in (m for m in model.morphs if isinstance(m, pmx.VertexMorph)):
        morph.offsets = [o for o in morph.offsets if o.index in index_map]
        for offset in morph.offsets:
            offset.index = index_map.get(offset.index, offset.index)
    
    # Update UV morphs, remove those that reference removed vertices
    for morph in (m for m in model.morphs if isinstance(m, pmx.UVMorph)):
        morph: pmx.UVMorph
        morph.offsets = [o for o in morph.offsets if o.index in index_map]
        for offset in morph.offsets:
            offset.index = index_map.get(offset.index, offset.index)

    return


def merge_geometry(base: pmx.Model, patch: pmx.Model) -> None:
    """Append patch model's geometry (vertices, faces, materials) to base model."""

    # Merge textures
    patch_to_base_tex: Dict[int, int] = {}
    for i, p_tex in enumerate(patch.textures):
        # Find or append texture
        for j, b_tex in enumerate(base.textures):
            if b_tex.path == p_tex.path:
                patch_to_base_tex[i] = j
                break
        else:
            patch_to_base_tex[i] = len(base.textures)
            base.textures.append(p_tex)
            print(f"🖼️➕ Appending new texture '{p_tex.path}' at index {patch_to_base_tex[i]}")

    # Append vertices
    vert_offset = len(base.vertices)
    base.vertices.extend(patch.vertices)

    # Update vertex indices in patch morphs (to be merged later)
    for morph in (m for m in patch.morphs if isinstance(m, pmx.VertexMorph)):
        for offset in morph.offsets:
            offset.index += vert_offset

    # Append faces (remapped)
    for face in patch.faces:
        base.faces.append((face[0] + vert_offset,
                           face[1] + vert_offset,
                           face[2] + vert_offset))

    # Append materials (with updated texture indices)
    for mat in patch.materials:
        mat: pmx.Material
        mat.texture = patch_to_base_tex.get(mat.texture, mat.texture)
        mat.sphere_texture = patch_to_base_tex.get(mat.sphere_texture, mat.sphere_texture)
        if not mat.is_shared_toon_texture:
            mat.toon_texture = patch_to_base_tex.get(mat.toon_texture, mat.toon_texture)
        base.materials.append(mat)

    # Update Material morphs in patch (to be merged later)
    for morph in (m for m in patch.morphs if isinstance(m, pmx.MaterialMorph)):
        for offset in morph.offsets:
            offset: pmx.MaterialMorphOffset
            # Remap material index to base model
            if offset.index < len(patch.materials) and offset.index >= 0:
                offset.index = next((i for i, m in enumerate(base.materials) if m.name == patch.materials[offset.index].name), -1)

    return


def reorder_materials(base: pmx.Model, desired_order: List[str]) -> None:
    """Reorder materials and corresponding face segments to match desired_order."""
    # Current segmentation
    counts = [m.vertex_count for m in base.materials]
    segments = compute_face_segments(counts)

    # Build mapping from material name to its segment and material instance
    name_to_seg = {m.name: seg for m, seg in zip(base.materials, segments)}
    name_to_mat = {m.name: m for m in base.materials}

    # Rebuild materials in new order
    new_materials = [name_to_mat[name] for name in desired_order if name in name_to_mat]
    mat_indices_before_after = {} # {old_idx, new_idx}
    for i, mat in enumerate(base.materials):
        new_idx = desired_order.index(mat.name) if mat.name in desired_order else -1
        mat_indices_before_after[i] = new_idx

    base.materials = new_materials

    # Rebuild faces accordingly
    new_faces = []
    for name in desired_order:
        seg = name_to_seg.get(name)
        if seg:
            start, end = seg
            for face in base.faces[start:end]:
                new_faces.append(face)
    base.faces = new_faces

    # Update vertex_count
    for m in base.materials:
        seg = name_to_seg[m.name]
        m.vertex_count = (seg[1] - seg[0]) * 3

    # Update Material morphs to match new material indices
    for morph in (m for m in base.morphs if isinstance(m, pmx.MaterialMorph)):
        for offset in morph.offsets:
            offset: pmx.MaterialMorphOffset
            if offset.index in mat_indices_before_after:
                offset.index = mat_indices_before_after[offset.index]
            else:
                offset.index = -1  # Unset if not found

    return



def merge_morphs(base: pmx.Model, patch: pmx.Model, bone_index_map: Dict[int, int] = None) -> None:
    """Append patch model's morphs to base model, replace/merge existing ones with the same name while keeping their order."""

    existing_morph_names = {m.name for m in base.morphs}
    replace_map: Dict[int, int] = {}  # Map patch morph indices to base morph indices for replacement
    new_morphs = []
    morph_index_map: Dict[int, int] = {}  # Map patch morph indices to base morph indices, used for GroupMorph remapping

    # Create a mapping of patch morph indices to base morph indices 
    for i, morph in enumerate(patch.morphs):
        if morph.name in existing_morph_names:  # Will be replaced in base model
            existing_index = next((j for j, m in enumerate(base.morphs) if m.name == morph.name), None)
            replace_map[i] = existing_index
            morph_index_map[i] = existing_index  # Map patch morph index to base morph index
        else:  # Will be appended to base model
            morph_index_map[i] = len(base.morphs) + len(new_morphs)  # offset by existing morphs
            new_morphs.append(morph)
            print(f"Ⓜ➕️Appending new morph '{morph.name}' at index {morph_index_map[i]}")

    # Update GroupMorph offsets to point to the correct morph indices in base model
    for morph in (m for m in patch.morphs if isinstance(m, pmx.GroupMorph)):
        morph: pmx.GroupMorph
        for offset in morph.offsets:
            offset: pmx.GroupMorphOffset
            offset.morph = morph_index_map.get(offset.morph, -1)

    # Append new morphs to base model
    base.morphs.extend(new_morphs)

    # Replace existing morphs in base model with patch morphs
    for patch_index, base_index in replace_map.items():
        morph = patch.morphs[patch_index]
        existing = base.morphs[base_index]

        # print(f"Replacing morph '{morph.name}' at index {base_index} with patch morph '{morph.name}' at index {patch_index}")

        # If already exist and they are different types, we cannot merge them no matter what. Just replace the existing morph with the new one.
        if existing and existing.type_index() != morph.type_index():
            base.morphs[base_index] = morph
            continue

        # Process morphs based on their type
        if isinstance(morph, pmx.GroupMorph): # We already remapped GroupMorph offsets above
            base.morphs[base_index] = morph # Replace existing morph with the new one
            continue

        if isinstance(morph, pmx.VertexMorph): # Vertex indices must be remapped at merge_geometry
            base.morphs[base_index].offsets.extend(morph.offsets) # Append offsets to existing morph
            continue

        if isinstance(morph, pmx.BoneMorph): # Bone indices must be remapped at merge_bones
            base.morphs[base_index] = morph # Replace existing morph with the new one
            continue

        if isinstance(morph, pmx.UVMorph): # UVMorph offsets must be remapped at merge_geometry
            base.morphs[base_index].offsets.extend(morph.offsets) # Append offsets to existing morph

        if isinstance(morph, pmx.MaterialMorph): # Material indices must be remapped at merge_geometry
            base.morphs[base_index] = morph

    return


def merge_rigidbodies_and_joints(base: pmx.Model, patch: pmx.Model) -> None:
    """Merge patch model's physics (Rigid Bodies and Joints) into base model."""

    # Create bone idx map patch -> base (assuming patch's bones are already appended to base model)
    patch_to_base_bone_map: Dict[int, int] = {}
    for i, patch_bone in enumerate(patch.bones):
        # Find the corresponding bone in the base model
        base_index = next((j for j, b in enumerate(base.bones) if b.name == patch_bone.name), None)
        if base_index is not None:  # already exists in base model
            patch_to_base_bone_map[i] = base_index
        else:  # May never happen
            raise ValueError(f"Bone '{patch_bone.name}' from patch model not found in base model. Please ensure bones are merged before merging physics.")

    # Update bone references in patch rigid bodies
    for rb in patch.rigids:
        if rb.bone in patch_to_base_bone_map:
            rb.bone = patch_to_base_bone_map[rb.bone]
            # print(f"⭕️ Updating rigid body '{rb.name}' bone reference to {rb.bone} (patch -> base)")
        else:
            # print(f"❌️ Rigid body '{rb.name}' bone reference {rb.bone} not found in patch bones, setting to -1 (unset).")
            rb.bone = -1  # Unset if not found

    # Append/Replace rigid bodies, while prepareing rigid body index map (patch -> base)
    patch_to_base_rigid_map: Dict[int, int] = {}
    for i, rb in enumerate(patch.rigids):
        existing_index = next((i for i, b in enumerate(base.rigids) if b.name == rb.name), None)
        if existing_index is not None:
            # Replace existing rigid body
            base.rigids[existing_index] = rb
            patch_to_base_rigid_map[i] = existing_index
            print(f"💎♻️ Replacing existing rigid body '{rb.name}' at index {existing_index} with patch rigid body.")
        else:
            # Append new rigid body
            base.rigids.append(rb)
            patch_to_base_rigid_map[i] = len(base.rigids) - 1
            print(f"💎➕ Appending new rigid body '{rb.name}' at index {patch_to_base_rigid_map[i]}")

    # Update joint references in patch joints
    for joint in patch.joints:
        if joint.src_rigid in patch_to_base_rigid_map:
            joint.src_rigid = patch_to_base_rigid_map[joint.src_rigid]
            # print(f"⭕️ Updating joint '{joint.name}' source rigid reference to {joint.src_rigid} (patch -> base)")
        else:
            joint.src_rigid = -1
            # print(f"❌️ Joint '{joint.name}' source rigid reference {joint.src_rigid} not found in patch rigid bodies, setting to -1 (unset).")
        if joint.dest_rigid in patch_to_base_rigid_map:
            joint.dest_rigid = patch_to_base_rigid_map[joint.dest_rigid]
            # print(f"⭕️ Updating joint '{joint.name}' destination rigid reference to {joint.dest_rigid} (patch -> base)")
        else:
            joint.dest_rigid = -1
            # print(f"❌️ Joint '{joint.name}' destination rigid reference {joint.dest_rigid} not found in patch rigid bodies, setting to -1 (unset).")

    # Append/Replace joints
    for joint in patch.joints:
        existing_index = next((i for i, j in enumerate(base.joints) if j.name == joint.name), None)
        if existing_index is not None:
            # Replace existing joint
            print(f"🔗♻️ Replacing existing joint '{joint.name}' at index {existing_index} with patch joint.")
            base.joints[existing_index] = joint
        else:
            # Append new joint
            print(f"🔗➕ Appending new joint '{joint.name}'")
            base.joints.append(joint)

    return


def merge_displaysettings(base: pmx.Model, patch: pmx.Model) -> None:
    """Merge patch model's display settings into base model."""
    print("Merging display settings is not implemented yet.")

    # Placeholder for merging display settings

    return


# Process pmx.Model objects by merging patch into base
def merge_models(base: pmx.Model, patch: pmx.Model, replace_bones: bool=False, merge_phys: bool=False, merge_disp: bool=False) -> None:
    """Merge patch into base: replace existing patch materials, then append."""

    # Merge patch bones
    merge_bones(base, patch, replace_bones)

    # Record original order
    original_names = [m.name for m in base.materials]
    patch_names = [m.name for m in patch.materials]

    # Remove existing materials from base
    for name in patch_names:
        if name in original_names:
            remove_material(base, name)
            # print(f"Replacing existing material '{name}' in base model.")
        else:
            print(f"🟡➕️ Appending new material '{name}'.")

    # Merge patch geometry
    merge_geometry(base, patch)

    # Merge patch morphs
    merge_morphs(base, patch)

    # Compute new desired order: originals without patch, then patch at end
    # desired = [n for n in original_names if n not in patch_names] + patch_names
    desired = [n for n in original_names]
    for n in patch_names:
        if n not in desired:
            desired.append(n)

    # Reorder materials and faces
    reorder_materials(base, desired)

    # Merge physics if requested
    if merge_phys:
        merge_rigidbodies_and_joints(base, patch)

    # Merge display settings if requested
    if merge_disp:
        # Not implemented yet, but can be done by merging DisplaySettings
        # merge_displaysettings(base, patch)
        # For now, just print a message
        print("Merging display settings is not implemented yet.")
        pass

    return


# Report functions to print model structure and check for empty morphs
def post_load_report(model: pmx.Model, name:str) -> None:
    """Print a report of the model's structure after loading."""
    print(f"{name}: {len(model.vertices)} vertices, {len(model.faces)} faces, "
          f"{len(model.materials)} materials, {len(model.morphs)} morphs")
    return

def report_empty_morphs(model: pmx.Model) -> None:
    """Report empty morphs in the model."""
    empty_morphs = [m for m in model.morphs if isinstance(m, pmx.VertexMorph) and not m.offsets]
    if empty_morphs:
        print("FYI: The following VertexMorphs are empty and will not have any effect on the model:")
        for morph in empty_morphs:
            print(f"  - {morph.name} (index: {model.morphs.index(morph)})")
    else:
        print("No empty VertexMorphs found.")


def load_pmx_file(path: str) -> pmx.Model:
    """Load a PMX model from the specified path."""
    try:
        model = pmx.load(path)
        return model
    except Exception as e:
        print(f"Error loading PMX model from '{path}': {e}")


def save_pmx_file(model: pmx.Model, path: str) -> bool:
    """Save a PMX model to the specified path."""
    try:
        pmx.save(path, model)
    except Exception as e:
        print(f"Error saving PMX model to '{path}': {e}")
        return False
    return True


# Main function to load, merge, and save PMX model files
def merge_pmx_files(path_base:str, path_patch:str, path_out:str, replace_bones:bool=False, merge_phys:bool=False, merge_disp:bool=False) -> Tuple[bool, str]:
    if not path_base or not path_patch or not path_out:
        return False, "Base, patch and output paths must be specified."
    if path_base == path_patch:
        return False, "Base and patch files cannot be the same."

    if path_out == path_base:
        print("NOTICE: Overwriting the base model.")
    
    base = load_pmx_file(path_base)
    if not base:
        return False, f"Failed to load base model from '{path_base}'. Please check the file path and format."
    post_load_report(base, f"Base model '{path_base}'")

    if detect_duplicate_elements(base):
        return False, f"Base model {path_base} has duplicate elements, merging may not work correctly. Please fix the base model before merging."

    patch = load_pmx_file(path_patch)
    if not patch:
        return False, f"Failed to load patch model from '{path_patch}'. Please check the file path and format."
    post_load_report(patch, f"Patch model '{path_patch}'")

    if detect_duplicate_elements(patch):
        return False, f"Patch model {path_patch} has duplicate elements, merging may not work correctly. Please fix the patch model before merging."


    merge_models(base, patch, replace_bones, merge_phys, merge_disp)
    post_load_report(base, f"Merged model '{path_out}'")

    ret = save_pmx_file(base, path_out)
    if not ret:
        return False, f"Failed to save merged model to '{path_out}'. Please check the file path and permissions."

    # report_empty_morphs(base)
    return True, f"Merge completed successfully ({path_base} + {path_patch} -> {path_out})"

