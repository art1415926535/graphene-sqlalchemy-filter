# GraphQL
import graphene

# Project
from graphene_sqlalchemy_filter import FilterSet
from models import User


class UserFilter(FilterSet):
    is_admin = graphene.Boolean(description='username = admin')

    @staticmethod
    def is_admin_filter(info, query, value):
        """Simple filter return only clause."""
        if value:
            return User.username == 'admin'
        else:
            return User.username != 'admin'

    class Meta:
        model = User
        fields = {
            'username': ['eq', 'ne', 'in', 'ilike'],
            'balance': [...],
        }
