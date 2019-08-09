# Standard Library
from copy import deepcopy

# GraphQL
import graphene

# Project
from graphene_sqlalchemy_filter import FilterSet, filters
from tests import models
from tests.graphql_objects import USER_FILTER_FIELDS, UserFilter


def test_custom_filter_field_type():
    filter_fields = deepcopy(UserFilter._meta.fields)

    assert 'is_admin' in filter_fields
    is_rich = filter_fields['is_admin']
    assert isinstance(is_rich, graphene.InputField)
    assert is_rich.type is graphene.Boolean
    del filter_fields['is_admin']


def test_default_filter_field_types():
    filter_fields = deepcopy(UserFilter._meta.fields)

    for model_field, operators in USER_FILTER_FIELDS.items():
        for op in operators:
            field = model_field
            graphql_op = UserFilter.GRAPHQL_EXPRESSION_NAMES[op]
            if graphql_op:
                field += filters.DELIMITER + graphql_op

            assert field in filter_fields, 'Field not found: ' + field
            assert isinstance(filter_fields[field], graphene.InputField)
            del filter_fields[field]


def test_conjunction_filter_field_types():
    filter_fields = deepcopy(UserFilter._meta.fields)

    for op in [UserFilter.AND, UserFilter.OR]:
        assert op in filter_fields
        assert isinstance(filter_fields[op], graphene.InputField)

        input_field = filter_fields[op].type
        assert isinstance(input_field, graphene.List)

        input_field_of_type = input_field.of_type
        assert isinstance(input_field_of_type, graphene.NonNull)

        non_null_input_field_of_type = input_field_of_type.of_type
        assert non_null_input_field_of_type is UserFilter

        del filter_fields[op]


def test_not_filter_field_type():
    filter_fields = UserFilter._meta.fields
    op = UserFilter.NOT

    assert op in filter_fields
    assert isinstance(filter_fields[op], graphene.InputField)

    input_field = filter_fields[op].type
    assert input_field is UserFilter


def test_number_filter_fields():
    user_filters = {
        'username': ['eq', 'in', 'ilike'],
        'balance': ['ne', 'gt', 'lt', 'range', 'is_null'],
    }

    class F(UserFilter):
        class Meta:
            model = models.User
            fields = user_filters

    required_count = 6  # and, or, not, is_admin, is_moderator, member_of_group

    # Add default filters.
    for values in user_filters.values():
        if values == F.ALL:
            raise ValueError('Not supported in test')

        required_count += len(values)

    filter_fields = F._meta.fields
    assert len(filter_fields) == required_count, list(filter_fields)


def test_shortcut():
    class F(FilterSet):
        class Meta:
            model = models.User
            fields = {'is_active': [...]}

    filter_fields = set(F._meta.fields)
    ok = {'is_active', 'is_active_ne', 'is_active_is_null', 'and', 'or', 'not'}

    assert filter_fields == ok


def test_meta_without_model():
    ok = {'field', 'and', 'or', 'not'}

    class F1(FilterSet):
        field = graphene.Boolean()

        @staticmethod
        def field_filter(info, query, value):
            return True

    filter_fields = set(F1._meta.fields)

    assert filter_fields == ok

    class F2(F1):
        class Meta:
            fields = {}

    filter_fields = set(F2._meta.fields)
    assert filter_fields == ok
