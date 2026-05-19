import logging
from flask import Blueprint, render_template, jsonify, request, abort
from flask_login import login_required, current_user
from flask_paginate import get_page_parameter, Pagination
from dbapp import db
from dbapp.models.tables import FILES, STUDIES, VOTES, FILEACCESS

logger = logging.getLogger(__name__)
dashboard_bp = Blueprint('dashboard_bp', __name__, template_folder='templates')


@dashboard_bp.route('/vote', methods=['POST'])
@login_required
def vote():
    study_id = request.json.get('study_id')
    form_helpful = request.json.get('helpful')

    helpful = form_helpful == 'helpful'

    if not STUDIES.query.filter(STUDIES.id == study_id).one_or_none():
        abort(404)

    user_id = current_user.id

    existing_vote = VOTES.query.filter(VOTES.user_id == user_id, VOTES.study_id == study_id).first()
    if existing_vote:
        db.session.delete(existing_vote)
        db.session.commit()

    new_vote = VOTES(user_id=user_id, study_id=study_id, helpful=helpful)
    db.session.add(new_vote)
    db.session.commit()

    helpful_count = VOTES.query.filter(VOTES.study_id == study_id, VOTES.helpful == True).count()
    unhelpful_count = VOTES.query.filter(VOTES.study_id == study_id, VOTES.helpful == False).count()

    return jsonify({
        'user_vote': helpful,
        'helpful': helpful_count,
        'unhelpful': unhelpful_count
    })


@dashboard_bp.route('/mypage', methods=['GET'])
@login_required
def mypage():
    votes = VOTES.query.filter(VOTES.user_id == current_user.id)
    helpful_study_ids = [vote.study_id for vote in votes if vote.helpful][0:5]
    helpful_pages = STUDIES.query.filter(STUDIES.id.in_(helpful_study_ids)).all()
    mystudies = current_user.studies[0:5]
    visited_pages = (
        db.session.query(FILES)
        .join(FILEACCESS, FILEACCESS.file_id == FILES.id)
        .filter(FILEACCESS.user_id == current_user.id)
        .limit(5)
        .all()
    )
    return render_template(
        'logined-pages/mypage.jinja2',
        title='マイページ',
        mystudies=mystudies,
        visited_pages=visited_pages,
        helpful_pages=helpful_pages
    )


@dashboard_bp.route('/mystudies', methods=['GET'])
@login_required
def mystudies():
    page = request.args.get(get_page_parameter(), type=int, default=1)
    results = current_user.studies
    rows = results[(page - 1) * 10: page * 10]
    pagination = Pagination(page=page, total=len(results), per_page=10, css_framework="BULMA")
    return render_template('user-pages/pagelist.jinja2', title='自分の研究', rows=rows, pagination=pagination)


@dashboard_bp.route('/visited_pages', methods=['GET'])
@login_required
def visited_pages():
    page = request.args.get(get_page_parameter(), type=int, default=1)
    results = (
        db.session.query(FILES)
        .join(FILEACCESS, FILEACCESS.file_id == FILES.id)
        .filter(FILEACCESS.user_id == current_user.id)
        .all()
    )
    rows = results[(page - 1) * 10: page * 10]
    pagination = Pagination(page=page, total=len(results), per_page=10, css_framework="BULMA")
    return render_template('user-pages/filelist.jinja2', title='閲覧履歴', rows=rows, pagination=pagination)


@dashboard_bp.route('/helpful_pages', methods=['GET'])
@login_required
def helpful_pages():
    page = request.args.get(get_page_parameter(), type=int, default=1)
    votes = VOTES.query.filter(VOTES.user_id == current_user.id)
    helpful_study_ids = [vote.study_id for vote in votes if vote.helpful]
    helpful_pages = STUDIES.query.filter(STUDIES.id.in_(helpful_study_ids)).all()

    rows = helpful_pages[(page - 1) * 10: page * 10]
    pagination = Pagination(page=page, total=len(helpful_pages), per_page=10, css_framework="BULMA")
    return render_template('user-pages/pagelist.jinja2', title='高評価したページ', rows=rows, pagination=pagination)
