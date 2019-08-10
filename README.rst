Graphene-SQLAlchemy-Filter
==========================

|circle-ci| |coveralls| |pypi|

Filters for `Graphene SQLAlchemy integration <https://github.com/graphql-python/graphene-sqlalchemy>`__

|preview|

Quick start
===========

Create a filter and add it to the graphene field.

.. code:: python

    from graphene_sqlalchemy_filter import FilterableConnectionField, FilterSet


    class UserFilter(FilterSet):
        is_admin = graphene.Boolean()

        class Meta:
            model = User
            fields = {
                'username': ['eq', 'ne', 'in', 'ilike'],
                'is_active': [...],  # shortcut!
            }

        @staticmethod
        def is_admin_filter(info, query, value):
            if value:
                return User.username == 'admin'
            else:
                return User.username != 'admin'


    class Query(ObjectType):
        all_users = FilterableConnectionField(UserConnection, filters=UserFilter())

Now, we're going to create query.

.. code::

    {
      allUsers (
        filters: {
          isActive: true,
          or: [
            {isAdmin: true},
            {usernameIn: ["moderator", "cool guy"]}
          ]
        }
      ){
        edges {
          node {
            id
            username
          }
        }
      }
    }

🔥 **Let's rock!** 🔥

--------------


Filters
=======

FilterSet class must inherit ``graphene_sqlalchemy_filter.FilterSet`` or
your subclass of this class.

Metaclass must contain the sqlalchemy model and fields.

There are three types of filters:

#. `automatically generated
   filters <#automatically-generated-filters>`__
#. `simple filters <#simple-filters>`__
#. `filters that require join <#filters-that-require-join>`__

Automatically generated filters
-------------------------------

.. code:: python

    class UserFilter(FilterSet):
       class Meta:
           model = User
           fields = {
               'username': ['eq', 'ne', 'in', 'ilike'],
               'is_active': [...],  # shortcut!
           }

Metaclass must contain the sqlalchemy model and fields.

Automatically generated filters must be specified by ``fields`` variable.
Key - field name of sqlalchemy model, value - list of expressions (or shortcut).

Allowed filter values: ``'eq'``, ``'ne'``, ``'like'``, ``'ilike'``,
``'regexp'``, ``'is_null'``, ``'in'``, ``'not_in'``, ``'lt'``,
``'lte'``, ``'gt'``, ``'gte'``, ``'range'``.

Shortcut (default: ``[...]``) will add all the allowed filters for this
type of sqlalchemy field.

Simple filters
--------------

.. code:: python

    class UserFilter(FilterSet):
        is_admin = graphene.Boolean()

        @staticmethod
        def is_admin_filter(info, query, value):
            if value:
                return User.username == 'admin'
            else:
                return User.username != 'admin'

Each simple filter has a class variable that passes to GraphQL schema as
an input type and function ``<field_name>_filter`` that makes
filtration.

The filtration function takes the following arguments:

-  ``info`` - ResolveInfo graphene object
-  ``query`` - sqlalchemy query (not used in that filters type)
-  ``value`` - the value of a filter

The return value can be any type of sqlalchemy clause. This means that
you can return ``not_(and_(or_(...), ...))``.

Metaclass is not required if you do not need automatically generated filters.

Filters that require join
-------------------------

This type of filter is the same as `simple filters <#simple-filters>`__
but has a different return type.

The filtration function should return a new sqlalchemy query and clause
(like simple filters).

.. code:: python

    class UserFilter(FilterSet):
        is_moderator = graphene.Boolean()

        @classmethod
        def is_admin_filter(cls, info, query, value):
            membership = cls.aliased(info, Membership, name='is_moderator')
      
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

Model aliases
~~~~~~~~~~~~~

The function ``cls.aliased(info, model, name='...')`` caches `sqlalchemy
aliases <https://docs.sqlalchemy.org/en/13/orm/query.html#sqlalchemy.orm.aliased>`__
in the query filtration scope by a given model class and name. It has
one differing parameter - ``info`` (graphene ResolveInfo object). Other
arguments are the same as `sqlalchemy.orm.aliased <https://docs.sqlalchemy.org/en/13/orm/query.html#sqlalchemy.orm.aliased>`__.

Identical joins will be skipped by sqlalchemy.

Features
========

Rename GraphQL filter field
---------------------------

.. code:: python

    class CustomField(FilterableConnectionField):
        filter_arg = 'where'
        

    class Query(ObjectType):
        all_users = CustomField(UserConnection, where=UserFilter())
        all_groups = FilterableConnectionField(GroupConnection, filters=GroupFilter())

.. code::

    {
      allUsers (where: {isActive: true}){
        edges { node { id } }
      }
      allGroups (filters: {nameIn: ["python", "development"]}){
        edges { node { id } }
      }
    }

Rename expression
-----------------

.. code:: python

    class BaseFilter(FilterSet):
        GRAPHQL_EXPRESSION_NAMES = dict(
            FilterSet.GRAPHQL_EXPRESSION_NAMES,
            **{'eq': 'equal', 'not': 'i_never_asked_for_this'}
        )

        class Meta:
            abstract = True


    class UserFilter(BaseFilter):
        class Meta:
            model = User
            fields = {'first_name': ['eq'], 'last_name': ['eq']}

.. code::

    {
      allUsers (filters: {iNeverAskedForThis: {firstNameEqual: "Adam", lastNameEqual: "Jensen"}}){
        edges { node { id } }
      }
    }

Custom shortcut value
---------------------

.. code:: python

    class BaseFilter(FilterSet):
        ALL = '__all__'

        class Meta:
            abstract = True


    class UserFilter(BaseFilter):
        class Meta:
            model = User
            fields = {'username': '__all__'}

Localization of documentation
-----------------------------

.. code:: python

    class BaseFilter(FilterSet):
        DESCRIPTIONS = {
            'eq': 'Полностью совпадает.',
            'ne': 'Не совпадает.',
            'like': 'Регистрозависимая проверка строки по шлабону.',
            'ilike': 'Регистронезависимая проверка строки по шлабону.',
            'regexp': 'Регистрозависимая проверка строки по регулярному выражению.',
            'is_null': 'Равно ли значение `null`. Принемает `true` или `false`.',
            'in': 'Проверка вхождения в список.',
            'not_in': 'Проверка не вхождения в список.',
            'lt': 'Меньше, чем указанное значение.',
            'lte': 'Меньше или равно указанному значению.',
            'gt': 'Больше, чем указанное значение.',
            'gte': 'Больше или равно указанному значению.',
            'range': 'Значение входит в диапазон значений.',
            'and': 'Объединение фильтров с помощью ``AND``.',
            'or': 'Объединение фильтров с помощью ``OR``.',
            'not': 'Отрицание указанных фильтров.',
        }

        class Meta:
            abstract = True

Custom expression
-----------------

.. code:: python

    def today_filter(field, value: bool):
        today = func.date(field) == date.today()
        return today if value else not_(today)


    class BaseFilter(FilterSet):
        # Add expression.
        TODAY = 'today'

        EXTRA_EXPRESSIONS = {
            'today': {
                # Add the name of the expression in GraphQL.
                'graphql_name': 'today',
                # Update allowed filters (used by shortcut).
                'for_types': [types.Date, types.DateTime],
                # Add a filtering function (takes the sqlalchemy field and value).
                'filter': today_filter,
                # Add the GraphQL input type. Column type by default.
                'input_type': (
                    lambda type_, nullable, doc: graphene.Boolean(nullable=False)
                ),
                # Description for the GraphQL schema.
                'description': 'It is today.',
            }
        }

        class Meta:
            abstract = True


    class PostFilter(BaseFilter):
        class Meta:
            model = Post
            fields = {'created': ['today'], 'updated': [...]}

.. code::

    {
      allPosts (filters: {createdToday: false, updatedToday: true}){
        edges { node { id } }
      }
    }

.. |preview| image:: https://github.com/art1415926535/graphene-sqlalchemy-filter/blob/master/preview.gif?raw=true
.. |circle-ci| image:: https://circleci.com/gh/art1415926535/graphene-sqlalchemy-filter.svg?style=svg
   :target: https://circleci.com/gh/art1415926535/graphene-sqlalchemy-filter
.. |coveralls| image:: https://coveralls.io/repos/github/art1415926535/graphene-sqlalchemy-filter/badge.svg?branch=master
   :target: https://coveralls.io/github/art1415926535/graphene-sqlalchemy-filter?branch=master
.. |pypi| image:: https://badge.fury.io/py/graphene-sqlalchemy-filter.svg
    :target: https://badge.fury.io/py/graphene-sqlalchemy-filter