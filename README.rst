============================
graphene-sqlalchemy-filter
============================
Filters for `Graphene SQLAlchemy integration <https://github.com/graphql-python/graphene-sqlalchemy>`_

.. image:: https://github.com/art1415926535/graphene-sqlalchemy-filter/blob/master/preview.gif?raw=true

Quick start
-----------

Create a filter and add it to the graphene field.

.. code-block:: python

    from graphene_sqlalchemy_filter import FilterableConnectionField, FilterSet


    class UserFilter(FilterSet):
        is_admin = Boolean()

        class Meta:
            model = User
            fields = {
                'username': ['eq', 'ne', 'in', 'ilike'],
                'is_active': [...],  # shortcut!
            }

        @classmethod
        def is_admin_filter(cls, info, query, value):
            if value:
                return User.username == 'admin'
            else:
                return User.username != 'admin'


    class Query(ObjectType):
        all_users = FilterableConnectionField(UserConnection, filters=UserFilter())


Now, we're going to create query.

.. code-block::

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


---------------

**Let's rock!**