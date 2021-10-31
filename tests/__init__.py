# Standard Library
import re

# GraphQL
from graphene_sqlalchemy import __version__ as gqls_version


try:
    gqls_version = tuple([int(x) for x in gqls_version.split('.')])
except ValueError:
    gqls_version = tuple([int(x) for x in re.findall(r'\d+',gqls_version)])
