import sqlite3

import pytest

from graphene_sqlalchemy.utils import EnumValue

from graphene_sqlalchemy_filter.connection_field import (
    FilterableConnectionField,
    ModelLoader,
    NestedFilterableConnectionField,
)
from graphene_sqlalchemy_filter.versions import gsqla_version_lt_2_1_2

from .models import Article, Author, Group, User


@pytest.mark.skipif(gsqla_version_lt_2_1_2, reason="not used")
@pytest.mark.skipif(
    # https://stackoverflow.com/questions/45335276/sqlite-select-query-including-a-values-in-the-where-clause-returns-correctly-w
    sqlite3.sqlite_version_info < (3, 15, 2),
    reason="requires sqlite 3.15.2 or higher",
)
def test_composite_pk(info_builder, session):
    info = info_builder(path=["author"], field_name="articles")

    author = Author(first_name="Ally", last_name="A")
    session.add(author)
    article_1 = Article(
        author_first_name=author.first_name,
        author_last_name=author.last_name,
        text="abc",
    )
    article_2 = Article(
        author_first_name=author.first_name,
        author_last_name=author.last_name,
        text="123",
    )
    session.bulk_save_objects([article_1, article_2])
    session.commit()

    sorting = EnumValue("TEXT_ASC", Article.text.asc())
    ml = ModelLoader(Author, Article, info, {"sort": [sorting]})
    assert set(ml.parent_model_pks) == {"first_name", "last_name"}

    key = ml.parent_model_object_to_key(author)
    a1, a2 = ml.load(key).get()
    assert a1.text == "123"
    assert a2.text == "abc"


@pytest.mark.skipif(gsqla_version_lt_2_1_2, reason="not used")
def test_custom_filter_arg():
    custom_filter_arg = "where"

    class CustomFiled(FilterableConnectionField):
        filter_arg = custom_filter_arg
        filters = {None: None}  # bool(filters) is True

    assert CustomFiled.filter_arg == custom_filter_arg

    model_loader_class = CustomFiled.factory.model_loader_class
    assert model_loader_class.filter_arg == custom_filter_arg


@pytest.mark.skipif(gsqla_version_lt_2_1_2, reason="not used")
def test_model_dataloader_creation(info_builder):
    info = info_builder(
        path=["user", "edges", 0, "node", "groups"], field_name="groups"
    )
    get_data_loader = (
        NestedFilterableConnectionField._get_or_create_data_loader
    )

    model_loader_1 = get_data_loader(
        User(), Group, info, {"filters": {"name": "group_name"}}
    )
    assert isinstance(model_loader_1, ModelLoader)

    model_loader_2 = get_data_loader(
        User(), Group, info, {"filters": {"name": "group_name"}}
    )
    assert model_loader_1 is model_loader_2

    info = info_builder(
        path=["user", "edges", 0, "node", "anotherGroups"], field_name="groups"
    )
    model_loader_3 = get_data_loader(
        User(), Group, info, {"filters": {"name": "group_name"}}
    )
    assert model_loader_1 is not model_loader_3


@pytest.mark.skipif(gsqla_version_lt_2_1_2, reason="not used")
def test_flask_context(info_builder):
    class Request:
        pass

    info = info_builder(
        path=["user", "edges", 0, "node", "groups"],
        field_name="groups",
        context=Request(),
    )
    get_data_loader = (
        NestedFilterableConnectionField._get_or_create_data_loader
    )

    model_loader_1 = get_data_loader(
        User(), Group, info, {"filters": {"name": "group_name"}}
    )
    assert isinstance(model_loader_1, ModelLoader)

    model_loader_2 = get_data_loader(
        User(), Group, info, {"filters": {"name": "group_name"}}
    )
    assert model_loader_1 is model_loader_2

    info = info_builder(
        path=["user", "edges", 0, "node", "anotherGroups"],
        field_name="groups",
        context=Request(),
    )
    model_loader_3 = get_data_loader(
        User(), Group, info, {"filters": {"name": "group_name"}}
    )
    assert model_loader_1 is not model_loader_3
