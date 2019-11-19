# Third Party
import pytest

# Database
from sqlalchemy import Column, Integer
from sqlalchemy.ext.declarative import declarative_base

# Project
from graphene_sqlalchemy_filter.connection_field import (
    FilterableConnectionField,
    ModelLoader,
    ModelNotSupported,
    NestedFilterableConnectionField,
    graphene_sqlalchemy_version_lt_2_1_2,
)
from tests.models import User


@pytest.mark.skipif(graphene_sqlalchemy_version_lt_2_1_2, reason='not used')
def test_wrong_pk(info):
    class TestModel(declarative_base()):
        __tablename__ = 'test_model'
        id_1 = Column(Integer, primary_key=True)
        id_2 = Column(Integer, primary_key=True)

    with pytest.raises(ModelNotSupported):
        ModelLoader(TestModel, info, {})


@pytest.mark.skipif(graphene_sqlalchemy_version_lt_2_1_2, reason='not used')
def test_custom_filter_arg():
    custom_filter_arg = 'where'

    class CustomFiled(FilterableConnectionField):
        filter_arg = custom_filter_arg
        filters = {None: None}  # bool(filters) is True

    assert CustomFiled.filter_arg == custom_filter_arg

    model_loader_class = CustomFiled.factory.model_loader_class
    assert model_loader_class.filter_arg == custom_filter_arg


@pytest.mark.skipif(graphene_sqlalchemy_version_lt_2_1_2, reason='not used')
def test_model_dataloader_creation(info):
    info.path = ['user', 'edges', 0, 'node', 'groups']
    info.field_name = 'groups'
    get_data_loader = (
        NestedFilterableConnectionField._get_or_create_data_loader
    )

    model_loader_1 = get_data_loader(
        User(), info, {'filters': {'username': 'user_1'}}
    )
    assert isinstance(model_loader_1, ModelLoader)

    model_loader_2 = get_data_loader(
        User(), info, {'filters': {'username': 'user_1'}}
    )
    assert model_loader_1 is model_loader_2

    info.path = ['user', 'edges', 0, 'node', 'anotherGroups']
    model_loader_3 = get_data_loader(
        User(), info, {'filters': {'username': 'user_1'}}
    )
    assert model_loader_1 is not model_loader_3


@pytest.mark.skipif(graphene_sqlalchemy_version_lt_2_1_2, reason='not used')
def test_flask_context(info):
    class Request:
        pass

    info.path = ['user', 'edges', 0, 'node', 'groups']
    info.field_name = 'groups'
    info.context = Request()
    get_data_loader = (
        NestedFilterableConnectionField._get_or_create_data_loader
    )

    model_loader_1 = get_data_loader(
        User(), info, {'filters': {'username': 'user_1'}}
    )
    assert isinstance(model_loader_1, ModelLoader)

    model_loader_2 = get_data_loader(
        User(), info, {'filters': {'username': 'user_1'}}
    )
    assert model_loader_1 is model_loader_2

    info.path = ['user', 'edges', 0, 'node', 'anotherGroups']
    model_loader_3 = get_data_loader(
        User(), info, {'filters': {'username': 'user_1'}}
    )
    assert model_loader_1 is not model_loader_3
