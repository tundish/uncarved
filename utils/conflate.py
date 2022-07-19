#! /usr/bin/env python
# encoding: utf-8

import argparse
import configparser
import pathlib
import sys
from textwrap import dedent
import unittest


"""
This utility translates a graph defined in a TOML file to an equivalent .dot

Usage:

    python -m utils.toml2dot --label "Taxonomy MIDGET CABS 2P" --digraph \
        design/taxonomy.toml > design/taxonomy.dot

    dot -Tsvg design/taxonomy.dot > design/taxonomy.svg

"""

class Conf(configparser.ConfigParser):

    @classmethod
    def loads(cls, text, **kwargs):
        rv = cls(**kwargs)
        rv.read_string(text)
        return rv

    def __init__(self, *args, interpolation=None, **kwargs):
        interpolation = interpolation or configparser.ExtendedInterpolation()
        super().__init__(interpolation=interpolation, **kwargs)


class TestLoad(unittest.TestCase):

    def test_sections(self):
        text = """
        [A]
        tag = 1

        [A.B.C]
        tag = 1

        [  D ]
        """
        conf = Conf.loads(text)
        self.assertEqual(["A", "A.B.C", "D"], list(conf.sections.keys()))

    def test_table(self):
        text = """
        [A]
        tag = 1

        [A.B.C]
        tag = 2

        [  D ]
        """
        conf = Conf.loads(text)
        self.assertEqual(1, conf.sections["A"].get("tag"))
        self.assertEqual({"tag": 2}, conf.sections["A.B.C"])

    def test_get(self):
        text = """
        [A.B.C]
        tag = 1
        """
        conf = Conf.loads(text)
        self.assertEqual({"tag": 1}, conf.sections["A.B.C"])

    def test_graphs_unique(self):
        text = """
        [A]
        graphs = ["a", "b"]
        [B]
        [C]
        graphs = ["a"]
        """
        conf = Conf.loads(text)
        self.assertEqual({"a", "b"}, conf.graphs)
        for i in ("A", "B", "C"):
            with self.subTest(i=i):
                self.assertFalse(conf.is_arc(conf.data[i]))

    def test_graphs_sublevels(self):
        text = """
        [A]
        graphs = ["a"]
        [A.B]
        graphs = ["b"]
        """
        conf = Conf.loads(text)
        self.assertEqual({"a", "b"}, conf.graphs)

    def test_loads(self):
        text = """
        [A]
        [B]
        """
        conf = Conf.loads(text)
        self.assertIsInstance(conf, Conf)

    def test_dumps(self):
        text = """
        [A]
        [B]
        """
        conf = Conf.loads(text)
        self.assertIsInstance(conf, Conf)


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
        conf = Conf.loads(text)
        self.assertEqual(2, len(conf.nodes))
        self.assertEqual("A", conf.nodes["A"].label)
        self.assertTrue(all(i.parent is None for i in conf.nodes.values()))
        self.assertTrue(all(isinstance(i.data, dict) for i in conf.nodes.values()))

    def test_node_parent_tree(self):
        text = """
        [A]
        [A.B]
        [C]
        [C.B]
        """
        conf = Conf.loads(text)
        self.assertEqual(4, len(conf.nodes))
        self.assertEqual("A", conf.nodes["A"].label)
        self.assertEqual("A", conf.nodes["A.B"].parent)
        self.assertEqual("C", conf.nodes["C.B"].parent)

    def test_node_parent_gap(self):
        text = """
        [A]
        [C.B.C]
        [C]
        [A.B.C]
        """
        conf = Conf.loads(text)
        self.assertEqual(4, len(conf.nodes))
        self.assertEqual("A", conf.nodes["A.B.C"].parent)
        self.assertEqual("C", conf.nodes["C.B.C"].parent)

    def test_node_children(self):
        text = """
        [A]
        [C.B.C]
        [C]
        [A.B.C]
        """
        conf = Conf.loads(text)
        self.assertEqual(4, len(conf.nodes))
        self.assertEqual(["A.B.C"], conf.children("A"))
        self.assertEqual("C", conf.nodes["C.B.C"].parent)

    def test_node_rank(self):
        text = """
        [A]
        [C.B.C]
        [C]
        [A.B.C]
        """
        conf = Conf.loads(text)
        self.assertEqual(0, conf.nodes["A"].rank)
        self.assertEqual(2, conf.nodes["A.B.C"].rank)
        print(conf.children("A"))

    def test_arc_labels(self):
        text = """
        [A.B]
        [A.B.c]
        target = "C"
        [C]
        [C.ab]
        target = "A.B"
        """
        conf = Conf.loads(text)
        self.assertEqual(2, len(conf.nodes))
        self.assertEqual(1, len(conf.nodes["A.B"].arcs))
        self.assertEqual(1, len(conf.nodes["C"].arcs))

    def test_node_to_dot(self):
        text = """
        [A]
        [C.B.C]
        [C]
        [A.B.C]
        """
        conf = Conf.loads(text)
        self.assertEqual(4, len(conf.nodes))
        self.assertEqual("C", conf.nodes["C.B.C"].parent)


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

    writer = ()
    print(*list(writer), sep="\n", file=sys.stdout)


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
