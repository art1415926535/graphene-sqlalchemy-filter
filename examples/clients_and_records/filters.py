# Project
from graphene_sqlalchemy_filter import FilterableConnectionField, FilterSet
from models import Clients, Records


class ClientsFilter(FilterSet):
    class Meta:
        model = Clients
        fields = {'name': ['eq', 'ne', 'in', 'ilike']}


class RecordsFilter(FilterSet):
    class Meta:
        model = Records
        fields = {'id': [...]}


class MyFilterableConnectionField(FilterableConnectionField):
    filters = {Clients: ClientsFilter(), Records: RecordsFilter()}
