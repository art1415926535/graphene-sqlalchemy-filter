# Project
from graphene_sqlalchemy_filter import FilterableConnectionField, FilterSet
from models import TaskModel


class GroupTaskFilter(FilterSet):
    class Meta:
        model = TaskModel
        fields = {
            'title': ['eq'],
            'done': ['eq'],
            'categories': ['eq'],
        }


class GroupFilterableConnectionField(FilterableConnectionField):
    filters = {TaskModel: GroupTaskFilter()}
