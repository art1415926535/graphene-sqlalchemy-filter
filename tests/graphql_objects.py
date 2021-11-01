# GraphQL
import graphene
from graphene import Connection, Node
from graphene_sqlalchemy import SQLAlchemyObjectType

# Database
from sqlalchemy import Integer, and_

# Project
from graphene_sqlalchemy_filter import FilterableConnectionField, FilterSet
from tests import gqls_version

# This module
from .models import Article, Assignment, Author, Group, Membership, Task, User


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
    'id': ['eq'],
    'username': ['eq', 'ne', 'in', 'ilike'],
    'balance': ['eq', 'ne', 'gt', 'lt', 'range', 'is_null'],
    'is_active': ['eq', 'ne'],
    'username_hybrid_property': ['eq', 'ne', 'in'],
    'assignments': {'task': {'name': ['eq'], 'id': ['eq']}, 'active': ['eq']},
}


if gqls_version >= (2, 2, 0):
    USER_FILTER_FIELDS['status'] = ['eq']


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


class MembershipFilter(BaseFilter):
    class Meta:
        model = Membership
        fields = {'is_moderator': [...]}


class GroupFilter(BaseFilter):
    class Meta:
        model = Group
        fields = {'name': [...], 'parent_group_id': ['is_null']}


class ArticleFilter(FilterSet):
    class Meta:
        model = Article
        fields = {
            'author_first': [...],
            'author_last': [...],
        }


class AuthorFilter(FilterSet):
    class Meta:
        model = Author
        fields = {
            'author_first': [...],
            'author_last': [...],
        }


class TaskFilter(FilterSet):
    class Meta:
        model = Task
        fields = {
            'users': {'username': [...]},
            'status_name': [...],
            'assignments': {'task': {'name': [...]}},
        }


class AssignmentFilter(FilterSet):
    class Meta:
        model = Assignment
        fields = {'task': {'assignments': {'active': [...]}}}


class MyFilterableConnectionField(FilterableConnectionField):
    filters = {
        User: UserFilter(),
        Membership: MembershipFilter(),
        Group: GroupFilter(),
        Article: ArticleFilter(),
        Author: AuthorFilter(),
        Task: TaskFilter(),
        Assignment: AssignmentFilter(),
    }


class UserNode(SQLAlchemyObjectType):
    class Meta:
        model = User
        interfaces = (Node,)
        connection_field_factory = MyFilterableConnectionField.factory


class UserConnection(Connection):
    class Meta:
        node = UserNode


class MembershipNode(SQLAlchemyObjectType):
    class Meta:
        model = Membership
        interfaces = (Node,)
        connection_field_factory = MyFilterableConnectionField.factory


class MembershipConnection(Connection):
    class Meta:
        node = MembershipNode


class GroupNode(SQLAlchemyObjectType):
    class Meta:
        model = Group
        interfaces = (Node,)
        connection_field_factory = MyFilterableConnectionField.factory


class GroupConnection(Connection):
    class Meta:
        node = GroupNode


class AuthorNode(SQLAlchemyObjectType):
    class Meta:
        model = Author
        interfaces = (graphene.relay.Node,)
        connection_field_factory = MyFilterableConnectionField.factory


class AuthorConnection(Connection):
    class Meta:
        node = AuthorNode


class ArticleNode(SQLAlchemyObjectType):
    class Meta:
        model = Article
        interfaces = (graphene.relay.Node,)
        connection_field_factory = MyFilterableConnectionField.factory


class ArticleConnection(Connection):
    class Meta:
        node = ArticleNode


class TaskNode(SQLAlchemyObjectType):
    class Meta:
        model = Task
        interfaces = (graphene.relay.Node,)


class TaskConnection(Connection):
    class Meta:
        node = TaskNode


class AssignmentNode(SQLAlchemyObjectType):
    class Meta:
        model = Assignment
        interfaces = (graphene.relay.Node,)


class AssignmentConnection(Connection):
    class Meta:
        node = AssignmentNode


class Query(graphene.ObjectType):
    field = MyFilterableConnectionField(UserConnection)
    all_groups = MyFilterableConnectionField(GroupConnection)
    all_authors = MyFilterableConnectionField(AuthorConnection)
    all_articles = MyFilterableConnectionField(ArticleConnection)
    tasks = MyFilterableConnectionField(TaskConnection)
    assignments = MyFilterableConnectionField(AssignmentConnection)


schema = graphene.Schema(query=Query)
