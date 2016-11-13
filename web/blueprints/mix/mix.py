from datetime import datetime, timedelta

import logging

from flask import Blueprint, jsonify, request, url_for, redirect, render_template
from flask_login import current_user

from common.models import db, UserMixDetail

def make_blueprint():

    mix_blueprint = Blueprint('mix_blueprint', __name__, template_folder='templates')

    @mix_blueprint.route('/mix/users')
    def mix_users():
        return render_template('mix_users.html')

    @mix_blueprint.route('/mix/<int:mix_id>')
    def mix(mix_id):
        """Page to give details of a mix.

        Parameters
            mix_id - mix to return the detailed page of
        """
        mix_requested = UserMixDetail.query.filter_by(id=mix_id).first_or_404()
        return render_template('mix_details.html', mix=mix_requested)

    @mix_blueprint.route('/mix/edit', methods=['GET', 'POST'])
    def mix_edit():
        mix_requested = current_user.user_mix_details

        if request.method == 'GET':
            return render_template('mix_edit.html', mix=mix_requested)
        elif request.method == 'POST':

            if mix_requested is None:
                mix_requested = UserMixDetail()
                current_user.user_mix_details = mix_requested
            mix_requested.title = request.form.get('title') or ''
            mix_requested.goal = request.form.get('goal') or ''
            mix_requested.level = request.form.get('level') or ''
            mix_requested.description = request.form.get('description') or ''
            mix_requested.enabled = request.form.get('add') is not None

            mix_requested.refresh_date = datetime.utcnow()

            db.session().commit()

            if mix_requested.enabled:
                return redirect(url_for('mix_blueprint.mix', mix_id=current_user.id))
            else:
                return render_template('mix_edit.html', mix=mix_requested)

    @mix_blueprint.route('/api/mixs')
    def api_mixs():
        """Endpoint for the datatable to request mixs."""

        draw = request.args.get('draw', '1')
        length = 25
        start = int(request.args.get('start', '0'))

        date_limit = datetime.utcnow() - timedelta(days=7)

        query = UserMixDetail.query\
            .order_by(UserMixDetail.refresh_date)\
            .filter(UserMixDetail.refresh_date > date_limit.isoformat())\
            .filter_by(enabled=True)

        count = query.count()

        query = query.offset(start)\
            .limit(length)

        data = []
        for mix in query.all():
            data.append([mix.user.nickname, mix.goal, mix.level, mix.title, str(mix.id)])
        results = {
            "draw": draw,
            "recordsTotal": count,
            "recordsFiltered": count,
            "data": data
        }
        return jsonify(results)


    return mix_blueprint
