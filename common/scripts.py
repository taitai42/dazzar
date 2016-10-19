from flask_script import Manager

from web.web_application import app, db
from common.models import User
import common.constants as constants

manager = Manager(app)


###########
# Scripts #
###########


@manager.option('-i', '--id', dest='steam_id', default='76561197961298382')
def make_admin(steam_id):
    """Make the user with the specified steam_id an Admin.
    Useful for the first admin.

    Attributes:
        steam_id - user steam id to make admin
    """
    user = User.query.filter_by(id=steam_id).first()
    if user is None:
        print('No user to raise admin.')
    else:
        user.give_permission(constants.PERMISSION_ADMIN)
        db.session().commit()


#######################
# Setup Manage Script #
#######################


if __name__ == '__main__':
    manager.run()
