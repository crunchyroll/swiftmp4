"""
@project MP4 Stream
@author Young Kim (shadowing71@gmail.com)

StreamMp4.py - Represents a StreamMp4 that is a Pseudo-stream equivalent
"""

import os
from StreamAtoms import StreamAtomTree

# StreamMp4 - Used to stream a static MP4 file
class StreamMp4(object):
    atoms = None
    data = None
    
    def __init__(self, source, destination, start):
        self.source = source
        self.source_file = open(self.source, "rb")
        self.destination = destination
        self.start = int(float(start) * 1000)
    
    # pushToStream - Converts source file for pseudo-streaming
    def pushToStream(self):
        # Parse the MP4 into StreamAtom elements
        self._parseMp4()
        # Update StreamAtom elements
        self._updateAtoms()
        # Write to Stream
        self._writeToStream()
    
    def _parseMp4(self):
        source_size = os.path.getsize(self.source)
        self.atoms = StreamAtomTree(self.source_file, 0, source_size, 
                                    '', False, self.start)
    
    def _updateAtoms(self):
        self.data = {'CHUNK_OFFSET' : 0}
        for atom in self.atoms.get_atoms():
            if atom.copy:
                atom.update(self.data)
    
    def _writeToStream(self):
        file = open(self.destination, "w")
        for type in ["ftyp", "moov", "mdat"]:
            for atom in self.atoms.get_atoms():
                if atom.copy and atom.type == type:
                    atom.pushToStream(file, self.data)
        file.close()
    
    # getAtoms - Used primarily for debugging purposes
    def getAtoms(self):
        return self.atoms


class MalformedMP4(Exception):
    pass


class SwiftMp4Buffer(object):
    def __init__(self):
        self.buf = []
    
    def write(self, bytes):
        self.buf.append(bytes)
    
    def __iter__(self):
        self.queue = iter(list(self.buf))
        self.buf = []
        return self
    
    def next(self):
        return self.queue.next()
    

# SwiftStreamMp4 - Adapted version of StreamMp4 for Swift
class SwiftStreamMp4(StreamMp4):
    def __init__(self, source_file, source_size, start):
        self.source = None
        self.destination = None
        self.source_file = source_file
        self.source_size = source_size
        self.start = int(float(start) * 1000)
    
    def _parseMp4(self):
        self.atoms = StreamAtomTree(self.source_file, 0, self.source_size,
                                    '', False, self.start)
    
    def _yieldMetadataToStream(self):
        self.destination = SwiftMp4Buffer()
        if self._verifyMetadata():
            for type in ["ftyp", "moov", "mdat"]:
                for atom in self.atoms.get_atoms():
                    if atom.copy and atom.type == type:
                        atom.pushToStream(self.destination, self.data)
                        for chunk in self.destination:
                            yield chunk
        else:
            # The correct thing to do is to adjust the amount of bytes
            # to be requested to parse the metadata
            raise MalformedMP4()
    
    def _getByteRangeToRequest(self):
        if self._verifyMetadata():
            for atom in self.atoms.get_atoms():
                if atom.type == "mdat":
                    return (atom.stream_offset, atom.stream_offset + atom.stream_size-1)
        else:
            # The correct thing to do is to adjust the amount of bytes
            # to be requested to parse the metadata
            raise MalformedMP4()
    
    def _verifyMetadata(self):
        # Verify that correct metadata was parsed
        atom_type = {'ftyp': False, 'moov': False, 'mdat': False}
        for type in atom_type:
            for atom in self.atoms.get_atoms():
                if atom.type == type:
                    atom_type[type] = True
        verified = True
        for type in atom_type:
            verified = verified and atom_type[type]
        return verified
    
