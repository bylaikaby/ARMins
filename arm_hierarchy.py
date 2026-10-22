"""Resolve ARM regions from the provider's explicit Level_1..Level_6 table.

Version: 0.7.0 (local/unreleased)
Last updated: 2026-10-22
Change history: CHANGELOG.md
Status: experimental

The CSV remains an external input. This module uses only the Python standard
library and never infers parentage from row or numeric index ordering.
"""

import csv
import hashlib
import json
import re
from pathlib import Path


VERSION = "0.7.0 (local/unreleased)"
LEVELS = tuple(range(1, 7))
SIDE_PREFIXES = {"CL": ("L", "C"), "CR": ("R", "C"),
                 "SL": ("L", "S"), "SR": ("R", "S")}
REQUIRED_COLUMNS = tuple(
    column
    for level in LEVELS
    for column in (f"Level_{level}", f"Level_{level}_abbr", f"Level_{level}_index")
)


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _index(value, row_number, level):
    text = (value or "").strip()
    if not re.fullmatch(r"[0-9]+", text) or int(text) <= 0:
        raise ValueError(f"row {row_number}: Level_{level}_index must be a positive integer, got {text!r}")
    return int(text)


def _side_namespace(abbreviation, row_number, level):
    text = (abbreviation or "").strip()
    prefix = text.split("_", 1)[0]
    if prefix not in SIDE_PREFIXES or "_" not in text or not text.split("_", 1)[1]:
        raise ValueError(f"row {row_number}: Level_{level}_abbr has unsupported hemisphere/namespace prefix {text!r}")
    return SIDE_PREFIXES[prefix]


def _remove_prefix(value, prefix):
    return value[len(prefix) + 1:] if value.startswith(prefix + "_") else value


class ArmHierarchy:
    """Strict resolver for an explicit bilateral six-level ARM key table."""

    def __init__(self, path, rows, source_sha256):
        self.path = Path(path).expanduser().resolve()
        self.source_sha256 = source_sha256.upper()
        self.nodes = {}
        self._parse(rows)

    @classmethod
    def from_file(cls, path):
        path = Path(path).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f"ARM hierarchy table not found: {path}")
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            columns = set(reader.fieldnames or ())
            missing = [name for name in REQUIRED_COLUMNS if name not in columns]
            if missing:
                flat = {"Index", "Abbreviation", "First_Level", "Last_Level"}.issubset(columns)
                if flat:
                    raise ValueError(
                        "flat First_Level/Last_Level key cannot resolve explicit parent paths; "
                        "use ARM_key_table.csv with Level_1..Level_6 columns"
                    )
                raise ValueError(f"ARM hierarchy table is missing explicit columns: {missing}")
            rows = list(reader)
        if not rows:
            raise ValueError("ARM hierarchy table contains no data rows")
        return cls(path, rows, _sha256(path))

    def _parse(self, rows):
        for row_number, row in enumerate(rows, start=2):
            prefix_path = []
            semantic_path = []
            row_side = None
            row_namespace = None
            row_nodes = []
            previous_blank = False
            wm_gm = (row.get("WM/GM") or "").strip()
            for level in LEVELS:
                full = (row.get(f"Level_{level}") or "").strip()
                abbr = (row.get(f"Level_{level}_abbr") or "").strip()
                raw_index = (row.get(f"Level_{level}_index") or "").strip()
                if not full and not abbr and not raw_index:
                    previous_blank = True
                    continue
                if previous_blank or not full or not abbr or not raw_index:
                    raise ValueError(f"row {row_number}: hierarchy levels must be contiguous and have full name, abbreviation, and index")
                index = _index(raw_index, row_number, level)
                side, namespace = _side_namespace(abbr, row_number, level)
                if row_side is None:
                    row_side, row_namespace = side, namespace
                elif (side, namespace) != (row_side, row_namespace):
                    raise ValueError(f"row {row_number}: mixed hemisphere or cortical/subcortical namespace in path")
                prefix = abbr.split("_", 1)[0]
                norm_abbr = _remove_prefix(abbr, prefix)
                norm_full = _remove_prefix(full, prefix)
                prefix_path.append((namespace, index, norm_abbr, norm_full))
                semantic_path.append((namespace, norm_abbr, norm_full))
                path_key = tuple(prefix_path)
                mirror_key = tuple(semantic_path)
                key = (side, namespace, level, index)
                node = {
                    "side": side,
                    "namespace": namespace,
                    "level": level,
                    "index": index,
                    "abbreviation": abbr,
                    "full_name": full,
                    "wm_gm": wm_gm,
                    "path_key": path_key,
                    "mirror_key": mirror_key,
                }
                previous = self.nodes.get(key)
                if previous is not None:
                    stable = (previous["namespace"], previous["abbreviation"],
                              previous["full_name"], previous["path_key"], previous["mirror_key"])
                    current = (namespace, abbr, full, path_key, mirror_key)
                    if stable != current:
                        raise ValueError(f"row {row_number}: conflicting hierarchy identity/path for {side} L{level} index {index}")
                else:
                    self.nodes[key] = node
                row_nodes.append(node)
            if len(row_nodes) != 6:
                raise ValueError(f"row {row_number}: expected six explicit hierarchy levels, found {len(row_nodes)}")

        if not self.nodes:
            raise ValueError("ARM hierarchy table has no valid nodes")
        self._node_list = sorted(
            self.nodes.values(),
            key=lambda item: (item["level"], item["side"], item["index"], item["abbreviation"]),
        )

    def search(self, query, side=None, level=None):
        """Return individual exact-index or case-insensitive name candidates."""
        query = str(query).strip()
        if not query:
            raise ValueError("search query cannot be empty")
        side = side.upper() if side else None
        if side not in (None, "L", "R"):
            raise ValueError("side must be L or R")
        if level is not None and int(level) not in LEVELS:
            raise ValueError("level filter must be between 1 and 6")
        numeric = bool(re.fullmatch(r"[0-9]+", query))
        folded = query.casefold()
        matches = []
        for node in self._node_list:
            if side and node["side"] != side:
                continue
            if level is not None and node["level"] != int(level):
                continue
            if numeric:
                if node["index"] != int(query):
                    continue
            elif (folded not in node["abbreviation"].casefold()
                  and folded not in node["full_name"].casefold()):
                continue
            profile = self._descendant_leaf_nodes(node)
            matches.append({
                "side": node["side"],
                "namespace": node["namespace"],
                "level": node["level"],
                "index": node["index"],
                "abbreviation": node["abbreviation"],
                "full_name": node["full_name"],
                "descendant_count": len(profile),
                "descendant_ids": [leaf["index"] for leaf in profile],
                "path": [
                    {"level": item["level"], "index": item["index"],
                     "abbreviation": item["abbreviation"], "full_name": item["full_name"]}
                    for item in self._path_nodes(node)
                ],
            })
        return matches

    def _path_nodes(self, node):
        result = []
        for level in range(1, node["level"] + 1):
            candidates = [item for item in self._node_list
                          if item["side"] == node["side"] and item["level"] == level
                          and item["path_key"] == node["path_key"][:level]]
            if len(candidates) != 1:
                raise ValueError(f"ambiguous path identity at {node['side']} L{level} for {node['abbreviation']}")
            result.append(candidates[0])
        return result

    def _descendant_leaf_nodes(self, node):
        prefix = node["path_key"]
        leaves = [item for item in self._node_list
                  if item["side"] == node["side"] and item["level"] == 6
                  and item["path_key"][:node["level"]] == prefix]
        return sorted(leaves, key=lambda item: (item["index"], item["abbreviation"]))

    def _find_node(self, index, level, side, namespace=None):
        matches = [node for key, node in self.nodes.items()
                   if key[0] == side.upper() and key[2] == int(level) and key[3] == int(index)
                   and (namespace is None or key[1] == str(namespace).upper())]
        if not matches:
            raise ValueError(f"no ARM hierarchy node for {side.upper()} L{level} index {index}")
        if len(matches) != 1:
            raise ValueError(f"ARM hierarchy index {index} is ambiguous across namespaces; select its namespace")
        return matches[0]

    def _counterpart(self, node):
        opposite = "R" if node["side"] == "L" else "L"
        matches = [item for item in self._node_list
                   if item["side"] == opposite and item["level"] == node["level"]
                   and item["mirror_key"] == node["mirror_key"]]
        if len(matches) != 1:
            raise ValueError(
                f"opposite-side counterpart for {node['side']} L{node['level']} index {node['index']} "
                f"is {'missing' if not matches else 'ambiguous'} in explicit hierarchy identities"
            )
        return matches[0]

    def profile_for(self, index, level, side, namespace=None):
        """Resolve bilateral leaf sets and a bijective map from explicit table identities."""
        if int(level) not in LEVELS:
            raise ValueError("selected hierarchy level must be between 1 and 6")
        side = str(side).upper()
        if side not in ("L", "R"):
            raise ValueError("side must be L or R")
        selected = self._find_node(index, level, side, namespace=namespace)
        counterpart = self._counterpart(selected)
        left_node, right_node = (selected, counterpart) if side == "L" else (counterpart, selected)
        left_leaves = self._descendant_leaf_nodes(left_node)
        right_leaves = self._descendant_leaf_nodes(right_node)
        if not left_leaves or not right_leaves:
            raise ValueError("selected ARM hierarchy node has no descendant L6 leaves on one or both sides")

        left_by_path = {}
        for leaf in left_leaves:
            left_by_path.setdefault(leaf["mirror_key"], []).append(leaf)
        right_by_path = {}
        for leaf in right_leaves:
            right_by_path.setdefault(leaf["mirror_key"], []).append(leaf)
        if set(left_by_path) != set(right_by_path):
            raise ValueError("opposite-side L6 leaves do not have matching explicit hierarchy identities")

        pairs = []
        for path_key in sorted(left_by_path, key=lambda key: left_by_path[key][0]["index"]):
            left_matches, right_matches = left_by_path[path_key], right_by_path[path_key]
            if len(left_matches) != 1 or len(right_matches) != 1:
                raise ValueError("opposite-side L6 hierarchy identity is ambiguous; refusing mirror mapping")
            left, right = left_matches[0], right_matches[0]
            pairs.append({
                "left_id": left["index"], "right_id": right["index"],
                "left_abbreviation": left["abbreviation"],
                "left_full_name": left["full_name"],
                "right_abbreviation": right["abbreviation"],
                "right_full_name": right["full_name"],
            })
        if (len({item["left_id"] for item in pairs}) != len(pairs)
                or len({item["right_id"] for item in pairs}) != len(pairs)):
            raise ValueError("opposite-side L6 mapping is not bijective")

        profile = {
            "schema": "armins.region-profile.v1",
            "source_path": str(self.path),
            "source_sha256": self.source_sha256,
            "working_side": side,
            "selected": self._public_node(selected),
            "counterpart": self._public_node(counterpart),
            "left_node": self._public_node(left_node),
            "right_node": self._public_node(right_node),
            "left_leaves": [self._public_node(item) for item in left_leaves],
            "right_leaves": [self._public_node(item) for item in right_leaves],
            "pair_map": pairs,
        }
        # A paired region has one stable identity regardless of which side the
        # operator chose for editing. The selected side remains explicit data.
        identity = {
            "schema": profile["schema"],
            "source_sha256": profile["source_sha256"],
            "left_node": profile["left_node"],
            "right_node": profile["right_node"],
            "left_leaves": profile["left_leaves"],
            "right_leaves": profile["right_leaves"],
            "pair_map": profile["pair_map"],
        }
        profile["profile_hash"] = hashlib.sha256(
            json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest().upper()
        return profile

    @staticmethod
    def _public_node(node):
        return {key: node[key] for key in
                ("side", "namespace", "level", "index", "abbreviation", "full_name")}

    def resolve(self, query, side, level=None, namespace=None):
        """Resolve one exact ID/abbreviation selection; never unions text hits."""
        query = str(query).strip()
        side = str(side).upper()
        if not query:
            raise ValueError("region query cannot be empty; use search to find candidates")
        if level is None:
            raise ValueError("region level is required; use search to choose a level")
        if re.fullmatch(r"[0-9]+", query):
            return self.profile_for(int(query), level, side, namespace=namespace)
        folded = query.casefold()
        matches = [node for node in self._node_list
                   if node["side"] == side and node["level"] == int(level)
                   and node["abbreviation"].casefold() == folded
                   and (namespace is None or node["namespace"] == str(namespace).upper())]
        if len(matches) != 1:
            if not matches:
                raise ValueError("no exact abbreviation match; use search to find candidates")
            labels = [f"namespace {item['namespace']} index {item['index']}"
                      for item in matches[:12]]
            raise ValueError(f"abbreviation is ambiguous; select an explicit result: {labels}")
        match = matches[0]
        return self.profile_for(match["index"], match["level"], side, namespace=match["namespace"])
