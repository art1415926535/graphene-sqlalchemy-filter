from sqlalchemy import Column, Integer, String
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Query, declarative_base

from graphene_sqlalchemy_filter import FilterSet


Base = declarative_base()


class Post(Base):
    __tablename__ = "post"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tags = Column(ARRAY(String(10)))


class PostFilter(FilterSet):
    class Meta:
        model = Post
        fields = {"tags": [...]}


def test_eq(info):
    filters = {"tags": ["a", "b"]}
    post_query = Query(Post)
    query = PostFilter.filter(info, post_query, filters)

    sql = str(query.statement.compile(dialect=postgresql.dialect()))
    ok = (
        "SELECT post.id, post.tags \n"
        "FROM post \n"
        "WHERE post.tags = CAST(%(param_1)s::VARCHAR(10)[] AS VARCHAR(10)[])"
    )
    assert sql == ok


def test_contained_by(info):
    filters = {"tags_contained_by": ["a", "b"]}
    post_query = Query(Post)
    query = PostFilter.filter(info, post_query, filters)

    sql = str(query.statement.compile(dialect=postgresql.dialect()))
    ok = (
        "SELECT post.id, post.tags \n"
        "FROM post \n"
        "WHERE post.tags <@ CAST(%(param_1)s::VARCHAR(10)[] AS VARCHAR(10)[])"
    )
    assert sql == ok


def test_contains(info):
    filters = {"tags_contains": ["a", "b"]}
    post_query = Query(Post)
    query = PostFilter.filter(info, post_query, filters)

    sql = str(query.statement.compile(dialect=postgresql.dialect()))
    ok = (
        "SELECT post.id, post.tags \n"
        "FROM post \n"
        "WHERE post.tags @> CAST(%(param_1)s::VARCHAR(10)[] AS VARCHAR(10)[])"
    )
    assert sql == ok


def test_overlap(info):
    filters = {"tags_overlap": ["a", "b"]}
    post_query = Query(Post)
    query = PostFilter.filter(info, post_query, filters)

    sql = str(query.statement.compile(dialect=postgresql.dialect()))
    ok = (
        "SELECT post.id, post.tags \n"
        "FROM post \n"
        "WHERE post.tags && CAST(%(param_1)s::VARCHAR(10)[] AS VARCHAR(10)[])"
    )
    assert sql == ok
