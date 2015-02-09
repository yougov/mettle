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
        'psycopg2==2.5.4',
        'sqlalchemy==0.9.8',
        'Werkzeug==0.10.1',
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
