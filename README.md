# Graphene-SQLAlchemy-Filter

[![CI](https://github.com/art1415926535/graphene-sqlalchemy-filter/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/art1415926535/graphene-sqlalchemy-filter/actions/workflows/ci.yml) [![Coverage Status](https://codecov.io/gh/art1415926535/graphene-sqlalchemy-filter/graph/badge.svg?token=uEk5snJdaT)](https://codecov.io/gh/art1415926535/graphene-sqlalchemy-filter) [![PyPI version](https://badge.fury.io/py/graphene-sqlalchemy-filter.svg)](https://badge.fury.io/py/graphene-sqlalchemy-filter)

Filters for [Graphene SQLAlchemy integration](https://github.com/graphql-python/graphene-sqlalchemy)

![preview](https://github.com/art1415926535/graphene-sqlalchemy-filter/blob/master/preview.gif?raw=true)

## Choosing the Right Library

> ❗**Important:** This project does **not** support **graphene-sqlalchemy v3**.  
> Starting from v3, **filtering is already included** in the upstream library.

Use the following table to decide which package fits your needs:

| Graphene-SQLAlchemy version | What to use | Notes |
|------------|-------------|-------|
| **v2.x** | ✅ `graphene-sqlalchemy-filter` | Provides flexible filtering integration. |
| **v3.x** | ❌ Not supported here | [Built-in filtering](https://github.com/graphql-python/graphene-sqlalchemy/pull/357) is already available in `graphene-sqlalchemy` itself. |


# Quick start

Create a filter and add it to the graphene field.
```python
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

```

Now, we're going to create a query.
```graphql
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
```

---


# Filters

FilterSet class must inherit `graphene_sqlalchemy_filter.FilterSet` or your subclass of this class.

There are three types of filters:  
  1. [automatically generated filters](#automatically-generated-filters)  
  1. [simple filters](#simple-filters)  
  1. [filters that require join](#filters-that-require-join)  


## Automatically generated filters
```python
class UserFilter(FilterSet):
   class Meta:
       model = User
       fields = {
           'username': ['eq', 'ne', 'in', 'ilike'],
           'is_active': [...],  # shortcut!
       }
```
Metaclass must contain the sqlalchemy model and fields.

Automatically generated filters must be specified by `fields` variable. 
Key - field name of sqlalchemy model, value - list of expressions (or shortcut).

Shortcut (default: `[...]`) will add all the allowed filters for this type of sqlalchemy field (does not work with `hybrid_property`).

| Key            | Description                     | GraphQL postfix |
|----------------|---------------------------------|-----------------|
| `eq`           | equal                           |                 |
| `ne`           | not equal                       | Ne              |
| `like`         | like                            | Like            |
| `ilike`        | insensitive like                | Ilike           |
| `is_null`      | is null                         | IsNull          |
| `in`           | in                              | In              |
| `not_in`       | not in                          | NotIn           |
| `lt`           | less than                       | Lt              |
| `lte`          | less than or equal              | Lte             |
| `gt`           | greater than                    | Gt              |
| `gte`          | greater than or equal           | Gte             |
| `range`        | in range                        | Range           |
| `contains`     | contains (PostgreSQL array)     | Contains        |
| `contained_by` | contained_by (PostgreSQL array) | ContainedBy     |
| `overlap`      | overlap (PostgreSQL array)      | Overlap         |

## Simple filters
```python
class UserFilter(FilterSet):
    is_admin = graphene.Boolean()

    @staticmethod
    def is_admin_filter(info, query, value):
        if value:
            return User.username == 'admin'
        else:
            return User.username != 'admin'
```
Each simple filter has a class variable that passes to GraphQL schema as an input type and function `<field_name>_filter` that makes filtration.

The filtration function takes the following arguments:
  * `info` - ResolveInfo graphene object
  * `query` - sqlalchemy query (not used in that filters type)
  * `value` - the value of a filter

The return value can be any type of sqlalchemy clause. This means that you can return `not_(and_(or_(...), ...))`.

Metaclass is not required if you do not need automatically generated filters.

## Filters that require joins

Sometimes a filter needs columns that live on a **different table**. These “join filters” work just like [simple filters](#simple-filters), but they must:

1) create (or reuse) a SQLAlchemy alias for the related table,  
2) join that alias to the current query, and  
3) return **both** the (possibly modified) query and a SQLAlchemy boolean clause.

### Use the built-ins: `cls._join` and `cls._outerjoin`

`FilterSet` provides two helper methods that are **idempotent**:

- `cls._join(query, target_alias, onclause, ...)`
- `cls._outerjoin(query, target_alias, onclause, ...)`

These helpers inspect the current query and **skip adding the same alias twice**. That means you can safely reuse the **same alias object** across multiple filters without generating duplicate JOINs or “ambiguous column” errors.

**Important:** Always obtain the alias with `cls.aliased(query, Model, name=...)`. Reusing the **same alias name** via `cls.aliased(...)` ensures you get the **same alias object** for the lifetime of that query, so `_join` / `_outerjoin` can recognize it and de-duplicate the JOIN.

### Example: multiple filters sharing the same join

Two filters on `Membership` both need the joined `User`. Using the same alias name (`"member_user"`) makes them share the same JOIN.

```python
class MembershipFilter(FilterSet):
    username = graphene.String(description="Username of the member user")
    user_id = graphene.Int(description="ID of the member user")

    @classmethod
    def username_filter(cls, info, query, value):
        user = cls.aliased(query, User, name="member_user")
        query = cls._join(query, user, Membership.user_id == user.id)
        return query, (user.username == value)

    @classmethod
    def user_id_filter(cls, info, query, value):
        user = cls.aliased(query, User, name="member_user")
        query = cls._join(query, user, Membership.user_id == user.id)
        return query, (user.id == value)

    class Meta:
        model = Membership
        fields = {"is_moderator": [...]}
```

```graphql
{
  allMemberships(filters: {and: [{userId: 1}, {username: "Ally"}, {isModerator: true}]}) {
    edges { node { id } }
  }
}
```

If a client applies both `username` and `user_id` at once, the final SQL will contain **only one** `JOIN ... AS member_user ...` even though both filters called `_join`.


### When to use `_join` vs `_outerjoin`

- Use **`_join` (INNER JOIN)** when a matching related row is **required** for the result to qualify.  
- Use **`_outerjoin` (LEFT OUTER JOIN)** when you may filter on **presence or absence** of related rows.

Both helpers take the same arguments you’d pass to SQLAlchemy’s `.join()` / `.outerjoin()`.

### Best practices & gotchas

- **Always return `(query, clause)`** from a filter method. Modifications to the query (joins) must be returned for the framework to compose them with other filters.
- **Alias once, reuse often.** Call `cls.aliased(query, Model, name="…")` in each filter that needs the same table and reuse the **same `name`** to get the same alias object.
- **Different semantics → different aliases.** If two filters must join the **same table with different roles/conditions**, give them **different alias names** (e.g., `"author_user"` vs `"reviewer_user"`). `_join` only de-duplicates identical alias targets; intentionally separate roles should use separate aliases.
- **Don’t mix different ON conditions with the same alias.** If you need different join predicates, either (a) combine them into the WHERE clause using the one join you already have, or (b) introduce a second alias with a different name.
- **Order-independent.** Because `_join`/`_outerjoin` are idempotent, the final query is stable regardless of the order in which filters are applied.
- **Performance.** It’s safe (and cheap) to call `_join`/`_outerjoin` in multiple filters; duplicate calls are skipped.


### Model aliases

Use `cls.aliased(query, Model, name="...")` to obtain a SQLAlchemy alias object that is *scoped to the current query*. It mirrors `sqlalchemy.orm.aliased(...)` in signature and behavior, with one additional parameter: `query` (the SQLAlchemy `Query` instance). 

- **Idempotent within the query:** when you call `cls.aliased(...)` with the same `Model` and `name`, you’ll get back the *same alias object* for the lifetime of that query. This enables `_join` / `_outerjoin` to recognize and de-duplicate identical joins.
- **Naming matters:** reuse the *same* `name` across different filters that refer to the same logical relationship (e.g., `"member_user"`). Different logical roles or different join predicates should use *different* names (e.g., `"author_user"` vs. `"reviewer_user"`).
- **Works with `_join` / `_outerjoin`:** always acquire the alias via `cls.aliased(...)` before joining. The helpers will skip the join if that alias is already present on the query.
- **Do not reuse an alias for different ON conditions:** if two filters need different join predicates, either (a) keep a single join and express the differences in the WHERE clause using the same alias, or (b) create a second alias with a different `name`.

In short: `cls.aliased(...)` is the canonical way to declare and *reuse* aliases across multiple filters operating on the same query, ensuring stable, duplicate-free JOINs.



## Default filters (_default_filter)

You can define a `_default_filter` on your FilterSet to always apply a condition, even when no `filters` argument is provided.

- If your default condition doesn't need joins, return a SQLAlchemy clause.
- If it needs joins, return a tuple `(query, clause)`, same as in “filters that require join”.
- Default filters are applied to both top-level fields and nested GraphQL connections.

Example (no join):
```python
class UserFilter(FilterSet):
    @staticmethod
    def _default_filter(info, query):
        # Only active users by default
        return User.is_active.is_(True)

    class Meta:
        model = User
        fields = {'username': ['eq', 'ilike']}
```

With a join:
```python
class MembershipFilter(FilterSet):
    @classmethod
    def _default_filter(cls, info, query):
        m = cls.aliased(query, Membership, name='only_mods')
        query = cls._join(query, m, and_(User.id == m.user_id, m.is_moderator.is_(True)))
        return query, m.id.isnot(None)

    class Meta:
        model = Membership
        fields = {}
```

Effect in GraphQL (applies even without passing `filters`):
```graphql
{
  allUsers {
    edges { node { id username } }
  }
  # Also works for nested connections:
  group(id: "...") {
    users {
      edges { node { id username } }
    }
  }
}
```

# Features

## Filter registration and nested fields filters

Filters can be registered for each SQLAlchemy model in a subclass of `FilterableConnectionField`.

Register your filters by inheriting `FilterableConnectionField` and setting `filters` (key - SQLAlchemy model, value - FilterSet object).

```python
class CustomField(FilterableConnectionField):
    filters = {
        User: UserFilter(),
    }
```

Overriding `SQLAlchemyObjectType.connection_field_factory` allows you to generate nested connections with filters.

```python
class UserNode(SQLAlchemyObjectType):
    class Meta:
        model = User
        interfaces = (Node,)
        connection_field_factory = CustomField.factory
```

**Important:**
  1. Pagination (first/after, last/before) is performed in Python (keep this in mind when working with large amounts of data)
  1. Nested filters work via dataloaders
  1. This module optimizes one-to-many relationships, to optimize many-to-one relationships use [sqlalchemy_bulk_lazy_loader](https://github.com/operator/sqlalchemy_bulk_lazy_loader)
  1. Nested filters require `graphene_sqlalchemy>=2.1.2`


### Example
```python
# Filters

class UserFilter(FilterSet):
   class Meta:
       model = User
       fields = {'is_active': [...]}
       


class CustomField(FilterableConnectionField):
    filters = {
        User: UserFilter(),
    }


# Nodes

class UserNode(SQLAlchemyObjectType):
    class Meta:
        model = User
        interfaces = (Node,)
        connection_field_factory = CustomField.factory


class GroupNode(SQLAlchemyObjectType):
    class Meta:
        model = Group
        interfaces = (Node,)
        connection_field_factory = CustomField.factory


# Connections

class UserConnection(Connection):
    class Meta:
        node = UserNode


class GroupConnection(Connection):
    class Meta:
        node = GroupNode


# Query

class Query(ObjectType):
    all_users = CustomField(UserConnection)
    all_groups = CustomField(GroupConnection)

```

```graphql
{
  allUsers (filters: {isActive: true}){
    edges { node { id } }
  }
  allGroups {
    edges {
      node {
        users (filters: {isActive: true}) {
          edges { node { id } }
        }
      }
    }
  }
}
```

## Rename GraphQL filter field

```python
class CustomField(FilterableConnectionField):
    filter_arg = 'where'


class Query(ObjectType):
    all_users = CustomField(UserConnection, where=UserFilter())
    all_groups = FilterableConnectionField(GroupConnection, filters=GroupFilter())

```

```graphql
{
  allUsers (where: {isActive: true}){
    edges { node { id } }
  }
  allGroups (filters: {nameIn: ["python", "development"]}){
    edges { node { id } }
  }
}
```


## Rename expression

```python
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

```

```graphql
{
  allUsers (filters: {iNeverAskedForThis: {firstNameEqual: "Adam", lastNameEqual: "Jensen"}}){
    edges { node { id } }
  }
}
```


## Custom shortcut value

```python
class BaseFilter(FilterSet):
    ALL = '__all__'

    class Meta:
        abstract = True


class UserFilter(BaseFilter):
    class Meta:
        model = User
        fields = {'username': '__all__'}

```


## Localization of documentation

```python
class BaseFilter(FilterSet):
    DESCRIPTIONS = {
        'eq': 'Полностью совпадает.',
        'ne': 'Не совпадает.',
        'like': 'Регистрозависимая проверка строки по шаблону.',
        'ilike': 'Регистронезависимая проверка строки по шаблону.',
        'is_null': 'Равно ли значение `null`. Принимает `true` или `false`.',
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

```


## Custom expression

```python
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
```

```graphql
{
  allPosts (filters: {createdToday: false, updatedToday: true}){
    edges { node { id } }
  }
}
```


## Custom column types
`ALLOWED_FILTERS` and `EXTRA_ALLOWED_FILTERS` only affect shortcut.

If you do not use the shortcut, you can skip the next steps described in the section.

```python
class MyString(types.String):
    pass


class BaseFilter(FilterSet):
    # You can override all allowed filters
    # ALLOWED_FILTERS = {types.Integer: ['eq']}
    
    # Or add new column type
    EXTRA_ALLOWED_FILTERS = {MyString: ['eq']}

    class Meta:
        abstract = True

```
