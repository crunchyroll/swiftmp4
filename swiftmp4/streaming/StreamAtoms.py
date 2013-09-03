"""
@project MP4 Stream
@author Young Kim (shadowing71@gmail.com)

StreamAtoms.py - Outlines generic Atom structure to be used for parsing
                 ISO 14996-12 compliant MP4s
"""
import os
import struct

from Helper import read8, read24, read32, read64, type_to_str, EndOfFile
from StreamExceptions import *

# ISO 14996-12 Atoms that are Trees
ATOM_TREES = [ 'moov', 'trak', 'edts', 'mdia',
               'minf', 'dinf', 'stbl', 'mvex',
               'moof', 'traf', 'mfra', 'skip',
               'udta', 'meta', 'dinf', 'ipro',
               'sinf', 'fiin', 'paen', 'meco'
               ]

# Parses an Atom Tree
def parse_atom_tree(mp4, range, start):
    atoms = []
    while mp4.tell() < range:
        atom = parse_atom(mp4, start)
        if atom is None:
            break
        else:
            atoms.append(atom)
            if (atom.offset + atom.size) >= range:
                # Terminate loop instead of prematurely going on
                break
            mp4.seek(atom.offset + atom.size, os.SEEK_SET)
    return atoms

# Parses an Atom
def parse_atom(mp4, start):
    try:
        offset = mp4.tell()
        is_64 = False
        size = read32(mp4)
        type = type_to_str(read32(mp4))
        if (size == 1):
            size = read64(mp4)
            is_64 = True
        elif (size == 0):
            # Hack to be able to interpret StringIO
            if hasattr(mp4, 'fileno'):
                size = (os.fstat(mp4.fileno()).st_size - offset)
            else:
                if type == 'mdat':
                    raise MalformedMP4()
                else:
                    size = (mp4.len - offset)
        return create_atom(mp4, offset, size, type, is_64, start)
    except EndOfFile:
        return None

def create_atom(mp4, offset, size, type, is_64, start):
    try:
        return eval("%s(mp4, offset, size, type, is_64, start)" % type)
    except NameError:
        if type in ATOM_TREES:
            return StreamAtomTree(mp4, offset, size, type, is_64, start)
        else:
            return StreamAtom(mp4, offset, size, type, is_64, start)
    except TypeError:
        return StreamAtom(mp4, offset, size, type, is_64, start)

# Generic StreamAtom Object - Equivalent to Box in ISO specs
class StreamAtom(object):
    # Copy verifies if parsed Atom should be copied into Stream
    copy = False
    
    def __init__(self, file, offset, size, type, is_64, start):
        self.file = file
        self.offset = offset
        self.size = size
        self.type = type
        self.is_64 = is_64
        self.start = start
        self.children = []
        self.attrs = {}
    
    def _set_attr(self, key, value):
        self.attrs[key] = value
    
    def _set_children(self, children):
        for child in children:
            child.parent = self
        self.children = children
    
    def get_attribute(self, key):
        return self.attrs[key]
    
    def get_atoms(self):
        return self.children
    
    # Prepare StreamAtom to be pushed into a stream
    def update(self, data={}):
        raise NotImplementedError()
    
    # Returns amount of bytes copied into file
    def pushToStream(self, stream, data={}):
        raise NotImplementedError()
    

# Generic StreamFullAtom - Equivalent to FullBox in ISO specs
class StreamFullAtom(StreamAtom):
    def  __init__(self, file, offset, size, type, is_64, start):
        StreamAtom.__init__(self, file, offset, size, type, is_64, start)
        self.version = read8(file)
        self.bit = read24(file)
    

# Generic StreamAtomTree - Represents a Tree of Atoms
class StreamAtomTree(StreamAtom):
    def __init__(self, file, offset, size, type, is_64, start):
        StreamAtom.__init__(self, file, offset, size, type, is_64, start)
        children = parse_atom_tree(file, offset+size, start)
        self._set_children(children)
        self.update_order = []
        self.stream_order = []
    
    def update(self, data={}):
        if self.copy:
            # Force each atom that is copyable to update itself
            if self.update_order:
                for type in self.update_order:
                    for atom in self.get_atoms():
                        if atom.copy and atom.type == type:
                            atom.update(data)
            else:
                for atom in self.get_atoms():
                    if atom.copy:
                        atom.update(data)
            atom_size = 0
            for atom in self.get_atoms():
                if atom.copy:
                    atom_size += atom.size
            # Calculate if 64 bit flag has to be written in
            if atom_size > 4294967287:
                self.size = atom_size + 16
                self.is_64 = True
            else:
                self.size = atom_size + 8
                self.is_64 = False
    
    def pushToStream(self, stream, data={}):
        if self.copy:
            if self.is_64:
                stream.write(struct.pack(">I4sQ", 1, self.type, self.size))
            else:
                stream.write(struct.pack(">I4s", self.size, self.type))
            if self.stream_order:
                for type in self.stream_order:
                    for atom in self.get_atoms():
                        if atom.copy and atom.type == type:
                            atom.pushToStream(stream, data)
            else:
                for atom in self.get_atoms():
                    if atom.copy:
                        atom.pushToStream(stream, data)
    

# Import specific Mp4Atoms
from StreamMp4Atoms import *
