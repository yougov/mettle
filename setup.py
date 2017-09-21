#!/usr/bin/env python

# Project skeleton maintained at https://github.com/jaraco/skeleton

import io

import setuptools

with io.open('README.rst', encoding='utf-8') as readme:
    long_description = readme.read()

name = 'mettle'
description = (
    'A micro service framework for data pipelines, providing'
    'scheduling, retrying, and error reporting.'
)
nspkg_technique = 'native'
"""
Does this package use "native" namespace packages or
pkg_resources "managed" namespace packages?
"""

params = dict(
    name=name,
    use_scm_version=True,
    author="YouGov, Plc.",
    author_email="opensource@yougov.com",
    description=description or name,
    long_description=long_description,
    url="https://github.com/yougov/" + name,
    packages=setuptools.find_packages(),
    include_package_data=True,
    namespace_packages=(
        name.split('.')[:-1] if nspkg_technique == 'managed'
        else []
    ),
    python_requires='>=2.7,<3.0',
    install_requires=[
        'Beaker==1.6.4',
        'croniter==0.3.5',
        'functools32==3.2.3-1',
        'gevent==1.0.1',
        'gunicorn==19.1.1',
        'iso8601>=0.1.10',
        'pgpubsub>=0.0.4',
        'psycogreen==1.0',
        'psycopg2==2.5.4',
        'PyYAML==3.11',
        'spa==0.0.7',
        'sqlalchemy==0.9.8',
        'Werkzeug==0.10.1',

        # leave mettle-protocol and its dependencies loosely versioned.
        'mettle-protocol>=1.0.1',
        'pika>=0.9.14,<=0.10.0',
        'utc',
    ],
    extras_require={
        'testing': [
            'pytest>=2.8',
            'pytest-sugar',
            'collective.checkdocs',
        ],
        'docs': [
            'sphinx',
            'jaraco.packaging>=3.2',
            'rst.linker>=1.9',
        ],
    },
    setup_requires=[
        'setuptools_scm>=1.15.0',
    ],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 2.7",
    ],
    entry_points={
        'console_scripts': [
            'mettle = mettle.cli:main',
        ],
    },
)
if __name__ == '__main__':
    setuptools.setup(**params)
