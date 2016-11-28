import math
import logging

from flask_script import Manager

from web.web_application import app, db
from common.models import User, Scoreboard, Match
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
def migration_script_1():
    """Temp migration script.
    """

    # Clean scoreboard

    for scoreboard in Scoreboard.query:
        db.session.delete(scoreboard)
    db.session.commit()

    # Refresh sections
    for user in User.query:
        if user.solo_mmr is not None:
            if user.solo_mmr > 5000:
                user.section = constants.LADDER_HIGH
            elif user.solo_mmr < 3000:
                if user.section is None:
                    user.section = constants.LADDER_LOW
            else:
                if user.section != constants.LADDER_HIGH:
                    user.section = constants.LADDER_MEDIUM

        # Detect vouched
        if user.has_permission(constants.PERMISSION_PLAY_VIP):
            user.section = constants.LADDER_HIGH

        # If no right to play
        if user.section is None:
            continue

        # Create scoreboard
        scoreboard = user.scoreboards.filter_by(ladder_name=user.section).first()
        if scoreboard is None:
            scoreboard = Scoreboard(user, user.section)
            db.session.add(scoreboard)
    db.session.commit()

    # Replay matches to update data and mmr, everyone starts at 5K
    for match in Match.query.order_by(Match.created):
        match.section = constants.LADDER_HIGH
        match.radiant_win = None

        for player in match.players:
            user = player.player
            scoreboard = user.scoreboards.filter_by(ladder_name=match.section).first()
            if scoreboard is None:
                continue
            if player.mmr_after == player.mmr_before - 150:
                player.is_dodge = True
                scoreboard.dodge += 1
                player.mmr_before = scoreboard.mmr
                player.mmr_after = player.mmr_before - 150
                scoreboard.mmr = player.mmr_after
            elif player.mmr_after == player.mmr_before - 300:
                player.is_leave = True
                scoreboard.matches += 1
                scoreboard.leave += 1
                player.mmr_before = scoreboard.mmr
                player.mmr_after = player.mmr_before - 300
                scoreboard.mmr = player.mmr_after
            elif player.mmr_after == player.mmr_before + 50:
                match.radiant_win = player.is_radiant
                scoreboard.matches += 1
                scoreboard.win += 1
                player.mmr_before = scoreboard.mmr
                player.mmr_after = player.mmr_before + 50
                scoreboard.mmr = player.mmr_after
            elif player.mmr_after == player.mmr_before - 50:
                match.radiant_win = not player.is_radiant
                scoreboard.matches += 1
                scoreboard.loss += 1
                player.mmr_before = scoreboard.mmr
                player.mmr_after = player.mmr_before - 50
                scoreboard.mmr = player.mmr_after
            else:
                player.mmr_before = scoreboard.mmr
                player.mmr_after = scoreboard.mmr
        db.session.commit()


#######################
# Setup Manage Script #
#######################


if __name__ == '__main__':
    manager.run()
