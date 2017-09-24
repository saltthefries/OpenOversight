from getpass import getpass
import imp
from migrate.versioning import api
import sys

from flask_script import Manager, Server, Shell

from app import app
from app.models import db, User
from app.config import config


manager = Manager(app)
manager.add_command("runserver", Server(host="0.0.0.0", port=3000))


def make_shell_context():
    return dict(app=app, db=db)


manager.add_command("shell", Shell(make_context=make_shell_context))


@manager.command
def makemigrations(config_name="default"):
    """Make database migrations"""

    SQLALCHEMY_MIGRATE_REPO = config['default'].SQLALCHEMY_MIGRATE_REPO
    SQLALCHEMY_DATABASE_URI = config['default'].SQLALCHEMY_DATABASE_URI

    v = api.db_version(SQLALCHEMY_DATABASE_URI, SQLALCHEMY_MIGRATE_REPO)
    migration = SQLALCHEMY_MIGRATE_REPO + ('/versions/%03d_migration.py' % (v + 1))
    tmp_module = imp.new_module('old_model')
    old_model = api.create_model(SQLALCHEMY_DATABASE_URI, SQLALCHEMY_MIGRATE_REPO)
    exec(old_model, tmp_module.__dict__)
    script = api.make_update_script_for_model(SQLALCHEMY_DATABASE_URI, SQLALCHEMY_MIGRATE_REPO, tmp_module.meta, db.metadata)
    open(migration, "wt").write(script)

    print('New migration saved as ' + migration)
    print('Run python manage.py upgrade_db to upgrade the database')


@manager.command
def migrate(config_name="default"):
    """Migrate/upgrade the database"""

    SQLALCHEMY_MIGRATE_REPO = config['default'].SQLALCHEMY_MIGRATE_REPO
    SQLALCHEMY_DATABASE_URI = config['default'].SQLALCHEMY_DATABASE_URI
    api.upgrade(SQLALCHEMY_DATABASE_URI, SQLALCHEMY_MIGRATE_REPO)
    v = api.db_version(SQLALCHEMY_DATABASE_URI, SQLALCHEMY_MIGRATE_REPO)
    print('Current database version: ' + str(v))


@manager.command
def downgrade_db(config_name="default"):
    """Downgrade the database"""

    SQLALCHEMY_MIGRATE_REPO = config['default'].SQLALCHEMY_MIGRATE_REPO
    SQLALCHEMY_DATABASE_URI = config['default'].SQLALCHEMY_DATABASE_URI

    v = api.db_version(SQLALCHEMY_DATABASE_URI, SQLALCHEMY_MIGRATE_REPO)
    api.downgrade(SQLALCHEMY_DATABASE_URI, SQLALCHEMY_MIGRATE_REPO, v - 1)
    v = api.db_version(SQLALCHEMY_DATABASE_URI, SQLALCHEMY_MIGRATE_REPO)
    print('Current database version: ' + str(v))


@manager.command
def make_admin_user():
    "Add confirmed administrator account"
    while True:
        username = raw_input("Username: ")
        user = User.query.filter_by(username=username).one_or_none()
        if user:
            print "Username is already in use"
        else:
            break

    while True:
        email = raw_input("Email: ")
        user = User.query.filter_by(email=email).one_or_none()
        if user:
            print "Email address already in use"
        else:
            break

    while True:
        password = getpass("Password: ")
        password_again = getpass("Type your password again: ")

        if password == password_again:
            break
        print "Passwords did not match"

    u = User(username=username, email=email, password=password,
             confirmed=True, is_administrator=True)
    db.session.add(u)
    db.session.commit()
    print "Administrator {} successfully added".format(username)
    app.logger.info('Administrator {} added with email {}'.format(username,
                                                                  email))


@manager.command
def link_images_to_department():
    """Link existing images to first department"""
    from app.models import Image, db
    images = Image.query.all()
    print "Linking images to first department:"
    for image in images:
        if not image.department_id:
            sys.stdout.write(".")
            image.department_id = 1
        else:
            print "Skipped! Department already assigned"
    db.session.commit()


if __name__ == "__main__":
    manager.run()
