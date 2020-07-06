import nox


module = 'graphene_sqlalchemy_filter'
tests = 'tests'
dirs = [module, tests]


@nox.session(python='3.7')
def lint(session):
    session.install('flake8', 'black', 'isort==4.3.21')

    session.run('black', '--check', '-l', '79', '-S', *dirs)
    session.run('isort', '--check-only', *dirs)
    session.run('flake8', '--show-source', '--statistics', *dirs)


@nox.session(python=['3.6', '3.7'])
@nox.parametrize("graphene_sqlalchemy", ['==2.1.0', '==2.2.0', '==2.2.1'])
def test(session, graphene_sqlalchemy):
    session.install('pytest')
    session.install('-e', '.')
    session.install(f'graphene-sqlalchemy{graphene_sqlalchemy}')
    session.run('pytest', *dirs, *session.posargs)


@nox.session(python='3.7')
def coverage(session):
    session.install('pytest', 'pytest-cov', 'coverage<5.0.0')
    session.install('-e', '.')
    session.run(
        'pytest',
        '--cov-report',
        'term-missing',
        '--cov',
        *dirs,
        *session.posargs,
    )
