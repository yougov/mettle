#!/usr/bin/python

import setuptools

setup_params = dict(
    name='mettle',
    version='0.0.1',
    author='Y Team',
    author_email=', '.join([
        'alejandro.rivera@yougov.com',
        'fernando.gutierrez@yougov.com',
        'brent.tubbs@gmail.com',
    ]),
    packages=setuptools.find_packages(),
    include_package_data=True,
    install_requires=[
        'croniter==0.3.5',
        'gevent==1.0.1',
        'gevent-websocket==0.9.3',
        'gunicorn==19.1.1',
        'psycogreen==1.0',
        'psycopg2==2.5.4',
        'PyYAML==3.11',
        'sqlalchemy==0.9.8',
        'Werkzeug==0.10.1',

        # leave mettle-protocol and its dependencies unversioned for now.
        'mettle-protocol',
        'pika',
        'utc',
    ],
    entry_points={
        'console_scripts': [
            'mettle = mettle.cli:main',
        ]
    },
    description='A robust framework for scheduling and executing ETL jobs.',
)

if __name__ == '__main__':
    setuptools.setup(**setup_params)
