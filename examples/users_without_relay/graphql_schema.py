# GraphQL
import graphene

# Project
import models
from filters import UserFilter


class User(graphene.ObjectType):
    id = graphene.Int()
    username = graphene.String()
    balance = graphene.Int()


class Query(graphene.ObjectType):
    all_users = graphene.List(User, filters=UserFilter())

    def resolve_all_users(self, info, filters=None):
        query = models.User.query
        if filters is not None:
            query = UserFilter.filter(info, query, filters)

        return query


schema = graphene.Schema(query=Query)
