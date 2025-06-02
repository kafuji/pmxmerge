# -*- coding: utf-8 -*-
# Copyright 2014 MMD Tools authors
# This file is part of MMD Tools.

# Modified by Kafuji Sato
# Changes:
# - Added NamedList class for named elements (Bone, Material, Texture, Morph, DisplayGroup etc.)
# - Reference to Vertices changed to vertex object references instead of indices.
# - Reference to Bones, Materials, Morphs, Textures, DisplayItems, RigidBodies, and Joints changed to name instead of index (Blender's convention)
# - Material have corresponding faces instead of just vertex count.
# - Changed load/save functions to reflect the new structure.
# - Added type annotations for better clarity.
from __future__ import annotations

import logging
import struct
from typing import (Dict, Generic, Iterable, List, Optional, Tuple, TypeVar,
                    Union, overload)

# Set up logging
logging.basicConfig(level=logging.DEBUG)

##################################################################################
# Basic container classes
T = TypeVar('T')
class NamedElements(list[T], Generic[T]):
    """
    A list that allows accessing elements by name in O(1).
    All elements must have a non-empty, unique 'name' attribute.
    """
    __slots__ = ("_name_cache",)
    
    def __init__(self, items: Iterable[T] = ()):
        super().__init__()
        self._name_cache: Dict[str, Tuple[int, T]] = {}
        for item in items:
            self._validate_item(item)
            super().append(item)
        self._rebuild_cache()

    def _validate_item(self, item: T):
        if not hasattr(item, "name"):
            raise ValueError("Item has no 'name' attribute.")
        if not item.name:
            raise ValueError("Empty name is not allowed.")

    def _rebuild_cache(self):
        """Rebuild the name-to-(index, item) cache."""
        self._name_cache.clear()
        for idx, item in enumerate(self):
            self._name_cache[item.name] = (idx, item)

    def __repr__(self):
        names = [str(item.name) for item in self]
        return f"<NamedElementListWithCache(names={names})>"

    @overload
    def __getitem__(self, idx: int) -> T: ...

    @overload
    def __getitem__(self, idx: slice) -> NamedElements[T]: ...

    def __getitem__( self, idx: Union[int, slice, str] ) -> Union[T, NamedElements[T]]:
        if isinstance(idx, str):
            entry = self._name_cache.get(idx)
            if entry is None:
                raise KeyError(f"Name '{idx}' not found.")
            return entry[1]

        result = super().__getitem__(idx)
        if isinstance(idx, slice):
            return NamedElements(result)
        else:
            return result

    def __setitem__(self, idx: Union[int, slice], value: Union[T, Iterable[T]]):
        if isinstance(idx, int):
            self._validate_item(value)
            super().__setitem__(idx, value)
        else:
            new_items = list(value)
            for item in new_items:
                self._validate_item(item)
            super().__setitem__(idx, new_items)
        self._rebuild_cache()

    def append(self, item: T):
        self._validate_item(item)
        super().append(item)
        self._rebuild_cache()

    def insert(self, idx: int, item: T):
        self._validate_item(item)
        super().insert(idx, item)
        self._rebuild_cache()

    def extend(self, items: Iterable[T]):
        for item in items:
            self._validate_item(item)
        super().extend(items)
        self._rebuild_cache()

    def pop(self, idx: int = -1) -> T:
        item = super().pop(idx)
        self._rebuild_cache()
        return item

    def remove(self, item: T):
        super().remove(item)
        self._rebuild_cache()

    def __delitem__(self, idx: Union[int, slice]):
        super().__delitem__(idx)
        self._rebuild_cache()

    def clear(self):
        super().clear()
        self._rebuild_cache()

    def __contains__(self, key: Union[str, T]) -> bool:
        if not isinstance(key, str):
            key = key.name
        return key in self._name_cache

    def get(self, name: str, default: Optional[T] = None) -> Optional[T]:
        """Get an element by its name in O(1) with a default value."""
        entry = self._name_cache.get(name)
        return entry[1] if entry else default

    def name_by_index(self, index: int ) -> Optional[str]:
        """Get the name of an element by its index in O(1). Returns None if not found."""
        if 0 <= index < len(self):
            return self[index].name
        return None

    def index(self, key: Union[str, T]) -> int:
        """Get the index of an element by its name in O(1). Returns -1 if not found. Key can be a name string or an element."""
        if isinstance(key, str):
            entry = self._name_cache.get(key)
            return entry[0] if entry else -1
        for i, item in enumerate(self):
            if item == key:
                return i
        return -1

    def validate(self):
        seen_names = set()
        for i, item in enumerate(self):
            if not item.name:
                raise ValueError(f"Empty name at index {i}.")
            if item.name in seen_names:
                raise ValueError(f"Duplicate name '{item.name}' at index {i}.")
            seen_names.add(item.name)


class TextureList(list):
    """
    A list of Texture objects with special handling.
        - [out of range index] returns None instead of the last value.
        - index(unknown value) returns -1, instead of raising ValueError.
    Otherwise behaves like a normal list.
    """
    def __getitem__(self, index: int) -> Optional[Texture]:
        if index < 0 or index >= len(self):
            return None
        return super().__getitem__(index)

    def index(self, value: Texture) -> int:
        try:
            return super().index(value)
        except ValueError:
            return -1

##################################################################################
class InvalidFileError(Exception):
    pass
class UnsupportedVersionError(Exception):
    pass

class FileStream:
    def __init__(self, path, file_obj, pmx_header):
        self.__path = path
        self.__file_obj = file_obj
        self.__header: Optional[Header] = pmx_header

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def path(self):
        return self.__path

    def header(self):
        if self.__header is None:
            raise Exception
        return self.__header

    def setHeader(self, pmx_header):
        self.__header = pmx_header

    def close(self):
        if self.__file_obj is not None:
            self.__file_obj.close()
            self.__file_obj = None

class FileReadStream(FileStream):
    def __init__(self, path, pmx_header=None):
        self.__fin = open(path, 'rb')
        FileStream.__init__(self, path, self.__fin, pmx_header)

    def __readIndex(self, size, typedict):
        index = None
        if size in typedict :
            index, = struct.unpack(typedict[size], self.__fin.read(size))
        else:
            raise ValueError('invalid data size %s'%str(size))
        return index

    def __readSignedIndex(self, size):
        return self.__readIndex(size, { 1 :"<b", 2 :"<h", 4 :"<i"})

    def __readUnsignedIndex(self, size):
        return self.__readIndex(size, { 1 :"<B", 2 :"<H", 4 :"<I"})


    # READ methods for indexes
    def readVertexIndex(self):
        return self.__readUnsignedIndex(self.header().vertex_index_size)

    def readBoneIndex(self):
        return self.__readSignedIndex(self.header().bone_index_size)

    def readTextureIndex(self):
        return self.__readSignedIndex(self.header().texture_index_size)

    def readMorphIndex(self):
        return self.__readSignedIndex(self.header().morph_index_size)

    def readRigidIndex(self):
        return self.__readSignedIndex(self.header().rigid_index_size)

    def readMaterialIndex(self):
        return self.__readSignedIndex(self.header().material_index_size)

    # READ / WRITE methods for general types
    def readInt(self):
        v, = struct.unpack('<i', self.__fin.read(4))
        return v

    def readShort(self):
        v, = struct.unpack('<h', self.__fin.read(2))
        return v

    def readUnsignedShort(self):
        v, = struct.unpack('<H', self.__fin.read(2))
        return v

    def readStr(self):
        length = self.readInt()
        buf, = struct.unpack('<%ds'%length, self.__fin.read(length))
        return str(buf, self.header().encoding.charset, errors='replace')

    def readFloat(self):
        v, = struct.unpack('<f', self.__fin.read(4))
        return v

    def readVector(self, size):
        return struct.unpack('<'+'f'*size, self.__fin.read(4*size))

    def readByte(self):
        v, = struct.unpack('<B', self.__fin.read(1))
        return v

    def readBytes(self, length):
        return self.__fin.read(length)

    def readSignedByte(self):
        v, = struct.unpack('<b', self.__fin.read(1))
        return v

    def current_pos(self):
        return self.__fin.tell()

class FileWriteStream(FileStream):
    def __init__(self, path, pmx_header=None):
        self.__fout = open(path, 'wb')
        FileStream.__init__(self, path, self.__fout, pmx_header)

    def __writeIndex(self, index, size, typedict):
        if size in typedict :
            self.__fout.write(struct.pack(typedict[size], int(index)))
        else:
            raise ValueError('invalid data size %s'%str(size))
        return

    def __writeSignedIndex(self, index, size):
        return self.__writeIndex(index, size, { 1 :"<b", 2 :"<h", 4 :"<i"})

    def __writeUnsignedIndex(self, index, size):
        return self.__writeIndex(index, size, { 1 :"<B", 2 :"<H", 4 :"<I"})

    # WRITE methods for indexes
    def writeVertexIndex(self, index):
        return self.__writeUnsignedIndex(index, self.header().vertex_index_size)

    def writeBoneIndex(self, index):
        return self.__writeSignedIndex(index, self.header().bone_index_size)

    def writeTextureIndex(self, index):
        return self.__writeSignedIndex(index, self.header().texture_index_size)

    def writeMorphIndex(self, index):
        return self.__writeSignedIndex(index, self.header().morph_index_size)

    def writeRigidIndex(self, index):
        return self.__writeSignedIndex(index, self.header().rigid_index_size)

    def writeMaterialIndex(self, index):
        return self.__writeSignedIndex(index, self.header().material_index_size)


    def writeInt(self, v):
        self.__fout.write(struct.pack('<i', int(v)))

    def writeShort(self, v):
        self.__fout.write(struct.pack('<h', int(v)))

    def writeUnsignedShort(self, v):
        self.__fout.write(struct.pack('<H', int(v)))

    def writeStr(self, v):
        data = v.encode(self.header().encoding.charset)
        self.writeInt(len(data))
        self.__fout.write(data)

    def writeFloat(self, v):
        self.__fout.write(struct.pack('<f', float(v)))

    def writeVector(self, v):
        self.__fout.write(struct.pack('<'+'f'*len(v), *v))

    def writeByte(self, v):
        self.__fout.write(struct.pack('<B', int(v)))

    def writeBytes(self, v):
        self.__fout.write(v)

    def writeSignedByte(self, v):
        self.__fout.write(struct.pack('<b', int(v)))
    
    def current_pos(self):
        return self.__fout.tell()


class Encoding:
    _MAP = [
        (0, 'utf-16-le'),
        (1, 'utf-8'),
        ]

    def __init__(self, arg):
        self.index = 0
        self.charset = ''
        t = None
        if isinstance(arg, str):
            t = list(filter(lambda x: x[1]==arg, self._MAP))
            if len(t) == 0:
                raise ValueError('invalid charset %s'%arg)
        elif isinstance(arg, int):
            t = list(filter(lambda x: x[0]==arg, self._MAP))
            if len(t) == 0:
                raise ValueError('invalid index %d'%arg)
        else:
            raise ValueError('invalid argument type')
        t = t[0]
        self.index = t[0]
        self.charset  = t[1]

    def __repr__(self):
        return '<Encoding charset %s>'%self.charset


class Header:
    PMX_SIGN = b'PMX '
    VERSION = 2.0
    def __init__(self, model=None):
        self.sign = self.PMX_SIGN
        self.version = 0

        self.encoding = Encoding('utf-16-le')
        self.additional_uvs = 0

        self.vertex_index_size = 1
        self.texture_index_size = 1
        self.material_index_size = 1
        self.bone_index_size = 1
        self.morph_index_size = 1
        self.rigid_index_size = 1

        if model is not None:
            self.updateIndexSizes(model)

    def updateIndexSizes(self, model: Model):
        self.vertex_index_size = self.__getIndexSize(len(model.vertices), False)
        self.texture_index_size = self.__getIndexSize(len(model.textures), True)
        self.material_index_size = self.__getIndexSize(len(model.materials), True)
        self.bone_index_size = self.__getIndexSize(len(model.bones), True)
        self.morph_index_size = self.__getIndexSize(len(model.morphs), True)
        self.rigid_index_size = self.__getIndexSize(len(model.rigids), True)
        self.additional_uvs = model.additional_uvs

    @staticmethod
    def __getIndexSize(num, signed):
        s = 1
        if signed:
            s = 2
        if (1<<8)/s > num:
            return 1
        elif (1<<16)/s > num:
            return 2
        else:
            return 4

    def load(self, fs: FileReadStream):
        self.sign = fs.readBytes(4)
        if self.sign[:3] != self.PMX_SIGN[:3]:
            raise InvalidFileError('File signature is invalid.')
        self.version = fs.readFloat()
        if self.version != self.VERSION:
            raise UnsupportedVersionError('unsupported PMX version: %.1f'%self.version)
        if fs.readByte() != 8 or self.sign[3] != self.PMX_SIGN[3]:
            raise InvalidFileError('File header is invalid or corrupted.')

        self.encoding = Encoding(fs.readByte())
        self.additional_uvs = fs.readByte()
        self.vertex_index_size = fs.readByte()
        self.texture_index_size = fs.readByte()
        self.material_index_size = fs.readByte()
        self.bone_index_size = fs.readByte()
        self.morph_index_size = fs.readByte()
        self.rigid_index_size = fs.readByte()

    def save(self, fs: FileWriteStream):
        fs.writeBytes(self.PMX_SIGN)
        fs.writeFloat(self.VERSION)
        fs.writeByte(8)
        fs.writeByte(self.encoding.index)
        fs.writeByte(self.additional_uvs)
        fs.writeByte(self.vertex_index_size)
        fs.writeByte(self.texture_index_size)
        fs.writeByte(self.material_index_size)
        fs.writeByte(self.bone_index_size)
        fs.writeByte(self.morph_index_size)
        fs.writeByte(self.rigid_index_size)

    def __repr__(self):
        return '<Header encoding %s, uvs %d, vtx %d, tex %d, mat %d, bone %d, morph %d, rigid %d>'%(
            str(self.encoding),
            self.additional_uvs,
            self.vertex_index_size,
            self.texture_index_size,
            self.material_index_size,
            self.bone_index_size,
            self.morph_index_size,
            self.rigid_index_size,
            )


################################################################################
# Model Root Class
################################################################################
class Model:
    def __init__(self):
        self.filepath = ""
        self.header = None

        self.name = ""
        self.name_e = ""
        self.comment = ""
        self.comment_e = ""

        self.vertices: List[Vertex] = []
        self.faces: List[Face] = []
        self.textures: TextureList[Texture] = TextureList()
        self.materials: NamedElements[Material] = NamedElements[Material]()
        self.bones: NamedElements[Bone] = NamedElements[Bone]()
        self.morphs: NamedElements[Morph] = NamedElements[Morph]()

        self.displaygroup: NamedElements[DisplayGroup] = NamedElements[DisplayGroup]()

        self.rigids: NamedElements[RigidBody] = NamedElements[RigidBody]()
        self.joints: NamedElements[Joint] = NamedElements[Joint]()

        # Index maps for vertex->index fast lookup, Should be initialized before use
        self.vert_index: Dict[Vertex, int] = {}

        # Additional UVs count
        self.additional_uvs: int = 0

    ################################################################################
    # Index Lookup functions (used by save() function of each class to serialize data.
    def ensure_vertex_lookup_table(self):
        """Ensure vertex lookup tables for fast index access are initialized."""
        # Use instance as reference for vertices and textures
        self.vert_index = {vert: i for i, vert in enumerate(self.vertices)}

    ################################################################################
    def load(self, fs: FileReadStream):
        if self.filepath != "":
            raise ValueError(f"Model already loaded from {self.filepath}. Please create a new Model instance to load another file.")

        logging.debug("======== Loading Model ========")

        self.filepath = fs.path()
        self.header = fs.header()
        self.additional_uvs = self.header.additional_uvs # Store additional UVs count

        self.name = fs.readStr()
        self.name_e = fs.readStr()

        self.comment = fs.readStr()
        self.comment_e = fs.readStr()

        ########################################
        # Load Vertices
        num_vertices = fs.readInt()
        for i in range(num_vertices):
            v = Vertex()
            v.load(fs) # Vertex has reference to bones, but we don't pass self here because bones will be loaded later.
            self.vertices.append(v)
        logging.debug(f"Loaded {len(self.vertices)}")


        ########################################
        # Load Faces
        num_faces = fs.readInt()
        for i in range(int(num_faces/3)):
            face = Face()
            face.load(fs, self)
            self.faces.append(face)
        logging.debug(f"Loaded {len(self.faces)} faces")


        ########################################
        # Load Textures
        num_textures = fs.readInt()
        for i in range(num_textures):
            path = fs.readStr()
            self.textures.append(Texture.from_path(path))
            # logging.debug(f"Texture loaded: {path}, index {i}")
        logging.debug(f"Loaded {len(self.textures)} textures")

        ########################################
        # Load Materials
        num_materials = fs.readInt()
        for i in range(num_materials):
            m = Material()
            m.load(fs, self)
            self.materials.append(m)
        logging.debug(f"Loaded {len(self.materials)} materials")

        # Set faces to materials
        segment_start = 0
        for mat in self.materials:
            segment_end = segment_start + mat.vertex_count // 3
            mat.faces = self.faces[segment_start:segment_end]
            segment_start = segment_end
        
        del self.faces  # Clear master face list, as materials now own their faces

        ########################################
        # Load Bones
        num_bones = fs.readInt()
        for i in range(num_bones):
            b = Bone()
            b.load(fs, self)
            self.bones.append(b)
        logging.debug(f"Loaded {len(self.bones)} bones")

        # Resolve bones internal references
        for bone in self.bones:
            bone.resolve_bone_references(self)

        # Resolve vertices BoneWeight's bone references
        for v in self.vertices:
            v.weight.resolve_bone_references(self)

        ########################################
        # Load Morphs
        num_morph = fs.readInt()
        # display_categories = {0: 'System', 1: 'Eyebrow', 2: 'Eye', 3: 'Mouth', 4: 'Other'}
        for i in range(num_morph):
            m = Morph.create(fs, self)
            self.morphs.append(m)
        logging.debug(f"Loaded {len(self.morphs)} morphs")


        ########################################
        # Load Display Groups
        num_disp = fs.readInt()
        for i in range(num_disp):
            d = DisplayGroup()
            d.load(fs, self)
            self.displaygroup.append(d)
        logging.debug(f"Loaded {len(self.displaygroup)} display groups")

        ########################################
        # Load Rigid Bodies
        num_rigid = fs.readInt()
        # rigid_types = {0: 'Sphere', 1: 'Box', 2: 'Capsule'}
        # rigid_modes = {0: 'Static', 1: 'Dynamic', 2: 'Dynamic(track to bone)'}
        for i in range(num_rigid):
            r = RigidBody()
            r.load(fs, self)
            self.rigids.append(r)
        logging.debug(f"Loaded {len(self.rigids)} rigid bodies")

        ########################################
        # Load Joints
        num_joints = fs.readInt()
        for i in range(num_joints):
            j = Joint()
            j.load(fs, self)
            self.joints.append(j)
        logging.debug(f"Loaded {len(self.joints)} joints")

        return

    def save(self, fs: FileWriteStream):
        fs.writeStr(self.name)
        fs.writeStr(self.name_e)

        fs.writeStr(self.comment)
        fs.writeStr(self.comment_e)

        # Ensure lookup table for each list
        self.purge_deleted_vertices() # Remove deleted vertices before saving
        self.ensure_vertex_lookup_table()

        logging.debug("======== Saving Model ========")

        ##########################################
        # Save Vertices
        fs.writeInt(len(self.vertices))
        for i in self.vertices:
            i.save(fs, self)
        logging.debug(f"Saved {len(self.vertices)} vertices")

        ###########################################
        # Save Faces

        # Old way: save all faces directly
        # fs.writeInt(len(self.faces)*3)
        # for face in self.faces:
        #     face.save(fs, self)

        # New: Instead of writing the face list directly, we write face lists owned by materials.
        # So we can sort, remove materials without managing the master face list before saving.
        num_faces = sum(len(mat.faces) for mat in self.materials)
        fs.writeInt(num_faces*3)
        for mat in self.materials:
            for face in mat.faces:
                face.save(fs, self)
        logging.debug(f"Saved {num_faces} faces from {len(self.materials)} materials")

        ##########################################
        # Save Textures
        fs.writeInt(len(self.textures))
        for t in self.textures:
            fs.writeStr(t)  # Write the texture path as a string
            # logging.debug(f"Texture saved: {t}, index {self.textures.index(t)}")
        logging.debug(f"Saved {len(self.textures)} textures")

        ##########################################
        # Save Materials
        fs.writeInt(len(self.materials))
        for i in self.materials:
            i.save(fs, self)

        logging.debug(f"Saved {len(self.materials)} materials")

        ############################################
        # Save Bones
        fs.writeInt(len(self.bones))
        for i in self.bones:
            i.save(fs, self)
        logging.debug(f"Saved {len(self.bones)} bones")

        ############################################
        # Save Morphs
        fs.writeInt(len(self.morphs))
        for i in self.morphs:
            i.save(fs, self)
        logging.debug(f"Saved {len(self.morphs)} morphs")

        ############################################
        # Save Display Groups
        fs.writeInt(len(self.displaygroup))
        for i in self.displaygroup:
            i.save(fs, self)
        logging.debug(f"Saved {len(self.displaygroup)} display groups")

        ############################################
        # Save Rigid Bodies
        fs.writeInt(len(self.rigids))
        for i in self.rigids:
            i.save(fs, self)
        logging.debug(f"Saved {len(self.rigids)} rigid bodies")

        ############################################
        # Save Joints
        fs.writeInt(len(self.joints))
        for i in self.joints:
            i.save(fs, self)
        logging.debug(f"Saved {len(self.joints)} joints")


    def __repr__(self):
        return '<Model name %s, name_e %s, comment %s, comment_e %s, textures %s>'%(
            self.name,
            self.name_e,
            self.comment,
            self.comment_e,
            str(self.textures),
            )


    ################################################################################
    # Helper functions for managing model elements
    ################################################################################

    def append_vertices(self, vertices: List[Vertex]) -> None:
        """
        Append a list of vertices to the model. 
        Index lookup table will not be updated. (use ensure_lookup_table() if needed).
        """
        self.vertices.extend(vertices)
        return

    def remove_material(self, material: Material) -> None:
        """Remove a material and it's faces, vertices from the model."""
        if not material in self.materials:
            raise ValueError(f"Material {material.name} not found in model.")

        # Gather all vertices used by the new faces and other materials
        verts_used: set[Vertex] = set()
        for mat in (m for m in self.materials if m is not material):
            for face in mat.faces:
                verts_used.update(face.vertices)

        # Mark as deleted all vertices that are not used by any remaining material
        for v in (v for v in self.vertices if v not in verts_used):
            v.deleted = True

        # Remove the material and it's faces from the model (material owns faces)
        self.materials.remove(material)
        return


    def replace_material_faces(self, material: Material, new_faces: List[Face]) -> None:
        """Replace the faces of a material with new faces. Assuming verts for new faces are already in the model."""
        if not material in self.materials:
            raise ValueError(f"Material {material.name} not found in model.")

        # Gather all vertices used by the new faces and other materials
        verts_used: set[Vertex] = set()
        for mat in (m for m in self.materials if m is not material):
            for face in mat.faces:
                verts_used.update(face.vertices)

        verts_used.update(v for f in new_faces for v in f.vertices)

        # Mark as deleted all vertices that are not used by any remaining material
        for v in (v for v in self.vertices if v not in verts_used):
            v.deleted = True

        # Retrieve the new list of faces
        material.faces = new_faces
        return


    def purge_deleted_vertices( self ) -> None: # Call this before calling ensure_lookup_table()!
        """
        Physically remove all vertices marked as deleted from the model.
        This will also remove any MorphOffset that references deleted vertices.
        ensure_lookup_table() should be called after this to rebuild the index maps.
        """
        # Remove MorphOffset(Vertex and UV) which reference deleted vertices
        for morph in self.morphs:
            if isinstance(morph, VertexMorph):
                morph.offsets = [o for o in morph.offsets if not getattr(o.vertex, "deleted", False)]
            elif isinstance(morph, UVMorph):
                morph.offsets = [o for o in morph.offsets if not getattr(o.vertex, "deleted", False)]

        # Physically remove deleted vertices from the master list
        self.vertices = [v for v in self.vertices if not getattr(v, "deleted", False)]
        return

    def purge_unused_vertices(self) -> None:
        """
        Physically remove vertices that are not referenced by any material faces.
        This will also remove any MorphOffset that references deleted vertices.
        ensure_lookup_table() should be called after this to rebuild the index maps.
        """
        # Gather all vertices used by the materials
        verts_used: set[Vertex] = set()
        for mat in self.materials:
            for face in mat.faces:
                verts_used.update(face.vertices)

        # Mark as deleted all vertices that are not used by any material
        for v in (v for v in self.vertices if v not in verts_used):
            v.deleted = True

        # Purge deleted vertices
        self.purge_deleted_vertices()
        return

    def ensure_texture(self, tex: Texture) -> Texture:
        """
        Ensure a texture with the given path exists in the model.
        Append a new Texture if not found, or return the existing one.
        """
        if tex not in self.textures:
            self.textures.append(tex)
        return tex

    def purge_unused_textures(self) -> None:
        """
        Physically remove textures that are not referenced by any material.
        ensure_lookup_table() should be called after this to rebuild the index maps.
        """
        # Gather all textures used by the materials
        tex_used: set(str) = set()
        for mat in self.materials:
            tex_used.add(mat.texture) if mat.texture else None
            tex_used.add(mat.sphere_texture) if mat.sphere_texture else None
            tex_used.add(mat.toon_texture) if mat.toon_texture else None

        # Build a new list of textures that are used
        self.textures = TextureList([Texture.from_path(t) for t in self.textures if t in tex_used])
        return



class Vertex:
    __slots__ = ("deleted","co","normal","uv","additional_uvs","weight","edge_scale")

    def __init__(self):
        self.deleted = False
        self.co = [0.0, 0.0, 0.0]
        self.normal = [0.0, 0.0, 0.0]
        self.uv = [0.0, 0.0]
        self.additional_uvs = []
        self.weight: BoneWeight = None
        self.edge_scale = 1

    def __repr__(self):
        if self.deleted:
            return '<Vertex (deleted)>'
        return '<Vertex co %s, normal %s, uv %s, additional_uvs %s, weight %s, edge_scale %s>'%(
            str(self.co),
            str(self.normal),
            str(self.uv),
            str(self.additional_uvs),
            str(self.weight),
            str(self.edge_scale),
            )

    def load(self, fs: FileReadStream):
        self.co = fs.readVector(3)
        self.normal = fs.readVector(3)
        self.uv = fs.readVector(2)
        self.additional_uvs = []
        for i in range(fs.header().additional_uvs):
            self.additional_uvs.append(fs.readVector(4))
        self.weight = BoneWeight()
        self.weight.load(fs)
        self.edge_scale = fs.readFloat()

    def save(self, fs: FileWriteStream, model: Model):
        if self.deleted:
            raise ValueError('Cannot save a deleted vertex.')

        fs.writeVector(self.co)
        fs.writeVector(self.normal)
        fs.writeVector(self.uv)
        for i in self.additional_uvs:
            fs.writeVector(i)
        for i in range(fs.header().additional_uvs-len(self.additional_uvs)):
            fs.writeVector((0,0,0,0))
        self.weight.save(fs, model)
        fs.writeFloat(self.edge_scale)


class BoneWeightSDEF:
    __slots__ = ("weight", "c", "r0", "r1")
    def __init__(self, weight=0, c=None, r0=None, r1=None):
        self.weight = weight
        self.c = c
        self.r0 = r0
        self.r1 = r1

class BoneWeight:
    __slots__ = ("bone_indices", "bones", "weights", "type")
    BDEF1 = 0
    BDEF2 = 1
    BDEF4 = 2
    SDEF  = 3

    def __init__(self):
        self.bone_indices: List[int] = [] # Resolve after all bones are loaded
        self.bones: List[str] = []
        self.weights: List[float] = []
        self.type = self.BDEF1


    def load(self, fs: FileReadStream ):
        self.type = fs.readByte()

        if self.type == self.BDEF1:
            self.bone_indices.append(fs.readBoneIndex())
        elif self.type == self.BDEF2:
            self.bone_indices += [fs.readBoneIndex(), fs.readBoneIndex()]
            self.weights.append(fs.readFloat())
        elif self.type == self.BDEF4:
            for _ in range(4): # BDEF4 has 4 bone indices
                self.bone_indices.append(fs.readBoneIndex())
            self.weights = fs.readVector(4)
        elif self.type == self.SDEF:
            self.bone_indices += [fs.readBoneIndex(), fs.readBoneIndex()]
            self.weights = BoneWeightSDEF()
            self.weights.weight = fs.readFloat()
            self.weights.c = fs.readVector(3)
            self.weights.r0 = fs.readVector(3)
            self.weights.r1 = fs.readVector(3)
        else:
            raise ValueError('invalid weight type %s'%str(self.type))

    def resolve_bone_references(self, model: Model):
        """Resolve bone references from indices after all bones are loaded."""
        self.bones = [model.bones.name_by_index(i) for i in self.bone_indices]
        del self.bone_indices  # Remove indices after resolving references


    def save(self, fs: FileWriteStream, model: Model):
        fs.writeByte(self.type)
        if self.type == self.BDEF1:
            fs.writeBoneIndex(model.bones.index(self.bones[0]))
        elif self.type == self.BDEF2:
            for i in range(2):
                fs.writeBoneIndex(model.bones.index(self.bones[i]))
            fs.writeFloat(self.weights[0])
        elif self.type == self.BDEF4:
            for i in range(4):
                fs.writeBoneIndex(model.bones.index(self.bones[i]))
            for i in range(4):
                fs.writeFloat(self.weights[i])
        elif self.type == self.SDEF:
            for i in range(2):
                fs.writeBoneIndex(model.bones.index(self.bones[i]))
            if not isinstance(self.weights, BoneWeightSDEF):
                raise ValueError('weights should be BoneWeightSDEF for SDEF type')
            fs.writeFloat(self.weights.weight)
            fs.writeVector(self.weights.c)
            fs.writeVector(self.weights.r0)
            fs.writeVector(self.weights.r1)
        else:
            raise ValueError('invalid weight type %s'%str(self.type))


class Face:
    __slots__ = ("vertices",)

    def __init__(self):
        self.vertices: List[Vertex] = [None, None, None]

    def __repr__(self):
        return '<Face v1 %s, v2 %s, v3 %s>'%(str(self.vertices[0]), str(self.vertices[1]), str(self.vertices[2]))

    def load(self, fs: FileReadStream, model: Model) -> Face:
        self.vertices[2] = model.vertices[fs.readVertexIndex()] # Stored in reverse order
        self.vertices[1] = model.vertices[fs.readVertexIndex()]
        self.vertices[0] = model.vertices[fs.readVertexIndex()]

    def save(self, fs: FileWriteStream, model: Model):
        fs.writeVertexIndex(model.vert_index[self.vertices[2]])
        fs.writeVertexIndex(model.vert_index[self.vertices[1]])
        fs.writeVertexIndex(model.vert_index[self.vertices[0]])

import os
class Texture(str):
    """
    Texture class to represent a texture file path.
    This class is a simple wrapper around a string to represent texture paths.
    Automatically converts paths to relative Windows-style paths in same manner.
    """
    def sanitize(self):
        if not os.path.isabs(self):
            self = os.path.normpath(os.path.join(os.getcwd(), self)) # to absolute path
        self = os.path.relpath(self, start=os.getcwd()).replace(os.path.sep, '\\') # to relative path with windows style
        return self

    @classmethod
    def from_path(cls, path: str) -> 'Texture':
        if not isinstance(path, str):
            raise ValueError("Texture path must be a string.")
        return cls(path)

    def load(self, fs: FileReadStream):
        path = fs.readStr()
        self = Texture.from_path(path)

    def save(self, fs: FileWriteStream):
        fs.writeStr(self)


class Material:
    SPHERE_MODE_OFF = 0
    SPHERE_MODE_MULT = 1
    SPHERE_MODE_ADD = 2
    SPHERE_MODE_SUBTEX = 3

    def __init__(self):
        self.name = ""
        self.name_e = ""

        self.diffuse = []
        self.specular = []
        self.shininess = 0
        self.ambient = []

        self.is_double_sided = True
        self.enabled_drop_shadow = True
        self.enabled_self_shadow_map = True
        self.enabled_self_shadow = True
        self.enabled_toon_edge = False

        self.edge_color = []
        self.edge_size = 1

        self.texture: Optional[Texture] = None
        self.sphere_texture: Optional[Texture] = None
        self.sphere_texture_mode = 0
        self.is_shared_toon_texture = True
        self.shared_toon_texture_idx: int = 0
        self.toon_texture: Optional[Texture] = None

        self.comment = ''

        # Geometry
        self.vertex_count = 0
        self.faces: List[Face] = [] # No Serialize. Set after all materials are loaded


    def __repr__(self):
        return '<Material name %s, name_e %s, diffuse %s, specular %s, shininess %.2f, ambient %s, texture %s, sphere_texture %s, toon_texture %s, comment %s>'%(
            self.name,
            self.name_e,
            str(self.diffuse),
            str(self.specular),
            self.shininess,
            str(self.ambient),
            str(self.texture),
            str(self.sphere_texture),
            str(self.toon_texture),
            str(self.comment),
        )


    def load(self, fs: FileReadStream, model: Model):
        self.name = fs.readStr()
        self.name_e = fs.readStr()

        self.diffuse = fs.readVector(4)
        self.specular = fs.readVector(3)
        self.shininess = fs.readFloat()
        self.ambient = fs.readVector(3)

        flags = fs.readByte()
        self.is_double_sided = bool(flags & 1)
        self.enabled_drop_shadow = bool(flags & 2)
        self.enabled_self_shadow_map = bool(flags & 4)
        self.enabled_self_shadow = bool(flags & 8)
        self.enabled_toon_edge = bool(flags & 16)

        self.edge_color = fs.readVector(4)
        self.edge_size = fs.readFloat()

        self.texture = model.textures[fs.readTextureIndex()]
        self.sphere_texture = model.textures[fs.readTextureIndex()]
        self.sphere_texture_mode = fs.readSignedByte()

        self.is_shared_toon_texture = (fs.readSignedByte() == 1)
        if self.is_shared_toon_texture:
            self.shared_toon_texture_idx = fs.readSignedByte()
        else:
            self.toon_texture = model.textures[fs.readTextureIndex()]

        self.comment = fs.readStr()
        self.vertex_count = fs.readInt()

    def save(self, fs: FileWriteStream, model: Model):
        fs.writeStr(self.name)
        fs.writeStr(self.name_e)

        fs.writeVector(self.diffuse)
        fs.writeVector(self.specular)
        fs.writeFloat(self.shininess)
        fs.writeVector(self.ambient)

        flags = 0
        flags |= int(self.is_double_sided)
        flags |= int(self.enabled_drop_shadow) << 1
        flags |= int(self.enabled_self_shadow_map) << 2
        flags |= int(self.enabled_self_shadow) << 3
        flags |= int(self.enabled_toon_edge) << 4
        fs.writeByte(flags)

        fs.writeVector(self.edge_color)
        fs.writeFloat(self.edge_size)

        fs.writeTextureIndex(model.textures.index(self.texture))
        fs.writeTextureIndex(model.textures.index(self.sphere_texture))
        fs.writeSignedByte(self.sphere_texture_mode)

        if self.is_shared_toon_texture:
            fs.writeSignedByte(1)
            fs.writeSignedByte(self.shared_toon_texture_idx)
        else:
            fs.writeSignedByte(0)
            fs.writeTextureIndex(model.textures.index(self.toon_texture))

        fs.writeStr(self.comment)
        fs.writeInt(len(self.faces) * 3)  # Number of vertices in faces, each face has 3 vertices


class Coordinate: # Used by Bone.localCoordinate
    def __init__(self, xAxis, zAxis):
        self.x_axis = xAxis
        self.z_axis = zAxis


class Bone:
    def __init__(self):
        self.name = ""
        self.name_e = ""

        self.location = []
        self.parent_index = -1 # Resolved after loading bones
        self.parent: str = ""
        self.transform_order = 0

        # vector3 or bone for display connection
        self.displayConnectionType = 0 # 0: Vector, 1: Bone
        self.displayConnectionBoneIndex: int = -1 # Resolved after loading bones
        self.displayConnectionBone: str = "" # Resolved after loading bones
        self.displayConnectionVector: List[float] = [] # Vector3

        self.isRotatable = True
        self.isMovable = True
        self.isVisible = True
        self.isControllable = True

        self.isIK = False

        self.hasAdditionalRotate = False
        self.hasAdditionalLocation = False

        self.additionalTransformBoneIndex: int = -1 # Resolved after loading bones
        self.additionalTransformBone: str = "" # Resolved after loading bones
        self.additionalTransformInfluence: float = 0.0 # Resolved after loading bones

        self.fixed_axis = None # None or Vector3

        self.localCoordinate: Optional[Coordinate] = None # None or Coordinate object

        self.transAfterPhys = False

        self.externalTransKey: Optional[int] = None

        self.ik_target_index: int = -1 # Resolved after loading bones
        self.ik_target: str = ""
        self.loopCount = 8
        self.rotationConstraint = 0.03

        self.ik_links: List[IKLink] = []

    def __repr__(self):
        return '<Bone name %s, name_e %s>'%(
            self.name,
            self.name_e,)

    def load(self, fs: FileReadStream, model: Model):
        self.name = fs.readStr()
        self.name_e = fs.readStr()

        self.location = fs.readVector(3)
        self.parent_index = fs.readBoneIndex()
        self.transform_order = fs.readInt()

        flags = fs.readShort()
        if flags & 0x0001: # displayConnection is a Bone
            self.displayConnectionType = 1
            self.displayConnectionBoneIndex = fs.readBoneIndex()
        else:
            self.displayConnectionType = 0
            self.displayConnectionVector = fs.readVector(3)

        self.isRotatable    = ((flags & 0x0002) != 0)
        self.isMovable      = ((flags & 0x0004) != 0)
        self.isVisible        = ((flags & 0x0008) != 0)
        self.isControllable = ((flags & 0x0010) != 0)

        self.isIK           = ((flags & 0x0020) != 0)

        self.hasAdditionalRotate = ((flags & 0x0100) != 0)
        self.hasAdditionalLocation = ((flags & 0x0200) != 0)
        if self.hasAdditionalRotate or self.hasAdditionalLocation:
            self.additionalTransformBoneIndex = fs.readBoneIndex()
            self.additionalTransformInfluence = fs.readFloat()


        if flags & 0x0400:
            self.fixed_axis = fs.readVector(3)
        else:
            self.fixed_axis = None

        if flags & 0x0800:
            xaxis = fs.readVector(3)
            zaxis = fs.readVector(3)
            self.localCoordinate = Coordinate(xaxis, zaxis)
        else:
            self.localCoordinate = None

        self.transAfterPhys = ((flags & 0x1000) != 0)

        if flags & 0x2000:
            self.externalTransKey = fs.readInt()
        else:
            self.externalTransKey = None

        if self.isIK:
            self.ik_target_index = fs.readBoneIndex()
            self.loopCount = fs.readInt()
            self.rotationConstraint = fs.readFloat()

            iklink_num = fs.readInt()
            self.ik_links: List[IKLink] = []
            for i in range(iklink_num):
                link = IKLink()
                link.load(fs, model)
                self.ik_links.append(link)

    def resolve_bone_references(self, model: Model):
        """Resolve bone references after all bones are loaded."""
        self.parent = model.bones.name_by_index(self.parent_index)
        self.displayConnectionBone = model.bones.name_by_index(self.displayConnectionBoneIndex)
        self.additionalTransformBone = model.bones.name_by_index(self.additionalTransformBoneIndex)
        if self.isIK:
            self.ik_target = model.bones.name_by_index(self.ik_target_index)
            del self.ik_target_index

        del self.parent_index
        del self.displayConnectionBoneIndex
        del self.additionalTransformBoneIndex

        # Resolve IK links
        for link in self.ik_links:
            link.resolve_bone_references(model)


    def save(self, fs: FileWriteStream, model: Model):
        fs.writeStr(self.name)
        fs.writeStr(self.name_e)

        fs.writeVector(self.location)
        fs.writeBoneIndex(model.bones.index(self.parent))
        fs.writeInt(self.transform_order)

        flags = 0
        flags |= int(self.displayConnectionType == 1) # 0x0001
        flags |= int(self.isRotatable) << 1
        flags |= int(self.isMovable) << 2
        flags |= int(self.isVisible) << 3
        flags |= int(self.isControllable) << 4
        flags |= int(self.isIK) << 5

        flags |= int(self.hasAdditionalRotate) << 8
        flags |= int(self.hasAdditionalLocation) << 9
        flags |= int(self.fixed_axis is not None) << 10
        flags |= int(self.localCoordinate is not None) << 11

        flags |= int(self.transAfterPhys) << 12
        flags |= int(self.externalTransKey is not None) << 13

        fs.writeShort(flags)

        if flags & 0x0001:
            fs.writeBoneIndex(model.bones.index(self.displayConnectionBone))
        else:
            fs.writeVector(self.displayConnectionVector)

        if self.hasAdditionalRotate or self.hasAdditionalLocation:
            fs.writeBoneIndex(model.bones.index(self.additionalTransformBone))
            fs.writeFloat(self.additionalTransformInfluence)

        if flags & 0x0400:
            fs.writeVector(self.fixed_axis)

        if flags & 0x0800:
            fs.writeVector(self.localCoordinate.x_axis)
            fs.writeVector(self.localCoordinate.z_axis)

        if flags & 0x2000:
            fs.writeInt(self.externalTransKey)

        if self.isIK:
            fs.writeBoneIndex(model.bones.index(self.ik_target))
            fs.writeInt(self.loopCount)
            fs.writeFloat(self.rotationConstraint)

            fs.writeInt(len(self.ik_links))
            for i in self.ik_links:
                i.save(fs, model)


class IKLink:
    def __init__(self):
        self.target_index = -1
        self.target:str = ""
        self.maximumAngle = None
        self.minimumAngle = None

    def __repr__(self):
        return '<IKLink target %s>'%(str(self.target))

    def load(self, fs: FileReadStream, model: Model):
        self.target_index = fs.readBoneIndex()
        flag = fs.readByte()
        if flag == 1:
            self.minimumAngle = fs.readVector(3)
            self.maximumAngle = fs.readVector(3)
        else:
            self.minimumAngle = None
            self.maximumAngle = None

    def resolve_bone_references(self, model: Model):
        self.target = model.bones.name_by_index(self.target_index)
        del self.target_index

    def save(self, fs: FileWriteStream, model: Model):
        fs.writeBoneIndex(model.bones.index(self.target))
        if isinstance(self.minimumAngle, (tuple, list)) and isinstance(self.maximumAngle, (tuple, list)):
            fs.writeByte(1)
            fs.writeVector(self.minimumAngle)
            fs.writeVector(self.maximumAngle)
        else:
            fs.writeByte(0)

class Morph:
    CATEGORY_SYSTEM = 0
    CATEGORY_EYEBROW = 1
    CATEGORY_EYE = 2
    CATEGORY_MOUTH = 3
    CATEGORY_OTHER = 4

    def __init__(self, name: str, name_e: str, category: int, **kwargs):
        self.offsets: List[Union[VertexMorphOffset, UVMorphOffset, BoneMorphOffset, MaterialMorphOffset]] = []
        self.name: str = name
        self.name_e: str = name_e
        self.category: int = category

    def __repr__(self):
        return '<Morph name %s, name_e %s>'%(self.name, self.name_e)

    def type_index(self):
        raise NotImplementedError

    @staticmethod
    def create(fs: FileReadStream, model: Model) -> Morph:
        _CLASSES = {
            0: GroupMorph,
            1: VertexMorph,
            2: BoneMorph,
            3: UVMorph,
            4: UVMorph,
            5: UVMorph,
            6: UVMorph,
            7: UVMorph,
            8: MaterialMorph,
            }

        name = fs.readStr()
        name_e = fs.readStr()
        category = fs.readSignedByte()
        typeIndex = fs.readSignedByte()
        ret = _CLASSES[typeIndex](name, name_e, category, type_index = typeIndex)
        ret.load(fs, model)
        return ret

    def load(self, fs: FileReadStream, model: Model):
        raise NotImplementedError (f"Should be implemented in subclass {self.__class__.__name__}")

    def save(self, fs: FileWriteStream, model: Model):
        fs.writeStr(self.name)
        fs.writeStr(self.name_e)
        fs.writeSignedByte(self.category)
        fs.writeSignedByte(self.type_index())
        fs.writeInt(len(self.offsets))
        for i in self.offsets:
            i.save(fs, model)

class VertexMorph(Morph):
    def __init__(self, *args, **kwargs):
        self.offsets: List[VertexMorphOffset] = []
        Morph.__init__(self, *args, **kwargs)

    def type_index(self):
        return 1

    def load(self, fs: FileReadStream, model: Model):
        num = fs.readInt()
        for i in range(num):
            t = VertexMorphOffset()
            t.load(fs, model)
            self.offsets.append(t)

class VertexMorphOffset:
    def __init__(self):
        self.vertex: Vertex = None
        self.offset: List[float] = []

    def load(self, fs: FileReadStream, model: Model):
        self.vertex = model.vertices[fs.readVertexIndex()]
        self.offset = fs.readVector(3)

    def save(self, fs: FileWriteStream, model: Model):
        fs.writeVertexIndex(model.vert_index[self.vertex])
        fs.writeVector(self.offset)

class UVMorph(Morph):
    def __init__(self, *args, **kwargs):
        self.uv_index = kwargs.get('type_index', 3) - 3
        self.offsets: List[UVMorphOffset] = []
        Morph.__init__(self, *args, **kwargs)

    def type_index(self):
        return self.uv_index + 3

    def load(self, fs: FileReadStream, model: Model):
        self.offsets: List[UVMorphOffset] = []
        num = fs.readInt()
        for i in range(num):
            t = UVMorphOffset()
            t.load(fs, model)
            self.offsets.append(t)

class UVMorphOffset:
    def __init__(self):
        self.vertex: Vertex = None
        self.offset = []

    def load(self, fs: FileReadStream, model: Model):
        self.vertex = model.vertices[fs.readVertexIndex()]
        self.offset = fs.readVector(4)

    def save(self, fs: FileWriteStream, model: Model):
        fs.writeVertexIndex(model.vert_index[self.vertex])
        fs.writeVector(self.offset)

class BoneMorph(Morph):
    def __init__(self, *args, **kwargs):
        Morph.__init__(self, *args, **kwargs)

    def type_index(self):
        return 2

    def load(self, fs: FileReadStream, model: Model):
        self.offsets: List[BoneMorphOffset] = []
        num = fs.readInt()
        for i in range(num):
            t = BoneMorphOffset(self.name)
            t.load(fs, model)
            self.offsets.append(t)

class BoneMorphOffset:
    def __init__(self, owner_name:str):
        self.owner = owner_name
        self.bone: str = ""
        self.location_offset: List[float] = []
        self.rotation_offset: List[float] = []

    def __repr__(self):
        return '<BoneMorphOffset bone %s, location_offset %s, rotation_offset %s>'%(
            self.bone,
            str(self.location_offset),
            str(self.rotation_offset),
            )

    def load(self, fs: FileReadStream, model: Model):
        self.bone = model.bones.name_by_index( fs.readBoneIndex() )
        self.location_offset = fs.readVector(3)
        self.rotation_offset = fs.readVector(4)

        if not any(self.rotation_offset):
            self.rotation_offset = (0, 0, 0, 1)

    def save(self, fs: FileWriteStream, model: Model):
        fs.writeBoneIndex(model.bones.index(self.bone))
        fs.writeVector(self.location_offset)
        fs.writeVector(self.rotation_offset)


class MaterialMorph(Morph):
    def __init__(self, *args, **kwargs):
        Morph.__init__(self, *args, **kwargs)

    def type_index(self):
        return 8

    def load(self, fs: FileReadStream, model: Model):
        self.offsets = []
        num = fs.readInt()
        for i in range(num):
            t = MaterialMorphOffset()
            t.load(fs, model)
            self.offsets.append(t)

class MaterialMorphOffset:
    TYPE_MULT = 0
    TYPE_ADD = 1

    def __init__(self):
        self.material: str = "" # Referenced by name
        self.offset_type = 0
        self.diffuse_offset = []
        self.specular_offset = []
        self.shininess_offset = 0
        self.ambient_offset = []
        self.edge_color_offset = []
        self.edge_size_offset = []
        self.texture_factor = []
        self.sphere_texture_factor = []
        self.toon_texture_factor = []

    def load(self, fs: FileReadStream, model: Model):
        self.material = model.materials.name_by_index( fs.readMaterialIndex() )
        self.offset_type = fs.readSignedByte()
        self.diffuse_offset = fs.readVector(4)
        self.specular_offset = fs.readVector(3)
        self.shininess_offset = fs.readFloat()
        self.ambient_offset = fs.readVector(3)
        self.edge_color_offset = fs.readVector(4)
        self.edge_size_offset = fs.readFloat()
        self.texture_factor = fs.readVector(4)
        self.sphere_texture_factor = fs.readVector(4)
        self.toon_texture_factor = fs.readVector(4)

    def save(self, fs: FileWriteStream, model: Model):
        fs.writeMaterialIndex(model.materials.index(self.material))
        fs.writeSignedByte(self.offset_type)
        fs.writeVector(self.diffuse_offset)
        fs.writeVector(self.specular_offset)
        fs.writeFloat(self.shininess_offset)
        fs.writeVector(self.ambient_offset)
        fs.writeVector(self.edge_color_offset)
        fs.writeFloat(self.edge_size_offset)
        fs.writeVector(self.texture_factor)
        fs.writeVector(self.sphere_texture_factor)
        fs.writeVector(self.toon_texture_factor)

class GroupMorph(Morph):
    def __init__(self, *args, **kwargs):
        Morph.__init__(self, *args, **kwargs)

    def type_index(self):
        return 0

    def load(self, fs: FileReadStream, model: Model):
        self.offsets = []
        num = fs.readInt()
        for i in range(num):
            t = GroupMorphOffset()
            t.load(fs, model)
            self.offsets.append(t)

class GroupMorphOffset:
    def __init__(self):
        self.morph: str = ""  # Reference by name
        self.factor: float = 0.0

    def load(self, fs: FileReadStream, model: Model):
        self.morph = model.morphs.name_by_index(fs.readMorphIndex())
        self.factor = fs.readFloat()

    def save(self, fs: FileWriteStream, model: Model):
        fs.writeMorphIndex(model.morphs.index(self.morph))
        fs.writeFloat(self.factor)


class DisplayGroup:
    def __init__(self):
        self.name: str = ""
        self.name_e: str = ""

        self.isSpecial: bool = False
        self.items: NamedElements[DisplayItem] = NamedElements[DisplayItem]()  # List of DisplayItem instances

    def __repr__(self):
        return '<Display name %s, name_e %s>'%(
            self.name,
            self.name_e,
            )

    def load(self, fs: FileReadStream, model: Model):
        self.name = fs.readStr()
        self.name_e = fs.readStr()

        self.isSpecial = (fs.readByte() == 1)
        num = fs.readInt()
        self.items = NamedElements[DisplayItem]()
        for i in range(num):
            item = DisplayItem()
            item.load(fs, model)
            self.items.append(item)

    def save(self, fs: FileWriteStream, model: Model):
        fs.writeStr(self.name)
        fs.writeStr(self.name_e)

        fs.writeByte(int(self.isSpecial))
        fs.writeInt(len(self.items))

        for item in self.items:
            item.save(fs, model)


class DisplayItem:
    def __init__(self):
        self.disp_type:int = 0  # 0 for Bone, 1 for Morph
        self.name: str = ""  # Reference by name, either Bone or Morph

    def __repr__(self):
        return f'<DisplayItem type {self.disp_type}, item {self.name}>'

    def load(self, fs: FileReadStream, model: Model):
        self.disp_type = fs.readByte()
        if self.disp_type == 0:
            self.name = model.bones.name_by_index(fs.readBoneIndex())
        elif self.disp_type == 1:
            self.name = model.morphs.name_by_index(fs.readMorphIndex())
        else:
            raise Exception(f'invalid display item type value: {self.disp_type}')
        
    def save(self, fs: FileWriteStream, model: Model):
        fs.writeByte(self.disp_type)
        if self.disp_type == 0:
            fs.writeBoneIndex(model.bones.index(self.name))
        elif self.disp_type == 1:
            fs.writeMorphIndex(model.morphs.index(self.name))
        else:
            raise Exception(f'invalid display item type value: {self.disp_type}')


class RigidBody:
    TYPE_SPHERE = 0
    TYPE_BOX = 1
    TYPE_CAPSULE = 2

    MODE_STATIC = 0
    MODE_DYNAMIC = 1
    MODE_DYNAMIC_BONE = 2
    def __init__(self):
        self.name = ""
        self.name_e = ""

        self.bone: str = ""  # Reference by name
        self.collision_group_number = 0
        self.collision_group_mask = 0

        self.type = 0
        self.size = []

        self.location = []
        self.rotation = []

        self.mass = 1
        self.velocity_attenuation = []
        self.rotation_attenuation = []
        self.bounce = []
        self.friction = []

        self.mode = 0

    def __repr__(self):
        return '<Rigid name %s, name_e %s>'%(
            self.name,
            self.name_e,
            )

    def load(self, fs: FileReadStream, model: Model):
        self.name = fs.readStr()
        self.name_e = fs.readStr()

        self.bone = model.bones.name_by_index(fs.readBoneIndex())

        self.collision_group_number = fs.readSignedByte()
        self.collision_group_mask = fs.readUnsignedShort()

        self.type = fs.readSignedByte()
        self.size = fs.readVector(3)

        self.location = fs.readVector(3)
        self.rotation = fs.readVector(3)

        self.mass = fs.readFloat()
        self.velocity_attenuation = fs.readFloat()
        self.rotation_attenuation = fs.readFloat()
        self.bounce = fs.readFloat()
        self.friction = fs.readFloat()

        self.mode = fs.readSignedByte()

    def save(self, fs: FileWriteStream, model: Model):
        fs.writeStr(self.name)
        fs.writeStr(self.name_e)

        fs.writeBoneIndex(model.bones.index(self.bone))

        fs.writeSignedByte(self.collision_group_number)
        fs.writeUnsignedShort(self.collision_group_mask)

        fs.writeSignedByte(self.type)
        fs.writeVector(self.size)

        fs.writeVector(self.location)
        fs.writeVector(self.rotation)

        fs.writeFloat(self.mass)
        fs.writeFloat(self.velocity_attenuation)
        fs.writeFloat(self.rotation_attenuation)
        fs.writeFloat(self.bounce)
        fs.writeFloat(self.friction)

        fs.writeSignedByte(self.mode)

class Joint:
    MODE_SPRING6DOF = 0
    def __init__(self):
        self.name = ''
        self.name_e = ''

        self.mode = 0

        self.src_rigid: str = "" # Reference by name
        self.dst_rigid: str = ""

        self.location = []
        self.rotation = []

        self.maximum_location = []
        self.minimum_location = []
        self.maximum_rotation = []
        self.minimum_rotation = []

        self.spring_constant = []
        self.spring_rotation_constant = []

    def load(self, fs: FileReadStream, model: Model):
        try: self._load(fs, model)
        except struct.error: # possibly contains truncated data
            if self.src_rigid is None or self.dst_rigid is None: raise
            self.location = self.location or (0, 0, 0)
            self.rotation = self.rotation or (0, 0, 0)
            self.maximum_location = self.maximum_location or (0, 0, 0)
            self.minimum_location = self.minimum_location or (0, 0, 0)
            self.maximum_rotation = self.maximum_rotation or (0, 0, 0)
            self.minimum_rotation = self.minimum_rotation or (0, 0, 0)
            self.spring_constant = self.spring_constant or (0, 0, 0)
            self.spring_rotation_constant = self.spring_rotation_constant or (0, 0, 0)

    def _load(self, fs: FileReadStream, model: Model):
        self.name = fs.readStr()
        self.name_e = fs.readStr()

        self.mode = fs.readSignedByte()

        self.src_rigid = model.rigids.name_by_index(fs.readRigidIndex())
        self.dst_rigid = model.rigids.name_by_index(fs.readRigidIndex())

        self.location = fs.readVector(3)
        self.rotation = fs.readVector(3)

        self.minimum_location = fs.readVector(3)
        self.maximum_location = fs.readVector(3)
        self.minimum_rotation = fs.readVector(3)
        self.maximum_rotation = fs.readVector(3)

        self.spring_constant = fs.readVector(3)
        self.spring_rotation_constant = fs.readVector(3)

    def save(self, fs: FileWriteStream, model: Model):
        fs.writeStr(self.name)
        fs.writeStr(self.name_e)

        fs.writeSignedByte(self.mode)

        fs.writeRigidIndex(model.rigids.index(self.src_rigid))
        fs.writeRigidIndex(model.rigids.index(self.dst_rigid))

        fs.writeVector(self.location)
        fs.writeVector(self.rotation)

        fs.writeVector(self.minimum_location)
        fs.writeVector(self.maximum_location)
        fs.writeVector(self.minimum_rotation)
        fs.writeVector(self.maximum_rotation)

        fs.writeVector(self.spring_constant)
        fs.writeVector(self.spring_rotation_constant)


def load(path:str) -> Model:
    with FileReadStream(path) as fs:
        header = Header()
        header.load(fs)
        fs.setHeader(header)
        model = Model()
        try:
            model.load(fs)
        except struct.error as e:
            raise ValueError(f"Corrupted file: {e}")

        return model

def save(path: str, model: Model) -> None:
    with FileWriteStream(path) as fs:
        header = Header(model)
        header.save(fs)
        fs.setHeader(header)
        model.save(fs)
