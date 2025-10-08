# Design of Telematics Systems 2025-26
# Universidad Carlos III de Madrid
#
# This class represents a map that it is read from a file
# The file represents a sea floor map
# The initial map is a 2D grid of characters: . (water) # (rock) P (port) I (island)
# The ships will ask if a cell can be traversed (it is not a rock)
# Then it will set the ship at the map, changing the type of cell to:
# S (ship) H (home) B (bar)

# The file is a text file with lines of equal length. X is the column index, Y is the row index
# (x,y) = (0,0) is the top-left corner of the map
# (x,y) = (width-1,height-1) is the bottom-right corner of the map

  

class Map:
    WATER, ROCK, PORT, ISLAND, SHIP, HOME, BAR = '.', '#', 'P', 'I', 'S', 'H', 'B'
    def __init__(self, filename):
        self.filename = filename
        self.map, self.height, self.width = self.load_map()

    def load_map(self):
        with open(self.filename, 'r') as f:
           map = [list(line.strip()) for line in f if line.strip()]
           if map:
               height = len(map)
               width = len(map[0])
               for row in map:
                   if len(row) != width:
                       raise ValueError("All rows in the map must have the same length")
               return map, height, width
        return [], 0, 0

    def can_sail(self, x, y):       
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.map[y][x] != Map.ROCK
        return False

    def get_cell_type(self, x, y):
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.map[y][x]
        return None

    def set_ship(self, x, y):
        if 0 <= x < self.width and 0 <= y < self.height:
            if self.map[y][x] == Map.WATER:
                self.map[y][x] = Map.SHIP
            elif self.map[y][x] == Map.PORT:
                self.map[y][x] = Map.HOME
            elif self.map[y][x] == Map.ISLAND:
                self.map[y][x] = Map.BAR
            return True
        return None

    def remove_ship(self, x, y):
        if 0 <= x < self.width and 0 <= y < self.height:
            if self.map[y][x] == Map.SHIP:
                self.map[y][x] = Map.WATER
            elif self.map[y][x] == Map.HOME:
                self.map[y][x] = Map.PORT
            elif self.map[y][x] == Map.BAR:
                self.map[y][x] = Map.ISLAND
        return None

    def __str__(self):
        return '\n'.join(''.join(row) for row in self.map)
