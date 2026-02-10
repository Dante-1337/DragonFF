import ctypes
import os

class SquishFlags:
    BC1 = 1 << 0  # BC1 -  8 bytes / 4x4 block
    BC2 = 1 << 1  # BC2 - 16 bytes / 4x4 block
    BC3 = 1 << 2  # BC3 - 16 bytes / 4x4 block
    BC4 = 1 << 3  # BC4 - 16 bytes / 4x4 block
    BC5 = 1 << 4  # BC5 - 16 bytes / 4x4 block

    QUALITY_CLUSTER   = 1 << 5  # good quality, good speed
    QUALITY_RANGE     = 1 << 6  # poor quality, fast speed
    QUALITY_ITERATIVE = 1 << 8  # best quality, slow speed

    WEIGHT_COLOR_BY_ALPHA = 1 << 7
    SOURCE_IS_BGRA        = 1 << 9

class SquishCompressor:
    def __init__(self, dll_path=None):
        if dll_path is None:
            lib_dir = os.path.dirname(__file__)
            candidates = [
                os.path.join(lib_dir, "squish.dll"),
                os.path.join(lib_dir, "squish.so"),
            ]
            for candidate in candidates:
                if os.path.exists(candidate):
                    dll_path = candidate
                    break
            
            if dll_path is None:
                raise FileNotFoundError(
                    f"Could not find squish library"
                )
        
        self.squish = ctypes.CDLL(dll_path)
        self._setup_function_signatures()
    
    def _setup_function_signatures(self):
        self.squish.GetStorageRequirements.argtypes = [
            ctypes.c_int, ctypes.c_int, ctypes.c_int
        ]
        self.squish.GetStorageRequirements.restype = ctypes.c_int
        
        self.squish.CompressImage.argtypes = [
            ctypes.POINTER(ctypes.c_ubyte),
            ctypes.c_int, ctypes.c_int,
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_float)
        ]
        
        self.squish.DecompressImage.argtypes = [
            ctypes.POINTER(ctypes.c_ubyte),
            ctypes.c_int, ctypes.c_int,
            ctypes.c_void_p,
            ctypes.c_int
        ]
    
    def compress(self, rgba_data, width, height, compression_type='DXT5', 
                quality='Good', metric='Uniform', premultiply_alpha=False):

        # Build compression flags
        flags = SquishFlags.WEIGHT_COLOR_BY_ALPHA
        
        # Compression type
        if compression_type == 'DXT1':
            flags |= SquishFlags.BC1
        elif compression_type in ('DXT2', 'DXT3'):
            flags |= SquishFlags.BC2
            if compression_type == 'DXT2':
                premultiply_alpha = True
        elif compression_type in ('DXT4', 'DXT5'):
            flags |= SquishFlags.BC3
            if compression_type == 'DXT4':
                premultiply_alpha = True
        else:
            raise ValueError(f"Unknown compression type: {compression_type}")
        
        # Quality setting
        if quality == 'Best':
            flags |= SquishFlags.QUALITY_ITERATIVE
        elif quality == 'Good':
            flags |= SquishFlags.QUALITY_CLUSTER
        elif quality == 'Poor':
            flags |= SquishFlags.QUALITY_RANGE
        else:
            raise ValueError(f"Unknown quality setting: {quality}")
        
        # Color metric weights
        if metric == 'Perceptual':
            metric_weights = (ctypes.c_float * 3)(0.2126, 0.7152, 0.0722)
            metric_ptr = ctypes.cast(metric_weights, ctypes.POINTER(ctypes.c_float))
        else:
            metric_ptr = None
        
        # Premultiply alpha if needed
        if premultiply_alpha:
            for i in range(0, len(rgba_data), 4):
                alpha_factor = rgba_data[i + 3] / 255.0
                rgba_data[i + 0] = int(rgba_data[i + 0] * alpha_factor)
                rgba_data[i + 1] = int(rgba_data[i + 1] * alpha_factor)
                rgba_data[i + 2] = int(rgba_data[i + 2] * alpha_factor)
        

        rgba_size = width * height * 4
        rgba_array = (ctypes.c_ubyte * rgba_size).from_buffer(rgba_data)
        
        compressed_size = self.squish.GetStorageRequirements(width, height, flags)
        compressed_data = bytearray(compressed_size)
        compressed_array = (ctypes.c_ubyte * compressed_size).from_buffer(compressed_data)

        self.squish.CompressImage(
            rgba_array, width, height, 
            compressed_array, flags, metric_ptr
        )
        
        return bytes(compressed_data)

    def decompress(self, compressed_data, width, height, compression_type='DXT5'):

        flags = 0
        
        if compression_type in ('DXT1', 'DXT2'):
            flags |= SquishFlags.BC1
        elif compression_type in ('DXT3', 'DXT4'):
            flags |= SquishFlags.BC2
        elif compression_type == 'DXT5':
            flags |= SquishFlags.BC3

        rgba_size = width * height * 4
        rgba_data = bytearray(rgba_size)
        rgba_array = (ctypes.c_ubyte * rgba_size).from_buffer(rgba_data)
        
        compressed_size = len(compressed_data)
        compressed_array = (ctypes.c_ubyte * compressed_size).from_buffer_copy(compressed_data)

        self.squish.DecompressImage(
            rgba_array, width, height,
            compressed_array, flags
        )
        
        return bytes(rgba_data)

_compressor = None

def get_compressor():
    global _compressor
    if _compressor is None:
        _compressor = SquishCompressor()
    return _compressor