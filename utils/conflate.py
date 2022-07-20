#! /usr/bin/env python
# encoding: utf-8

import argparse
import configparser
import pathlib
import re
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
        self.SECTCRE = re.compile("\[\s*(?P<header>\S+)\s*\]")

    @property
    def sections(self):
        return {k: v for k, v in self.items() if k != self.default_section}


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
        self.assertEqual("1", conf.sections["A"].get("tag"))
        self.assertEqual({"tag": 2}, conf.sections["A.B.C"])

    def test_get(self):
        text = """
        [A.B.C]
        tag = 1
        """
        conf = Conf.loads(text)
        self.assertEqual({"tag": 1}, conf.sections["A.B.C"])

    def test_defaults(self):
        text = """
        [DEFAULTS]
        flavour = vanilla
        [A]
        [B]
        flavour = strawberry
        """
        conf = Conf.loads(text)
        self.assertEqual("vanilla", conf.sections["A"].get("flavour"))
        self.assertEqual("strawberry", conf.sections["B"].get("flavour"))

    def test_substitution(self):
        text = """
        [DEFAULTS]
        flavour = vanilla
        [A]
        flavour = strawberry
        [B]
        flavour = ${A:flavour}
        """
        conf = Conf.loads(text)
        self.assertEqual("strawberry", conf.sections["A"].get("flavour"))
        self.assertEqual("strawberry", conf.sections["B"].get("flavour"))

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
