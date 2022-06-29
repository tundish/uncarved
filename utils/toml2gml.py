import argparse
import enum
import pathlib
import sys
from textwrap import dedent
import unittest

import toml

class Aliases(enum.Enum):

    graphs = ["graphs"]
    labels = ["labels"]
    source = ["source"]
    target = ["target"]
    weight = ["weight"]


class Model:

    @classmethod
    def loads(cls, text):
        data = toml.loads(text)
        return cls(data)

    @staticmethod
    def is_arc(table):
        return any(
            k in i.value
            for k in table
            for i in (Aliases.source, Aliases.target)
        )

    def __init__(self, data):
        self.data = data

    @property
    def graphs(self):
        return {
            i for table, k, v in self.walk()
            for i in (v if isinstance(v, list) else [v])
            if k in Aliases.graphs.value
        }

    def walk(self, node=None, parent=None):
        node = node or self.data
        for k, v in node.items():
            if v and isinstance(v, dict):
                yield from self.walk(node=v, parent=node)
            else:
                yield parent, k, v

    def table(self, path):
        keys = path.split(".")
        data = self.data
        for k in keys:
            data = data[k]
        return data

    def to_dot(self):
        a = 1
        return dedent(f"""
        strict digraph {{
        {a}
        }}
        """)


class TestLoad(unittest.TestCase):

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
    print(model.data)


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
