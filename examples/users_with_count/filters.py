# Project
from graphene_sqlalchemy_filter import FilterableConnectionField, FilterSet
from models import User


class UserFilter(FilterSet):
    class Meta:
        model = User
        fields = {'username': ['eq']}


class MyFilterableConnectionField(FilterableConnectionField):
    filters = {
        User: UserFilter(),
    }
