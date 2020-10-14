# Third Party
from flask import Flask
from flask_graphql import GraphQLView

# Project
from database import db_session, init_db
from graphql_schema import schema


app = Flask(__name__)
app.debug = True

app.add_url_rule(
    '/graphql',
    view_func=GraphQLView.as_view('graphql', schema=schema, graphiql=True),
)


@app.teardown_appcontext
def shutdown_session(exception=None):
    db_session.remove()


if __name__ == '__main__':
    init_db()
    app.run()
