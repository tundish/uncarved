import argparse
from collections import namedtuple
import dataclasses
import functools
import pathlib
import re
import sys
from textwrap import dedent
import unittest

import toml

"""
python -m utils.toml2dot mindmap.toml > mindmap.dot
dot -Tsvg mindmap.dot > mindmap.svg

"""

Arc = namedtuple(
    "Arc",
    ["label", "node", "target", "source", "weight"],
    defaults=(None, 1.0)
)


@dataclasses.dataclass(eq=False)
class Node:

    name: str

    label: str = None
    weight: float = 1.0
    arcs: list[Arc] = dataclasses.field(default_factory=list)
    data: dict = None
    parent: object = None

    def __post_init__(self):
        self.label = self.label or self.name


class Model:

    @classmethod
    def loads(cls, text):
        data = toml.loads(text)
        return cls(text, data)

    @staticmethod
    def is_arc(table):
        return set(table.keys()).intersection({"source", "target"})

    def __init__(self, text, data):
        self.text = text
        self.data = data
        self.table_finder = re.compile("\[\s*([\.\w]+)\s*\]")

    @property
    def graphs(self):
        return {
            i for table, k, v in self.walk()
            for i in (v if isinstance(v, list) else [v])
            if k == "graphs"
        }

    def walk(self, data=None, parent=None):
        data = data or self.data
        for k, v in data.items():
            if v and isinstance(v, dict):
                yield from self.walk(data=v, parent=data)
            else:
                yield parent, k, v

    @property
    @functools.cache
    def tables(self):
        rv = {}
        for path in self.table_finder.findall(self.text):
            keys = path.split(".")
            data = self.data
            for k in keys:
                data = data[k]
            rv[path] = data
        return rv

    @property
    @functools.cache
    def nodes(self):
        rv = {}
        arcs = {}
        fields = {i.name for i in dataclasses.fields(Node)}
        for name, table in self.tables.items():
            if self.is_arc(table):
                arcs[name] = table
                continue

            node = Node(name, **{k: v for k, v in table.items() if k in fields})
            node.data = table
            if "." in name:
                paths = name.split(".")
                for gen in range(1, len(paths)):
                    last = ".".join(paths[:-gen])
                    if last in self.tables:
                        node.parent = last

            rv[name] = node

        for name, table in arcs.items():
            parent, dot, label = name.rpartition(".")
            arc = Arc(
                table.get("label", label),
                node=parent or None,
                target=table.get("target"),
                weight=table.get("weight", 1.0)
            )
            try:
                rv[parent].arcs.append(arc)
            except AttributeError:
                print(
                    "Arc '", name, "' expects a Node for '", parent, "'.",
                    sep="", file=sys.stderr
                )
            except KeyError:
                print(
                    "No Node '", parent, "' for Arc '", name, "'.",
                    sep="", file=sys.stderr
                )

        return rv

    @functools.cache
    def children(self, name):
        return [
            k for k, v in self.nodes.items()
            if k != name and k.startswith(name)
        ]

    def subgraphs(self, parents=None):
        parents = parents or [v for v in self.nodes.values() if not v.parent]
        for p in parents:
            yield p
            children = [self.nodes[c] for c in self.children(p.name)]
            if children:
                yield from self.subgraphs(children)
                yield None

    def arcs(self):
        links = [
            (".".join(name.split(".")[:-1]), name)
            for name in self.tables if "." in name
        ]
        for parent, name in links:
            p = self.table(parent)
            t = self.table(name)
            if parent != name:
                if self.is_arc(t):
                    pass
                else:
                    yield p.get("label", parent), t.get("label", name)

    def to_dot(self, name="model", label=None, directed=True, strict=True):
        label = label or name
        arc_style = "->" if directed else "--"

        yield f"{'strict ' if strict else ''}{'digraph' if directed else 'graph'} {name} {{"
        yield f'    label="{label}"'
        for node in self.subgraphs():
            if node is None:
                yield ""
                yield "}"
            elif self.children(node.name):
                node_name = node.name.lower()
                yield ""
                yield f"subgraph cluster_{node_name} {{"
                yield f'    label="{node.label}"'
                yield f"    weight={node.weight:.2f}"
                yield ""
            else:
                node_hash = hash(node)
                yield f'{node_hash} [label="{node.label}", weight={node.weight:.02f}]'

        yield ""

        for node in self.nodes.values():
            node_hash = hash(node)
            for arc in node.arcs:
                target_hash = hash(self.nodes[arc.target])
                yield (
                    f"{node_hash} {arc_style} {target_hash}"
                    f' [label="{arc.label}", weight={arc.weight:.02f}]'
                )
        yield ""
        yield "}"


class TestLoad(unittest.TestCase):

    def test_tables(self):
        text = """
        [A]
        tag = 1

        [A.B.C]
        tag = 1

        [  D ]
        """
        model = Model.loads(text)
        self.assertEqual(["A", "A.B.C", "D"], list(model.tables.keys()))

    def test_table(self):
        text = """
        [A]
        tag = 1

        [A.B.C]
        tag = 2

        [  D ]
        """
        model = Model.loads(text)
        self.assertEqual(1, model.tables["A"].get("tag"))
        self.assertEqual({"tag": 2}, model.tables["A.B.C"])

    def test_get(self):
        text = """
        [A.B.C]
        tag = 1
        """
        model = Model.loads(text)
        self.assertEqual({"tag": 1}, model.tables["A.B.C"])

    def test_graphs_unique(self):
        text = """
        [A]
        graphs = ["a", "b"]
        [B]
        [C]
        graphs = ["a"]
        """
        model = Model.loads(text)
        self.assertEqual({"a", "b"}, model.graphs)
        for i in ("A", "B", "C"):
            with self.subTest(i=i):
                self.assertFalse(model.is_arc(model.data[i]))

    def test_graphs_sublevels(self):
        text = """
        [A]
        graphs = ["a"]
        [A.B]
        graphs = ["b"]
        """
        model = Model.loads(text)
        self.assertEqual({"a", "b"}, model.graphs)

    def test_loads(self):
        text = """
        [A]
        [B]
        """
        model = Model.loads(text)
        self.assertIsInstance(model, Model)

    def test_dumps(self):
        text = """
        [A]
        [B]
        """
        model = Model.loads(text)
        self.assertIsInstance(model, Model)


class TestNode(unittest.TestCase):

    def test_node_defaults(self):
        self.assertRaises(TypeError, Node)
        node = Node(name="test node")
        self.assertEqual("test node", node.label)
        self.assertEqual(1, node.weight)
        self.assertIsInstance(node.weight, float)
        self.assertEqual([], node.arcs)
        self.assertTrue(hash(node))

    def test_node_parent_root(self):
        text = """
        [A]
        [B]
        """
        model = Model.loads(text)
        self.assertEqual(2, len(model.nodes))
        self.assertEqual("A", model.nodes["A"].label)
        self.assertTrue(all(i.parent is None for i in model.nodes.values()))
        self.assertTrue(all(isinstance(i.data, dict) for i in model.nodes.values()))

    def test_node_parent_tree(self):
        text = """
        [A]
        [A.B]
        [C]
        [C.B]
        """
        model = Model.loads(text)
        self.assertEqual(4, len(model.nodes))
        self.assertEqual("A", model.nodes["A"].label)
        self.assertEqual("A", model.nodes["A.B"].parent)
        self.assertEqual("C", model.nodes["C.B"].parent)

    def test_node_parent_gap(self):
        text = """
        [A]
        [C.B.C]
        [C]
        [A.B.C]
        """
        model = Model.loads(text)
        self.assertEqual(4, len(model.nodes))
        self.assertEqual("A", model.nodes["A.B.C"].parent)
        self.assertEqual("C", model.nodes["C.B.C"].parent)

    def test_node_children(self):
        text = """
        [A]
        [C.B.C]
        [C]
        [A.B.C]
        """
        model = Model.loads(text)
        self.assertEqual(4, len(model.nodes))
        self.assertEqual(["A.B.C"], model.children("A"))
        self.assertEqual("C", model.nodes["C.B.C"].parent)

    def test_arc_labels(self):
        text = """
        [A.B]
        [A.B.c]
        target = "C"
        [C]
        [C.ab]
        target = "A.B"
        """
        model = Model.loads(text)
        self.assertEqual(2, len(model.nodes))
        self.assertEqual(1, len(model.nodes["A.B"].arcs))
        self.assertEqual(1, len(model.nodes["C"].arcs))

    def test_node_to_dot(self):
        text = """
        [A]
        [C.B.C]
        [C]
        [A.B.C]
        """
        model = Model.loads(text)
        self.assertEqual(4, len(model.nodes))
        self.assertEqual("C", model.nodes["C.B.C"].parent)


def main(args):
    if args.test:
        suite = unittest.defaultTestLoader.loadTestsFromName("__main__")
        unittest.TextTestRunner().run(suite)
        return 0
    else:
        if not args.input:
            text = sys.stdin.read()
            name = ""
        else:
            text = args.input.read_text()
            name = args.input.stem

    model = Model.loads(text)
    writer = model.to_dot(name=name, label=args.label, directed=args.directed)
    print("\n".join(writer), file=sys.stdout)


def parser():
    rv = argparse.ArgumentParser(__doc__)
    rv.add_argument(
        "--label", default=None,
        help="Set a label for the graph."
    )
    rv.add_argument(
        "--directed", default=False, action="store_true",
        help="Make arcs directional."
    )
    rv.add_argument(
        "--test", default=False, action="store_true",
        help="Run unit tests."
    )
    rv.add_argument(
        "input", nargs="?", type=pathlib.Path,
        help="Set input file."
    )
    return rv


def run():
    p = parser()
    args = p.parse_args()
    rv = main(args)
    sys.exit(rv)


if __name__ == "__main__":
    run()
