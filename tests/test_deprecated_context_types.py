import warnings

import pytest

from tests import models
from tests.graphql_objects import UserFilter


_warning_msg = (
    "Graphene resolve info is deprecated, use SQLAlchemy query. "
    'Hint: cls.aliased\\(query, Membership, name="is_moderator"\\)'
)


class FilterAliasedResolveInfo(UserFilter):
    @classmethod
    def is_moderator_filter(cls, info, query, value):
        cls.aliased(  # deprecation warning
            info, models.Membership, name="is_moderator"
        )
        return query, True


def test_dict_context(info_and_user_query):
    info, user_query = info_and_user_query
    info.context = {}
    filters = {}

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        UserFilter.filter(info, user_query, filters)


def test_object_context(info_and_user_query):
    info, user_query = info_and_user_query

    class Context:
        pass

    info.context = Context()
    filters = {}

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        UserFilter.filter(info, user_query, filters)


def test_slots_context(info_and_user_query):
    info, user_query = info_and_user_query

    class Context:
        __slots__ = ()

    info.context = Context()
    filters = {}

    with pytest.warns(RuntimeWarning):
        UserFilter.filter(info, user_query, filters)


def test_aliased_with_dict_context(info_and_user_query):
    info, user_query = info_and_user_query
    info.context = {}
    filters = {"is_moderator": True}
    with pytest.warns(DeprecationWarning, match=_warning_msg):
        FilterAliasedResolveInfo.filter(info, user_query, filters)


def test_aliased_with_object_context(info_and_user_query):
    info, user_query = info_and_user_query

    class Context:
        pass

    info.context = Context()
    filters = {"is_moderator": True}
    with pytest.warns(DeprecationWarning, match=_warning_msg):
        FilterAliasedResolveInfo.filter(info, user_query, filters)


def test_aliased_with_slots_context(info_and_user_query):
    info, user_query = info_and_user_query

    class Context:
        __slots__ = ()

    info.context = Context()
    filters = {"is_moderator": True}

    with (
        pytest.warns(RuntimeWarning),
        pytest.raises(RuntimeError),
        pytest.warns(DeprecationWarning, match=_warning_msg),
    ):
        FilterAliasedResolveInfo.filter(info, user_query, filters)
