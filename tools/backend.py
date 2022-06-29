import sys

from setuptools import build_meta as builder


def get_requires_for_build_sdist(config_settings=None):
    return builder.get_requires_for_build_sdist(config_settings=None)

def build_sdist(sdist_directory, config_settings=None):
    print("Reached integration point for custom behaviour via ", config_settings, file=sys.stderr)
    return builder.build_sdist(sdist_directory, config_settings=None)

def get_requires_for_build_wheel(config_settings=None):
    return builder.get_requires_for_build_wheel(config_settings)

def prepare_metadata_for_build_wheel(metadata_directory, config_settings=None):
    return builder.prepare_metadata_for_build_wheel(metadata_directory, config_settings=None)

def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
    return builder.build_wheel(wheel_directory, config_settings=None, metadata_directory=None)
