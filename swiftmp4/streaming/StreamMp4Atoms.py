"""
@project MP4 Stream
@author Young Kim (shadowing71@gmail.com)

StreamMp4Atoms.py - Outlines specific Atom implementations for parsing and         
                    streaming ISO 14996-12 compliant MP4s
                    
                    File is structured as follows:
                    ftyp
                    moov
                        cmov
                        mvhd
                        trak
                            tkhd
                            mdia
                                mdhd
                                hdlr
                                minf
                                    vmhd
                                    smhd
                                    dinf
                                    stbl
                                        stsd
                                        stts
                                        stss
                                        ctts
                                        stsc
                                        stsz
                                        stco
                                        co64
                        tkhd
                    mdat
"""
import os

from Helper import *
from StreamAtoms import StreamAtom, StreamFullAtom, StreamAtomTree
from StreamExceptions import *

## Additional classes to keep track of trak metadata
class TrakData(object):
    # Define necessary objects in Trak
    timescale = None
    chunks = None
    chunk_samples = None
    chunk_samples_size = None
    start_chunk = None
    start_sample = None
    start_offset = None
        
    def setTimescale(self, timescale):
        self.timescale = timescale
    
    def getTimescale(self):
        return self.timescale
    
    def setChunks(self, chunks):
        self.chunks = chunks
    
    def getChunks(self):
        return self.chunks
    
    def setChunkSamples(self, chunk_samples):
        self.chunk_samples = chunk_samples
    
    def getChunkSamples(self):
        return self.chunk_samples
    
    def setChunkSampleSize(self, chunk_sample_sizes):
        self.chunk_samples_size = chunk_sample_sizes
    
    def getChunkSampleSize(self):
        return self.chunk_samples_size
    
    def setStartChunk(self, start_chunk):
        self.start_chunk = start_chunk
    
    def getStartChunk(self):
        return self.start_chunk
    
    def setStartSample(self, start_sample):
        self.start_sample = start_sample
    
    def getStartSample(self):
        return self.start_sample
    
    def setStartOffset(self, start_offset):
        self.start_offset = start_offset
    
    def getStartOffset(self):
        return self.start_offset
    


### ftyp
class ftyp(StreamAtom):
    def __init__(self, file, offset, size, type, is_64, start):
        StreamAtom.__init__(self, file, offset, size, type, is_64, start)
        self.copy = True
    
    def update(self, data={}):
        data['CHUNK_OFFSET'] += self.size
    
    def pushToStream(self, stream, data={}):
        # ftyp is just copied over
        self.file.seek(self.offset, os.SEEK_SET)
        stream.write(self.file.read(self.size))
    

### moov
class moov(StreamAtomTree):
    def __init__(self, file, offset, size, type, is_64, start):
        StreamAtomTree.__init__(self, file, offset, size, type, is_64, start)
        self.update_order = ["cmov", "mvhd", "trak", "tkhd"]
        self.stream_order = ["cmov", "mvhd", "trak", "tkhd"]
        self.copy = True
    
    def update(self, data={}):
        # Obtain MP4_TIMESCALE from mvhd for tkhd
        for atom in self.get_atoms():
            if atom.type == 'mvhd':
                data['MP4_TIMESCALE'] = atom.timescale
        super(moov, self).update(data)
        
        # Update CHUNK_OFFSET
        data['CHUNK_OFFSET'] += self.size
    

### cmov
class cmov(StreamAtom):
    def __init__(self, file, offset, size, type, is_64, start):
        raise AtomNotSupported()
    

### mvhd
class mvhd(StreamFullAtom):
    def __init__(self, file, offset, size, type, is_64, start):
        StreamFullAtom.__init__(self, file, offset, size, type, is_64, start)
        
        # Obtain necessary metadata
        if (self.version == 1):
            self.file.seek(16, os.SEEK_CUR)
            self._set_attr('timescale', read32(self.file))
            self._set_attr('duration', read64(self.file))
        else:
            self.file.seek(8, os.SEEK_CUR)
            self._set_attr('timescale', read32(self.file))
            self._set_attr('duration', read32(self.file))
            
        # As an optimization, verify that given start is less than duration
        duration = self.get_attribute('duration')
        timescale = self.get_attribute('timescale')
        stream_duration = duration - (int(self.start) * timescale / 1000)
        if stream_duration < 0:
            raise StartOutOfRange()
        else:
            # Save timescale to global for use in tkhd update
            self.timescale = timescale
        self.copy = True
    
    def update(self, data={}):
        # mvhd only needs its duration updated
        duration = self.get_attribute('duration')
        timescale = self.get_attribute('timescale')
        stream_duration = duration - (int(self.start) * timescale / 1000)
        self._set_attr('duration', stream_duration)
    
    def pushToStream(self, stream, data={}):
        size = self.size
        self.file.seek(self.offset, os.SEEK_SET)
        # Write in the full box
        if self.is_64:
            size -= 20
            stream.write(self.file.read(20))
        else:
            size -= 12
            stream.write(self.file.read(12))
        # Write in replaced duration data
        if (self.version == 1):
            size -= 28
            stream.write(self.file.read(20))
            self.file.seek(8, os.SEEK_CUR)
            stream.write(struct.pack(">Q", self.get_attribute('duration')))
        else:
            size -= 16
            stream.write(self.file.read(12))
            self.file.seek(4, os.SEEK_CUR)
            stream.write(struct.pack(">I", self.get_attribute('duration')))
        stream.write(self.file.read(size))
    

### trak
class trak(StreamAtomTree):
    def __init__(self, file, offset, size, type, is_64, start):
        StreamAtomTree.__init__(self, file, offset, size, type, is_64, start)
        self.update_order = ["tkhd", "mdia"]
        self.stream_order = ["tkhd", "mdia"]
        self.copy = True
    
    def update(self, data={}):
        data['TRAK_DATA'] = TrakData()
        super(trak, self).update(data)
        
        if 'TRAK_START_OFFSET' not in data:
            data['TRAK_START_OFFSET'] = data['TRAK_DATA'].getStartOffset()
        else:
            data['TRAK_START_OFFSET'] = min(data['TRAK_START_OFFSET'], data['TRAK_DATA'].getStartOffset())
    

### tkhd
class tkhd(StreamFullAtom):
    def __init__(self, file, offset, size, type, is_64, start):
        StreamFullAtom.__init__(self, file, offset, size, type, is_64, start)
        
        # Obtain necessary metadata
        if (self.version == 1):
            self.file.seek(24, os.SEEK_CUR)
            self._set_attr('duration', read64(self.file))
        else:
            self.file.seek(16, os.SEEK_CUR)
            self._set_attr('duration', read32(self.file))
        self.copy = True
    
    def update(self, data={}):
        # tkhd only needs its duration updated
        duration = self.get_attribute('duration')
        stream_duration = duration - (int(self.start) * data['MP4_TIMESCALE'] / 1000)
        self._set_attr('duration', stream_duration)
    
    def pushToStream(self, stream, data={}):
        size = self.size
        self.file.seek(self.offset, os.SEEK_SET)
        # Write in the full box
        if self.is_64:
            size -= 20
            stream.write(self.file.read(20))
        else:
            size -= 12
            stream.write(self.file.read(12))
        # Write in replaced duration data
        if (self.version == 1):
            size -= 32
            stream.write(self.file.read(24))
            self.file.read(8)
            stream.write(struct.pack(">Q", self.get_attribute('duration')))
        else:
            size -= 20
            stream.write(self.file.read(16))
            self.file.read(4)
            stream.write(struct.pack(">I", self.get_attribute('duration')))
        stream.write(self.file.read(size))
    

### mdia
class mdia(StreamAtomTree):
    def __init__(self, file, offset, size, type, is_64, start):
        StreamAtomTree.__init__(self, file, offset, size, type, is_64, start)
        self.update_order = ["mdhd", "hdlr", "minf"]
        self.stream_order = ["mdhd", "hdlr", "minf"]
        self.copy = True
    

### mdhd
class mdhd(StreamFullAtom):
    def __init__(self, file, offset, size, type, is_64, start):
        StreamFullAtom.__init__(self, file, offset, size, type, is_64, start)
        self.copy = True
        
        # Obtain necessary metadata
        if (self.version == 1):
            self.file.seek(16, os.SEEK_CUR)
            self._set_attr('timescale', read32(self.file))
            self._set_attr('duration', read64(self.file))
        else:
            self.file.seek(8, os.SEEK_CUR)
            self._set_attr('timescale', read32(self.file))
            self._set_attr('duration', read32(self.file))
    
    def update(self, data={}):
        # Set trak metadata
        trak = data['TRAK_DATA']
        trak.setTimescale(self.get_attribute('timescale'))
        
        # mdhd only needs its duration updated
        duration = self.get_attribute('duration')
        timescale = self.get_attribute('timescale')
        stream_duration = duration - (int(self.start) * timescale / 1000)
        self._set_attr('duration', stream_duration)
    
    def pushToStream(self, stream, data={}):
        size = self.size
        self.file.seek(self.offset, os.SEEK_SET)
        # Write in the full box
        if self.is_64:
            size -= 20
            stream.write(self.file.read(20))
        else:
            size -= 12
            stream.write(self.file.read(12))
        # Write in replaced duration data
        if (self.version == 1):
            size -= 28
            stream.write(self.file.read(20))
            self.file.read(8)
            stream.write(struct.pack(">Q", self.get_attribute('duration')))
        else:
            size -= 16
            stream.write(self.file.read(12))
            self.file.read(4)
            stream.write(struct.pack(">I", self.get_attribute('duration')))
        stream.write(self.file.read(size))
    

### hdlr
class hdlr(StreamAtom):
    def __init__(self, file, offset, size, type, is_64, start):
        StreamAtom.__init__(self, file, offset, size, type, is_64, start)
        self.copy = True
    
    def update(self, data={}):
        # No modifications needed for hdlr
        return
    
    def pushToStream(self, stream, data={}):
        # hdlr is just copied over
        self.file.seek(self.offset, os.SEEK_SET)
        stream.write(self.file.read(self.size))
    

### minf
class minf(StreamAtomTree):
    def __init__(self, file, offset, size, type, is_64, start):
        StreamAtomTree.__init__(self, file, offset, size, type, is_64, start)
        self.update_order = ["vmhd", "smhd", "dinf", "stbl"]
        self.stream_order = ["vmhd", "smhd", "dinf", "stbl"]
        self.copy = True
    

### vmhd
class vmhd(StreamAtom):
    def __init__(self, file, offset, size, type, is_64, start):
        StreamAtom.__init__(self, file, offset, size, type, is_64, start)
        self.copy = True
    
    def update(self, data={}):
        # No modifications needed for vmhd
        return
    
    def pushToStream(self, stream, data={}):
        # vmhd is just copied over
        self.file.seek(self.offset, os.SEEK_SET)
        stream.write(self.file.read(self.size))
    

### smhd
class smhd(StreamAtom):
    def __init__(self, file, offset, size, type, is_64, start):
        StreamAtom.__init__(self, file, offset, size, type, is_64, start)
        self.copy = True
    
    def update(self, data={}):
        # No modifications needed for smhd
        return
    
    def pushToStream(self, stream, data={}):
        # smhd is just copied over
        self.file.seek(self.offset, os.SEEK_SET)
        stream.write(self.file.read(self.size))
    

### dinf
class dinf(StreamAtomTree):
    def __init__(self, file, offset, size, type, is_64, start):
        StreamAtomTree.__init__(self, file, offset, size, type, is_64, start)
        self.copy = True
    
    def update(self, data={}):
        # No modifications needed for dinf
        return
    
    def pushToStream(self, stream, data={}):
        # vmhd is just copied over
        self.file.seek(self.offset, os.SEEK_SET)
        stream.write(self.file.read(self.size))
    

### stbl
class stbl(StreamAtomTree):
    def __init__(self, file, offset, size, type, is_64, start):
        StreamAtomTree.__init__(self, file, offset, size, type, is_64, start)
        self.update_order = ["stsd", "stts", "stss", "ctts", "stsc", "stsz", "stco", "co64"]
        self.stream_order = ["stsd", "stts", "stss", "ctts", "stsc", "stsz", "stco", "co64"]
        self.copy = True
    
    def update(self, data={}):
        trak = data['TRAK_DATA']
        for atom in self.get_atoms():
            if (atom.type == 'stco') or (atom.type == 'co64'):
                trak.setChunks(atom.get_attribute('chunk_count'))
        super(stbl, self).update(data)
    

### stsd
class stsd(StreamAtom):
    def __init__(self, file, offset, size, type, is_64, start):
        StreamAtom.__init__(self, file, offset, size, type, is_64, start)
        self.copy = True
    
    def update(self, data={}):
        # No modifications needed for stsd
        return
    
    def pushToStream(self, stream, data={}):
        # stsd is just copied over
        self.file.seek(self.offset, os.SEEK_SET)
        stream.write(self.file.read(self.size))
    

### stts
class stts(StreamFullAtom):
    def __init__(self, file, offset, size, type, is_64, start):
        StreamFullAtom.__init__(self, file, offset, size, type, is_64, start)
        self.copy = True
        
        # Set stts metadata
        self._set_attr('entry_count', read32(self.file))
        entries = []
        while self.file.tell() < (offset+size):
            count = read32(self.file)
            if self.file.tell() > (offset+size):
                raise MalformedMP4()
            duration = read32(self.file)
            if self.file.tell() > (offset+size):
                raise MalformedMP4()
            entries.append((count, duration))
        if self.get_attribute('entry_count') != len(entries):
            raise MalformedMP4()
        else:
            self._set_attr('entries', entries)
    
    def update(self, data={}):
        # Derive stream_time from trak data
        trak = data['TRAK_DATA']
        trak_timescale = trak.getTimescale()
        start_sample = 0
        stream_time = int(self.start) * trak_timescale / 1000
        
        # Parse entries to determine what to truncate
        valid = False
        truncate_index = 0
        entries = self.get_attribute('entries')
        for index, entry in enumerate(entries):
            (count, duration) = entry
            if (stream_time < (count*duration)):
                start_sample += (stream_time / duration)
                count -= (stream_time / duration)
                entries[index] = (count, duration)
                truncate_index = index
                valid = True
                break
            else:
                # Update size accordingly
                self.size -= 8
                start_sample += count
                stream_time -= (count*duration)
                
        if valid:
            if truncate_index > 0:
                entries = entries[truncate_index:]
        
            # Modify own entries accordingly
            self._set_attr('entry_count', len(entries))
            self._set_attr('entries', entries)
            
            # Set startSample to be used in stss, stsc, ctts, stsz
            trak.setStartSample(start_sample)
        else:
            raise MalformedMP4()
    
    def pushToStream(self, stream, data={}):
        # Simply copy over the initial entries in stts
        self.file.seek(self.offset, os.SEEK_SET)
        
        # First, copy in FullBox
        if self.is_64:
            stream.write(self.file.read(8))
            self.file.seek(8, os.SEEK_CUR)
            stream.write(struct.pack(">Q", self.size))
        else:
            self.file.seek(4, os.SEEK_CUR)
            stream.write(struct.pack(">I", self.size))
            stream.write(self.file.read(4))
        stream.write(self.file.read(4))
        
        # Write in stts
        entries = self.get_attribute('entries')
        stream.write(struct.pack(">I", len(entries)))
        for entry in entries:
            (count, duration) = entry
            stream.write(struct.pack(">II", count, duration))
    

### stss
class stss(StreamFullAtom):
    def __init__(self, file, offset, size, type, is_64, start):
        StreamFullAtom.__init__(self, file, offset, size, type, is_64, start)
        self.copy = True
        
        # Set stss metadata
        self._set_attr('entry_count', read32(self.file))
        entries = []
        while self.file.tell() < (offset+size):
            entry = read32(self.file)
            if self.file.tell() > (offset+size):
                raise MalformedMP4()
            entries.append(entry)
        if self.get_attribute('entry_count') != len(entries):
            raise MalformedMP4()
        else:
            self._set_attr('entries', entries)
    
    def update(self, data={}):
        # Obtain start_sample from trak data
        trak = data['TRAK_DATA']
        start_sample = trak.getStartSample()
        
        if start_sample:
            start_sample += 1
            
            # Parse entries to determine what to truncate
            valid = False
            truncate_index = 0
            entries = self.get_attribute('entries')
            for index, entry in enumerate(entries):
                sample = entry
                if (sample >= start_sample):
                    valid = True
                    truncate_index = index
                    break
                else:
                    self.size -= 4
                    
            if valid:
                start_sample -= 1
                if truncate_index > 0:
                    entries = entries[truncate_index:]
                for index, entry in enumerate(entries):
                    sample = entry - start_sample
                    entries[index] = sample
                self._set_attr('entry_count', len(entries))
                self._set_attr('entries', entries)                
            else:
                raise MalformedMP4()
        else:
            # Signal that MP4 is being parsed incorrectly
            raise IncorrectParseMP4()
    
    def pushToStream(self, stream, data={}):
        # Simply copy over the initial entries in stss
        self.file.seek(self.offset, os.SEEK_SET)
        
        # First, copy in FullBox
        if self.is_64:
            stream.write(self.file.read(8))
            self.file.seek(8, os.SEEK_CUR)
            stream.write(struct.pack(">Q", self.size))
        else:
            self.file.seek(4, os.SEEK_CUR)
            stream.write(struct.pack(">I", self.size))
            stream.write(self.file.read(4))
        stream.write(self.file.read(4))
        
        # Write in stss
        entries = self.get_attribute('entries')
        stream.write(struct.pack(">I", len(entries)))
        for entry in entries:
            stream.write(struct.pack(">I", entry))
    

### ctts
class ctts(StreamFullAtom):
    def __init__(self, file, offset, size, type, is_64, start):
        StreamFullAtom.__init__(self, file, offset, size, type, is_64, start)
        self.copy = True
        
        # Set ctts metadat
        self._set_attr('entry_count', read32(self.file))
        entries = []
        while self.file.tell() < (offset+size):
            count = read32(self.file)
            if self.file.tell() > (offset+size):
                raise MalformedMP4()
            soffset = read32(self.file)
            if self.file.tell() > (offset+size):
                raise MalformedMP4()
            entries.append((count, soffset))
        if self.get_attribute('entry_count') != len(entries):
            raise MalformedMP4()
        else:
            self._set_attr('entries', entries)
    
    def update(self, data={}):
        # Obtain start_sample from trak data
        trak = data['TRAK_DATA']
        start_sample = trak.getStartSample()
        if start_sample:
            start_sample += 1
            
            # Parse entries to determine what to truncate
            valid = False
            truncate_index = 0
            entries = self.get_attribute('entries')
            for index, entry in enumerate(entries):
                (count, offset) = entry
                if (start_sample <= count):
                    count -= (start_sample - 1)
                    valid = True
                    entries[index] = (count, offset)
                    truncate_index = index
                    break
                else:
                    start_sample -= count
                    self.size -= 8
            if valid:
                if truncate_index > 0:
                    entries = entries[truncate_index:]
                
                # Modify own entries accordingly
                self._set_attr('entry_count', len(entries))
                self._set_attr('entries', entries)                
            else:
                # If it failed, just don't copy it
                self.copy = False
        else:
            self.copy = False
    
    def pushToStream(self, stream, data={}):
        if self.copy:
            # Simply copy over the initial entries in stts
            print 'new offset', self.offset
            self.file.seek(self.offset, os.SEEK_SET)
            
            # First, copy in FullBox
            if self.is_64:
                stream.write(self.file.read(8))
                self.file.seek(8, os.SEEK_CUR)
                stream.write(struct.pack(">Q", self.size))
            else:
                self.file.seek(4, os.SEEK_CUR)
                stream.write(struct.pack(">I", self.size))
                stream.write(self.file.read(4))
            stream.write(self.file.read(4))
            
            # Write in ctts
            entries = self.get_attribute('entries')
            stream.write(struct.pack(">I", len(entries)))
            for entry in entries:
                (count, offset) = entry
                stream.write(struct.pack(">II", count, offset))
    

### stsc
class stsc(StreamFullAtom):
    def __init__(self, file, offset, size, type, is_64, start):
        StreamFullAtom.__init__(self, file, offset, size, type, is_64, start)
        self.copy = True
        
        # Set stsc metadat
        self._set_attr('entry_count', read32(self.file))
        
        # Verify that stsc exists
        if (self.get_attribute('entry_count') == 0):
            raise MalformedMP4()
            
        entries = []
        while self.file.tell() < (offset+size):
            chunk = read32(self.file)
            if self.file.tell() > (offset+size):
                raise MalformedMP4()
            samples = read32(self.file)
            if self.file.tell() > (offset+size):
                raise MalformedMP4()
            id = read32(self.file)
            if self.file.tell() > (offset+size):
                raise MalformedMP4()
            entries.append((chunk, samples, id))
        if self.get_attribute('entry_count') != len(entries):
            raise MalformedMP4()
        else:
            self._set_attr('entries', entries)
    
    def update(self, data={}):
        # Obtain chunk data
        trak = data['TRAK_DATA']
        start_sample = trak.getStartSample()
        
        # Parse entries to determine what to modify
        valid = False
        truncate_index = 1
        entries = self.get_attribute('entries')
        
        # Iterate over chunks
        (chunk, samples, id) = entries[0]
        self.size -= 12
        
        while (truncate_index < len(entries)):
            (next_chunk, next_samples, next_id) = entries[truncate_index]
            n = (next_chunk - chunk) * samples
            
            if (start_sample <= n):
                valid = True
                break
                
            start_sample -= n
            chunk = next_chunk
            samples = next_samples
            id = next_id
            truncate_index += 1
            self.size -= 12
            
        if not valid:
            next_chunk = trak.getChunks()
            n = (next_chunk - chunk) * samples
            if (start_sample > n):
                raise MalformedMP4()
                
        # Modify stsc data
        if (samples == 0):
            raise MalformedMP4()
            
        # Proceed to truncate rest of entries
        truncate_index -= 1
        self.size += 12
        if truncate_index > 0:
            entries = entries[truncate_index:]
        (chunk, samples, id) = entries[0]
        entries[0] = (1, samples, id)
        
        # Calculate chunk offset data
        start_chunk = (chunk - 1) + (start_sample / samples)
        chunk_samples = start_sample % samples
        
        index = 1
        if (chunk_samples and (next_chunk - start_chunk) == 2):
            entries[0] = (1, samples - chunk_samples, id)
        elif chunk_samples:
            # Insert an entry
            entries.insert(0, (1, samples-chunk_samples, id))
            entries[1] = (2, samples, id)
            self.size += 12
            index += 1
            
        while (index < len(entries)):
            (chunk, samples, id) = entries[index]
            chunk -= start_chunk
            entries[index] = (chunk, samples, id)
            index += 1
        self._set_attr('entry_count', len(entries))
        self._set_attr('entries', entries)
        
        # Set metadata
        trak.setStartChunk(start_chunk)
        trak.setChunkSamples(chunk_samples)
    
    def pushToStream(self, stream, data={}):
        # Simply copy over the initial entries in stts
        self.file.seek(self.offset, os.SEEK_SET)
        
        # First, copy in FullBox
        if self.is_64:
            stream.write(self.file.read(8))
            self.file.seek(8, os.SEEK_CUR)
            stream.write(struct.pack(">Q", self.size))
        else:
            self.file.seek(4, os.SEEK_CUR)
            stream.write(struct.pack(">I", self.size))
            stream.write(self.file.read(4))
        stream.write(self.file.read(4))
        
        # Write in stsc
        entries = self.get_attribute('entries')
        stream.write(struct.pack(">I", len(entries)))
        for entry in entries:
            (chunk, samples, id) = entry
            stream.write(struct.pack(">III", chunk, samples, id))
    

### stsz
class stsz(StreamFullAtom):
    def __init__(self, file, offset, size, type, is_64, start):
        StreamFullAtom.__init__(self, file, offset, size, type, is_64, start)
        self.copy = True
        
        # Set stsz metadata
        self._set_attr('uniform_size', read32(self.file))
        self._set_attr('entry_count', read32(self.file))
        self.uniform = True
        
        if self.get_attribute('uniform_size') == 0:
            self.uniform = False
            entries = []
            while self.file.tell() < (offset+size):
                entry = read32(self.file)
                if self.file.tell() > (offset+size):
                    raise MalformedMP4()
                entries.append(entry)
            if self.get_attribute('entry_count') != len(entries):
                raise MalformedMP4()
            else:
                self._set_attr('entries', entries)
    
    def update(self, data={}):
        # stsz only needs to be updated if it is not uniform
        if not self.uniform:
            # Obtain start_sample from trak data
            trak = data['TRAK_DATA']
            start_sample = trak.getStartSample()
            chunk_samples = trak.getChunkSamples()
            
            if (start_sample > self.get_attribute('entry_count')):
                raise MalformedMP4()
                
            truncate_index = start_sample
            entries = self.get_attribute('entries')
            
            # Determine and set chunk_sample_size
            chunk_sample_size = 0
            chunk_index = truncate_index - chunk_samples
            while (chunk_index < truncate_index):
                chunk_sample_size += entries[chunk_index]
                chunk_index += 1
            trak.setChunkSampleSize(chunk_sample_size)
            
            # Modify stsz
            if (truncate_index > 0):
                entries = entries[truncate_index:]
                self.size -= (4*truncate_index)
            self._set_attr('entry_count', len(entries))
            self._set_attr('entries', entries)
    
    def pushToStream(self, stream, data={}):
        self.file.seek(self.offset, os.SEEK_SET)
        
        if self.uniform:
            # stsz is just copied over
            stream.write(self.file.read(self.size))
        else:
            # Copy in fullbox
            if self.is_64:
                stream.write(self.file.read(8))
                self.file.seek(8, os.SEEK_CUR)
                stream.write(struct.pack(">Q", self.size))
            else:
                self.file.seek(4, os.SEEK_CUR)
                stream.write(struct.pack(">I", self.size))
                stream.write(self.file.read(4))
            stream.write(self.file.read(4))
            
            # Write in stsz
            entries = self.get_attribute('entries')
            stream.write(struct.pack(">II", 0, len(entries)))
            for entry in entries:
                stream.write(struct.pack(">I", entry))
    

### stco
class stco(StreamFullAtom):
    def __init__(self, file, offset, size, type, is_64, start):
        StreamFullAtom.__init__(self, file, offset, size, type, is_64, start)
        self.copy = True
        
        # Obtain metadata
        self._set_attr('chunk_count', read32(self.file))
        entries = []
        while self.file.tell() < (offset+size):
            chunk_offset = read32(self.file)
            if self.file.tell() > (offset+size):
                raise MalformedMP4()
            entries.append(chunk_offset)
        if self.get_attribute('chunk_count') != len(entries):
            raise MalformedMP4()
        else:
            self._set_attr('entries', entries)
    
    def update(self, data={}):
        trak = data['TRAK_DATA']
        start_chunk = trak.getStartChunk()
        chunks = trak.getChunks()
        entries = self.get_attribute('entries')
        
        if not entries or (start_chunk > chunks):
            raise MalformedMP4()
        truncate_index = start_chunk
        
        if truncate_index > 0:
            entries = entries[truncate_index:]
            self.size -= (4 * truncate_index)
        
        # Set start offset
        start_offset = entries[0] + trak.getChunkSampleSize()
        trak.setStartOffset(start_offset)
        entries[0] = start_offset
        
        self._set_attr('chunk_count', len(entries))
        self._set_attr('entries', entries)        
    
    def pushToStream(self, stream, data={}):
        # Simply copy over the initial entries in stco
        self.file.seek(self.offset, os.SEEK_SET)
        
        # First, copy in FullBox
        if self.is_64:
            stream.write(self.file.read(8))
            self.file.seek(8, os.SEEK_CUR)
            stream.write(struct.pack(">Q", self.size))
        else:
            self.file.seek(4, os.SEEK_CUR)
            stream.write(struct.pack(">I", self.size))
            stream.write(self.file.read(4))
        stream.write(self.file.read(4))
        
        # Write in stco
        entries = self.get_attribute('entries')
        stream.write(struct.pack(">I", len(entries)))
        for entry in entries:
            stream.write(struct.pack(">I", entry+data['CHUNK_OFFSET']))
    

### co64
class co64(StreamFullAtom):
    def __init__(self, file, offset, size, type, is_64, start):
        StreamFullAtom.__init__(self, file, offset, size, type, is_64, start)
        self.copy = True
        
        # Obtain metadata
        self._set_attr('chunk_count', read32(self.file))
        entries = []
        while self.file.tell() < (offset+size):
            chunk_offset = read64(self.file)
            if self.file.tell() > (offset+size):
                raise MalformedMP4()
            entries.append(chunk_offset)
        if self.get_attribute('chunk_count') != len(entries):
            raise MalformedMP4()
        else:
            self._set_attr('entries', entries)
    
    def update(self, data={}):
        trak = data['TRAK_DATA']
        start_chunk = trak.getStartChunk()
        chunks = trak.getChunks()
        entries = self.get_attribute('entries')
        
        if not entries or (start_chunk > chunks):
            raise MalformedMP4()
        truncate_index = start_chunk
        
        if truncate_index > 0:
            entries = entries[truncate_index:]
            self.size -= (8 * truncate_index)
        
        # Set start offset
        start_offset = entries[0] + trak.getChunkSampleSize()
        trak.setStartOffset(start_offset)
        entries[0] = start_offset
        
        self._set_attr('chunk_count', len(entries))
        self._set_attr('entries', entries)
    
    def pushToStream(self, stream, data={}):
        # Simply copy over the initial entries in co64
        self.file.seek(self.offset, os.SEEK_SET)
        
        # First, copy in FullBox
        if self.is_64:
            stream.write(self.file.read(8))
            self.file.seek(8, os.SEEK_CUR)
            stream.write(struct.pack(">Q", self.size))
        else:
            self.file.seek(4, os.SEEK_CUR)
            stream.write(struct.pack(">I", self.size))
            stream.write(self.file.read(4))
        stream.write(self.file.read(4))
        
        # Write in co64
        entries = self.get_attribute('entries')
        stream.write(struct.pack(">I", len(entries)))
        for entry in entries:
            stream.write(struct.pack(">Q", entry+data['CHUNK_OFFSET']))
    

### mdat
class mdat(StreamAtom):
    def __init__(self, file, offset, size, type, is_64, start):
        StreamAtom.__init__(self, file, offset, size, type, is_64, start)
        self.file_offset = 0
        self.copy = True
    
    def update(self, data={}):
        start_offset = data['TRAK_START_OFFSET']
        
        # Save file offsets
        self.stream_offset = start_offset
        self.stream_size = (self.offset + self.size - start_offset)
        
        # Determine file size
        self.size = self.stream_size
        if self.is_64:
            self.size += 16
            data['CHUNK_OFFSET'] += 16
        else:
            self.size += 8
            data['CHUNK_OFFSET'] += 8
            
        data['CHUNK_OFFSET'] -= self.stream_offset
    
    def pushToStream(self, stream, data={}):
        # Write in the Box portion of the mdat
        if self.is_64:
            stream.write(struct.pack(">I4sQ", 0, self.type, self.size))
        else:
            stream.write(struct.pack(">I4s", self.size, self.type))
    
