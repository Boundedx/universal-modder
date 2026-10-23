#!/usr/bin/env python3
"""Generate Minas Tirith as a WildPlans blueprint (.wplan) for RuneScape: Dragonwilds.

The city is made only from the game's own building pieces (the Castle kit by default), so it builds,
saves and loads like anything a player builds by hand. WildPlans (a UE4SS Lua mod, github.com/kaedon78/WildPlans)
does the placing in game: copy the .wplan into its blueprints folder, pin it, and place it as free ghosts
(any world) or as real pieces (Creative worlds).

    python make_minas_tirith.py                      # MinasTirith.wplan + preview.png, the default size
    python make_minas_tirith.py --size small         # ~1/2 the pieces, for a first test
    python make_minas_tirith.py --style kharidian    # the pale sandstone set (Umbral Sands) instead of grey castle stone
    python make_minas_tirith.py --stairs-flip        # if the gate stairs came out facing the wall

Layout (X is the front of the city, where the Great Gate is; Z is up; 1 cell = 300 cm, the game's
foundation size):

* Seven tiers, each a stone terrace one foundation (3 m) higher than the one outside it, rasterised from
  concentric circles onto the building grid. Every tier edge gets a wall with battlements.
* A gate in each tier's wall, alternating between the south-east and north-east as in the books (the Great
  Gate faces due east), with stairs from the terrace below up to each gate.
* The prow: the great spur of rock that runs east from the Citadel through every tier but the first, with
  a tunnel through it at each tier so the road can wind back and forth.
* The Citadel on the seventh tier, the White Tower (a square stone tower with windows, stained glass,
  battlements and a spire) and a white tree in the Court of the Fountain in front of it.
* Mount Mindolluin: a ridge of stacked foundations behind the city that hides the cut-off back of the
  tiers (--no-mountain leaves it out).

Piece numbers are the game's shipped BuildingPieceDataIndex values. The file also records each piece's asset
path ("piecedata" lines), which WildPlans goes by when a game update or another building mod renumbers pieces.
"""
from __future__ import annotations

import argparse
import math
import sys
from collections import Counter
from pathlib import Path

CELL = 300.0          # cm, a large foundation's side; the game's building grid is 150
HALF = CELL / 2

# The pieces used, per building style: shipped index, asset path, local bounds (cm; min/max X, Y, Z) as the
# game reports them (from WildPlans' data/piece_bounds.txt). Pivots: foundations and floors at the top centre,
# walls at the bottom centre (running along local X), beams and stairs at the centre.
_BB = "/Game/Gameplay/BaseBuilding_New/BuildingPieces/"
STYLES = {
    "castle": {
        "foundation": (299, _BB + "Tier3_Fellhollow/Foundations/DA_T3_Foundation_Large.DA_T3_Foundation_Large"),
        "wall": (399, _BB + "Tier3_Fellhollow/Walls/DA_T3_Wall_Large.DA_T3_Wall_Large"),
        "merlon": (158, _BB + "Tier3_Fellhollow/Walls/DA_T3_Wall_Plain_Medium.DA_T3_Wall_Plain_Medium"),
        "slit": (829, _BB + "Tier3_Fellhollow/Walls/DA_T3_Wall_SlitNew_Medium.DA_T3_Wall_SlitNew_Medium"),
        "gate": (495, _BB + "Tier3_Fellhollow/Walls/DA_T3_Wall_Large_Castle_Doorframe.DA_T3_Wall_Large_Castle_Doorframe"),
        "stairs": (340, _BB + "Tier3_Fellhollow/Stairs/DA_T3_Stairs_Straight.DA_T3_Stairs_Straight"),
        "floor": (49, _BB + "Tier3_Fellhollow/Floor/DA_T3_Floor_Large.DA_T3_Floor_Large"),
        "window": (832, _BB + "Tier3_Fellhollow/Walls/DA_T3_Wall_Large_Windowframe.DA_T3_Wall_Large_Windowframe"),
        "glass": (824, _BB + "Tier3_Fellhollow/Walls/DA_T3_Wall_StainedGlass_6.DA_T3_Wall_StainedGlass_6"),
        "spire": (12, _BB + "Tier3_Fellhollow/Beams/DA_T3_Beam_Thick_Large_Vertical.DA_T3_Beam_Thick_Large_Vertical"),
    },
    "kharidian": {
        "foundation": (814, _BB + "Tier4_UmbralSands/Foundations/DA_T4_Foundation_Large01.DA_T4_Foundation_Large01"),
        "wall": (380, _BB + "Tier4_UmbralSands/Walls/DA_T4_Wall_Large01.DA_T4_Wall_Large01"),
        "merlon": (615, _BB + "Tier4_UmbralSands/Walls/DA_T4_Wall_Medium01.DA_T4_Wall_Medium01"),
        "slit": (24, _BB + "Tier4_UmbralSands/Walls/DA_T4_Wall_Medium02.DA_T4_Wall_Medium02"),
        "gate": (318, _BB + "Tier4_UmbralSands/Walls/DA_T4_Wall_Large_Castle_Doorframe.DA_T4_Wall_Large_Castle_Doorframe"),
        "stairs": (41, _BB + "Tier4_UmbralSands/Stairs/DA_T4_Stairs_Straight.DA_T4_Stairs_Straight"),
        "floor": (258, _BB + "Tier4_UmbralSands/Floor/DA_T4_Floor_Large01.DA_T4_Floor_Large01"),
        "window": (737, _BB + "Tier4_UmbralSands/Walls/DA_T4_Wall_Large_Windowframe01.DA_T4_Wall_Large_Windowframe01"),
        "glass": (737, _BB + "Tier4_UmbralSands/Walls/DA_T4_Wall_Large_Windowframe01.DA_T4_Wall_Large_Windowframe01"),
        "spire": (175, _BB + "Tier4_UmbralSands/Beams/DA_T3_Beam_Thick_Pillar01.DA_T3_Beam_Thick_Pillar01"),
    },
}
TREE = (432, _BB + "Decorations/General/DA_BaseBuilding_Decoration_General_Wintumber_Tree."
        "DA_BaseBuilding_Decoration_General_Wintumber_Tree")

BOUNDS = {
    "foundation": (-150, 150, -150, 150, -300, 0),
    "wall": (-151.5, 151.5, -50, 50, 0, 303),
    "merlon": (-75, 75, -50, 50, 0, 150),
    "slit": (-75, 75, -50, 50, 0, 150),
    "gate": (-150, 150, -50, 50, 0, 300),
    "stairs": (-77.3, 75, -75, 75, -100, 75),
    "floor": (-150, 150, -150, 150, -37.5, 0),
    "window": (-150, 150, -50, 50, 0, 300),
    "glass": (-151.5, 151.5, -50, 50, 0, 303),
    "spire": (-50, 50, -50, 50, -150, 150),
    "tree": (-91.7, 88.5, -80.3, 81.2, -6.3, 295.7),
}

SIZES = {
    #          citadel radius (m), tier step (m), tower storeys
    "small":  dict(citadel_r=9.0, step=4.5, tower=8),
    "medium": dict(citadel_r=13.5, step=4.5, tower=12),
    "large":  dict(citadel_r=18.0, step=6.0, tower=16),
}

N4 = ((1, 0), (-1, 0), (0, 1), (0, -1))


class City:
    def __init__(self, citadel_r=13.5, step=4.5, tiers=7, tower=12, mountain=True, tunnels=True,
                 stairs_flip=False, stair_z=75.0, outer_wall=2, style="castle"):
        self.tiers, self.tower_storeys = tiers, tower
        self.mountain, self.tunnels = mountain, tunnels
        self.stairs_flip, self.stair_z, self.outer_wall = stairs_flip, stair_z, outer_wall
        self.style = style
        self.pieces: list[tuple[str, float, float, float, float]] = []   # kind, x, y, z, yaw
        # tier k (1 = outermost) is the disc of radius r[k]; the city is cut off behind at x_back
        self.r = {k: (citadel_r + (tiers - k) * step) * 100.0 for k in range(1, tiers + 1)}
        self.x_back = -0.6 * citadel_r * 100.0
        self._layout()

    # ------------------------------------------------------------------ the ground plan --
    def natural_level(self, i, j):
        """How many tiers' discs hold this cell's centre (0 = outside the city)."""
        x, y = i * CELL, j * CELL
        if x < self.x_back:
            return 0
        d = math.hypot(x, y)
        return sum(1 for k in range(1, self.tiers + 1) if d <= self.r[k])

    def _layout(self):
        R = int(math.ceil(self.r[1] / CELL)) + 1
        self.level, self.prow, self.removed = {}, set(), set()
        for i in range(-R, R + 1):
            for j in range(-R, R + 1):
                n = self.natural_level(i, j)
                if n:
                    self.level[(i, j)] = n
        # The prow: three cells wide, from the Citadel's edge out to the second tier's wall, as high as the Citadel.
        for (i, j), n in list(self.level.items()):
            if abs(j) <= 1 and i * CELL > 0 and 2 <= n < self.tiers:
                self.prow.add((i, j))
                self.level[(i, j)] = self.tiers
        # A tunnel through the prow on each tier it crosses (2 .. tiers-1): drop the layer just above that
        # tier's surface across all three cells of one slice. Its roof rests on the slice just outside it, so
        # that slice must be prow and whole at the roof's height; outermost tiers first. A tier that cannot
        # have one keeps a solid prow, and the next gate stays on the same side (see _gates).
        self.tunnel_slices = {}
        if self.tunnels:
            by_slice = {}
            for m in range(2, self.tiers):
                # a slice on this tier along the middle and on both sides, so the tunnel opens onto its terrace
                xs = sorted(i for (i, j) in self.prow if j == 0 and self.natural_level(i, 0) == m
                            and self.lvl((i, -2)) == m and self.lvl((i, 2)) == m)
                ok = []
                for i in xs:
                    if m + 1 == self.tiers:
                        ok.append(i)                       # the top layer: an open cut, no roof to hold
                    elif (i + 1, 0) in self.prow and by_slice.get(i + 1) != m + 1:
                        ok.append(i)
                if ok:
                    s = ok[len(ok) // 2]
                    self.tunnel_slices[m] = s
                    by_slice[s] = m
                    for j in (-1, 0, 1):
                        self.removed.add((s, j, m + 1))     # (cell, layer)

    def lvl(self, c):
        return self.level.get(c, 0)

    def surface(self, level):
        """Z (cm) of the top of a tier's terrace; tier 1 sits flush with the ground."""
        return (level - 1) * CELL

    # ------------------------------------------------------------------ pieces --
    def add(self, kind, x, y, z, yaw=0.0):
        self.pieces.append((kind, round(x, 3), round(y, 3), round(z, 3), round(yaw % 360.0, 4)))

    def edge(self, c, n):
        """Midpoint and wall yaw of the edge of cell c facing direction n."""
        (i, j), (dx, dy) = c, n
        x, y = i * CELL + dx * HALF, j * CELL + dy * HALF
        return x, y, (90.0 if dx else 0.0)

    def build(self):
        self._terraces()
        gates = self._gates()
        self._walls(gates)
        self._tower_and_court()
        if self.mountain:
            self._mountain()
        return self

    def _terraces(self):
        for (i, j), n in self.level.items():
            for layer in range(1, n + 1):
                if (i, j, layer) not in self.removed:
                    self.add("foundation", i * CELL, j * CELL, self.surface(layer))

    def _gates(self):
        """Pick one edge per tier for its gate; returns {(cell, dir): tier}."""
        gates = {}
        self.gate_info = {}
        side = -1.0
        for k in range(1, self.tiers + 1):
            # the Great Gate faces east; the rest alternate south-east / north-east wherever the tier below
            # has a tunnel through the prow to cross by, and stay on the same side where it has none
            if k >= 3 and (k - 1) in self.tunnel_slices:
                side = -side
            want = 0.0 if k == 1 else 40.0 * side
            wv = (math.cos(math.radians(want)), math.sin(math.radians(want)))
            best = None
            for c, lv in self.level.items():
                if lv != k or c in self.prow:
                    continue
                for n in N4:
                    b = (c[0] + n[0], c[1] + n[1])
                    if self.lvl(b) != k - 1 or b in self.prow or (k > 1 and b not in self.level):
                        continue
                    if (n[0] * wv[0] + n[1] * wv[1]) < 0.5:        # must face roughly outwards that way
                        continue
                    x, y, _ = self.edge(c, n)
                    ang = abs((math.degrees(math.atan2(y, x)) - want + 180) % 360 - 180)
                    # prefer a landing that is two cells deep, so the stairs start on open ground
                    b2 = (b[0] + n[0], b[1] + n[1])
                    deep = k == 1 or self.lvl(b2) == k - 1
                    score = (0 if deep else 1, round(ang, 1))
                    if best is None or score < best[0]:
                        best = (score, c, n)
            if best:
                _, c, n = best
                gates[(c, n)] = k
                self.gate_info[k] = (c, n)
        return gates

    def _walls(self, gates):
        for c, lv in self.level.items():
            for n in N4:
                b = (c[0] + n[0], c[1] + n[1])
                lb = self.lvl(b)
                if lb >= lv:
                    continue
                if lb == 0 and b[0] * CELL < self.x_back and self.mountain:
                    continue                              # against the mountain
                x, y, yaw = self.edge(c, n)
                z = self.surface(lv)
                tx, ty = -n[1], n[0]                      # along the edge
                outer = lb == 0 and lv == 1
                courses = self.outer_wall if outer else 1
                g = gates.get((c, n))
                for s in range(courses):
                    kind = "gate" if (g and s == 0) else "wall"
                    self.add(kind, x, y, z + s * CELL, yaw)
                top = z + courses * CELL
                # battlements: one merlon on each 300 cm edge (two over a gate, as its gatehouse);
                # every third edge of the outer wall carries an arrow slit instead
                if g:
                    for off in (-75.0, 75.0):
                        self.add("merlon", x + tx * off, y + ty * off, top, yaw)
                else:
                    kind = "slit" if (outer and (c[0] + c[1]) % 3 == 0) else "merlon"
                    self.add(kind, x - tx * 75.0, y - ty * 75.0, top, yaw)
                if g and g > 1:
                    self._stairs(c, n, lb)

    def _stairs(self, c, n, lb):
        """Two flights side by side on the landing cell outside a gate, from tier lb up to lb + 1."""
        bx, by = (c[0] + n[0]) * CELL, (c[1] + n[1]) * CELL
        up = (-n[0], -n[1])                                  # towards the gate
        yaw = math.degrees(math.atan2(up[1], up[0])) + (180.0 if self.stairs_flip else 0.0)
        tx, ty = -n[1], n[0]
        z0 = self.surface(lb)
        for side in (-75.0, 75.0):
            for step_i, along in enumerate((-75.0, 75.0)):   # lower flight on the outer half
                x = bx + up[0] * along + tx * side
                y = by + up[1] * along + ty * side
                self.add("stairs", x, y, z0 + step_i * 150.0 + self.stair_z, yaw)

    def _tower_and_court(self):
        top = max(self.level.values())
        cit = [c for c, lv in self.level.items() if lv == top and c not in self.prow]
        i0 = min(i for i, _ in cit)
        cells = [(i, j) for i in range(i0, i0 + 3) for j in (-1, 0, 1)]
        if not all(self.lvl(c) == top for c in cells):
            print("warning: the citadel is too small for a 3x3 tower; skipping it", file=sys.stderr)
            return
        base = self.surface(top)
        storeys = self.tower_storeys
        cs = set(cells)
        for s in range(storeys):
            z = base + s * CELL
            for c in cells:
                for n in N4:
                    if (c[0] + n[0], c[1] + n[1]) in cs:
                        continue
                    x, y, yaw = self.edge(c, n)
                    middle = (n[0] and c[1] == 0) or (n[1] and c[0] == i0 + 1)
                    if s == 0 and n == (1, 0) and c[1] == 0:
                        kind = "gate"                       # the tower door, facing the court
                    elif middle and s == storeys - 1:
                        kind = "glass"
                    elif middle and s % 3 == 1:
                        kind = "window"
                    else:
                        kind = "wall"
                    self.add(kind, x, y, z, yaw)
            if s % 4 == 3 or s == storeys - 1:              # a floor every few storeys, and the roof
                for c in cells:
                    self.add("floor", c[0] * CELL, c[1] * CELL, z + CELL)
        roof = base + storeys * CELL
        for c in cells:                                      # battlements round the roof
            for n in N4:
                if (c[0] + n[0], c[1] + n[1]) in cs:
                    continue
                x, y, yaw = self.edge(c, n)
                tx, ty = -n[1], n[0]
                self.add("merlon", x - tx * 75.0, y - ty * 75.0, roof, yaw)
        cx, cy = (i0 + 1) * CELL, 0.0
        for b in range(3):                                   # the spire
            self.add("spire", cx, cy, roof + 150.0 + b * CELL)
        self.tower_cells = cells
        # the White Tree, in the court in front of the tower door
        tree = (i0 + 4, 0)
        if self.lvl(tree) == top and tree not in self.prow:
            self.add("tree", tree[0] * CELL, 0.0, base)

    def _mountain(self):
        """A ridge of stacked foundations behind the city, higher than whatever tier it backs."""
        ib = min(i for i, _ in self.level)                   # the first column inside the city
        js = [j for (i, j) in self.level if i == ib]
        jmin, jmax = min(j for (_, j) in self.level), max(j for (_, j) in self.level)
        width = max(abs(jmin), abs(jmax)) + 2
        peak_extra = 4
        for j in range(-width, width + 1):
            # the highest tier this column backs
            backed = max([self.lvl((i, j)) for i in range(ib, ib + 3)] + [0])
            t = abs(j) / float(width)
            extra = int(round(peak_extra * (1 - t * t)))
            layers = backed + extra if backed else max(1, extra - 1)
            for depth, cut in ((1, 0), (2, 1)):              # two rows deep, the back row lower
                i = ib - depth
                for layer in range(1, max(1, layers - cut) + 1):
                    self.add("foundation", i * CELL, j * CELL, self.surface(layer))
        del js

    # ------------------------------------------------------------------ output --
    def wplan(self, name="MinasTirith"):
        pal = dict(STYLES[self.style])
        pal["tree"] = TREE
        used = sorted({pal[k][0]: pal[k][1] for k, *_ in self.pieces}.items())
        NL = "\n"
        out = [
            "# WildPlans v2",
            "# generated by universal-modder examples/dragonwilds-minas-tirith/make_minas_tirith.py",
            "# offsets are in the STRUCTURE's frame, centimetres, Z up",
            "# piece <index> <dx> <dy> <dz> <yaw> <sx> <sy> <sz> [ghost]",
            "# yaw is relative to origin_yaw; 'ghost' marks an unbuilt piece",
            "version 2",
            f"name {name}",
            "grid 150.0",
            "source generated",
            "origin 0.000 0.000 0.000",
            "origin_yaw 0.0000",
            f"count {len(self.pieces)}",
        ]
        out += [f"piecedata {i} {p}" for i, p in used]
        for kind, x, y, z, yaw in self.pieces:
            yaw180 = yaw - 360.0 if yaw > 180.0 else yaw
            out.append(f"piece {pal[kind][0]} {x:.3f} {y:.3f} {z:.3f} {yaw180:.4f} 1.0000 1.0000 1.0000 ghost   # {kind}")
        return NL.join(out) + NL

    def summary(self):
        cnt = Counter(k for k, *_ in self.pieces)
        xs = [p[1] for p in self.pieces]
        ys = [p[2] for p in self.pieces]
        zs = [p[3] for p in self.pieces]
        return {
            "pieces": len(self.pieces),
            "by_kind": dict(cnt.most_common()),
            "depth_m": round((max(xs) - min(xs) + CELL) / 100, 1),     # front to back, mountain included
            "width_m": round((max(ys) - min(ys) + CELL) / 100, 1),     # side to side
            "height_m": round((max(zs) - min(zs)) / 100 + 3, 1),
            "gates": {k: (c, n) for k, (c, n) in sorted(self.gate_info.items())},
            "tunnels": dict(sorted(self.tunnel_slices.items())),
        }


# ---------------------------------------------------------------------- preview --
COLOURS = {
    "foundation": (200, 196, 186), "wall": (232, 230, 222), "merlon": (240, 238, 232), "slit": (220, 216, 206),
    "gate": (150, 110, 70), "stairs": (170, 150, 120), "floor": (210, 206, 196), "window": (120, 150, 190),
    "glass": (190, 120, 200), "spire": (250, 250, 250), "tree": (245, 245, 245),
}


def _corners(kind, x, y, z, yaw):
    x0, x1, y0, y1, z0, z1 = BOUNDS[kind]
    c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    pts = []
    for lx, ly in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        pts.append((x + lx * c - ly * s, y + lx * s + ly * c))
    return pts, z + z0, z + z1


def render_preview(pieces, path, size=1600, view_deg=60.0):
    """An isometric preview (painter's algorithm over every piece's bounding box)."""
    from PIL import Image, ImageDraw

    a = math.radians(view_deg)
    ca, sa = math.cos(a), math.sin(a)

    def proj(x, y, z):
        u = x * ca - y * sa
        v = x * sa + y * ca
        return u * 0.866, v * 0.5 - z * 0.9, v            # screen x, screen y, depth

    boxes = []
    for kind, x, y, z, yaw in pieces:
        pts, zlo, zhi = _corners(kind, x, y, z, yaw)
        depth = proj(x, y, 0)[2] + (zlo + zhi) * 0.001
        boxes.append((depth, kind, pts, zlo, zhi))
    boxes.sort(key=lambda b: b[0])
    allp = [proj(px, py, zz) for _, _, pts, zl, zh in boxes for (px, py) in pts for zz in (zl, zh)]
    minx, maxx = min(p[0] for p in allp), max(p[0] for p in allp)
    miny, maxy = min(p[1] for p in allp), max(p[1] for p in allp)
    scale = (size - 80) / max(maxx - minx, maxy - miny)
    W, H = int((maxx - minx) * scale) + 80, int((maxy - miny) * scale) + 80
    img = Image.new("RGB", (W, H), (120, 160, 200))
    d = ImageDraw.Draw(img)

    def S(p):
        return ((p[0] - minx) * scale + 40, (p[1] - miny) * scale + 40)

    for _, kind, pts, zlo, zhi in boxes:
        col = COLOURS[kind]
        top = [S(proj(px, py, zhi)) for px, py in pts]
        for k in range(4):                               # the sides, shaded by which way they face
            p0, p1 = pts[k], pts[(k + 1) % 4]
            quad = [S(proj(*p0, zlo)), S(proj(*p1, zlo)), S(proj(*p1, zhi)), S(proj(*p0, zhi))]
            nx, ny = p1[1] - p0[1], -(p1[0] - p0[0])
            shade = 0.55 + 0.25 * ((nx * ca - ny * sa) / (math.hypot(nx, ny) or 1) + 1) / 2
            d.polygon(quad, fill=tuple(int(v * shade) for v in col), outline=(90, 90, 90))
        d.polygon(top, fill=col, outline=(110, 110, 110))
    img.save(path)
    return path


def render_plan(city, path, px=10):
    """A top-down height map: tier colours, prow outlined, gates in red, tower in black."""
    from PIL import Image, ImageDraw

    cells = list(city.level)
    is_ = [c[0] for c in cells]
    js = [c[1] for c in cells]
    i0, i1, j0, j1 = min(is_) - 3, max(is_) + 2, min(js) - 2, max(js) + 2
    W, H = (j1 - j0 + 1) * px, (i1 - i0 + 1) * px
    img = Image.new("RGB", (W, H), (60, 110, 60))
    d = ImageDraw.Draw(img)
    top = max(city.level.values())
    for (i, j), lv in city.level.items():
        g = int(120 + 130 * lv / top)
        x, y = (j - j0) * px, (i1 - i) * px                      # front (+X) at the top of the image
        d.rectangle([x, y, x + px - 1, y + px - 1], fill=(g, g, g - 10),
                    outline=(170, 120, 60) if (i, j) in city.prow else None)
    for k, (c, n) in city.gate_info.items():
        b = (c[0] + n[0], c[1] + n[1])
        for (i, j) in (c, b):
            x, y = (j - j0) * px, (i1 - i) * px
            d.rectangle([x + 2, y + 2, x + px - 3, y + px - 3], fill=(200, 40, 40))
    for (i, j) in getattr(city, "tower_cells", []):
        x, y = (j - j0) * px, (i1 - i) * px
        d.rectangle([x + 1, y + 1, x + px - 2, y + px - 2], fill=(30, 30, 30))
    img = img.resize((W * 2, H * 2), Image.NEAREST)
    img.save(path)
    return path


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--size", choices=sorted(SIZES), default="medium")
    ap.add_argument("--style", choices=sorted(STYLES), default="castle",
                    help="castle = grey stone (Tier 3 Castle kit); kharidian = pale sandstone (Umbral Sands kit)")
    ap.add_argument("--tower", type=int, help="White Tower storeys (3 m each); overrides --size")
    ap.add_argument("--no-mountain", action="store_true", help="leave out the ridge behind the city")
    ap.add_argument("--no-tunnels", action="store_true", help="a solid prow, no tunnels through it")
    ap.add_argument("--outer-wall", type=int, default=2, help="courses of the first (outer) wall, 3 m each")
    ap.add_argument("--stairs-flip", action="store_true", help="turn every stair 180 degrees")
    ap.add_argument("--stair-z", type=float, default=75.0, help="height of a stair's pivot above its landing (cm)")
    ap.add_argument("--name", default="MinasTirith", help="blueprint name (and file name)")
    ap.add_argument("-o", "--out", default=None, help="output folder (default: next to this script)")
    ap.add_argument("--no-preview", action="store_true")
    a = ap.parse_args(argv)

    sz = dict(SIZES[a.size])
    if a.tower is not None:
        sz["tower"] = a.tower
    city = City(citadel_r=sz["citadel_r"], step=sz["step"], tower=sz["tower"], mountain=not a.no_mountain,
                tunnels=not a.no_tunnels, stairs_flip=a.stairs_flip, stair_z=a.stair_z,
                outer_wall=a.outer_wall, style=a.style).build()
    out = Path(a.out) if a.out else Path(__file__).resolve().parent
    out.mkdir(parents=True, exist_ok=True)
    wp = out / f"{a.name}.wplan"
    wp.write_text(city.wplan(a.name), encoding="utf-8", newline="\n")
    s = city.summary()
    print(f"wrote {wp}")
    print(f"  {s['pieces']} pieces; about {s['width_m']} m wide, {s['depth_m']} m front to back"
          f" and {s['height_m']} m to the top of the spire")
    print("  " + ", ".join(f"{v} {k}" for k, v in s["by_kind"].items()))
    if not a.no_preview:
        try:
            print(f"  preview: {render_preview(city.pieces, out / f'{a.name}_preview.png')}")
            print(f"  plan:    {render_plan(city, out / f'{a.name}_plan.png')}")
        except ImportError:
            print("  (install Pillow for the preview images: pip install pillow)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
