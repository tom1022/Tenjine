import os
from flask import Blueprint, render_template, request, redirect, send_file, abort, session, make_response, url_for
from flask_paginate import Pagination, get_page_parameter
from flask_login import current_user
from sqlalchemy import desc, not_, func, case
from datetime import datetime
from dbapp import app, db
from dbapp.models.tables import FILES, TAGS, VOTES, NEWS, STUDIES, FILEACCESS, FILEPREVIEW
from dbapp.tools import convertMarkdown, SearchEngine, FilterStudyFiles, FilterStudiesHiddenFiles
from dbapp.models.tables import FILES, TAGS, VOTES, NEWS, STUDIES, FILEACCESS, FILEPREVIEW, STUDYGRAVES, FILEGRAVES

user_bp = Blueprint('user_bp', __name__, template_folder='templates')

@user_bp.route('/')
def index():
    access_rank = STUDIES.query.join(FILES).filter(STUDIES.grave_data==False).group_by(STUDIES.id).order_by(desc(func.sum(FILES.access_count))).limit(10).all()
    preview_rank = STUDIES.query.join(FILES).filter(STUDIES.grave_data==False).group_by(STUDIES.id).order_by(desc(func.sum(FILES.preview_count))).limit(10).all()
    helpful_rank = db.session.query(
        STUDIES.id,
        STUDIES.name,
        func.count(VOTES.study_id),
        func.sum(case((VOTES.helpful == True, 1), (VOTES.helpful == False, -1), else_=0)),
    ).outerjoin(
        VOTES,
        VOTES.study_id == STUDIES.id
    ).filter(
        STUDIES.grave_data == False
    ).group_by(
        STUDIES.id
    ).order_by(
        func.sum(case((VOTES.helpful == True, 1), (VOTES.helpful == False, -1), else_=0)).desc()
    ).limit(10)

    return render_template(
        'user-pages/index.html',
        title='トップページ',
        access_rank=access_rank,
        preview_rank=preview_rank,
        helpful_rank=helpful_rank
    )

@user_bp.route('/taglist')
def taglist():
    tags = TAGS.query.order_by(TAGS.name).all()
    return render_template('user-pages/taglist.html', title="タグ一覧", tags=tags)

@user_bp.route('/study/<id>')
def study(id):
    data = STUDIES.query.filter(STUDIES.id == id).one_or_none()
    if data is None:
        abort(404)

    grave = STUDYGRAVES.query.filter(STUDYGRAVES.study_id==data.id).one_or_none()
    admin = False
    if current_user.is_authenticated:
        admin = current_user.has_role('Admin')
    if grave is not None and not admin:
        return render_template("user-pages/grave.html", title="削除された研究", data=grave), 404

    votes = VOTES.query.filter(VOTES.study_id==data.id)
    helpful_votes = votes.filter(VOTES.helpful==True).count()
    unhelpful_votes = votes.count() - helpful_votes

    if current_user.is_authenticated:
        editable = id in [x.id for x in current_user.studies] or current_user.has_role('Admin')
    else:
        editable = False

    user_vote = None
    if current_user.is_authenticated:
        user_vote = VOTES.query.filter(VOTES.user_id==current_user.id, VOTES.study_id==data.id).one_or_none()

    summary = convertMarkdown(data.raw_markdown)

    return render_template(
        'user-pages/study.html',
        title=data.name,
        data=FilterStudyFiles(data, admin),
        summary=summary,
        helpful_votes=helpful_votes,
        unhelpful_votes=unhelpful_votes,
        user_vote=user_vote,
        editable=editable
    )

@user_bp.route('/file/<id>')
def file(id):
    data = FILES.query.filter(FILES.id == id).one_or_none()
    if data is None:
        abort(404)

    grave = FILEGRAVES.query.filter(FILEGRAVES.file_id==data.id).one_or_none()
    admin = False
    if current_user.is_authenticated:
        admin = current_user.has_role('Admin')
    if grave is not None and not admin:
        return render_template("user-pages/grave.html", title="削除されたファイル", data=grave), 404
    parent_grave = STUDYGRAVES.query.filter(STUDYGRAVES.study_id==data.study_id).one_or_none()
    if parent_grave is not None and not admin:
        return render_template("user-pages/grave.html", title="削除された研究", data=parent_grave), 404


    # セッションにアクセス情報がまだ存在しない場合、アクセス情報をセッションに追加
    if 'accessed_files' not in session:
        session['accessed_files'] = {}

    # ファイルIDがアクセス情報にない場合、アクセスカウントを増加
    if data.id not in session['accessed_files']:
        # ここでアクセスカウントを増加させる操作を行う
        data.access_count += 1
        session['accessed_files'][data.id] = True

        if current_user.is_authenticated:
            # 閲覧履歴を追加
            access_history = FILEACCESS(
                user_id=current_user.id,
                file_id=data.id
            )
            db.session.add(access_history)

        # データベースに変更を保存
        db.session.commit()

    summary = data.summary.split('\n')
    filetypes = ['ポスター発表','プレゼンテーション', '報告書', '要旨', '動画', '画像']
    filetype = filetypes[data.type-1]

    return render_template(
        'user-pages/file.html',
        title=data.name,
        data=data,
        filetype=filetype,
        summary=summary,
    )

@user_bp.route('/file/<id>/preview')
def preview(id):
    data = FILES.query.filter(FILES.id == id).one_or_none()
    if data is None:
        abort(404)

    grave = FILEGRAVES.query.filter(FILEGRAVES.file_id==data.id).one_or_none()
    admin = False
    if current_user.is_authenticated:
        admin = current_user.has_role('Admin')
    if grave is not None and not admin:
        return render_template("user-pages/grave.html", title="削除されたファイル", data=grave), 404

    # セッションにプレビュー情報がまだ存在しない場合、プレビュー情報をセッションに追加
    if 'previewed_files' not in session:
        session['previewed_files'] = {}

    # ファイルIDがプレビュー情報にない場合、プレビューカウントを増加
    if data.id not in session['previewed_files']:
        # ここでプレビューカウントを増加させる操作を行う
        data.preview_count += 1
        session['previewed_files'][data.id] = True

        if current_user.is_authenticated:
            # 閲覧履歴を追加
            previewed_history = FILEPREVIEW(
                user_id=current_user.id,
                file_id=data.id
            )
            db.session.add(previewed_history)

        # データベースに変更を保存
        db.session.commit()
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], data.study.id, data.filename)
    if not os.path.isfile(filepath):
        abort(500)

    file_extension = filepath.split(".")[-1]
    if file_extension == "pdf":
        mimetype = 'application/pdf'
    elif file_extension == "mp4":
        mimetype = 'video/mp4'
    elif file_extension == "png":
        mimetype = 'image/png'

    return make_response(
        send_file(
            filepath,
            as_attachment=False,
            download_name=data.name,
            mimetype=mimetype
        )
    )

@user_bp.route('/news/')
def newslist():
    newslist = NEWS.query.order_by(NEWS.create_at.desc()).all()
    page = request.args.get(get_page_parameter(), type=int, default=1)
    rows = newslist[(page - 1)*10: page*10]
    pagination = Pagination(page=page, total=len(newslist), per_page=10, css_framework="BULMA")

    return render_template('user-pages/newslist.html', title="お知らせ", rows=rows, pagination=pagination)

@user_bp.route('/news/<id>')
def news(id=''):
    news = NEWS.query.filter(NEWS.id==id).one_or_none()
    if news is None:
        abort(404)

    news_text = convertMarkdown(news.raw_markdown)

    title = news.name

    return render_template('user-pages/news.html', title=title, news_text=news_text, news=news)

@user_bp.route('/search', methods=['GET'])
def search():
    raw_query = request.args.get('query', default="")

    create_date_start = request.args.get('create_date_start')
    create_date_start = create_date_start if create_date_start else "0001-01-01"

    create_date_end = request.args.get('create_date_end')
    create_date_end = create_date_end if create_date_end else "9999-12-31"

    update_date_start = request.args.get('update_date_start')
    update_date_start = update_date_start if update_date_start else "0001-01-01"

    update_date_end = request.args.get('update_date_end')
    update_date_end = update_date_end if update_date_end else "9999-12-31"

    field = request.args.get('field', default=0, type=int)

    ascending = request.args.get('ascending', default="True") == "True"
    sort_column = request.args.get('sort_column', default="update_at")

    create_at_range = (datetime.strptime(create_date_start, '%Y-%m-%d'), datetime.strptime(create_date_end, '%Y-%m-%d'))
    update_at_range = (datetime.strptime(update_date_start, '%Y-%m-%d'), datetime.strptime(update_date_end, '%Y-%m-%d'))

    admin = False
    if current_user.is_authenticated:
        admin = current_user.has_role('Admin')

    result_pages = SearchEngine(
        search_terms=raw_query,
        ascending=ascending,
        create_at_range=create_at_range,
        update_at_range=update_at_range,
        sort_column=sort_column,
        field=field,
        admin=admin
    )

    page = request.args.get(get_page_parameter(), type=int, default=1)
    per_page = request.args.get('pp', type=int, default=10)
    rows = result_pages[0][(page - 1)*per_page: page*per_page]
    pagination = Pagination(page=page, total=len(result_pages[0]), per_page=per_page, css_framework="BULMA")

    return render_template(
        'user-pages/search.html',
        title=result_pages[1],
        rows=rows,
        pagination=pagination
    )


@user_bp.route('/tag/<id>')
def tag(id=None):
    if id == '' or id is None:
        return redirect(url_for('user_bp.taglist'))
    else:
        results = TAGS.query.filter(TAGS.id==id).one_or_none()

        if results is None:
            abort(404)
        tips = results.tips.split('\n')
        page = request.args.get(get_page_parameter(), type=int, default=1)
        admin = False
        if current_user.is_authenticated:
            admin = current_user.has_role('Admin')

        filtered_studies = []
        for study in results.studies:
            if study.grave_data == False:
                filtered_studies.append(study)

        results.studies = filtered_studies

        studies = FilterStudiesHiddenFiles(results.studies, admin)
        rows = studies[(page - 1)*10: page*10]
        pagination = Pagination(page=page, total=len(studies), per_page=10, css_framework="BULMA")
        return render_template(
            'user-pages/tag.html',
            title=results.name,
            tips=tips,
            flag=1,
            rows=rows,
            pagination=pagination,
            results=results
        )
