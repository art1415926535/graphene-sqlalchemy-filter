import importlib.metadata
import re


_gsqla_version_match = re.match(
    r"(\d+)\.(\d+)\.(\d+)", importlib.metadata.version("graphene-sqlalchemy")
)
gsqla_version = ()
if _gsqla_version_match:
    gsqla_version: tuple[int, ...] = tuple(
        int(x) for x in _gsqla_version_match.groups()
    )

_graphql_version_match = re.match(
    r"(\d+)\.(\d+)\.(\d+)", importlib.metadata.version("graphql-core")
)
graphql_version = ()
if _graphql_version_match:
    graphql_version: tuple[int, ...] = tuple(
        int(x) for x in _graphql_version_match.groups()
    )


gsqla_version_lt_2_1_2 = gsqla_version < (2, 1, 2)
graphql_version_lt_3_0_0 = graphql_version < (3, 0, 0)
