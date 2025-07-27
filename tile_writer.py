import framebuf
from uctypes import bytearray_at, addressof
from sys import implementation

from writer import _get_id
from common import ticks_ms, ticks_add, ticks_diff, sleep_ms


class Writer(object):
    tiles = {}

    def __init__(self, device, tiles):
        self.devid = _get_id(device)
        self.device = device
        self.map = framebuf.MONO_HLSB
        self.screenwidth = device.width  # In pixels
        self.screenheight = device.height
        self.bgcolor = 0  # Monochrome background and foreground colors
        self.fgcolor = 1
        self.tiles = tiles

    def print_tile(self, tile, tile_width, tile_height, offset_x, offset_y):
        fbc = framebuf.FrameBuffer(bytearray(tile), tile_width, tile_height, self.map)
        self.device.blit(fbc, offset_x, offset_y)
        del fbc

    def print_tile_id(self, tile_id, offset_x, offset_y):
        tile = self.tiles[tile_id]
        fbc = framebuf.FrameBuffer(bytearray(tile["tile"]), tile["width"], tile["height"], self.map)
        self.device.blit(fbc, offset_x, offset_y)
        del fbc
        
    def add_tiles(self, tiles):
        for tile in tiles:
            self.tiles[tile["id"]] = tile["body"]
            
    def add_tile(self, tile_id, tile_body):
        self.tiles[tile_id] = tile_body
        
    def remove_tiles(self, tile_ids):
        for tile_id in tile_ids:
            if tile_id in self.tiles:
                del self.tiles[tile_id]
        
    def remove_tile(self, tile_id):
        if tile_id in self.tiles:
            del self.tiles[tile_id]
