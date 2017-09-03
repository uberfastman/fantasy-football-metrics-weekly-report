import os
import sys

from distribute_setup import use_setuptools
use_setuptools()

from setuptools import setup, find_packages

README = open('README.rst').read()
VERSION = "0.7.7"

setup(name='yql',
    version=VERSION,
    description='Python YQL - client library for YQL (Yahoo Query Language)',
    long_description=README,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Programming Language :: Python",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
    ],
    keywords='web YQL',
    author="Stuart Colville",
    author_email="pypi@muffinresearch.co.uk",
    url="http://muffinresearch.co.uk/",
    license="BSD",
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires = ['httplib2', 'oauth2'],
    tests_require = ['nosetests', 'coverage'],
    test_suite="yql.tests",
    entry_points = """\
    """
)

