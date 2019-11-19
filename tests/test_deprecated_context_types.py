# Third Party
import pytest

# Project
from tests import models
from tests.graphql_objects import UserFilter


class FilterAliasedResolveInfo(UserFilter):
    @classmethod
    def is_moderator_filter(cls, info, query, value):
        cls.aliased(  # deprecation warning
            info, models.Membership, name='is_moderator'
        )
        return query, True


def test_dict_context(info_and_user_query):
    info, user_query = info_and_user_query
    info.context = {}
    filters = {}

    with pytest.warns(None) as record:
        UserFilter.filter(info, user_query, filters)
        if record:
            pytest.fail('No warnings expected!')


def test_object_context(info_and_user_query):
    info, user_query = info_and_user_query

    class Context:
        pass

    info.context = Context()
    filters = {}

    with pytest.warns(None) as record:
        UserFilter.filter(info, user_query, filters)
        if record:
            pytest.fail('No warnings expected!')


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
    filters = {'is_moderator': True}

    with pytest.warns(DeprecationWarning):
        FilterAliasedResolveInfo.filter(info, user_query, filters)


def test_aliased_with_object_context(info_and_user_query):
    info, user_query = info_and_user_query

    class Context:
        pass

    info.context = Context()
    filters = {'is_moderator': True}
    msg = (
        r'Graphene resolve info is deprecated, use SQLAlchemy query. '
        r'Hint: cls.aliased\(query, Membership, name="is_moderator"\)'
    )
    with pytest.warns(DeprecationWarning, match=msg):
        FilterAliasedResolveInfo.filter(info, user_query, filters)


def test_aliased_with_slots_context(info_and_user_query):
    info, user_query = info_and_user_query

    class Context:
        __slots__ = ()

    info.context = Context()
    filters = {'is_moderator': True}

    with pytest.warns(RuntimeWarning), pytest.raises(RuntimeError):
        FilterAliasedResolveInfo.filter(info, user_query, filters)
