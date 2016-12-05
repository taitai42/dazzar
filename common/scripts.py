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
    """Make the user with the specified steam_id an Admin. Useful for the first admin.

    Args:
        steam_id: user steam id (as 64bits) to make admin.
    """
    user = db.session().query(User).filter_by(id=steam_id).first()
    if user is None:
        print('No user to raise admin.')
    else:
        user.give_permission(constants.PERMISSION_ADMIN, True)
        db.session().commit()


@manager.command
def recompute_scoreboards():
    """Delete all current scoreboard aggregates and rebuild them from match data."""

    # Delete scoreboards
    Scoreboard.query.delete()
    db.session.commit()

    # Recreate user current scoreboard
    for user in User.query.filter(User.section != None).all():
        scoreboard = Scoreboard(user=user, ladder_name=user.section)
        db.session.add(scoreboard)

    # Replay all games
    for match in Match.query.order_by(Match.created).all():
        for player in match.players:

            scoreboard = player.player.scoreboards.filter_by(ladder_name=match.section).first()
            if scoreboard is None:
                scoreboard = Scoreboard(user=player.player, ladder_name=match.section)
                db.session.add(scoreboard)

            if player.is_dodge:
                player.mmr_before = scoreboard.mmr
                player.mmr_after = max(player.mmr_before - 150, 0)
                scoreboard.mmr = player.mmr_after
                scoreboard.dodge += 1
            elif player.is_leaver:
                player.mmr_before = scoreboard.mmr
                player.mmr_after = max(player.mmr_before - 300, 0)
                scoreboard.mmr = player.mmr_after
                scoreboard.leave += 1
                if match.radiant_win is not None:
                    scoreboard.matches += 1
            else:
                if match.radiant_win is not None:
                    scoreboard.matches += 1
                    if (match.radiant_win and player.is_radiant) or (not match.radiant_win and not player.is_radiant):
                        player.mmr_before = scoreboard.mmr
                        player.mmr_after = player.mmr_before + 50
                        scoreboard.mmr = player.mmr_after
                        scoreboard.win += 1
                    else:
                        player.mmr_before = scoreboard.mmr
                        player.mmr_after = max(player.mmr_before - 50, 0)
                        scoreboard.mmr = player.mmr_after
                        scoreboard.loss += 1
    db.session.commit()


#######################
# Setup Manage Script #
#######################


if __name__ == '__main__':
    manager.run()
