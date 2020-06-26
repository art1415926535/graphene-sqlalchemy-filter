# GraphQL
from graphene_sqlalchemy import __version__ as gqls_version


gqls_version = tuple([int(x) for x in gqls_version.split('.')])
