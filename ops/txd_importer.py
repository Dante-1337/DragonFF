# GTA DragonFF - Blender scripts to edit basic GTA formats
# Copyright (C) 2019  Parik

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import bpy
import os

from ..gtaLib import txd

_D3D_TO_COMPRESSION = {
    txd.D3DFormat.D3D_DXT1: "1",
    txd.D3DFormat.D3D_DXT2: "2",
    txd.D3DFormat.D3D_DXT3: "3",
    txd.D3DFormat.D3D_DXT4: "4",
    txd.D3DFormat.D3D_DXT5: "5",
}

_RASTER_TO_ENUM = {
    txd.RasterFormat.RASTER_8888: "1",
    txd.RasterFormat.RASTER_4444: "2",
    txd.RasterFormat.RASTER_1555: "3",
    txd.RasterFormat.RASTER_888:  "4",
    txd.RasterFormat.RASTER_565:  "5",
    txd.RasterFormat.RASTER_555:  "6",
    txd.RasterFormat.RASTER_LUM:  "7",
}

_MODE_TO_FILTER = {
    0x00: "0",
    0x01: "1",
    0x02: "2",
    0x03: "3",
    0x04: "4",
    0x05: "5",
    0x06: "6",
}

_NIBBLE_TO_ADDR = {
    0x00: "0",
    0x01: "1",
    0x02: "2",
    0x03: "3",
    0x04: "4",
}

_PALETTE_TO_ENUM = {
    txd.PaletteType.PALETTE_NONE: "0",
    txd.PaletteType.PALETTE_4:    "1",
    txd.PaletteType.PALETTE_8:    "2",
}


#######################################################
class txd_importer:

    skip_mipmaps = True
    pack = True

    __slots__ = [
        'txd',
        'images',
        'file_name'
    ]

    #######################################################
    def _init():
        self = txd_importer

        # Variables
        self.txd = None
        self.images = {}
        self.file_name = ""

    #######################################################
    def _create_image(name, rgba, width, height, pack=False):
        pixels = []
        for h in range(height - 1, -1, -1):
            offset = h * width * 4
            pixels += list(map(lambda b: b / 0xff, rgba[offset:offset+width*4]))

        image = bpy.data.images.new(name, width, height, alpha=True)
        image.pixels = pixels

        if pack:
            image.pack()

        return image

    #######################################################
    def _populate_texture_props(image, tex):
        if not hasattr(image, 'dff'):
            return

        props = image.dff

        if tex.d3d_format in _D3D_TO_COMPRESSION:
            props.image_compression = _D3D_TO_COMPRESSION[tex.d3d_format]
        else:
            props.image_compression = "0"

        raster_type = tex.get_raster_format_type()
        props.image_raster = _RASTER_TO_ENUM.get(raster_type, "0")

        palette_type = tex.get_raster_palette_type()
        props.image_palette = _PALETTE_TO_ENUM.get(palette_type, "0")

        has_mips = tex.get_raster_has_mipmaps()
        props.image_mipmap = "1" if has_mips else "0"

        props.image_filter = _MODE_TO_FILTER.get(tex.filter_mode, "6")

        u_nibble = tex.uv_addressing & 0x0F
        v_nibble = (tex.uv_addressing >> 4) & 0x0F
        props.image_uaddress = _NIBBLE_TO_ADDR.get(u_nibble, "1")
        props.image_vaddress = _NIBBLE_TO_ADDR.get(v_nibble, "1")

    #######################################################
    def import_textures():
        self = txd_importer

        txd_name = os.path.basename(self.file_name).lower()

        # Import native textures
        for tex in self.txd.native_textures:
            images = []
            num_levels = tex.num_levels if not self.skip_mipmaps else 1

            for level in range(num_levels):
                image_name = "%s/%s/%d" % (txd_name, tex.name, level)
                image = bpy.data.images.get(image_name)
                if not image:
                    image = txd_importer._create_image(image_name,
                                                        tex.to_rgba(level),
                                                        tex.get_width(level),
                                                        tex.get_height(level),
                                                        self.pack)

                    if level == 0:
                        txd_importer._populate_texture_props(image, tex)

                images.append(image)

            self.images[tex.name] = images

        # Import textures
        for tex, imgs in zip(self.txd.textures, self.txd.images):
            images = []
            num_levels = len(imgs) if not self.skip_mipmaps else 1

            for level in range(num_levels):
                img = imgs[level]
                image_name = "%s/%s/%d" % (txd_name, tex.name, level)
                image = txd_importer._create_image(image_name,
                                                    img.to_rgba(),
                                                    img.width,
                                                    img.height,
                                                    self.pack)
                images.append(image)

            self.images[tex.name] = images

    #######################################################
    def import_txd(file_name):
        self = txd_importer
        self._init()

        self.txd = txd.txd()
        self.txd.load_file(file_name)
        self.file_name = file_name

        self.import_textures()

#######################################################
def import_txd(options):

    txd_importer.skip_mipmaps = options['skip_mipmaps']
    txd_importer.pack = options['pack']

    txd_importer.import_txd(options['file_name'])

    return txd_importer
