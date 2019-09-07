# GraphQL
import graphene
from graphene import Connection, Node
from graphene_sqlalchemy import SQLAlchemyObjectType

# Database
from sqlalchemy import Integer, and_

# Project
from graphene_sqlalchemy_filter import FilterableConnectionField, FilterSet

# This module
from .models import Group, Membership, User


class UserNode(SQLAlchemyObjectType):
    class Meta:
        model = User
        interfaces = (Node,)


class UserConnection(Connection):
    class Meta:
        node = UserNode


class BaseFilter(FilterSet):
    EXTRA_EXPRESSIONS = {
        'zero': {
            'graphql_name': 'eq_zero',
            'for_types': [Integer],
            'filter': lambda f, v: f == 0 if v else f != 0,
            'input_type': (lambda t, n, d: graphene.Boolean(nullable=False)),
            'description': 'Equal to zero.',
        }
    }

    class Meta:
        abstract = True


USER_FILTER_FIELDS = {
    'username': ['eq', 'ne', 'in', 'ilike'],
    'balance': ['eq', 'ne', 'gt', 'lt', 'range', 'is_null'],
    'is_active': ['eq', 'ne'],
}


class UserFilter(BaseFilter):
    is_admin = graphene.Boolean(description='User name = admin')
    is_moderator = graphene.Boolean(description='User is a moderator')
    member_of_group = graphene.String(
        description='Member of the group that is named'
    )

    @staticmethod
    def is_admin_filter(info, query, value):
        """Simple filter return only clause."""
        if value:
            return User.username == 'admin'
        else:
            return User.username != 'admin'

    @classmethod
    def is_moderator_filter(cls, info, query, value):
        membership = cls.aliased(query, Membership, name='is_moderator')

        query = query.join(
            membership,
            and_(
                User.id == membership.user_id,
                membership.is_moderator.is_(True),
            ),
        )

        if value:
            filter_ = membership.id.isnot(None)
        else:
            filter_ = membership.id.is_(None)
        return query, filter_

    @classmethod
    def member_of_group_filter(cls, info, query, value):
        membership = cls.aliased(query, Membership, name='member_of')
        group = cls.aliased(query, Group, name='of_group')

        query = query.join(membership, User.memberships).join(
            group, membership.group
        )

        return query, group.name == value

    class Meta:
        model = User
        fields = USER_FILTER_FIELDS


class Query(graphene.ObjectType):
    field = FilterableConnectionField(UserConnection, filters=UserFilter())


schema = graphene.Schema(query=Query)
