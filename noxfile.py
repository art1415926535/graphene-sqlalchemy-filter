# Project
import nox


module = 'graphene_sqlalchemy_filter'
tests = 'tests'
dirs = [module, tests]


@nox.session(python=['3.6', '3.7'])
def test(session):
    session.install('pytest', 'pytest-cov')
    session.run('pip', 'install', '-e', '.')
    session.run(
        'pytest',
        '--cov-report',
        'term-missing',
        '--cov',
        *dirs,
        *session.posargs,
    )


@nox.session(python='3.6')
def lint(session):
    session.install('flake8', 'black', 'isort')

    session.run('black', '--check', '-l', '79', '-S', *dirs)
    session.run('isort', '--check-only', '-rc', *dirs)
    session.run('flake8', '--show-source', '--statistics', *dirs)
