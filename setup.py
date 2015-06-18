#!/usr/bin/python

import setuptools

setup_params = dict(
    name='mettle',
    version='0.7.1',
    author='Y Team',
    author_email=', '.join([
        'alejandro.rivera@yougov.com',
        'fernando.gutierrez@yougov.com',
        'brent.tubbs@gmail.com',
    ]),
    packages=setuptools.find_packages(),
    include_package_data=True,

    # Dependency versions are intentionally pinned to prevent surprises at
    # deploy time.  The world is not yet safely semver.
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
        'spa>=0.0.6',
        'sqlalchemy==0.9.8',
        'Werkzeug==0.10.1',

        # leave mettle-protocol and its dependencies loosely versioned.
        'mettle-protocol>=1.0.1',
        'pika',
        'utc',
    ],
    entry_points={
        'console_scripts': [
            'mettle = mettle.cli:main',
        ]
    },
    description='A micro service framework for data pipelines, providing scheduling, retrying, and error reporting.',
)

if __name__ == '__main__':
    setuptools.setup(**setup_params)
