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
import itertools
import re
from sets import Set

class Quadrant:
    def __init__(self, maps, name, tier1_map):
        self.maps = maps
        self.name = name
        self.tier1_map = tier1_map
        self.tiers = [ [] ]
        self.build()

    def build(self):
        self.tiers.append([ self.tier1_map ])
        tier = 1
        while True:
            nexts = []
            for amap in self.tiers[tier]:
                nexts += self.maps.get_next_rank_maps(amap)
            nexts_ordered = []
            for amap in nexts:
                if amap not in nexts_ordered:
                    nexts_ordered += [ amap ]
            if len(nexts_ordered) > 0:
                self.tiers.append(nexts_ordered)
            else:
                break
            tier += 1

    def get_subgraph_str(self, invert_ranking=False):
        qname = self.name.replace(' ', '_')
        str = 'subgraph %s {\n' % qname
        hdr = '  '
        str += hdr + 'subgraph %s_white {\n' % qname
        for tier in xrange(1, 6):
            if len(self.tiers) <= tier:
                break
            str += hdr + '  ' + ' '.join(map(lambda x: '"%s"' % x, self.tiers[tier])) + '\n'
        str += hdr + '}\n'
        str += hdr + 'subgraph %s_yellow {\n' % qname
        str += hdr + '  ' + 'node [style=filled color=yellow]\n'
        for tier in xrange(6, 11):
            if len(self.tiers) <= tier:
                break
            str += hdr + '  ' + ' '.join(map(lambda x: '"%s"' % x, self.tiers[tier])) + '\n'
        str += hdr + '}\n'
        str += hdr + 'subgraph %s_red {\n' % qname
        str += hdr + '  ' + 'node [style=filled color=red]\n'
        for tier in xrange(11, 17):
            if len(self.tiers) <= tier:
                break
            str += hdr + '  ' + ' '.join(map(lambda x: '"%s"' % x, self.tiers[tier])) + '\n'
        str += hdr + '}\n'
        str += hdr + '\n'

        # Same ranking
        for tier in xrange(1, 17):
            if len(self.tiers) <= tier:
                break
            str += hdr + '{rank=same ' + ' '.join(map(lambda x: '"%s"' % x, self.tiers[tier])) + '}\n'
        str += '\n\n'

        # Dependencies
        for tier in xrange(1, len(self.tiers)):
            for amap in self.tiers[tier]:
                if not self.maps.deps_ranked.has_key(amap):
                    continue
                for higher in self.maps.deps_ranked[amap]:
                    if invert_ranking:
                        str += hdr + '"%s" -- "%s"\n' % (higher, amap)
                    else:
                        str += hdr + '"%s" -- "%s"\n' % (amap, higher)
        str += '}\n\n'

        return str

    def get_same_ranks(self,quad):
        # Same ranking
        str = ''
        for tier in xrange(1, 17):
            if len(self.tiers) <= tier or len(quad.tiers) <= tier:
                break
            str += '  ' + '{rank=same ' + '"%s"' % self.tiers[tier][0] + '"%s"' % quad.tiers[tier][0] + '}\n'

        return str

class Maps:
    def __init__(self):
        self.deps_ranked = {}
        self.deps_floating = {}
        self.deps_invisible = {}
        self.tiers = []
        self.aliases = {}
        self.maps = []

    def add_maps(self, maps):
        for amap in maps:
            if not amap in self.maps:
                self.maps.append(amap)

    def add_ranked_dependency(self, lower, highers):
        #print 'Add ranked for %s -> %s' % (lower, ','.join(highers))
        if self.deps_ranked.has_key(lower):
            for higher in highers:
                self.deps_ranked[lower].append(higher)
        else:
            self.deps_ranked[lower] = highers

    def add_floating_dependency(self, lower, highers):
        if self.deps_floating.has_key(lower):
            for higher in highers:
                self.deps_floating[lower].append(higher)
        else:
            self.deps_floating[lower] = highers

    def add_invisible_dependency(self, lower, highers):
        if self.deps_invisible.has_key(lower):
            for higher in highers:
                self.deps_invisible[lower].append(higher)
        else:
            self.deps_invisible[lower] = highers
            
    def read_file(self, filename):
        re_alias = '([^=]*)=(.*)'
        re_ranked_dependency = '([^>:]*)[:<] *(.*)'
        re_floating_dependency = '([^~]*)~ *(.*)'
        re_invisible_dependency = '([^{]*){ *(.*)'

        lines = [line.strip('\n') for line in open(filename)]
        for line in lines:
            if len(line) == 0:
                continue

            if line[0] == '#':
                continue

            m = re.search(re_alias, line)
            if m:
                aliases[m.group(1)] = m.group(2)

            m = re.search(re_ranked_dependency, line)
            if m:
                lower = m.group(1).strip()
                highers = map(lambda x: x.strip(), m.group(2).split(','))
                self.add_ranked_dependency(lower, highers)
                self.add_maps([ lower ])
                self.add_maps(highers)
            
            m = re.search(re_floating_dependency, line)
            if m:
                lower = m.group(1).strip()
                highers = map(lambda x: x.strip(), m.group(2).split(','))
                self.add_floating_dependency(lower, highers)
                self.add_maps([ lower ])
                self.add_maps(highers)

            m = re.search(re_invisible_dependency, line)
            if m:
                lower = m.group(1).strip()
                highers = map(lambda x: x.strip(), m.group(2).split(','))
                self.add_invisible_dependency(lower, highers)
                self.add_maps([ lower ])
                self.add_maps(highers)
                
        self.build_tiers()

    def find_leaves(self, deps):
        not_leaves = Set(itertools.chain(*deps.values()))
        leaves = Set(deps.keys())
        leaves.difference_update(not_leaves)

        leaves_ordered = []
        for leaf in self.maps:
            if leaf in leaves:
                leaves_ordered += [ leaf ]

        return leaves_ordered

    def get_next_rank_maps(self, amap):
        nexts = []
        if self.deps_ranked.has_key(amap):
            for bmap in self.deps_ranked[amap]:
                if bmap not in nexts:
                    nexts.append(bmap)

        return nexts
        
    def build_tiers(self):
        self.tiers.append([])
        self.tiers.append(self.find_leaves(self.deps_ranked))
        tier = 1

        while len(self.tiers) > tier:
            currents = self.tiers[tier]
            nexts = []
            for current in currents:
                for next in self.get_next_rank_maps(current):
                    if next not in nexts:
                        nexts.append(next)
            if len(nexts) > 0:
                self.tiers.append(nexts)
            tier += 1

    def get_floating_deps(self):
        str = ''
        for amap in self.deps_floating.keys():
            for bmap in self.deps_floating[amap]:
                str += '"%s" -- "%s" [ weight = 0 ];\n' % (amap, bmap)
        return str

    def get_invisible_deps(self):
        str = ''
        for amap in self.deps_invisible.keys():
            for bmap in self.deps_invisible[amap]:
                str += '"%s" -- "%s" [ style = "invis" ];\n' % (amap, bmap)
        return str

parser = argparse.ArgumentParser(description='Maps graph generator.')
parser.add_argument('filename', help='input filename')
parser.add_argument('--list_maps', dest='cmd', action='store_const', const='list_maps')
parser.add_argument('--list_links', dest='cmd', action='store_const', const='list_links')
args = parser.parse_args()

if args.cmd:
    cmd= args.cmd
else:
    cmd = 'dot'

mp = Maps()
mp.read_file(args.filename) # "3.6_Synthesis.maps")

tier1s = mp.find_leaves(mp.deps_ranked)
if len(tier1s) != 4:
    print 'Error: we should have exactly 4 Tier1 maps'
    print 'Tier1: %s' % ','.join(tier1s)
    exit(1)

if cmd == 'dot':
    q_nw = Quadrant(mp, 'NW', mp.tiers[1][0])
    q_ne = Quadrant(mp, 'NE', mp.tiers[1][1])
    q_sw = Quadrant(mp, 'SW', mp.tiers[1][2])
    q_se = Quadrant(mp, 'SE', mp.tiers[1][3])
    
    print '# File generated by map_deps.py, don\'t edit manually please !!!\n'
    print 'graph Atlas {\n'
    print 'ranksep = .5\n'
    print 'nodesep = .75\n'
    
    print q_nw.get_subgraph_str()
    print q_ne.get_subgraph_str()
    
    print 'subgraph Shaper {'
    print '  "Shaper"'
    print '  }\n'
    
    print q_sw.get_subgraph_str(True)
    print q_se.get_subgraph_str(True)
    
    print '# Inter-subgraph links'
    print mp.get_floating_deps()
    print '\n'
    
    print '# Invisible links'
    print mp.get_invisible_deps()
    
    print '# Inter-quadrant alignment'
    print q_nw.get_same_ranks(q_ne)
    print q_sw.get_same_ranks(q_se)
    
    print '}\n'

if cmd == 'list_maps':
    tier = 1
    for maps in mp.tiers[1:]:
        print 'T%d: ' % tier + ','.join(maps)
        tier += 1

if cmd == 'list_links':
    tier = 1
    for maps in mp.tiers[1:]:
        hdr = '  ' * (tier - 1)
        for amap in maps:
            if mp.deps_ranked.has_key(amap):
                print hdr + '%s -> ' % amap + ','.join(mp.deps_ranked[amap])
        tier += 1
