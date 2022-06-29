import argparse
import sys
import unittest

class TestLoad(unittest.TestCase):

    def test_levels(self):
        self.assertFalse("Poo")

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
