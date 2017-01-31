from datetime import datetime

from flask_script import Manager

from web.web_application import app, db
from common.job_queue import QueueAdapter, JobScan
from common.models import User, Scoreboard, Match, ProfileScanInfo, QueuedPlayer, PlayerInMatch
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

    # Replay all games
    for match in Match.query.order_by(Match.created).all():
        for player in match.players:
            if not player.is_dodge and not player.is_leaver and match.radiant_win is None:
                continue

            scoreboard = player.player.scoreboards.filter_by(ladder_name=match.section).first()
            if scoreboard is None:
                scoreboard = Scoreboard(user=player.player, ladder_name=match.section)
                db.session.add(scoreboard)

            if player.is_dodge:
                scoreboard.points -= 2
                scoreboard.dodge += 1
            elif player.is_leaver:
                scoreboard.points -= 3
                scoreboard.leave += 1
                if match.radiant_win is not None:
                    scoreboard.matches += 1
            else:
                if match.radiant_win is not None:
                    scoreboard.matches += 1
                    if (match.radiant_win and player.is_radiant) or (not match.radiant_win and not player.is_radiant):
                        scoreboard.points += 1
                        scoreboard.win += 1
                    else:
                        scoreboard.loss += 1
    db.session.commit()


@manager.command
def scan_all_users():
    """Queue the refresh scan of all users."""
    job_queue = QueueAdapter(app.config['RABBITMQ_LOGIN'], app.config['RABBITMQ_PASSWORD'])
    for user in User.query.all():
        if user.profile_scan_info is None:
            user.profile_scan_info = ProfileScanInfo(user)

        user.profile_scan_info.last_scan_request = datetime.utcnow()
        job_queue.produce(JobScan(steam_id=user.id))

    db.session.commit()


#######################
# Setup Manage Script #
#######################


if __name__ == '__main__':
    manager.run()
