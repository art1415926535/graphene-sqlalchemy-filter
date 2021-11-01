# Database
from sqlalchemy.orm import Query

# Project
from tests import models
from tests.graphql_objects import TaskFilter


def test_sql_query(info):
    filters = {'users': {'username': 'user name'}, 'status_name': 'done'}
    task_query = Query(models.Task)
    query = TaskFilter.filter(info, task_query, filters)
    where_clause = str(query.whereclause)
    ok = (
        '(EXISTS (SELECT 1'
        ' FROM task, task_assignments'
        ' WHERE task.id = task_assignments.task_id AND (EXISTS (SELECT 1'
        ' FROM "user"'
        ' WHERE "user".user_id = task_assignments.user_id AND '
        '"user".username = :username_1)))) AND (EXISTS (SELECT 1'
        ' FROM status, task'
        ' WHERE status.id = task.status_id AND status.name = :name_1))'
    )
    assert where_clause.replace('\n', '') == ok
