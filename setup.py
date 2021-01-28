import ast
import re

from setuptools import find_packages, setup


_version_re = re.compile(r'__version__\s+=\s+(.*)')


with open('graphene_sqlalchemy_filter/__init__.py', 'rb') as f:
    version = str(
        ast.literal_eval(_version_re.search(f.read().decode('utf-8')).group(1))
    )


with open('README.rst', encoding='utf-8') as f:
    long_description = f.read()


requirements = [
    'graphene-sqlalchemy>=2.1.0,<3',
    'SQLAlchemy<2',
]


setup(
    name='graphene-sqlalchemy-filter',
    version=version,
    description='Filters for Graphene SQLAlchemy integration',
    url='https://github.com/art1415926535/graphene-sqlalchemy-filter',
    author='Artem Fedotov',
    license='MIT',
    long_description=long_description,
    classifiers=[
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: Implementation :: PyPy',
    ],
    keywords='api graphql protocol rest relay graphene',
    packages=find_packages(exclude=['tests']),
    install_requires=requirements,
    python_requires='>=3.6'
)
