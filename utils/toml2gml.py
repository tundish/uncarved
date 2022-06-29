import argparse
import sys
import unittest

import toml


class Model:

    @classmethod
    def loads(cls, text):
        data = toml.loads(text)
        return cls(data)

    def __init__(self, data):
        self.data = data

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


class TestLoad(unittest.TestCase):

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


def main(args):
    unittest.main()


def parser():
    rv = argparse.ArgumentParser(__doc__)
    return rv


def run():
    p = parser()
    args = p.parse_args()
    rv = main(args)
    sys.exit(rv)


if __name__ == "__main__":
    run()
