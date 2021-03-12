# Standard Library
from copy import deepcopy

# Third Party
import pytest

# GraphQL
import graphene

# Database
from sqlalchemy import Column, types

# Project
from graphene_sqlalchemy_filter import FilterSet, filters
from tests import models
from tests.graphql_objects import USER_FILTER_FIELDS, UserFilter
from tests.models import Base


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
            if op not in UserFilter.GRAPHQL_EXPRESSION_NAMES:
                continue
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

    with pytest.raises(AttributeError, match='Model not specified'):

        class F3(F1):
            class Meta:
                fields = {'username': [...]}


def test_old_extra_expression_register():
    def zero_filter(field, value: bool):
        return field == 0 if value else field != 0

    def zero_type(field_type, nullable, doc):
        return graphene.Boolean(nullable=False)

    class F(FilterSet):
        EQ_ZERO = 'zero'

        # Add the name of the expression in GraphQL.
        GRAPHQL_EXPRESSION_NAMES = dict(
            FilterSet.GRAPHQL_EXPRESSION_NAMES, zero='eq_zero'
        )

        # Update allowed filters (used by shortcut).
        ALLOWED_FILTERS = dict(FilterSet.ALLOWED_FILTERS)
        ALLOWED_FILTERS[types.Integer] = FilterSet.ALLOWED_FILTERS[
            types.Integer
        ] + [EQ_ZERO]

        # Add a filtering function (takes the sqlalchemy field and value).
        FILTER_FUNCTIONS = dict(FilterSet.FILTER_FUNCTIONS, zero=zero_filter)

        # Add the GraphQL input type. Equals the column type if not specified.
        FILTER_OBJECT_TYPES = dict(
            FilterSet.FILTER_OBJECT_TYPES, zero=zero_type
        )

        # Description for the GraphQL schema.
        DESCRIPTIONS = dict(FilterSet.DESCRIPTIONS, zero='Equal to zero.')

        class Meta:
            abstract = True

    class UserFilter(F):
        class Meta:
            model = models.User
            fields = {'balance': [...], 'id': ['zero']}

    filter_fields = set(UserFilter._meta.fields)
    ok = {
        'balance',
        'balance_gt',
        'balance_gte',
        'balance_in',
        'balance_is_null',
        'balance_lt',
        'balance_lte',
        'balance_ne',
        'balance_not_in',
        'balance_range',
        'balance_eq_zero',
        'id_eq_zero',
        'and',
        'not',
        'or',
    }
    assert filter_fields == ok


def test_extra_expression():
    class NewInt(types.Integer):
        pass

    class BaseFilter(FilterSet):
        EXTRA_EXPRESSIONS = {
            'zero': {
                'graphql_name': 'eq_zero',
                'for_types': [types.Integer, NewInt],
                'filter': lambda f, v: f == 0 if v else f != 0,
                'input_type': (
                    lambda t, n, d: graphene.Boolean(nullable=False)
                ),
                'description': 'Equal to zero.',
            }
        }

        class Meta:
            abstract = True

    class AnotherBaseFilter(FilterSet):
        EXTRA_EXPRESSIONS = {
            'gte_zero': {  # Should not be found
                'graphql_name': 'gte_zero',
                'for_types': [types.Integer, NewInt],
                'filter': lambda f, v: f > 0 if v else f <= 0,
                'input_type': (
                    lambda t, n, d: graphene.Boolean(nullable=False)
                ),
                'description': 'Greater than zero.',
            }
        }

        class Meta:
            abstract = True

    class AnotherUserFilter(AnotherBaseFilter):
        class Meta:
            model = models.User
            fields = {'id': [...]}

    class UserFilter(BaseFilter):
        EXTRA_EXPRESSIONS = {
            'ne_zero': {
                'graphql_name': 'ne_zero',
                'for_types': [types.Integer, NewInt],
                'filter': lambda f, v: f != 0 if v else f == 0,
                'input_type': (
                    lambda t, n, d: graphene.Boolean(nullable=False)
                ),
                'description': 'Not equal zero.',
            }
        }

        class Meta:
            model = models.User
            fields = {'balance': [...], 'id': ['zero']}

    filter_fields = set(UserFilter._meta.fields)
    ok = {
        'balance',
        'balance_gt',
        'balance_gte',
        'balance_in',
        'balance_is_null',
        'balance_lt',
        'balance_lte',
        'balance_ne',
        'balance_not_in',
        'balance_range',
        'balance_eq_zero',  # Added by BaseFilter.
        'balance_ne_zero',  # Added by UserFilter.
        'id_eq_zero',  # Added by BaseFilter.
        'and',
        'not',
        'or',
    }
    assert filter_fields == ok


def test_sql_alchemy_subclass_column_types():
    class F(FilterSet):
        ALLOWED_FILTERS = {types.Integer: ['eq', 'gt']}

        class Meta:
            abstract = True

    class MyNVARCHAR(types.NVARCHAR):
        pass

    class TestModel(Base):
        __tablename__ = 'test'

        id = Column(types.SmallInteger, primary_key=True, autoincrement=True)
        text = Column(MyNVARCHAR)

    class TestFilter(F):
        EXTRA_ALLOWED_FILTERS = {types.String: ['eq']}

        class Meta:
            model = TestModel
            fields = {'id': [...], 'text': [...]}

    filter_fields = set(TestFilter._meta.fields)
    ok = {'id', 'id_gt', 'text', 'text_is_null', 'and', 'not', 'or'}

    assert filter_fields == ok


def test_sql_alchemy_wrong_column_types():
    class F(FilterSet):
        ALLOWED_FILTERS = {}

        class Meta:
            abstract = True

    msg = 'Unsupported column type. Hint: use EXTRA_ALLOWED_FILTERS.'
    with pytest.raises(KeyError, match=msg):

        class TestFilter(F):
            class Meta:
                model = models.User
                fields = {'id': [...]}


def test_generate_relationship_filter_field_names_concatenate_parents():
    filter_fields = deepcopy(UserFilter._meta.fields)

    assert filter_fields["assignments"].type._meta.name == "user_assignments"
    assert (
        getattr(
            filter_fields["assignments"].type, "and"
        ).type.of_type.of_type._meta.name
        == "user_assignments_and"
    )
    assert (
        getattr(
            filter_fields["assignments"].type, "or"
        ).type.of_type.of_type._meta.name
        == "user_assignments_or"
    )
    assert (
        getattr(filter_fields["assignments"].type, "not").type._meta.name
        == "user_assignments_not"
    )
    assert (
        filter_fields["assignments"].type.task.type._meta.name
        == "user_assignments_task"
    )
    assert (
        getattr(
            filter_fields["assignments"].type.task.type, "and"
        ).type.of_type.of_type._meta.name
        == "user_assignments_task_and"
    )
    assert (
        getattr(
            filter_fields["assignments"].type.task.type, "or"
        ).type.of_type.of_type._meta.name
        == "user_assignments_task_or"
    )
    assert (
        getattr(
            filter_fields["assignments"].type.task.type, "not"
        ).type._meta.name
        == "user_assignments_task_not"
    )
