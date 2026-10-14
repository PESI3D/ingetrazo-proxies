# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Peter Müller (PESI3D) — https://pesi3d.de
"""Proxies — swap heavy objects for light stand-ins, keep the originals on disk.

Select groups or component instances (an imported tree, a sofa, a car) and
run Extensions ▸ Proxies ▸ Create Proxies…. Each object keeps its name,
place, layer and instances, but its geometry is replaced by a light proxy
mesh; the full geometry is written to an external .igz next to the document.
The document gets small and the viewport fast.

Proxy mesh types:
- Box — the object's bounding box (in its own axes).
- Convex hull — a hull through at most «Hull points» extreme points.
- Vertex cloud — small crosses on a share of the original vertices.
- From source — the original, reduced to a share of its faces (vertex
  clustering), optionally keeping its materials.

Originals are saved individually (one .igz per object), all together (one
.igz) or by layer (one .igz per layer). Every .igz opens in IngeTrazo as a
normal document.

Extensions ▸ Proxies ▸ Show Originals brings the full geometry back (before
Render with Blender or an export), Show Proxies swaps it out again — the
selected proxies, or all of them when nothing is selected. Copies of a
component share one proxy, exactly as they share one definition.

A proxy whose original is shown can be made a proxy again (other type or
settings); its original stays in the file it already has.

One undo step per command. The dialog is non-modal: orbit, pan and zoom
while the Live Preview shows the proxies in the model — the same Preview
button as in every PESI3D plugin; OK keeps the preview as it is.

Not affiliated with Spline Dynamics or Autodesk; «Q-Proxies» and «3ds Max»
are named only to describe the workflow this plugin follows.
"""
from __future__ import annotations

import math
import os
import re
import uuid
from pathlib import Path

KEY = "proxy_tool"
VERSION = "1.0"

TYPES = ("box", "hull", "cloud", "source")
MODES = ("individual", "together", "layer")

_TEXTS = {
    "de": {
        "Proxies": "Proxies",
        "Create Proxies…": "Proxies erstellen…",
        "Show Originals": "Originale anzeigen",
        "Show Proxies": "Proxies anzeigen",
        "Select All Proxies": "Alle Proxies auswählen",
        "Replace the selected objects by light proxies; the originals go to .igz files.":
            "Ersetzt die gewählten Objekte durch leichte Proxies; die Originale kommen in .igz-Dateien.",
        "Load the full geometry of the selected proxies (all when nothing is selected).":
            "Lädt die volle Geometrie der gewählten Proxies (aller, wenn nichts gewählt ist).",
        "Swap the selected originals back to proxies (all when nothing is selected).":
            "Tauscht die gewählten Originale wieder gegen Proxies (alle, wenn nichts gewählt ist).",
        "Select groups or components first.": "Zuerst Gruppen oder Komponenten auswählen.",
        "Selection": "Auswahl",
        "{n} object(s), {d} definition(s), {f} faces":
            "{n} Objekt(e), {d} Definition(en), {f} Flächen",
        "Only objects with more than": "Nur Objekte mit mehr als",
        " faces": " Flächen",
        "Proxy mesh": "Proxy-Mesh",
        "Box": "Box",
        "Convex hull": "Konvexe Hülle",
        "Vertex cloud": "Punktwolke",
        "From source": "Aus Original (reduziert)",
        "Hull points": "Hüllpunkte",
        "Points": "Punkte",
        "Max points": "Max. Punkte",
        "Keep faces": "Flächen behalten",
        "Keep materials": "Materialien behalten",
        "Colour": "Farbe",
        "See-through": "Durchscheinend",
        "Save originals": "Originale speichern",
        "Individually": "Einzeln",
        "All together": "Alle zusammen",
        "By layer": "Nach Layer",
        "Folder": "Ordner",
        "Browse…": "Durchsuchen…",
        "Preview": "Vorschau",
        "Create": "Erstellen",
        "Cancel": "Abbrechen",
        "Result": "Ergebnis",
        "{a} → {b} faces": "{a} → {b} Flächen",
        "{a} faces → {b} points": "{a} Flächen → {b} Punkte",
        "Choose a folder for the originals.": "Einen Ordner für die Originale wählen.",
        "Created {n} proxy definition(s) ({i} object(s)), originals in {p}":
            "{n} Proxy-Definition(en) erstellt ({i} Objekt(e)), Originale in {p}",
        "Nothing to do: no selected object passes the filter.":
            "Nichts zu tun: kein gewähltes Objekt erfüllt den Filter.",
        "No proxies to swap.": "Keine Proxies zum Tauschen.",
        "Originals shown: {n} definition(s)": "Originale angezeigt: {n} Definition(en)",
        "Proxies shown: {n} definition(s)": "Proxies angezeigt: {n} Definition(en)",
        "Original not found: {p}": "Original nicht gefunden: {p}",
        "{n} proxy(ies) selected": "{n} Proxy(s) ausgewählt",
        "Could not write {p}: {e}": "Konnte {p} nicht schreiben: {e}",
        "Already a proxy — skipped: {n}": "Schon ein Proxy — übersprungen: {n}",
        "{n} already a proxy — Show Originals first":
            "{n} schon Proxy — zuerst «Originale anzeigen»",
    },
    "es": {
        "Proxies": "Proxies",
        "Create Proxies…": "Crear proxies…",
        "Show Originals": "Mostrar originales",
        "Show Proxies": "Mostrar proxies",
        "Select All Proxies": "Seleccionar todos los proxies",
        "Replace the selected objects by light proxies; the originals go to .igz files.":
            "Sustituye los objetos seleccionados por proxies livianos; los originales van a archivos .igz.",
        "Load the full geometry of the selected proxies (all when nothing is selected).":
            "Carga la geometría completa de los proxies seleccionados (todos si no hay selección).",
        "Swap the selected originals back to proxies (all when nothing is selected).":
            "Vuelve a cambiar los originales seleccionados por proxies (todos si no hay selección).",
        "Select groups or components first.": "Primero seleccione grupos o componentes.",
        "Selection": "Selección",
        "{n} object(s), {d} definition(s), {f} faces":
            "{n} objeto(s), {d} definición(es), {f} caras",
        "Only objects with more than": "Solo objetos con más de",
        " faces": " caras",
        "Proxy mesh": "Malla proxy",
        "Box": "Caja",
        "Convex hull": "Envolvente convexa",
        "Vertex cloud": "Nube de vértices",
        "From source": "Del original (reducido)",
        "Hull points": "Puntos de envolvente",
        "Points": "Puntos",
        "Max points": "Puntos máx.",
        "Keep faces": "Conservar caras",
        "Keep materials": "Conservar materiales",
        "Colour": "Color",
        "See-through": "Translúcido",
        "Save originals": "Guardar originales",
        "Individually": "Individualmente",
        "All together": "Todos juntos",
        "By layer": "Por capa",
        "Folder": "Carpeta",
        "Browse…": "Examinar…",
        "Preview": "Vista previa",
        "Create": "Crear",
        "Cancel": "Cancelar",
        "Result": "Resultado",
        "{a} → {b} faces": "{a} → {b} caras",
        "{a} faces → {b} points": "{a} caras → {b} puntos",
        "Choose a folder for the originals.": "Elija una carpeta para los originales.",
        "Created {n} proxy definition(s) ({i} object(s)), originals in {p}":
            "{n} definición(es) proxy creadas ({i} objeto(s)), originales en {p}",
        "Nothing to do: no selected object passes the filter.":
            "Nada que hacer: ningún objeto seleccionado pasa el filtro.",
        "No proxies to swap.": "No hay proxies para cambiar.",
        "Originals shown: {n} definition(s)": "Originales mostrados: {n} definición(es)",
        "Proxies shown: {n} definition(s)": "Proxies mostrados: {n} definición(es)",
        "Original not found: {p}": "Original no encontrado: {p}",
        "{n} proxy(ies) selected": "{n} proxy(s) seleccionados",
        "Could not write {p}: {e}": "No se pudo escribir {p}: {e}",
        "Already a proxy — skipped: {n}": "Ya es un proxy — omitido: {n}",
        "{n} already a proxy — Show Originals first":
            "{n} ya es proxy — primero «Mostrar originales»",
    },
}


def _tr(text: str, **kw) -> str:
    """``text`` in the interface language, with ``{n}``-style fields."""
    try:
        from core.i18n import current_language
        lang = current_language()
    except Exception:  # noqa: BLE001
        lang = "en"
    out = _TEXTS.get(lang, {}).get(text, text)
    return out.format(**kw) if kw else out


DEFAULTS = {
    "type": "box",
    "hull_points": 64,
    "cloud_pct": 5.0,
    "cloud_max": 2000,
    "source_pct": 10.0,
    "keep_mat": True,
    "color": [0.95, 0.55, 0.15],
    "see_through": False,
    "min_faces_on": False,
    "min_faces": 1000,
    "mode": "individual",
}

#: Opacity of a see-through proxy.
_SEE_THROUGH = 0.35
#: Edges between proxy faces flatter than this draw soft (no hard line).
_SOFT_DEG = 25.0


# ---------------------------------------------------------------------------
# 1. Geometry of an object, as NumPy arrays in its own (definition) frame.
# ---------------------------------------------------------------------------

def _definition_root(group):
    """A throwaway root that places ``group``'s definition at identity: the
    proxy is built in the definition's own frame, so every instance carries
    it with its own transform. A classic group is already in world space."""
    from core.group import Group
    from PySide6.QtGui import QMatrix4x4
    root = Group.__new__(Group)
    root.mesh = group.mesh
    root.children = list(getattr(group, "children", None) or [])
    root.xform = QMatrix4x4() if group.xform is not None else None
    return root


def _mesh_arrays(mesh, cache=None):
    """``(P, T, A, S)`` of one mesh: positions ``(n,3)``, triangles ``(m,3)``,
    per-triangle face attrs (list) and loose edges ``(s,2)``."""
    import numpy as np
    key = id(mesh)
    if cache is not None and key in cache:
        return cache[key]
    pos, index = [], {}

    def vid(v):
        i = index.get(id(v))
        if i is None:
            i = index[id(v)] = len(pos)
            pos.append(v.position.toTuple())
        return i

    tris, attrs = [], []
    for f in mesh.faces:
        loop = f.loop
        n = len(loop)
        if n < 3:
            continue
        a = f.attrs
        if not f.hole_loops and n <= 4:
            i0, i1, i2 = vid(loop[0]), vid(loop[1]), vid(loop[2])
            tris.append((i0, i1, i2))
            attrs.append(a)
            if n == 4:
                tris.append((i0, i2, vid(loop[3])))
                attrs.append(a)
            continue
        try:
            parts = f.triangulate()
        except Exception:  # noqa: BLE001 - a broken face is skipped
            parts = []
        for t in parts:
            base = len(pos)
            pos.extend(p.toTuple() for p in t)
            tris.append((base, base + 1, base + 2))
            attrs.append(a)
    segs = []
    for e in mesh.edges:
        if not e.faces:
            segs.append((vid(e.v0), vid(e.v1)))
    out = (np.array(pos, dtype=np.float64).reshape(-1, 3),
           np.array(tris, dtype=np.int64).reshape(-1, 3),
           attrs,
           np.array(segs, dtype=np.int64).reshape(-1, 2))
    if cache is not None:
        cache[key] = out
    return out


def gather_geometry(group, cache=None):
    """The full geometry of ``group`` in its definition frame (nested
    placements folded in): ``(P, T, A, S)`` as in :func:`_mesh_arrays`."""
    import numpy as np
    from core.group import iter_placements, np_affine
    Ps, Ts, As, Ss, off = [], [], [], [], 0
    for pg, m in iter_placements(_definition_root(group)):
        P, T, A, S = _mesh_arrays(pg.mesh, cache)
        if not len(P):
            continue
        if m is not None:
            rot, tr = np_affine(m)
            P = P @ rot.T + tr
        Ps.append(P)
        Ts.append(T + off)
        As.extend(A)
        Ss.append(S + off)
        off += len(P)
    if not Ps:
        z = np.zeros((0, 3))
        return z, np.zeros((0, 3), np.int64), [], np.zeros((0, 2), np.int64)
    return np.vstack(Ps), np.vstack(Ts), As, np.vstack(Ss)


def face_count(group) -> int:
    from core.group import iter_placements
    return sum(len(pg.mesh.faces) for pg, _m in iter_placements(group))


# ---------------------------------------------------------------------------
# 2. Proxy meshes. A «spec» is {"P": (k,3), "faces": [[i…]], "attrs": [dict],
#    "segs": (s,2)} — cheap to preview, turned into a Mesh on Create.
# ---------------------------------------------------------------------------

def _empty_spec():
    import numpy as np
    return {"P": np.zeros((0, 3)), "faces": [], "attrs": [],
            "segs": np.zeros((0, 2), np.int64)}


def box_spec(P):
    """The bounding box of ``P`` (6 quads); a flat object gives one
    rectangle, a straight one a line."""
    import numpy as np
    if not len(P):
        return _empty_spec()
    lo, hi = P.min(axis=0), P.max(axis=0)
    ext = hi - lo
    diag = float(np.linalg.norm(ext)) or 1.0
    flat = ext < 1e-6 * diag
    spec = _empty_spec()
    if flat.sum() >= 2:
        spec["P"] = np.array([lo, hi])
        spec["segs"] = np.array([[0, 1]])
        return spec
    if flat.sum() == 1:
        k = int(np.argmax(flat))
        u, v = [i for i in range(3) if i != k]
        corners = []
        for cu, cv in ((0, 0), (1, 0), (1, 1), (0, 1)):
            p = lo.copy()
            p[u] = (lo, hi)[cu][u]
            p[v] = (lo, hi)[cv][v]
            corners.append(p)
        spec["P"] = np.array(corners)
        spec["faces"] = [[0, 1, 2, 3]]
        spec["attrs"] = [None]
        return spec
    C = np.array([[(lo, hi)[(i >> 0) & 1][0], (lo, hi)[(i >> 1) & 1][1],
                   (lo, hi)[(i >> 2) & 1][2]] for i in range(8)])
    # Corner i: bit0 = x, bit1 = y, bit2 = z. Loops counter-clockwise
    # seen from outside.
    spec["P"] = C
    spec["faces"] = [[0, 2, 3, 1], [4, 5, 7, 6], [0, 1, 5, 4],
                     [2, 6, 7, 3], [0, 4, 6, 2], [1, 3, 7, 5]]
    spec["attrs"] = [None] * 6
    return spec


def _fibonacci_dirs(k):
    import numpy as np
    i = np.arange(k, dtype=np.float64) + 0.5
    phi = np.arccos(1.0 - 2.0 * i / k)
    theta = math.pi * (1.0 + 5 ** 0.5) * i
    return np.stack([np.cos(theta) * np.sin(phi),
                     np.sin(theta) * np.sin(phi), np.cos(phi)], axis=1)


def extreme_points(P, k):
    """Indices of the points of ``P`` furthest along ``k`` directions spread
    over the sphere (plus the six axis directions) — the vertices a hull
    through at most about ``k`` points keeps."""
    import numpy as np
    D = np.vstack([_fibonacci_dirs(max(4, int(k))),
                   np.array([[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0],
                             [0, 0, 1], [0, 0, -1]], dtype=np.float64)])
    best_v = np.full(len(D), -np.inf)
    best_i = np.zeros(len(D), dtype=np.int64)
    c = P.mean(axis=0)
    step = 20000
    for s in range(0, len(P), step):
        dots = (P[s:s + step] - c) @ D.T
        j = dots.argmax(axis=0)
        v = dots[j, np.arange(len(D))]
        better = v > best_v
        best_v[better] = v[better]
        best_i[better] = j[better] + s
    return np.unique(best_i)


def convex_hull(P):
    """Triangles ``[(a, b, c)]`` of the convex hull of ``P`` (small: a few
    hundred points), counter-clockwise from outside. ``None`` when the
    points are flat or fewer than four."""
    import numpy as np
    n = len(P)
    if n < 4:
        return None
    diag = float(np.linalg.norm(P.max(axis=0) - P.min(axis=0))) or 1.0
    eps = 1e-9 * diag
    i0 = int(np.argmin(P[:, 0]))
    i1 = int(np.argmax(np.linalg.norm(P - P[i0], axis=1)))
    d = P[i1] - P[i0]
    if np.linalg.norm(d) < 1e-7 * diag:
        return None
    cr = np.linalg.norm(np.cross(P - P[i0], d), axis=1)
    i2 = int(np.argmax(cr))
    if cr[i2] < 1e-7 * diag * diag:
        return None
    nrm = np.cross(P[i1] - P[i0], P[i2] - P[i0])
    h = (P - P[i0]) @ nrm
    i3 = int(np.argmax(np.abs(h)))
    if abs(h[i3]) < 1e-7 * diag * np.linalg.norm(nrm):
        return None
    inside = (P[i0] + P[i1] + P[i2] + P[i3]) / 4.0

    def oriented(a, b, c):
        nn = np.cross(P[b] - P[a], P[c] - P[a])
        if (inside - P[a]) @ nn > 0:
            return (a, c, b)
        return (a, b, c)

    faces = [oriented(i0, i1, i2), oriented(i0, i1, i3),
             oriented(i0, i2, i3), oriented(i1, i2, i3)]

    def plane(f):
        a, b, c = f
        nn = np.cross(P[b] - P[a], P[c] - P[a])
        ln = np.linalg.norm(nn)
        return (nn / ln if ln > 0 else nn), P[a]

    planes = {f: plane(f) for f in faces}
    order = [i for i in np.argsort(-np.linalg.norm(P - inside, axis=1)).tolist()
             if i not in (i0, i1, i2, i3)]
    for p in order:
        x = P[p]
        visible = [f for f in faces if (x - planes[f][1]) @ planes[f][0] > eps]
        if not visible:
            continue
        vset = set(visible)
        dedges = set()
        for a, b, c in visible:
            dedges.update(((a, b), (b, c), (c, a)))
        horizon = [(a, b) for (a, b) in dedges if (b, a) not in dedges]
        faces = [f for f in faces if f not in vset]
        for f in visible:
            planes.pop(f, None)
        for a, b in horizon:
            f = (a, b, p)
            faces.append(f)
            planes[f] = plane(f)
    return faces


def hull_spec(P, points=64):
    import numpy as np
    if len(P) < 4:
        return box_spec(P)
    idx = extreme_points(P, points)
    Q = P[idx]
    # Merge points closer than a hair (they make sliver triangles).
    diag = float(np.linalg.norm(Q.max(axis=0) - Q.min(axis=0))) or 1.0
    key = np.round(Q / (1e-5 * diag)).astype(np.int64)
    _u, first = np.unique(key, axis=0, return_index=True)
    Q = Q[np.sort(first)]
    tris = convex_hull(Q)
    if not tris:
        return box_spec(P)
    used = sorted({i for t in tris for i in t})
    remap = {o: n for n, o in enumerate(used)}
    spec = _empty_spec()
    spec["P"] = Q[used]
    spec["faces"] = [[remap[a], remap[b], remap[c]] for a, b, c in tris]
    spec["attrs"] = [None] * len(tris)
    return spec


def cloud_spec(P, pct=5.0, max_points=2000, seed=1):
    """Small 3D crosses on ``pct`` % of the distinct vertices (at most
    ``max_points``), spread evenly by a fixed random draw."""
    import numpy as np
    if not len(P):
        return _empty_spec()
    diag = float(np.linalg.norm(P.max(axis=0) - P.min(axis=0))) or 1.0
    key = np.round(P / (1e-6 * diag)).astype(np.int64)
    _u, first = np.unique(key, axis=0, return_index=True)
    U = P[np.sort(first)]
    n = max(1, min(int(max_points), int(round(len(U) * pct / 100.0))))
    n = min(n, len(U))
    rng = np.random.default_rng(seed)
    pick = np.sort(rng.choice(len(U), size=n, replace=False))
    C = U[pick]
    s = 0.004 * diag
    offs = np.array([[s, 0, 0], [-s, 0, 0], [0, s, 0], [0, -s, 0],
                     [0, 0, s], [0, 0, -s]])
    pts = (C[:, None, :] + offs[None, :, :]).reshape(-1, 3)
    base = np.arange(n) * 6
    segs = np.stack([np.concatenate([base, base + 2, base + 4]),
                     np.concatenate([base + 1, base + 3, base + 5])], axis=1)
    spec = _empty_spec()
    spec["P"] = pts
    spec["segs"] = segs
    return spec


def _cluster(P, T, cell, lo):
    """Vertex clustering at grid size ``cell``: ``(Q, T2, keep)``."""
    import numpy as np
    g = np.floor((P - lo) / cell).astype(np.int64)
    _u, inv = np.unique(g, axis=0, return_inverse=True)
    inv = inv.reshape(-1)
    k = int(inv.max()) + 1 if len(inv) else 0
    cnt = np.bincount(inv, minlength=k).astype(np.float64)
    Q = np.stack([np.bincount(inv, weights=P[:, a], minlength=k)
                  for a in range(3)], axis=1) / np.maximum(cnt, 1)[:, None]
    T2 = inv[T]
    ok = ((T2[:, 0] != T2[:, 1]) & (T2[:, 1] != T2[:, 2])
          & (T2[:, 0] != T2[:, 2]))
    idx = np.nonzero(ok)[0]
    if len(idx):
        srt = np.sort(T2[idx], axis=1)
        _u2, first = np.unique(srt, axis=0, return_index=True)
        idx = idx[np.sort(first)]
    return Q, T2, idx


def source_spec(P, T, A, pct=10.0, keep_mat=True):
    """The original reduced to about ``pct`` % of its triangles (vertex
    clustering — robust on any soup, keeps the silhouette)."""
    import numpy as np
    if not len(T):
        return box_spec(P)
    target = max(4, int(len(T) * pct / 100.0))
    lo = P.min(axis=0)
    diag = float(np.linalg.norm(P.max(axis=0) - lo)) or 1.0
    if target >= len(T):
        Q, T2, idx = P, T, np.arange(len(T))
    else:
        a, b = diag * 1e-5, diag      # cell sizes: a → too many, b → too few
        best = None
        for _ in range(18):
            c = math.sqrt(a * b)
            Q, T2, idx = _cluster(P, T, c, lo)
            if len(idx) > target:
                a = c
            else:
                b = c
                best = (Q, T2, idx)
            if b / a < 1.05:
                break
        if best is None or not len(best[2]):
            Q, T2, idx = _cluster(P, T, a, lo)
        else:
            Q, T2, idx = best
        if not len(idx):
            return box_spec(P)
    tris = T2[idx]
    used = np.unique(tris)
    remap = np.full(len(Q), -1, dtype=np.int64)
    remap[used] = np.arange(len(used))
    spec = _empty_spec()
    spec["P"] = Q[used]
    spec["faces"] = remap[tris].tolist()
    if keep_mat:
        keys = ("color", "mat", "opacity")
        spec["attrs"] = [({k: A[i][k] for k in keys if k in A[i]} or None)
                         if A[i] else None for i in idx.tolist()]
    else:
        spec["attrs"] = [None] * len(idx)
    return spec


def make_spec(P, T, A, params):
    kind = params.get("type", "box")
    if kind == "hull":
        return hull_spec(P, int(params.get("hull_points", 64)))
    if kind == "cloud":
        return cloud_spec(P, float(params.get("cloud_pct", 5.0)),
                          int(params.get("cloud_max", 2000)))
    if kind == "source":
        return source_spec(P, T, A, float(params.get("source_pct", 10.0)),
                           bool(params.get("keep_mat", True)))
    return box_spec(P)


def spec_edges(spec):
    """Unique edges of a spec as an ``(e,2)`` index array (for previews)."""
    import numpy as np
    pairs = []
    for f in spec["faces"]:
        for i in range(len(f)):
            a, b = f[i], f[(i + 1) % len(f)]
            pairs.append((a, b) if a < b else (b, a))
    arr = np.array(pairs, dtype=np.int64).reshape(-1, 2)
    if len(arr):
        arr = np.unique(arr, axis=0)
    segs = spec["segs"]
    if len(segs):
        arr = np.vstack([arr, segs]) if len(arr) else segs
    return arr


def spec_face_count(spec) -> int:
    return len(spec["faces"])


def build_mesh(spec, params):
    """A new :class:`Mesh` from ``spec``, painted with the proxy colour (or
    keeping the source's materials), seams between flat faces soft."""
    import numpy as np
    from core.mesh import Mesh
    mesh = Mesh()
    P = np.asarray(spec["P"], dtype=np.float64)
    colour = list(params.get("color", DEFAULTS["color"]))[:3]
    see = bool(params.get("see_through"))
    keep = params.get("type") == "source" and bool(params.get("keep_mat", True))
    faces = spec["faces"]
    if faces:
        corners = np.concatenate([np.asarray(f, dtype=np.int64) for f in faces])
        pos = P[corners]
        ring = np.array([len(f) for f in faces], dtype=np.int64)
        attrs = []
        for a in spec["attrs"]:
            if keep and a:
                d = dict(a)
            else:
                d = {"color": [colour[0], colour[1], colour[2], 1.0]}
            if see:
                d["opacity"] = _SEE_THROUGH
            attrs.append(d)
        try:
            mesh.add_faces_bulk(pos, ring, np.ones(len(faces), dtype=np.int64),
                                attrs)
        except Exception:  # noqa: BLE001 - fall back face by face
            from PySide6.QtGui import QVector3D
            for f, d in zip(faces, attrs):
                try:
                    nf = mesh.add_face([QVector3D(*P[i]) for i in f])
                    nf.attrs.update(d)
                except Exception:  # noqa: BLE001 - degenerate face
                    pass
        _soften(mesh)
    segs = spec["segs"]
    if len(segs):
        vobjs, inv = mesh.bulk_weld(P)
        mesh.add_edges_welded(vobjs, inv[segs[:, 0]], inv[segs[:, 1]])
    mesh._chunk_dirty = True
    mesh._mut_serial += 1
    return mesh


def _soften(mesh) -> None:
    lim = math.cos(math.radians(_SOFT_DEG))
    normals = {}
    for e in mesh.edges:
        if len(e.faces) != 2:
            continue
        f1, f2 = e.faces
        n1 = normals.get(id(f1))
        if n1 is None:
            n1 = normals[id(f1)] = f1.normal()
        n2 = normals.get(id(f2))
        if n2 is None:
            n2 = normals[id(f2)] = f2.normal()
        if (n1.x() * n2.x() + n1.y() * n2.y() + n1.z() * n2.z()) >= lim:
            e.soft = True


# ---------------------------------------------------------------------------
# 3. Proxies in the document: which groups, which definitions.
# ---------------------------------------------------------------------------

def proxy_info(group):
    ext = getattr(group, "ext", None) or {}
    info = ext.get(KEY)
    return info if isinstance(info, dict) and info.get("id") else None


def selected_groups(scene):
    from core.group import Group
    top = set(id(g) for g in scene.groups)
    return [g for g in scene.selection if isinstance(g, Group) and id(g) in top]


def definitions(scene, groups):
    """``[(key, [instances…])]``: the selected objects grouped by what they
    share. A component instance brings every top-level sibling that shares
    its definition (one proxy for all of them); a classic group stands
    alone."""
    out, seen = [], {}
    for g in groups:
        k = ("m", id(g.mesh)) if g.xform is not None else ("g", id(g))
        if k in seen:
            continue
        if g.xform is not None:
            inst = [s for s in scene.groups
                    if s.xform is not None and s.mesh is g.mesh]
        else:
            inst = [g]
        seen[k] = len(out)
        out.append((k, inst))
    return out


def _safe(name: str) -> str:
    s = re.sub(r"[^\w\-]+", "_", name or "", flags=re.UNICODE).strip("_")
    return s[:48] or "object"


def _doc_path(viewport):
    win = viewport.window()
    p = getattr(win, "_current_path", None)
    return str(p) if p else None


def default_folder(viewport) -> str:
    doc = _doc_path(viewport)
    if not doc:
        return ""
    base, _ext = os.path.splitext(doc)
    return base + "_proxies"


def _resolve(info, viewport) -> str:
    """The original's file: relative to the document first (a moved
    project), then the absolute path it was written to."""
    doc = _doc_path(viewport)
    rel = info.get("rel")
    if rel and doc:
        p = os.path.normpath(os.path.join(os.path.dirname(doc), rel))
        if os.path.isfile(p):
            return p
    return info.get("file", "")


def _target_file(folder, mode, group, pid) -> str:
    if mode == "together":
        return os.path.join(folder, "proxies.igz")
    if mode == "layer":
        return os.path.join(folder, _safe(group.layer or "Layer0") + ".igz")
    return os.path.join(folder, f"{_safe(group.name)}_{pid[:6]}.igz")


# ---------------------------------------------------------------------------
# 4. Original .igz files.
# ---------------------------------------------------------------------------

def _file_entry(group, mesh, children, pid, name):
    """The group written to an original file: the definition at identity
    (or the classic group as it is), tagged with the proxy id."""
    from core.group import Group
    from PySide6.QtGui import QMatrix4x4
    g = Group(mesh, name=name)
    if group.xform is not None:
        g.xform = QMatrix4x4()
        g.component = bool(getattr(group, "component", True))
    g.children = list(children or [])
    g.layer = group.layer
    g.ext = {KEY: {"id": pid}}
    return g


def _used_materials(scene, entries) -> dict:
    from core.group import iter_placements
    names = set()
    for e in entries:
        for pg, _m in iter_placements(e):
            for f in pg.mesh.faces:
                n = f.attrs.get("mat")
                if n:
                    names.add(n)
    return {n: m for n, m in getattr(scene, "materials", {}).items() if n in names}


def write_originals(scene, path, entries) -> None:
    """Write ``entries`` (file groups) to ``path``; a file that exists keeps
    its other originals (All together / By layer add to it)."""
    from core.scene import Scene
    from formats import igz
    out = Scene()
    ids = {e.ext[KEY]["id"] for e in entries}
    if os.path.isfile(path):
        old = Scene()
        igz.load_into(old, Path(path))
        out.groups = [g for g in old.groups
                      if ((g.ext or {}).get(KEY) or {}).get("id") not in ids]
        out.materials = dict(old.materials)
    out.groups = list(out.groups) + list(entries)
    out.materials.update(_used_materials(scene, entries))
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    igz.save_scene(out, Path(path))


def read_originals(path) -> tuple:
    """``({proxy id: group}, materials)`` of an original file."""
    from core.scene import Scene
    from formats import igz
    sc = Scene()
    igz.load_into(sc, Path(path))
    found = {}
    for g in sc.groups:
        pid = ((g.ext or {}).get(KEY) or {}).get("id")
        if pid:
            found[pid] = g
    return found, dict(getattr(sc, "materials", {}) or {})


# ---------------------------------------------------------------------------
# 5. One undo step: swap the geometry of a set of groups.
# ---------------------------------------------------------------------------

_CMD = {}


def _swap_command_class():
    cls = _CMD.get("swap")
    if cls is not None:
        return cls
    from core.history import Command

    class SwapGeometryCommand(Command):
        """Give each group a new mesh / nested placements / ext; undo and redo
        are plain swaps (the meshes stay alive in the history)."""

        def __init__(self, items, materials=None) -> None:
            # items: [(group, mesh, children, ext)]
            self.items = [list(it) for it in items]
            self.materials = dict(materials or {})
            self._added = []

        def _swap(self, scene) -> None:
            for it in self.items:
                g = it[0]
                old = (g.mesh, list(g.children or []), g.ext)
                g.mesh, g.children, g.ext = it[1], list(it[2] or []), it[3]
                it[1], it[2], it[3] = old
                g.mesh._chunk_dirty = True
                g.mesh._attrs_dirty = True
            scene.version += 1

        def do(self, scene) -> None:
            mats = getattr(scene, "materials", None)
            if mats is not None and self.materials:
                self._added = [n for n in self.materials if n not in mats]
                for n in self._added:
                    mats[n] = self.materials[n]
            self._swap(scene)

        def undo(self, scene) -> None:
            self._swap(scene)
            mats = getattr(scene, "materials", None)
            for n in self._added:
                if mats is not None:
                    mats.pop(n, None)

    _CMD["swap"] = SwapGeometryCommand
    return SwapGeometryCommand


def _execute(viewport, items, materials=None) -> None:
    cls = _swap_command_class()
    cmd = cls(items, materials)
    viewport.history.execute(cmd)
    try:
        from core.history import _dirty_group_chunks
        _dirty_group_chunks(viewport.scene)
    except Exception:  # noqa: BLE001
        pass
    viewport.notify_scene_changed()
    viewport.update()
    return cmd


def _with_info(group, info):
    ext = dict(getattr(group, "ext", None) or {})
    ext[KEY] = dict(info)
    return ext


#: Proxy meshes built in this session, by proxy id — Show Proxies reuses
#: one while the original it was swapped for is unchanged.
_PROXY_CACHE: dict = {}


def _wait_cursor(on: bool) -> None:
    try:
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QApplication
        if on:
            QApplication.setOverrideCursor(Qt.WaitCursor)
        else:
            QApplication.restoreOverrideCursor()
    except Exception:  # noqa: BLE001
        pass


# ---------------------------------------------------------------------------
# 6. Commands: Create Proxies / Show Originals / Show Proxies.
# ---------------------------------------------------------------------------

def _can_proxy(g) -> bool:
    """A plain object, or a proxy whose original is shown right now (made
    into a proxy again, with the settings of this run)."""
    info = proxy_info(g)
    return info is None or info.get("state") == "original"


def plan_proxies(viewport, groups, params, folder, geo_cache=None,
                 spec_cache=None) -> dict:
    """Everything Create needs, without touching the document or the disk:
    the proxy meshes, the swap items and the original files to write.

    ``geo_cache`` / ``spec_cache`` (dicts kept by the dialog) save the
    geometry walk and the proxy math between previews."""
    scene = viewport.scene
    doc = _doc_path(viewport)
    mode = params.get("mode", "individual")
    blocked = [g for g in groups if not _can_proxy(g)]
    groups = [g for g in groups if _can_proxy(g)]
    defs = definitions(scene, groups)
    if params.get("min_faces_on"):
        lim = int(params.get("min_faces", 0))
        defs = [(k, inst) for k, inst in defs if face_count(inst[0]) > lim]
    pkey = tuple(sorted((a, str(params.get(a))) for a in
                        ("type", "hull_points", "cloud_pct", "cloud_max",
                         "source_pct", "keep_mat", "color", "see_through")))
    mesh_cache = {}
    by_file: dict = {}
    items, faces_in, faces_out, points = [], 0, 0, 0
    for dk, inst in defs:
        g0 = inst[0]
        old = proxy_info(g0)
        pid = old["id"] if old else uuid.uuid4().hex[:16]
        if geo_cache is not None and dk in geo_cache:
            P, T, A = geo_cache[dk]
        else:
            P, T, A, _S = gather_geometry(g0, mesh_cache)
            if geo_cache is not None:
                geo_cache[dk] = (P, T, A)
        sk = (dk, pkey)
        if spec_cache is not None and sk in spec_cache:
            spec = spec_cache[sk]
        else:
            spec = make_spec(P, T, A, params)
            if spec_cache is not None:
                spec_cache[sk] = spec
        proxy = build_mesh(spec, params)
        # A proxy made again keeps its original where it already lives.
        path = _resolve(old, viewport) if old else ""
        if not path:
            path = os.path.normpath(_target_file(folder, mode, g0, pid))
        by_file.setdefault(path, []).append(
            _file_entry(g0, g0.mesh, g0.children, pid, g0.name))
        rel = None
        if doc:
            try:
                rel = os.path.relpath(path, os.path.dirname(doc))
            except ValueError:      # another drive (Windows)
                rel = None
        n_in = face_count(g0)
        info = {"id": pid, "file": path, "rel": rel, "state": "proxy",
                "faces": n_in, "proxy_faces": spec_face_count(spec),
                "local": g0.xform is not None, "name": g0.name,
                "params": {k: params[k] for k in
                           ("type", "hull_points", "cloud_pct", "cloud_max",
                            "source_pct", "keep_mat", "color", "see_through")
                           if k in params}}
        _PROXY_CACHE[pid] = proxy
        for g in inst:
            items.append((g, proxy, [], _with_info(g, info)))
        faces_in += n_in
        faces_out += spec_face_count(spec)
        points += len(spec["segs"]) // 3
    return {"items": items, "files": by_file, "definitions": len(defs),
            "objects": sum(len(i) for _k, i in defs), "blocked": len(blocked),
            "faces_in": faces_in, "faces_out": faces_out, "points": points,
            "type": params.get("type"), "folder": folder}


def write_plan_files(viewport, plan) -> bool:
    for path, entries in plan["files"].items():
        try:
            write_originals(viewport.scene, path, entries)
        except Exception as exc:  # noqa: BLE001
            viewport.flash_status(_tr("Could not write {p}: {e}", p=path, e=exc), 8000)
            return False
    return True


def _created_status(viewport, plan) -> None:
    msg = _tr("Created {n} proxy definition(s) ({i} object(s)), originals in {p}",
              n=plan["definitions"], i=plan["objects"], p=plan["folder"])
    if plan["blocked"]:
        msg += " · " + _tr("Already a proxy — skipped: {n}", n=plan["blocked"])
    viewport.flash_status(msg, 8000)


def create_proxies(viewport, groups, params, folder) -> dict | None:
    """Create Proxies without the dialog: plan, write the originals, swap
    (one undo step)."""
    _wait_cursor(True)
    try:
        plan = plan_proxies(viewport, groups, params, folder)
        if not plan["items"]:
            viewport.flash_status(_tr("Nothing to do: no selected object passes the filter."), 5000)
            return None
        if not write_plan_files(viewport, plan):
            return None
        _execute(viewport, plan["items"])
    finally:
        _wait_cursor(False)
    _created_status(viewport, plan)
    return {"definitions": plan["definitions"], "objects": plan["objects"]}


def _target_proxies(scene, state):
    """Proxy groups in ``state`` among the selection (all when the
    selection holds none), with every top-level sibling sharing a mesh."""
    sel = [g for g in selected_groups(scene) if proxy_info(g)]
    base = sel or [g for g in scene.groups if proxy_info(g)]
    base = [g for g in base if proxy_info(g).get("state") == state]
    out, seen = [], set()
    for g in base:
        pid = proxy_info(g)["id"]
        if pid in seen:
            continue
        seen.add(pid)
        inst = [s for s in scene.groups
                if (proxy_info(s) or {}).get("id") == pid
                and proxy_info(s).get("state") == state]
        out.append((pid, inst))
    return out


def show_originals(viewport) -> int:
    from core.group import copy_group
    scene = viewport.scene
    targets = _target_proxies(scene, "proxy")
    if not targets:
        viewport.flash_status(_tr("No proxies to swap."), 4000)
        return 0
    _wait_cursor(True)
    try:
        files: dict = {}
        items, mats, missing = [], {}, []
        for pid, inst in targets:
            info = proxy_info(inst[0])
            path = _resolve(info, viewport)
            if path not in files:
                try:
                    files[path] = read_originals(path) if os.path.isfile(path) else ({}, {})
                except Exception:  # noqa: BLE001
                    files[path] = ({}, {})
            found, fmats = files[path]
            src = found.get(pid)
            if src is None:
                missing.append(path or info.get("name", pid))
                continue
            mats.update(fmats)
            _PROXY_CACHE[pid] = inst[0].mesh
            first = True
            for g in inst:
                kids = (list(src.children or []) if first else
                        [copy_group(c, _in_definition=True) for c in (src.children or [])])
                first = False
                new = dict(info)
                new["state"] = "original"
                new["serial"] = int(getattr(src.mesh, "_mut_serial", 0))
                items.append((g, src.mesh, kids, _with_info(g, new)))
        if items:
            _execute(viewport, items, mats)
    finally:
        _wait_cursor(False)
    if missing:
        viewport.flash_status(_tr("Original not found: {p}", p=", ".join(sorted(set(missing)))), 8000)
    else:
        viewport.flash_status(_tr("Originals shown: {n} definition(s)", n=len(targets)), 5000)
    return len(targets) - len(set(missing))


def show_proxies(viewport) -> int:
    scene = viewport.scene
    targets = _target_proxies(scene, "original")
    if not targets:
        viewport.flash_status(_tr("No proxies to swap."), 4000)
        return 0
    _wait_cursor(True)
    try:
        items = []
        for pid, inst in targets:
            g0 = inst[0]
            info = proxy_info(g0)
            params = dict(DEFAULTS)
            params.update(info.get("params") or {})
            changed = int(getattr(g0.mesh, "_mut_serial", 0)) != int(info.get("serial", -1))
            proxy = _PROXY_CACHE.get(pid)
            if changed:
                # Edited while shown: the file gets the new original.
                path = _resolve(info, viewport)
                entry = _file_entry(g0, g0.mesh, g0.children, pid, g0.name)
                try:
                    write_originals(scene, path, [entry])
                except Exception as exc:  # noqa: BLE001
                    viewport.flash_status(_tr("Could not write {p}: {e}", p=path, e=exc), 8000)
                    continue
                proxy = None
            if proxy is None:
                P, T, A, _S = gather_geometry(g0)
                spec = make_spec(P, T, A, params)
                proxy = build_mesh(spec, params)
                info = dict(info)
                info["faces"] = face_count(g0)
                info["proxy_faces"] = spec_face_count(spec)
                _PROXY_CACHE[pid] = proxy
            new = dict(info)
            new["state"] = "proxy"
            new.pop("serial", None)
            for g in inst:
                items.append((g, proxy, [], _with_info(g, new)))
        if items:
            _execute(viewport, items)
    finally:
        _wait_cursor(False)
    viewport.flash_status(_tr("Proxies shown: {n} definition(s)", n=len(targets)), 5000)
    return len(targets)


def select_all_proxies(viewport) -> None:
    scene = viewport.scene
    gs = [g for g in scene.groups if proxy_info(g)]
    try:
        scene.select(gs)
    except Exception:  # noqa: BLE001
        scene.selection.clear()
        scene.selection.update(gs)
        scene.version += 1
    viewport.flash_status(_tr("{n} proxy(ies) selected", n=len(gs)), 4000)
    viewport.update()


# ---------------------------------------------------------------------------
# 7. Dialog (non-modal) with the Live Preview of the PESI3D plugins: the
#    «Preview» button shows the real result in the model (one undo step,
#    taken back on every change and on Cancel, kept as it is by OK).
# ---------------------------------------------------------------------------

_STATE = {"dialog": None}


def _make_dialog_class():
    import json
    from PySide6.QtCore import QEventLoop, QSettings, Qt, QTimer
    from PySide6.QtGui import QColor
    from PySide6.QtWidgets import (QApplication, QCheckBox, QColorDialog,
                                   QComboBox, QDialog, QDoubleSpinBox,
                                   QFileDialog, QFormLayout, QHBoxLayout,
                                   QLabel, QLineEdit, QPushButton, QSpinBox,
                                   QVBoxLayout, QWidget)

    def fmt(x):
        return f"{x:,}".replace(",", ".")

    class ProxyDialog(QDialog):
        # The same look in every PESI3D plugin (Membrane, Grading, …).
        _PV_ON = ("QPushButton { background: #2e9e4f; color: white; "
                  "font-weight: bold; border: 1px solid #1f7a3a; "
                  "border-radius: 3px; padding: 3px 8px; }")
        _BANNER = {
            "live": "background: #1f5f33; color: #e8ffe9;",
            "busy": "background: #7a5a12; color: #fff6e0;",
            "paused": "background: #5c4a1a; color: #ffe9b8;",
            "error": "background: #7a1f1f; color: #ffecec;",
        }

        def __init__(self, viewport, groups, parent=None):
            super().__init__(parent)
            self.viewport = viewport
            self.groups = list(groups)
            self.geo_cache = {}
            self.spec_cache = {}
            self._preview_cmd = None
            self._busy = False
            self._computing = False
            self._block = None
            self.colour = list(DEFAULTS["color"])
            self._timer = QTimer(self)
            self._timer.setSingleShot(True)
            self._timer.setInterval(300)
            self._timer.timeout.connect(self._refresh_preview)
            self.setWindowTitle(f"{_tr('Proxies')} {VERSION} — {_tr('Create Proxies…')}")
            self.setModal(False)
            self.setAttribute(Qt.WA_DeleteOnClose, True)
            self._build_ui()
            self._load_settings()
            self._sync()

        # ---- UI ------------------------------------------------------------
        def _build_ui(self):
            lay = QVBoxLayout(self)
            form = QFormLayout()
            self.info = QLabel(self)
            self.info.setWordWrap(True)
            form.addRow(_tr("Selection"), self.info)

            row = QHBoxLayout()
            self.filt_on = QCheckBox(_tr("Only objects with more than"), self)
            self.filt_val = QSpinBox(self)
            self.filt_val.setRange(0, 100_000_000)
            self.filt_val.setSingleStep(1000)
            self.filt_val.setSuffix(_tr(" faces"))
            row.addWidget(self.filt_on)
            row.addWidget(self.filt_val, 1)
            form.addRow(row)

            self.kind = QComboBox(self)
            for code, label in (("box", "Box"), ("hull", "Convex hull"),
                                ("cloud", "Vertex cloud"), ("source", "From source")):
                self.kind.addItem(_tr(label), code)
            form.addRow(_tr("Proxy mesh"), self.kind)

            self.hull_pts = QSpinBox(self)
            self.hull_pts.setRange(8, 1024)
            form.addRow(_tr("Hull points"), self.hull_pts)
            self.cloud_row = QWidget(self)
            cr = QHBoxLayout(self.cloud_row)
            cr.setContentsMargins(0, 0, 0, 0)
            self.cloud_pct = QDoubleSpinBox(self)
            self.cloud_pct.setRange(0.01, 100.0)
            self.cloud_pct.setDecimals(2)
            self.cloud_pct.setSuffix(" %")
            self.cloud_max = QSpinBox(self)
            self.cloud_max.setRange(10, 200000)
            self.cloud_max.setSingleStep(500)
            cr.addWidget(self.cloud_pct, 1)
            cr.addWidget(QLabel(_tr("Max points"), self))
            cr.addWidget(self.cloud_max, 1)
            form.addRow(_tr("Points"), self.cloud_row)
            self.src_pct = QDoubleSpinBox(self)
            self.src_pct.setRange(0.1, 100.0)
            self.src_pct.setDecimals(1)
            self.src_pct.setSuffix(" %")
            form.addRow(_tr("Keep faces"), self.src_pct)
            self.keep_mat = QCheckBox(_tr("Keep materials"), self)
            form.addRow("", self.keep_mat)

            row = QHBoxLayout()
            self.col_btn = QPushButton(self)
            self.col_btn.setFixedWidth(60)
            self.see = QCheckBox(_tr("See-through"), self)
            row.addWidget(self.col_btn)
            row.addWidget(self.see)
            row.addStretch(1)
            form.addRow(_tr("Colour"), row)

            self.mode = QComboBox(self)
            for code, label in (("individual", "Individually"),
                                ("together", "All together"), ("layer", "By layer")):
                self.mode.addItem(_tr(label), code)
            form.addRow(_tr("Save originals"), self.mode)
            row = QHBoxLayout()
            self.folder = QLineEdit(self)
            browse = QPushButton(_tr("Browse…"), self)
            row.addWidget(self.folder, 1)
            row.addWidget(browse)
            form.addRow(_tr("Folder"), row)
            self.result = QLabel(self)
            form.addRow(_tr("Result"), self.result)
            lay.addLayout(form)

            self.pv_lbl = QLabel(self)
            self.pv_lbl.setWordWrap(True)
            self.pv_lbl.setVisible(False)
            lay.addWidget(self.pv_lbl)

            row = QHBoxLayout()
            self.preview = QPushButton("Preview", self)
            self.preview.setCheckable(True)
            self.preview.toggled.connect(self._preview_toggled)
            reset = QPushButton("Reset", self)
            reset.setToolTip("Back to the default settings.")
            reset.clicked.connect(self._reset)
            self.ok_btn = QPushButton("OK", self)
            self.ok_btn.setDefault(True)
            self.ok_btn.clicked.connect(self.accept)
            cancel = QPushButton("Cancel", self)
            cancel.clicked.connect(self.reject)
            row.addWidget(self.preview)
            row.addWidget(reset)
            row.addStretch(1)
            row.addWidget(self.ok_btn)
            row.addWidget(cancel)
            lay.addLayout(row)
            self._style_preview(False)

            for w in (self.filt_on, self.keep_mat, self.see):
                w.toggled.connect(self._changed)
            for w in (self.hull_pts, self.cloud_max, self.filt_val,
                      self.cloud_pct, self.src_pct):
                w.valueChanged.connect(self._changed)
            self.kind.currentIndexChanged.connect(self._changed)
            self.mode.currentIndexChanged.connect(self._changed)
            self.folder.editingFinished.connect(self._changed)
            self.col_btn.clicked.connect(self._pick_colour)
            browse.clicked.connect(self._pick_folder)

        def _paint_colour(self):
            r, g, b = (int(round(x * 255)) for x in self.colour)
            self.col_btn.setStyleSheet(f"background-color: rgb({r},{g},{b});")

        def _pick_colour(self):
            r, g, b = (int(round(x * 255)) for x in self.colour)
            c = QColorDialog.getColor(QColor(r, g, b), self)
            if c.isValid():
                self.colour = [c.redF(), c.greenF(), c.blueF()]
                self._paint_colour()
                self._changed()

        def _pick_folder(self):
            d = QFileDialog.getExistingDirectory(self, _tr("Folder"),
                                                 self.folder.text() or "")
            if d:
                self.folder.setText(d)
                self._changed()

        # ---- settings --------------------------------------------------------
        def _load_settings(self, defaults=False):
            st = QSettings()

            def sv(name, typ=None):
                d = DEFAULTS[name]
                if defaults:
                    return d
                k = f"plugins/{KEY}/{name}"
                return st.value(k, d) if typ is None else st.value(k, d, type=typ)

            self._busy = True
            self.kind.setCurrentIndex(max(0, self.kind.findData(sv("type"))))
            self.hull_pts.setValue(int(sv("hull_points")))
            self.cloud_pct.setValue(float(sv("cloud_pct")))
            self.cloud_max.setValue(int(sv("cloud_max")))
            self.src_pct.setValue(float(sv("source_pct")))
            self.keep_mat.setChecked(sv("keep_mat", bool))
            self.see.setChecked(sv("see_through", bool))
            self.filt_on.setChecked(sv("min_faces_on", bool))
            self.filt_val.setValue(int(sv("min_faces")))
            self.mode.setCurrentIndex(max(0, self.mode.findData(sv("mode"))))
            if not defaults:
                self.folder.setText(default_folder(self.viewport)
                                    or str(st.value(f"plugins/{KEY}/last_folder", "")))
            self.colour = list(DEFAULTS["color"])
            try:
                c = None if defaults else st.value(f"plugins/{KEY}/color", None)
                if c:
                    self.colour = [float(x) for x in str(c).split(",")][:3]
            except Exception:  # noqa: BLE001
                pass
            self._paint_colour()
            self._busy = False

        def _save_settings(self):
            st = QSettings()
            p = self.params()
            for k in ("type", "hull_points", "cloud_pct", "cloud_max", "source_pct",
                      "keep_mat", "see_through", "min_faces_on", "min_faces", "mode"):
                st.setValue(f"plugins/{KEY}/{k}", p[k])
            st.setValue(f"plugins/{KEY}/color", ",".join(f"{x:.4f}" for x in p["color"]))
            st.setValue(f"plugins/{KEY}/last_folder", self.folder.text())

        def params(self) -> dict:
            return {"type": self.kind.currentData(),
                    "hull_points": self.hull_pts.value(),
                    "cloud_pct": self.cloud_pct.value(),
                    "cloud_max": self.cloud_max.value(),
                    "source_pct": self.src_pct.value(),
                    "keep_mat": self.keep_mat.isChecked(),
                    "color": list(self.colour), "see_through": self.see.isChecked(),
                    "min_faces_on": self.filt_on.isChecked(),
                    "min_faces": self.filt_val.value(),
                    "mode": self.mode.currentData()}

        # ---- state -----------------------------------------------------------
        def _live_groups(self):
            live = set(id(g) for g in self.viewport.scene.groups)
            return [g for g in self.groups if id(g) in live]

        def _sync(self):
            """Enable the fields of the chosen type; count what Create would
            do (with the preview taken back, so nothing counts twice)."""
            k = self.kind.currentData()
            self.hull_pts.setEnabled(k == "hull")
            self.cloud_row.setEnabled(k == "cloud")
            self.src_pct.setEnabled(k == "source")
            self.keep_mat.setEnabled(k == "source")
            self.filt_val.setEnabled(self.filt_on.isChecked())
            if self._preview_cmd is not None:
                return                      # the live banner says it all
            gs = self._live_groups()
            ok = [g for g in gs if _can_proxy(g)]
            blocked = len(gs) - len(ok)
            defs = definitions(self.viewport.scene, ok)
            if self.filt_on.isChecked():
                defs = [(d, i) for d, i in defs
                        if face_count(i[0]) > self.filt_val.value()]
            total = sum(face_count(i[0]) for _d, i in defs)
            txt = _tr("{n} object(s), {d} definition(s), {f} faces",
                      n=sum(len(i) for _d, i in defs), d=len(defs), f=fmt(total))
            if blocked:
                txt += "\n" + _tr("{n} already a proxy — Show Originals first",
                                  n=blocked)
            self.info.setText(txt)
            self._block = (None if defs else
                           _tr("Nothing to do: no selected object passes the filter."))
            self.ok_btn.setEnabled(not self._block)

        def _result_text(self, plan):
            if plan["type"] == "cloud":
                return _tr("{a} faces → {b} points", a=fmt(plan["faces_in"]),
                           b=fmt(plan["points"]))
            return _tr("{a} → {b} faces", a=fmt(plan["faces_in"]),
                       b=fmt(plan["faces_out"]))

        def _state_key(self):
            p = self.params()
            return (json.dumps(p, sort_keys=True), self.folder.text().strip(),
                    tuple(sorted(id(g) for g in self._live_groups())))

        # ---- preview ---------------------------------------------------------
        def _banner(self, kind, text):
            self.pv_lbl.setStyleSheet(
                self._BANNER[kind] + " padding: 6px 8px; border-radius: 3px;")
            self.pv_lbl.setText(text)
            self.pv_lbl.setVisible(True)

        def _style_preview(self, on):
            if on:
                self.preview.setText("● Live Preview ON")
                self.preview.setStyleSheet(self._PV_ON)
                self.preview.setToolTip("The preview follows every change by "
                                        "itself — click to switch it off.")
            else:
                self.preview.setText("Preview")
                self.preview.setStyleSheet("")
                self.preview.setToolTip("Show the proxies in the model; they "
                                        "then update by themselves on every "
                                        "change.")
                self.pv_lbl.setVisible(False)
            if self.isVisible():
                QTimer.singleShot(0, self.adjustSize)

        def _changed(self, *_a):
            if self._busy:
                return
            if self.preview.isChecked():
                self._banner("busy", "⟳ Updating the preview…")
                self._timer.start()
            else:
                self.result.setText("")
                self._sync()

        def _reset(self):
            self._load_settings(defaults=True)
            self._changed()

        def _plan(self):
            return plan_proxies(self.viewport, self._live_groups(), self.params(),
                                os.path.normpath(self.folder.text().strip() or "."),
                                self.geo_cache, self.spec_cache)

        def _undo_preview(self):
            cmd = self._preview_cmd
            self._preview_cmd = None
            if cmd is None:
                return
            stack = getattr(self.viewport.history, "undo_stack", [])
            if stack and stack[-1] is cmd:
                self.viewport.history.undo()
                self.viewport.notify_scene_changed()
                self.viewport.update()

        def _refresh_preview(self):
            if self._computing:            # a change during a build: later
                self._timer.start()
                return
            self._undo_preview()
            self._sync()
            if not self.preview.isChecked():
                return
            if self._block:
                self._banner("paused", f"⏸ <b>Preview paused</b> — "
                             f"{self._block} It comes back by itself.")
                self.result.setText("")
                return
            self._banner("busy", "⟳ Updating the preview…")
            QApplication.processEvents(QEventLoop.ExcludeUserInputEvents)
            self._computing = True
            _wait_cursor(True)
            try:
                plan = self._plan()
                cmd = _execute(self.viewport, plan["items"])
                cmd.key = self._state_key()
                cmd.plan = plan
                self._preview_cmd = cmd
                self.result.setText(self._result_text(plan))
                self._banner("live", "● <b>LIVE PREVIEW</b> — "
                             + self._result_text(plan)
                             + " · changes apply instantly")
            except Exception as exc:  # noqa: BLE001
                self._preview_cmd = None
                self._banner("error", f"Preview failed: {exc}")
            finally:
                _wait_cursor(False)
                self._computing = False

        def _preview_toggled(self, on):
            self._style_preview(on)
            if on:
                self._refresh_preview()
            else:
                self._timer.stop()
                self._undo_preview()
                self._sync()

        # ---- close -------------------------------------------------------------
        def _keep_preview(self):
            """The live preview already IS the result for these settings:
            keep it (it is one undo step already) instead of building again."""
            cmd = self._preview_cmd
            if cmd is None or getattr(cmd, "key", None) != self._state_key():
                return None
            stack = getattr(self.viewport.history, "undo_stack", [])
            if not stack or stack[-1] is not cmd:
                return None
            self._preview_cmd = None
            return cmd

        def accept(self):
            if self._computing:
                return
            self._timer.stop()
            if not self.folder.text().strip():
                self.viewport.flash_status(_tr("Choose a folder for the originals."), 5000)
                self._pick_folder()
                if not self.folder.text().strip():
                    return
            self._save_settings()
            cmd = self._keep_preview()
            if cmd is not None:
                plan = cmd.plan
                if not write_plan_files(self.viewport, plan):
                    self._preview_cmd = cmd
                    self._undo_preview()
                    return
            else:
                self._undo_preview()
                self._sync()
                if self._block:
                    return
                _wait_cursor(True)
                try:
                    plan = self._plan()
                    if not plan["items"] or not write_plan_files(self.viewport, plan):
                        return
                    _execute(self.viewport, plan["items"])
                finally:
                    _wait_cursor(False)
            _created_status(self.viewport, plan)
            super().accept()

        def reject(self):
            if self._computing:
                return
            self._timer.stop()
            self._undo_preview()
            self._save_settings()
            super().reject()

        def closeEvent(self, ev):
            if self._computing:
                ev.ignore()
                return
            self._timer.stop()
            self._undo_preview()
            super().closeEvent(ev)

    return ProxyDialog


def open_dialog(viewport) -> None:
    """Non-modal: the viewport stays usable (orbit, pan, zoom) while the
    dialog is open. One dialog at a time."""
    groups = selected_groups(viewport.scene)
    if not groups:
        viewport.flash_status(_tr("Select groups or components first."), 4000)
        return
    old = _STATE.get("dialog")
    if old is not None:
        try:
            old.reject()
        except RuntimeError:
            pass
    cls = _CMD.get("dialog")
    if cls is None:
        cls = _CMD["dialog"] = _make_dialog_class()
    dlg = cls(viewport, groups, viewport.window())

    def gone(*_a):
        if _STATE.get("dialog") is dlg:
            _STATE["dialog"] = None

    dlg.finished.connect(gone)
    dlg.destroyed.connect(gone)
    _STATE["dialog"] = dlg
    dlg.show()
    dlg.raise_()


# ---------------------------------------------------------------------------
# 8. Registration.
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Toolbar (PESI3D): icons drawn in IngeTrazo's own icon style
# ---------------------------------------------------------------------------

def _pesi3d_icons():
    """Icon key → draw(painter, ink, accent) on a 48 px canvas."""
    import math  # noqa: F401
    from PySide6.QtCore import QPointF, QRectF, Qt  # noqa: F401
    from PySide6.QtGui import (QBrush, QColor, QPainterPath, QPen,  # noqa: F401
                               QPolygonF)

    def _a(c, alpha):
        return QColor(c.red(), c.green(), c.blue(), alpha)

    def _poly(pts):
        return QPolygonF([QPointF(x, y) for x, y in pts])

    def _cube(p, ink, acc, cx, cy, s, fill_alpha=150, dashed=False):
        h = s * 0.5
        top = _poly([(cx, cy - s), (cx + s, cy - h), (cx, cy), (cx - s, cy - h)])
        left = _poly([(cx - s, cy - h), (cx, cy), (cx, cy + s), (cx - s, cy + h)])
        right = _poly([(cx, cy), (cx + s, cy - h), (cx + s, cy + h), (cx, cy + s)])
        p.save()
        p.setPen(Qt.NoPen)
        if fill_alpha:
            p.setBrush(_a(acc, fill_alpha))
            p.drawPolygon(top)
            p.setBrush(_a(acc, int(fill_alpha * 0.55)))
            p.drawPolygon(left)
            p.setBrush(_a(acc, int(fill_alpha * 0.8)))
            p.drawPolygon(right)
        p.restore()
        p.save()
        if dashed:
            pen = QPen(ink, 2.2, Qt.DashLine)
            pen.setJoinStyle(Qt.RoundJoin)
            p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        outline = _poly([(cx, cy - s), (cx + s, cy - h), (cx + s, cy + h),
                         (cx, cy + s), (cx - s, cy + h), (cx - s, cy - h)])
        p.drawPolygon(outline)
        p.drawLine(QPointF(cx - s, cy - h), QPointF(cx, cy))
        p.drawLine(QPointF(cx + s, cy - h), QPointF(cx, cy))
        p.drawLine(QPointF(cx, cy), QPointF(cx, cy + s))
        p.restore()

    def _tree(p, ink, acc, cx, base, size=1.0, alpha=255, fill=0):
        col = _a(ink, alpha)
        p.save()
        pen = QPen(col, 3.0 * size)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.drawLine(QPointF(cx, base), QPointF(cx, base - 9 * size))
        pen.setWidthF(2.6 * size)
        pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(pen)
        p.setBrush(_a(acc, fill) if fill else QColor(0, 0, 0, 0))
        crown = QPainterPath()
        r = 8.5 * size
        cy = base - 9 * size - r * 0.8
        crown.addEllipse(QPointF(cx - r * 0.45, cy + r * 0.2), r * 0.7, r * 0.7)
        crown.addEllipse(QPointF(cx + r * 0.45, cy + r * 0.2), r * 0.7, r * 0.7)
        crown.addEllipse(QPointF(cx, cy - r * 0.35), r * 0.75, r * 0.75)
        crown = crown.simplified()
        p.drawPath(crown)
        p.restore()

    def proxy_create(p, ink, acc):
        # Detailed object (left, faint) → light box (right).
        _tree(p, ink, acc, 13, 38, 0.85, 255, fill=110)
        p.save()
        pen = QPen(acc, 2.6)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(pen)
        p.drawLine(QPointF(21, 13), QPointF(27, 13))
        p.drawPolyline(_poly([(24.5, 10.5), (27, 13), (24.5, 15.5)]))
        p.restore()
        _cube(p, ink, acc, 33, 29, 9.5)

    def proxy_show_originals(p, ink, acc):
        _tree(p, ink, acc, 24, 40, 1.35, 255, fill=130)

    def proxy_show_proxies(p, ink, acc):
        _tree(p, ink, acc, 24, 36, 1.0, 70)
        _cube(p, ink, acc, 24, 26, 13)

    def proxy_select_all(p, ink, acc):
        _cube(p, ink, acc, 14, 17, 7)
        _cube(p, ink, acc, 33, 17, 7)
        _cube(p, ink, acc, 14, 35, 7)
        # selection arrow on the fourth
        path = QPainterPath()
        x, y = 29, 26
        path.moveTo(x, y)
        path.lineTo(x, y + 17)
        path.lineTo(x + 4.6, y + 12.6)
        path.lineTo(x + 8, y + 19.5)
        path.lineTo(x + 10.8, y + 18.2)
        path.lineTo(x + 7.5, y + 11.3)
        path.lineTo(x + 13.5, y + 11.3)
        path.closeSubpath()
        p.save()
        p.setPen(QPen(QColor(255, 255, 255) if ink.lightness() < 128 else QColor(30, 30, 30), 1.6))
        p.setBrush(QBrush(ink))
        p.drawPath(path)
        p.restore()

    return {"create": proxy_create, "originals": proxy_show_originals, "proxies": proxy_show_proxies, "select": proxy_select_all}


def _pesi3d_toolbar(app, title, entries):
    """A toolbar of this plugin's own — one icon per command (PESI3D).

    ``entries`` = (icon key, text, tip, callable). The icons are drawn
    like IngeTrazo's own (views/icons.py: 48 px, ink = the palette's text
    colour, 3 px pen, the orange accent) and redrawn when the theme flips.
    The toolbar moves, floats and hides like the built-in ones (right-click
    on any toolbar); its place is kept by its objectName."""
    try:
        from PySide6.QtCore import QEvent, QObject, QSize, Qt
        from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPen, QPixmap
        from PySide6.QtWidgets import QApplication, QToolBar
    except Exception:  # noqa: BLE001 — no Qt, no toolbar
        return None
    win = getattr(app, "window", None)
    if win is None:
        return None
    draws = _pesi3d_icons()

    def make_icon(key):
        draw = draws.get(key)
        if draw is None:
            return QIcon()
        qa = QApplication.instance()
        ink = (QColor(qa.palette().windowText().color()) if qa is not None
               else QColor(40, 44, 52))
        pm = QPixmap(48, 48)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing, True)
        pen = QPen(ink, 3.0)
        pen.setJoinStyle(Qt.RoundJoin)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        try:
            draw(p, ink, QColor(243, 115, 41))
        finally:
            p.end()
        return QIcon(pm)

    name = f"pesi3d_{getattr(app, 'key', title)}"
    tb = None
    make = getattr(win, "_new_toolbar", None)     # the host's own builder
    if callable(make):
        try:
            tb = make(title, name)
        except Exception:  # noqa: BLE001
            tb = None
    if tb is None:
        tb = QToolBar(title, win)
        tb.setObjectName(name)
        tb.setMovable(True)
        tb.setFloatable(True)
        try:
            from views.icons import toolbar_icon_px
            px = int(toolbar_icon_px())
        except Exception:  # noqa: BLE001
            px = 24
        tb.setIconSize(QSize(px, px))
        tb.setToolButtonStyle(Qt.ToolButtonIconOnly)
        win.addToolBar(Qt.TopToolBarArea, tb)

    actions = []
    for key, text, tip, fn in entries:
        act = QAction(make_icon(key), text, tb)
        act.setToolTip(f"{text}\n{tip}" if tip else text)
        if tip:
            act.setStatusTip(tip)
        act.triggered.connect(lambda _c=False, f=fn: f())
        tb.addAction(act)
        actions.append((act, key))

    class _ThemeWatch(QObject):
        def eventFilter(self, obj, event):  # noqa: N802 — Qt override
            if event.type() in (QEvent.PaletteChange,
                                QEvent.ApplicationPaletteChange,
                                QEvent.StyleChange):
                for a, k in actions:
                    a.setIcon(make_icon(k))
            return False

    watch = _ThemeWatch(tb)
    tb.installEventFilter(watch)
    tb._pesi3d_watch = watch
    _pesi3d_place_later(win)
    return tb


def _pesi3d_place_later(win):
    """A toolbar the saved window layout does not know yet lands at the end
    of the top row, squeezed behind the built-in ones. Once the window is
    laid out, put new PESI3D toolbars on a row of their own under the
    built-in ones — only the first time each one appears; after that the
    user's own arrangement (saved with the window) wins. Every PESI3D
    plugin carries this code; the first one to get here does it for all."""
    if getattr(win, "_pesi3d_place_pending", False):
        return
    win._pesi3d_place_pending = True
    from PySide6.QtCore import QSettings, Qt, QTimer
    from PySide6.QtWidgets import QToolBar

    def place():
        win._pesi3d_place_pending = False
        try:
            st = QSettings()
            key = "plugins/pesi3d/placed_toolbars"
            placed = st.value(key) or []
            if isinstance(placed, str):
                placed = [placed]
            placed = list(placed)
            bars = [t for t in win.findChildren(QToolBar)
                    if t.objectName().startswith("pesi3d_")]
            new = [t for t in bars if t.objectName() not in placed]
            if not new:
                return
            fresh = not placed            # no PESI3D row yet → open one
            for i, t in enumerate(sorted(new, key=lambda t: t.objectName())):
                shown = not t.isHidden()
                win.removeToolBar(t)
                if fresh and i == 0:
                    win.addToolBarBreak(Qt.TopToolBarArea)
                win.addToolBar(Qt.TopToolBarArea, t)
                t.setVisible(shown)
            st.setValue(key, placed + [t.objectName() for t in new])
        except Exception:  # noqa: BLE001 — layout only, never break the app
            pass

    QTimer.singleShot(0, place)


def setup(app) -> None:
    """Extensions ▸ Proxies ▸ Create Proxies… / Show Originals / Show
    Proxies / Select All Proxies, and the matching right-click entries."""
    from PySide6.QtCore import QTimer

    def vp():
        return app.viewport

    sub = app.add_menu(_tr("Proxies"))
    entries = (
        ("Create Proxies…", lambda: open_dialog(vp()),
         "Replace the selected objects by light proxies; the originals go to .igz files."),
        ("Show Originals", lambda: show_originals(vp()),
         "Load the full geometry of the selected proxies (all when nothing is selected)."),
        ("Show Proxies", lambda: show_proxies(vp()),
         "Swap the selected originals back to proxies (all when nothing is selected)."),
        ("Select All Proxies", lambda: select_all_proxies(vp()), ""),
    )
    if sub is not None:
        for text, fn, tip in entries:
            a = sub.addAction(_tr(text))
            if tip:
                a.setStatusTip(_tr(tip))
            a.triggered.connect(lambda _c=False, f=fn: f())
    else:  # pragma: no cover - no Extensions menu
        for text, fn, tip in entries:
            app.add_menu_action(_tr(text), fn, tip=_tr(tip) if tip else None)

    def context(menu, selection) -> None:
        gs = selected_groups(app.viewport.scene)
        if not gs:
            return
        menu.addSeparator()
        plain = [g for g in gs if _can_proxy(g)]
        if plain:
            a = menu.addAction(_tr("Create Proxies…"))
            a.triggered.connect(
                lambda _c=False: QTimer.singleShot(0, lambda: open_dialog(vp())))
        states = {proxy_info(g).get("state") for g in gs if proxy_info(g)}
        if "proxy" in states:
            a = menu.addAction(_tr("Show Originals"))
            a.triggered.connect(
                lambda _c=False: QTimer.singleShot(0, lambda: show_originals(vp())))
        if "original" in states:
            a = menu.addAction(_tr("Show Proxies"))
            a.triggered.connect(
                lambda _c=False: QTimer.singleShot(0, lambda: show_proxies(vp())))

    app.add_context_menu(context)

    _pesi3d_toolbar(app, _tr("Proxies"), [
        (key, _tr(text), _tr(tip) if tip else "", fn)
        for key, (text, fn, tip) in zip(
            ("create", "originals", "proxies", "select"), entries)
    ])
