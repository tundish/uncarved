import argparse
from collections import namedtuple
import dataclasses
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
    ["source", "target", "label", "weight"],
    defaults=(1, )
)


@dataclasses.dataclass
class Node:

    label: str
    weight: float = 1.0
    arcs: list[Arc] = dataclasses.field(default_factory=list)


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

    def walk(self, node=None, parent=None):
        node = node or self.data
        for k, v in node.items():
            if v and isinstance(v, dict):
                yield from self.walk(node=v, parent=node)
            else:
                yield parent, k, v

    @property
    def tables(self):
        return self.table_finder.findall(self.text)

    def table(self, path):
        keys = path.split(".")
        data = self.data
        for k in keys:
            data = data[k]
        return data

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

    def to_dot(self, directed=True):
        arcs = [f"{parent} -> {node}" for parent, node in self.arcs()]

        a = "\n".join(arcs)
        return dedent(f"""
        strict digraph {{
        {a}
        }}
        """)


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
        self.assertEqual(["A", "A.B.C", "D"], model.tables)

    def test_table(self):
        text = """
        [A]
        tag = 1

        [A.B.C]
        tag = 2

        [  D ]
        """
        model = Model.loads(text)
        self.assertEqual(1, model.table("A").get("tag"))
        self.assertEqual({"tag": 2}, model.table("A.B.C"))

    def test_get(self):
        text = """
        [A.B.C]
        tag = 1
        """
        model = Model.loads(text)
        self.assertEqual({"tag": 1}, model.table("A.B.C"))

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
        node = Node(label="test node")
        self.assertEqual(1, node.weight)
        self.assertIsInstance(node.weight, float)
        self.assertEqual([], node.arcs)


def main(args):
    if args.test:
        suite = unittest.defaultTestLoader.loadTestsFromName("__main__")
        unittest.TextTestRunner().run(suite)
        return 0
    else:
        if not args.input:
            text = sys.stdin.read()
        else:
            text = args.input.read_text()

    model = Model.loads(text)
    print(model.to_dot())


def parser():
    rv = argparse.ArgumentParser(__doc__)
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