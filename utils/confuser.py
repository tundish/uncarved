#! /usr/bin/env python
# encoding: utf-8

import argparse
import configparser
import itertools
import pathlib
import re
import sys
import unittest


"""
This utility applies configparser substitution patterns as a preprocessor
for, eg: TOML files.

Usage:

    python -m utils.confuser design/taxonomy.toml | \
    python -m utils.toml2dot > design/taxonomy.dot

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

    @property
    def literals(self):
        d = self.defaults()
        return {k: dict(d, **s) for k, s in self.sections.items()}

    def dumps(self):
        rv = [
            itertools.chain(
                (f"[{l}]",),
                (f"{k} = {v}" for k, v in s.items())
            )
            for l, s in self.literals.items()
        ]
        return "\n".join(j for i in rv for j in i)


class TestConf(unittest.TestCase):

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
        self.assertEqual({"tag": "2"}, dict(conf.sections["A.B.C"]))

    def test_get(self):
        text = """
        [A.B.C]
        tag = 1
        """
        conf = Conf.loads(text)
        self.assertEqual({"tag": "1"}, dict(conf.sections["A.B.C"]))

    def test_defaults(self):
        text = """
        [DEFAULT]
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
        [DEFAULT]
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

    def test_literals(self):
        text = """
        [DEFAULT]
        flavour = vanilla
        [A]
        flavour = strawberry
        [B]
        flavour = ${A:flavour}
        """
        conf = Conf.loads(text)

    def test_dumps_simple(self):
        text = """
        [A]
        [B]
        """
        conf = Conf.loads(text)
        rv = conf.dumps()
        self.assertEqual("[A]\n[B]", rv)

    def test_dumps_substitution(self):
        text = """
        [DEFAULT]
        flavour = vanilla
        [A]
        flavour = strawberry
        [B]
        flavour = ${A:flavour}
        """
        conf = Conf.loads(text)
        rv = conf.dumps()
        self.assertNotIn("$", rv)

    def test_dumps_quotes(self):
        text = """
        [A]
        label = "day/night cycles"
        [B]
        color = {"r" = 0, "g" = 0, "b" = 0}
        """
        conf = Conf.loads(text)
        rv = conf.dumps()
        self.assertEqual(8, rv.count('"'))


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
