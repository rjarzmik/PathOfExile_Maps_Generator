#!/usr/bin/python
#
# Generates a graphic of Path of Exile Atlas of World
# The generation is launched as follows:
#   map_generator.py Synthesis.maps | dot -Tpng > Synthesis.png
#
# The input file (XXX.maps) has the following format :
#   - each line beginning with a # is a comment
#   - a map ranked dependency is written as : child<parent1,parent2,parent3
#       child, parent1, ... are map names (with spaces allowed)
#       if child is tier N, then parent* are tier N+1
#   - a 2 maps links without rank dependency, such as between same tiers, is
#     written as : map1~map2

import argparse
import re

class Map(object):
    """A map, indexed by its name, having a tier and linked maps"""

    def __init__(self, name):
        self.name = name.strip()
        self.tier = None
        self.aliases = []
        self.lowers = []
        self.highers = []
        self.related = []
        self.highers_invisible = []

    def add_alias(self, alias):
        a = alias.strip()
        if a not in self.aliases:
            self.aliases.add(a)

    def is_me(self, name):
        """Returns true if the name is either the map name or one of its aliases"""
        n = name.strip()
        return n == self.name or n in self.aliases

    def add_lower(self, lower):
        """Adds a link to another map, which has a tier of self.tier - 1"""
        if lower not in self.lowers:
            self.lowers.append(lower)

    def add_higher(self, higher, is_invisble=False):
        """Adds a link to another map, which has a tier of self.tier + 1"""
        if is_invisble:
            if higher not in self.highers_invisible:
                self.highers_invisible.append(higher)
        else:
            if higher not in self.highers:
                self.highers.append(higher)

    def add_related(self, related):
        """Adds a link to another map, which has an unknown tier relation to this map"""
        if related not in self.related:
            self.related.append(related)

    def get_print_name(self):
        return '"%s"' % self.name

    def __repr__(self):
        return 'Map(%s)' % self.name

class Quadrant(object):
    """A collection of tiered maps, with only 1 tier1 map."""

    def __init__(self, name, amap):
        self.name = name
        self.tiers = [ [] ]
        self.tiers.append([ amap ])
        self.build()

    def build(self):
        tier = 1
        if len(self.tiers[1]) != 1:
            raise ValueError('Quadrant can only be built out of 1 tier1 map, while we have %d' % len(self.tiers[1]))
        while True:
            nexts = []
            for mp in self.tiers[tier]:
                for higher in mp.highers:
                    if higher not in nexts:
                        nexts.append(higher)
            tier += 1
            if len(nexts) == 0:
                break

            self.tiers.append(nexts)

    def get_print_name(self):
        return self.name.replace(' ', '_')


class Atlas(object):
    """A collection of maps, linked and tiered"""

    def __init__(self):
        self.maps = []

    def _find_map(self, mapname):
        for mp in self.maps:
            if mp.is_me(mapname):
                return mp

        return None

    def _add_map(self, mapname):
        mp = Map(mapname)
        if mp not in self.maps:
            self.maps.append(mp)

        return mp

    def _find_or_create_map(self, mapname):
        mp = self._find_map(mapname)
        if not mp:
            mp = self._add_map(mapname)

        return mp

    def _add_link(self, map1, map2, link):
        if link == 'lower2higher':
            map2.add_lower(map1)
            map1.add_higher(map2)
        elif link == 'higher2lower':
            map1.add_lower(map2)
            map2.add_higher(map1)
        elif link == 'related':
            map1.add_related(map2)
            map2.add_related(map1)
        elif link == 'lower2higher_invisible':
            map1.add_higher(map2, True)
        else:
            raise ValueError
            
    def read_from_file(self, filename):
        re_alias = '([^=]*)=(.*)'
        re_ranked_dependency = '([^>:]*)[:<] *(.*)'
        re_floating_dependency = '([^~]*)~ *(.*)'
        re_invisible_dependency = '([^{]*){ *(.*)'

        lines = [ line.strip('\n') for line in open(filename) ]
        for line in lines:
            if len(line) == 0:
                continue

            if line[0] == '#':
                continue

            m = re.search(re_alias, line)
            if m:
                self._find_or_create_map(m.group(1)).add_alis(m.group(2))

            m = re.search(re_ranked_dependency, line)
            if m:
                lower = self._find_or_create_map(m.group(1).strip())
                highers = map(lambda x: self._find_or_create_map(x.strip()), m.group(2).split(','))
                for higher in highers:
                    self._add_link(lower, higher, 'lower2higher')
            
            m = re.search(re_floating_dependency, line)
            if m:
                lower = self._find_or_create_map(m.group(1).strip())
                highers = map(lambda x: self._find_or_create_map(x.strip()), m.group(2).split(','))
                for higher in highers:
                    self._add_link(lower, higher, 'related')

            m = re.search(re_invisible_dependency, line)
            if m:
                lower = self._find_or_create_map(m.group(1).strip())
                highers = map(lambda x: self._find_or_create_map(x.strip()), m.group(2).split(','))
                for higher in highers:
                    self._add_link(lower, higher, 'lower2higher_invisible')
                
        self.build_map_tiers()

    def build_map_tiers(self):
        tier1s = filter(lambda m: not m.lowers, self.maps)
        for m in tier1s:
            m.tier = 1
        tierNs = tier1s
        tier = 1
        while True:
            tierNs = [ m for mp in tierNs for m in mp.highers ]
            tier += 1
            for m in tierNs:
                m.tier = tier
            if len(tierNs) == 0:
                break

    def get_maps_of_tier(self, tier):
        return filter(lambda m: m.tier == tier, self.maps)

class Atlas2Graphviz(object):
    """Convert an Atlas to a graphviz graph"""
    def __init__(self, atlas):
        self.atlas = atlas
        self.quadrants = self._build_quadrants()

    def _build_quadrants(self):
        tier1s = filter(lambda m: len(m.lowers) == 0, self.atlas.maps)
        qds = []
        i = 0

        for name in [ 'NW', 'NE', 'SW', 'SE' ]:
            qds.append(Quadrant(name, tier1s[i]))
            i = i + 1
        return qds

    def get_floating_deps(self):
        str = ''
        for amap in self.atlas.maps:
            for bmap in amap.related:
                if amap.name < bmap.name:
                    continue
                str += '%s -- %s [ weight = 0 ];\n' % \
                    (amap.get_print_name(), bmap.get_print_name())
        return str

    def get_invisible_deps(self):
        str = ''
        for amap in self.atlas.maps:
            for bmap in amap.highers_invisible:
                str += '%s -- %s [ style = "invis" ];\n' % \
                    (amap.get_print_name(), bmap.get_print_name())

        return str

    def get_tiered_mapnames(self, quadrant, tier):
        mps_names = map(lambda x: x.get_print_name(), quadrant.tiers[tier])
        str = ' '.join(mps_names)

        return str

    def get_quadrant_range_str(self, quadrant, tmin, tmax, color):
        qname = quadrant.get_print_name().replace(' ', '_')
        str = 'subgraph %s_%s {' % (qname, color)
        str += '\n  ' + 'node [fontsize=24,';
        if color is not 'white':
            str += 'style=filled color=%s' % color
        str += ']'
        for tier in xrange(tmin, min(tmax + 1, len(quadrant.tiers))):
            str += '\n  ' + self.get_tiered_mapnames(quadrant, tier)
        str += '\n}'

        return str

    def get_quadrant_str(self, quadrant, invert_ranking=False):
        qname = quadrant.get_print_name().replace(' ', '_')
        # White, Yellow and Red maps
        str = 'subgraph %s {' % qname
        str += '\n  ' + self.get_quadrant_range_str(quadrant, 1, 5, 'white').replace('\n', '\n  ')
        str += '\n\n  ' + self.get_quadrant_range_str(quadrant, 6, 10, 'yellow').replace('\n', '\n  ')
        str += '\n\n  ' + self.get_quadrant_range_str(quadrant, 11, 16, 'red').replace('\n', '\n  ')
        str += '\n'

        # Same ranking
        for tier in xrange(1, min(17, len(quadrant.tiers))):
            str += '\n  ' + self.get_same_ranks_str(quadrant.tiers[tier]).replace('\n', '\n  ')
        str += '\n'

        # Dependencies
        for tier in xrange(1, len(quadrant.tiers)):
            for amap in quadrant.tiers[tier]:
                for higher in amap.highers:
                    if invert_ranking:
                        str += '\n  %s -- %s' % \
                            (higher.get_print_name(), amap.get_print_name())
                    else:
                        str += '\n  %s -- %s' % \
                            (amap.get_print_name(), higher.get_print_name())
        str += '\n}\n\n'

        return str

    def get_same_ranks_str(self, maps):
        mps_names = map(lambda x: x.get_print_name(), maps)
        return '{rank=same ' + ' '.join(mps_names) + '}'


parser = argparse.ArgumentParser(description='Maps graph generator.')
parser.add_argument('filename', help='input filename')
parser.add_argument('--list_maps', dest='cmd', action='store_const', const='list_maps')
parser.add_argument('--list_links', dest='cmd', action='store_const', const='list_links')
args = parser.parse_args()

if args.cmd:
    cmd= args.cmd
else:
    cmd = 'dot'

atlas = Atlas()
atlas.read_from_file(args.filename) # "3.6_Synthesis.maps")
a2g = Atlas2Graphviz(atlas)

if cmd == 'dot':
    if len(atlas.get_maps_of_tier(1)) != 4:
        raise ValueError('Can only handle 4 tier 1 maps, while we have : %s' % \
                         ' '.join(map(lambda m: m.get_print_name(), atlas.get_maps_of_tier(1))))

    print '# File generated by map_deps.py, don\'t edit manually please !!!\n'
    print 'graph Atlas {\n'
    print 'ranksep = .5\n'
    print 'nodesep = .75\n'
    #print 'fontsize = 20\n'
    
    print a2g.get_quadrant_str(a2g.quadrants[0])
    print a2g.get_quadrant_str(a2g.quadrants[1])
    
    print 'subgraph Shaper {'
    print '  "Shaper"'
    print '  }\n'
    
    print a2g.get_quadrant_str(a2g.quadrants[2], True)
    print a2g.get_quadrant_str(a2g.quadrants[3], True)
    
    print '# Inter-subgraph links'
    print a2g.get_floating_deps()
    
    print '# Invisible links'
    print a2g.get_invisible_deps()
    
    print '# Inter-quadrant alignment'
    for tier in xrange(1, min(17, a2g.quadrants[0], a2g.quadrants[1])):
        print a2g.get_same_ranks_str(a2g.quadrants[0].tiers[tier] + a2g.quadrants[1].tiers[tier])
    for tier in xrange(1, min(17, a2g.quadrants[2], a2g.quadrants[3])):
        print a2g.get_same_ranks_str(a2g.quadrants[2].tiers[tier] + a2g.quadrants[3].tiers[tier])
    
    print '}\n'

if cmd == 'list_maps':
    tier = 1
    while True:
        maps = atlas.get_maps_of_tier(tier)
        if len(maps) == 0:
            break
        print 'T%d: ' % tier + ','.join(map(lambda x: x.name, maps))
        tier += 1

if cmd == 'list_links':
    tier = 1
    while True:
        maps = atlas.get_maps_of_tier(tier)
        if len(maps) == 0:
            break
        hdr = '  ' * (tier - 1)
        for amap in maps:
            if len(amap.highers) > 0:
                print hdr + '%s -> ' % amap.name + ','.join(map(lambda x: x.name, amap.highers))
        tier += 1
