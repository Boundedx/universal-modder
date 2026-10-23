"""The Dragonwilds Minas Tirith generator (examples/dragonwilds-minas-tirith) writes a blueprint WildPlans can read,
and the plan is buildable: nothing doubled, every raised foundation resting on something, stairs on their landings.

    uv run --with pytest pytest -q tests/test_minas_tirith.py
"""
import re
import sys
from collections import Counter
from pathlib import Path

import pytest

EX = Path(__file__).resolve().parents[1] / "examples" / "dragonwilds-minas-tirith"
sys.path.insert(0, str(EX))

import make_minas_tirith as mt  # noqa: E402

# WildPlans' own piece-line pattern (capture.lua M.read): the index, 7 numbers and an optional "ghost"
PIECE = re.compile(r"^piece\s+(-?\d+)" + r"\s+(-?[\d.eE+\-]+)" * 7 + r"(\s+ghost)?$")


@pytest.fixture(scope="module", params=["small", "medium", "large"])
def city(request):
    return mt.City(**{k: v for k, v in mt.SIZES[request.param].items() if k != "tower"},
                   tower=mt.SIZES[request.param]["tower"]).build()


def test_wplan_parses_like_wildplans(city):
    text = city.wplan("T")
    header, pieces = {}, 0
    for raw in text.splitlines():
        line = re.sub(r"#.*$", "", raw).strip()
        if not line:
            continue
        key = line.split()[0]
        if key == "piece":
            assert PIECE.match(line), raw
            pieces += 1
        else:
            header[key] = line[len(key):].strip()
    assert header["version"] == "2" and header["name"] == "T"
    assert int(header["count"]) == pieces == len(city.pieces)
    # every index used has its asset path recorded
    used = {int(m.group(1)) for m in re.finditer(r"^piece (\d+)", text, re.M)}
    recorded = {int(m.group(1)) for m in re.finditer(r"^piecedata (\d+) /Game/", text, re.M)}
    assert used == recorded


def test_nothing_doubled(city):
    dup = [p for p, n in Counter((k, x, y, z) for k, x, y, z, _ in city.pieces).items() if n > 1]
    assert not dup
    # one wall-like piece per edge and height
    wallish = {"wall", "gate", "window", "glass"}
    slots = Counter((x, y, z) for k, x, y, z, _ in city.pieces if k in wallish)
    assert max(slots.values()) == 1


def test_foundations_are_connected_to_the_ground(city):
    """Every foundation reaches the ground layer through foundations it touches face to face
    (the tunnels' roofs are held by the prow beside and above them)."""
    found = {(x, y, z) for k, x, y, z, _ in city.pieces if k == "foundation"}
    seen = [f for f in found if f[2] == 0]
    reached = set(seen)
    while seen:
        x, y, z = seen.pop()
        for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            n = (x + dx * mt.CELL, y + dy * mt.CELL, z + dz * mt.CELL)
            if n in found and n not in reached:
                reached.add(n)
                seen.append(n)
    assert found == reached, sorted(found - reached)[:5]
    # and nothing floats over open air except a tunnel roof
    roofs = {(s * mt.CELL, j * mt.CELL) for s in city.tunnel_slices.values() for j in (-1, 0, 1)}
    for x, y, z in found:
        if z > 0 and (x, y, z - mt.CELL) not in found:
            assert (x, y) in roofs, (x, y, z)


def test_seven_gates_and_their_stairs(city):
    assert sorted(city.gate_info) == list(range(1, 8))
    assert sum(1 for k, *_ in city.pieces if k == "gate") == 8          # seven tiers + the tower door
    assert sum(1 for k, *_ in city.pieces if k == "stairs") == 4 * 6    # two flights x two steps, tiers 2..7
    for k, (c, n) in city.gate_info.items():
        b = (c[0] + n[0], c[1] + n[1])
        assert city.lvl(c) == k and city.lvl(b) == k - 1


def test_tower_tree_and_tunnels(city):
    kinds = Counter(k for k, *_ in city.pieces)
    assert kinds["spire"] == 3 and kinds["tree"] == 1 and kinds["glass"] == 4
    assert len(city.tunnel_slices) >= 4
    # consecutive gates sit on opposite sides only where the tier between them has a tunnel to cross by
    for k in range(3, 8):
        (c0, _), (c1, _) = city.gate_info[k - 1], city.gate_info[k]
        flipped = (c0[1] > 0) != (c1[1] > 0)
        assert flipped == ((k - 1) in city.tunnel_slices), k


def test_cli_writes_files(tmp_path):
    assert mt.main(["--size", "small", "-o", str(tmp_path), "--no-preview", "--style", "kharidian"]) == 0
    text = (tmp_path / "MinasTirith.wplan").read_text()
    assert "Tier4_UmbralSands" in text and "Tier3_Fellhollow" not in text


def test_the_road_reaches_the_citadel(city):
    """Walk in through the Great Gate: along each terrace, up each gate's stairs, through the prow's tunnels."""
    tunnel = {}
    for m, s in city.tunnel_slices.items():
        for j in (-1, 0, 1):
            tunnel[(s, j)] = m
    gates = {}
    for k, (c, n) in city.gate_info.items():
        b = (c[0] + n[0], c[1] + n[1])
        gates.setdefault((b, k - 1), []).append((c, k))

    def stand(c):                                    # the heights you can stand at in a cell
        h = {city.lvl(c)}
        if c in tunnel:
            h.add(tunnel[c])
        return h

    start = (city.gate_info[1][0], 1)
    seen, todo = {start}, [start]
    while todo:
        c, h = todo.pop()
        nxt = [((c[0] + dx, c[1] + dy), h) for dx, dy in mt.N4]
        nxt += gates.get((c, h), [])
        for c2, h2 in nxt:
            if h2 in stand(c2) and (c2, h2) not in seen:
                seen.add((c2, h2))
                todo.append((c2, h2))
    top = max(city.level.values())
    assert any(h == top for _, h in seen)
    assert {h for _, h in seen} == set(range(1, top + 1))
