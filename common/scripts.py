import math

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
    user = db.session().query(User).filter_by(id=steam_id).first()
    if user is None:
        print('No user to raise admin.')
    else:
        user.give_permission(constants.PERMISSION_ADMIN, True)
        db.session().commit()


@manager.command
def reset_vip_mmr():
    """Reset all VIP MMR to the default value.
    """
    for user in db.session().query(User).all():
        if user.solo_mmr is None or user.solo_mmr < 5000:
            user.vip_mmr = None
            user.give_permission(constants.PERMISSION_PLAY_VIP, False)
        else:
            user.vip_mmr = 2000 + math.floor((user.solo_mmr - 5000)/2)
    db.session().commit()


#######################
# Setup Manage Script #
#######################


if __name__ == '__main__':
    manager.run()
