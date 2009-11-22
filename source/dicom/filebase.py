# filebase.py 
"""Hold DicomFile class, which does basic I/O for a dicom file."""
# Copyright (c) 2008 Darcy Mason
# This file is part of pydicom, relased under an MIT license.
#    See the file license.txt included with this distribution, also
#    available at http://pydicom.googlecode.com

from dicom.tag import Tag
from struct import unpack, pack

from StringIO import StringIO
import logging
logger = logging.getLogger('pydicom')

class DicomIO(object):
    """File object which holds transfer syntax info and anything else we need."""
    
    max_read_attempts = 3 # number of times to read if don't get requested bytes
    defer_size = None     # default
    
    def __init__(self, *args, **kwargs):
        self._ImplicitVR = True   # start with this by default
    def __del__(self):
        self.close()
    def read_tag(self):
        """Read and return a dicom tag (two unsigned shorts) from the file."""
        return Tag((self.read_US(), self.read_US()))
    def write_tag(self, tag):
        """Write a dicom tag (two unsigned shorts) to the file."""
        tag = Tag(tag)  # make sure is an instance of class, not just a tuple or int
        self.write_US(tag.group)
        self.write_US(tag.element)
    def read_leUS(self):
        """Return an unsigned short from the file with little endian byte order"""
        bytes = self.read(2)
        if len(bytes) == 0: # needed for reading "next" tag when at end of file
            raise EOFError
        return unpack("<H", bytes)[0]
    
    def read_beUS(self):
        """Return an unsigned short from the file with big endian byte order"""
        bytes = self.read(2)
        if len(bytes) == 0: # needed for reading "next" tag when at end of file
            raise EOFError
        return unpack(">H", bytes)[0]
    
    def read_leUL(self):
        """Return an unsigned long read with little endian byte order"""
        return unpack("<L", self.read(4))[0]
    def read(self, length=None, need_exact_length=True):
        """Reads the required length, returns EOFError if gets less
        
        If length is None, then read all bytes
        """
        parent_read = self.parent_read # super(DicomIO, self).read
        if length is None:
            return parent_read() # get all of it
        bytes = parent_read(length)
        if len(bytes) < length and need_exact_length:
            # Didn't get all the desired bytes. Keep trying to get the rest. If reading across network, might want to add a delay here
            attempts = 0
            while attempts < self.max_read_attempts and len(bytes) < length:
                bytes += parent_read(length-len(bytes))
                attempts += 1
            if len(bytes) < length:
                start_pos = self.tell() - len(bytes)
                msg = "Unexpected end of file. "
                msg += "Read %d bytes of %d expected starting at position 0x%x" % (len(bytes), length, start_pos)
                # logger.error(msg)   # don't need this since raising error anyway
                raise EOFError, msg
        return bytes
    def write_leUS(self, val):
        """Write an unsigned short with little endian byte order"""
        self.write(pack("<H", val))
    def write_leUL(self, val):
        """Write an unsigned long with little endian byte order"""
        self.write(pack("<L", val))
    def write_beUS(self, val):
        """Write an unsigned short with big endian byte order"""
        self.write(pack(">H", val))
    def write_beUL(self, val):
        """Write an unsigned long with big endian byte order"""
        self.write(pack(">L", val))

    write_US = write_leUS   # XXX should we default to this?
    write_UL = write_leUL   # XXX "
    
    def read_beUL(self):
        """Return an unsigned long read with big endian byte order"""
        return unpack(">L", self.read(4))[0]

    # Set up properties BigEndian, LittleEndian, ImplicitVR, ExplicitVR.
    # Big/Little Endian changes functions to read unsigned short or long, e.g. length fields etc
    def _setLittleEndian(self, value):
        self._LittleEndian = value
        if value:  # LittleEndian
            self.read_US = self.read_leUS
            self.read_UL = self.read_leUL
            self.write_US = self.write_leUS
            self.write_UL = self.write_leUL
        else:      # BigEndian
            self.read_US = self.read_beUS
            self.read_UL = self.read_beUL
            self.write_US = self.write_beUS
            self.write_UL = self.write_beUL
        
    def _getLittleEndian(self):
        return self._LittleEndian
    def _setBigEndian(self, value):
        self.isLittleEndian = not value # note: must use self.isLittleEndian not self._LittleEndian
    def _getBigEndian(self):
        return not self.isLittleEndian
    def _getImplicitVR(self):
        return self._ImplicitVR
    def _setImplicitVR(self, value):
        self._ImplicitVR = value
    def _setExplicitVR(self, value):
        self.isImplicitVR = not value
    def _getExplicitVR(self):
        return not self.isImplicitVR
    
    isLittleEndian = property(_getLittleEndian, _setLittleEndian)
    isBigEndian =    property(_getBigEndian, _setBigEndian)
    isImplicitVR =   property(_getImplicitVR, _setImplicitVR)
    isExplicitVR =   property(_getExplicitVR, _setExplicitVR)
        
class DicomFileLike(DicomIO):
    def __init__(self, file_like_obj):
        self.parent_read = file_like_obj.read
        self.write = file_like_obj.write
        self.seek = file_like_obj.seek
        self.tell = file_like_obj.tell
        self.close = file_like_obj.close
        if hasattr(file_like_obj, 'name'):
            self.name = file_like_obj.name
        
def DicomFile(*args, **kwargs):
    return DicomFileLike(open(*args, **kwargs))

def DicomStringIO(*args, **kwargs):
    return DicomFileLike(StringIO(*args, **kwargs))
