import os, json, re
from ulid import ULID
from flask import Blueprint, render_template, jsonify, request, abort, url_for, redirect, flash
from flask_login import login_required, current_user
from flask_paginate import get_page_parameter, Pagination
from werkzeug.utils import secure_filename
from cv2 import VideoCapture
from PIL import Image, UnidentifiedImageError
from datetime import datetime
from dbapp import app, db
from dbapp.models.tables import USERS, FILES, STUDIES, TAGS, VOTES, FILEACCESS
from dbapp.form import UploadForm, StudyForm, AddAuthorForm, DelAuthorForm, FileEditForm
from dbapp.file_operation.pdf import PDF_extractor
from dbapp.tools import wikipedia_summary, sha256_hash, convertMarkdown, FilterStudiesHiddenFiles
from flask import url_for, redirect, flash
from PIL import Image, UnidentifiedImageError
from dbapp.tools import wikipedia_summary, sha256_hash

logined_bp = Blueprint('logined_bp', __name__, template_folder='templates')

@logined_bp.route('/create_study', methods=['GET', 'POST'])
@login_required
def create_study():
    form = StudyForm()
    if request.method == 'GET':
        return render_template('user-pages/create_study.html', title='研究グループの作成', form=form)
    if request.method == 'POST':
        if form.validate_on_submit():
            status = 'success'
            reason = ''

            try:
                form_title = form.title.data
                form_raw_markdown = form.raw_markdown.data
                form_tags = re.sub(r"(\[|'|\]|\s)", '',form.tags.data).split(',')
                form_field = int(form.field.data)
                id = str(ULID())

                user = USERS.query.filter(USERS.id==str(current_user.id)).one()

                tag_list = []
                for tag in form_tags:
                    tag = tag.replace('"', '')
                    check = TAGS.query.filter(TAGS.name == tag).first()
                    if check is None:
                        tagtip = wikipedia_summary(tag)
                        add_tag = TAGS(
                            name=tag,
                            tips=tagtip
                        )
                        db.session.add(add_tag)
                        db.session.commit()
                    tag_list.append(TAGS.query.filter(TAGS.name == tag).first())

                add_study = STUDIES(
                    id=id,
                    name=form_title,
                    raw_markdown=form_raw_markdown,
                    field=form_field,
                    tags=tag_list,
                    authors=[user]
                )

                db.session.add(add_study)
                db.session.flush()

                os.mkdir(os.path.join(app.config['UPLOAD_FOLDER'], id))

                db.session.commit()

            except Exception as e:
                status = 'failed'
                reason = e
                db.session.rollback()

            result = {'status': status, 'reason': reason, 'id': id, 'name': form_title}

            return render_template('user-pages/result_study.html', title='結果', result=result)

        return render_template('user-pages/create_study.html', title='研究フループの作成(エラー)', form=form)

@logined_bp.route('/edit_study/<id>', methods=['GET'])
@login_required
def edit_study(id):
    if not id in [x.id for x in current_user.studies] and not current_user.has_role('Admin'):
        abort(403)
    study = STUDIES.query.filter(STUDIES.id==id).one_or_none()
    if study is None:
        abort(404)

    summary = convertMarkdown(study.raw_markdown)
    study_form = StudyForm()
    add_author_form = AddAuthorForm()
    del_author_form = DelAuthorForm()
    return render_template(
        'user-pages/edit_study.html',
        title='研究グループの編集',
        id=id,
        summary=summary,
        study_form=study_form,
        add_author_form=add_author_form,
        del_author_form=del_author_form,
        data=study
    )


@logined_bp.route('/edit_study/<id>/update', methods=['POST'])
@login_required
def edit_study_update(id):
    if not id in [x.id for x in current_user.studies] and not current_user.has_role('Admin'):
        abort(403)
    study = STUDIES.query.filter(STUDIES.id==id).one_or_none()
    if study is None:
        abort(404)
    study_form = StudyForm()
    add_author_form = AddAuthorForm()
    del_author_form = DelAuthorForm()
    if study_form.validate_on_submit():
        try:
            form_title = study_form.title.data
            form_raw_markdown = study_form.raw_markdown.data
            form_tags = re.sub(r"(\[|'|\]|\s)", '',study_form.tags.data).split(',')
            form_field = int(study_form.field.data)

            tag_list = []
            for tag in form_tags:
                tag = tag.replace('"', '')
                check = TAGS.query.filter(TAGS.name == tag).first()
                if check is None:
                    tagtip = wikipedia_summary(tag)
                    add_tag = TAGS(
                        name=tag,
                        tips=tagtip
                    )
                    db.session.add(add_tag)
                    db.session.commit()
                tag_list.append(TAGS.query.filter(TAGS.name == tag).first())

            study.name = form_title
            study.raw_markdown = form_raw_markdown
            study.field = form_field
            study.tags = tag_list

            parent = STUDIES.query.filter(STUDIES.id==id).one()
            parent.update_at = datetime.now()

            db.session.flush()
            db.session.commit()

        except Exception as e:
            flash(e)
            db.session.rollback()

        return redirect(url_for('logined_bp.edit_study', id=id))

    summary = convertMarkdown(study.raw_markdown)
    return render_template(
        'user-pages/edit_study.html',
        title='研究グループの編集(エラー)',
        study_form=study_form,
        add_author_form=add_author_form,
        del_author_form=del_author_form,
        data=study,
        summary=summary
    )


@logined_bp.route('/edit_study/<id>/del_author', methods=['POST'])
@login_required
def edit_study_del_author(id):
    if not id in [x.id for x in current_user.studies] and not current_user.has_role('Admin'):
        abort(403)
    study = STUDIES.query.filter(STUDIES.id==id).one_or_none()
    if study is None:
        abort(404)
    study_form = StudyForm()
    add_author_form = AddAuthorForm()
    del_author_form = DelAuthorForm()
    if del_author_form.validate_on_submit():
        form_user_id = del_author_form.del_author_id.data

        try:
            study.authors.remove(USERS.query.filter(USERS.id==form_user_id).one())

            db.session.flush()
            db.session.commit()

        except Exception as e:
            flash(e)
            db.session.rollback()

        return redirect(url_for('logined_bp.edit_study', id=id))

    summary = convertMarkdown(study.raw_markdown)
    return render_template(
        'user-pages/edit_study.html',
        title='研究グループの編集(エラー)',
        study_form=study_form,
        add_author_form=add_author_form,
        del_author_form=del_author_form,
        data=study,
        summary=summary
    )

@logined_bp.route('/edit_study/<id>/add_author', methods=['POST'])
@login_required
def edit_study_add_author(id):
    if not id in [x.id for x in current_user.studies] and not current_user.has_role('Admin'):
        abort(403)
    study = STUDIES.query.filter(STUDIES.id==id).one_or_none()
    if study is None:
        abort(404)
    study_form = StudyForm()
    add_author_form = AddAuthorForm()
    del_author_form = DelAuthorForm()
    if add_author_form.validate_on_submit():
        form_user_id = add_author_form.add_author_id.data

        try:
            study.authors.append(USERS.query.filter(USERS.id==form_user_id).one())

            db.session.flush()
            db.session.commit()

        except Exception as e:
            flash(e)
            db.session.rollback()

        return redirect(url_for('logined_bp.edit_study', id=id))

    summary = convertMarkdown(study.raw_markdown)
    return render_template(
        'user-pages/edit_study.html',
        title='研究グループの編集(エラー)',
        study_form=study_form,
        add_author_form=add_author_form,
        del_author_form=del_author_form,
        data=study,
        summary=summary
    )

@logined_bp.route('/edit_study/<parent_id>/upload', methods=['GET', 'POST'])
@login_required
def upload(parent_id):
    if not parent_id in [x.id for x in current_user.studies] and not current_user.has_role('Admin'):
        abort(403)
    form = UploadForm()
    if request.method == 'GET':
        return render_template('user-pages/upload.html', title='ファイルの追加', form=form, parent_id=parent_id)
    if request.method == 'POST':
        if form.validate_on_submit():
            status = 'success'
            reason = ''
            savepath = ''
            try:
                form_summary = form.summary.data
                form_type = form.type.data
                form_pubyear = form.pubyear.data
                file_id = str(ULID())

                file = form.file.data

                filename = file.filename

                filename = datetime.now().strftime('%Y%m%d%H%M%S') + '-' + filename

                filename = secure_filename(filename)

                savepath = os.path.join(app.config['UPLOAD_FOLDER'], parent_id, filename)
                file.save(savepath)

                content = ''
                file_extension = os.path.splitext(savepath)[1].lower()
                if file_extension == ".pdf":
                    with open(savepath, "rb") as f:
                        pdf = PDF_extractor(f)

                        if pdf is None:
                            raise Exception("PDFドキュメントの解析に失敗しました。PDFドキュメントが破損している可能性があります。")

                        content = pdf["content"]

                elif file_extension == ".mp4":
                    check_mp4 = VideoCapture(savepath)
                    if not check_mp4.isOpened():
                        raise Exception("MP4動画の解析に失敗しました。MP4動画が破損している可能性があります。")

                    form_type = 5
                    check_mp4.release()

                elif file_extension == ".png":
                    check_png = Image.open(savepath)

                    check_png.verify()
                    
                    form_type = 6
                    check_png.close()
                
                else:
                    raise Exception("不正なファイルがアップロードされました")

                filehash = sha256_hash(savepath)

                fileUniqueCheck = FILES.query.filter(FILES.hashsum == filehash).one_or_none()
                if fileUniqueCheck is not None:
                    raise Exception("このファイルはすでにアップロードされています")

                user = USERS.query.filter(USERS.id==str(current_user.id)).one()

                add_file = FILES(
                    id=file_id,
                    name=file.filename,
                    hashsum=filehash,
                    summary=form_summary,
                    type=form_type,
                    content=content,
                    filename=filename,
                    pubyear=form_pubyear,
                    author=[user],
                    study_id=parent_id
                )

                db.session.add(add_file)

                parent = STUDIES.query.filter(STUDIES.id==parent_id).one()
                parent.update_at = datetime.now()

                db.session.flush()
                db.session.commit()

                name = add_file.name

            except UnidentifiedImageError:
                status = 'failed'
                reason = 'PNG画像の解析に失敗しました。PNG画像が破損している可能性があります'
                name = file.filename

                if os.path.exists(savepath):
                    os.remove(savepath)

                db.session.rollback()

            except Exception as e:
                status = 'failed'
                reason = e
                name = file.filename

                if os.path.exists(savepath):
                    os.remove(savepath)

                db.session.rollback()

            result = {'status': status, 'name': name, 'reason': reason, 'id': file_id, 'parent_id': parent_id}
            print(result)

            return render_template('user-pages/result_page.html', title='結果', result=result)

        return render_template('user-pages/upload.html', title='ファイルの追加(エラー)', form=form, parent_id=parent_id)

@logined_bp.route('/edit_file/<id>', methods=['GET', 'POST'])
@login_required
def edit_file(id):
    file = FILES.query.filter(FILES.id==id).one_or_none()
    if not file:
        abort(404)

    if not file.study_id in [x.id for x in current_user.studies] and not current_user.has_role('Admin'):
        abort(403)

    form = FileEditForm()
    if request.method == 'GET':
        return render_template('user-pages/edit_file.html', title='ファイルの追加', form=form, file_id=file.id, file=file)
    if request.method == 'POST':
        if form.validate_on_submit():
            try:
                file.summary = form.summary.data
                file.type = form.type.data
                file.pubyear = form.pubyear.data

                parent = STUDIES.query.filter(STUDIES.id==file.study_id).one()
                parent.update_at = datetime.now()

                db.session.flush()
                db.session.commit()

            except Exception as e:
                flash(e)
                db.session.rollback()

            return redirect(url_for('logined_bp.edit_file', id=id))

        return render_template('user-pages/edit_file.html', title='ファイルの更新(エラー)', form=form, file_id=file.id, file=file)



@logined_bp.route('/vote', methods=['POST'])
@login_required
def vote():
    if not current_user.is_authenticated:
        abort(403)
    study_id = request.json.get('study_id')
    form_helpful = request.json.get('helpful')

    if form_helpful == 'helpful':
        helpful = True
    else:
        helpful = False

    page = FILES.query.filter(STUDIES.id==study_id)
    if not page:
        abort(404)

    user_id = current_user.id

    vote = VOTES.query.filter(VOTES.user_id==user_id, VOTES.study_id==study_id).first()
    if vote:
        db.session.delete(vote)
        db.session.commit()

    vote = VOTES(user_id=user_id, study_id=study_id)

    vote.helpful = helpful
    db.session.add(vote)
    db.session.commit()

    helpful_count = VOTES.query.filter(VOTES.study_id==study_id, VOTES.helpful==True).count()
    unhelpful_count = VOTES.query.filter(VOTES.study_id==study_id, VOTES.helpful==False).count()

    return jsonify({
        'user_vote': helpful,
        'helpful': helpful_count,
        'unhelpful': unhelpful_count
    })

@logined_bp.route('/mypage', methods=['GET'])
@login_required
def mypage():
    votes = VOTES.query.filter(VOTES.user_id==current_user.id)
    helpful_study_ids = [vote.study_id for vote in votes if vote.helpful][0:5]
    helpful_pages = STUDIES.query.filter(STUDIES.id.in_(helpful_study_ids)).all()
    mystudies = current_user.studies[0:5]
    visited_pages_query = FILEACCESS.query.filter(FILEACCESS.user_id==current_user.id).limit(5).all()
    visited_pages = [FILES.query.filter(FILES.id==x.file_id).one() for x in visited_pages_query]
    return render_template('logined-pages/mypage.html', title="マイページ", mystudies=mystudies, visited_pages=visited_pages, helpful_pages=helpful_pages)

@logined_bp.route('/mystudies', methods=['GET'])
@login_required
def mystudies():
    page = request.args.get(get_page_parameter(), type=int, default=1)
    results = current_user.studies
    rows = results[(page - 1)*10: page*10]
    pagination = Pagination(page=page, total=len(results), per_page=10, css_framework="BULMA")

    return render_template('user-pages/pagelist.html', title="自分の研究", rows=rows, pagination=pagination)

@logined_bp.route('/visited_pages', methods=['GET'])
@login_required
def visited_pages():
    page = request.args.get(get_page_parameter(), type=int, default=1)
    visited_pages_query = FILEACCESS.query.filter(FILEACCESS.user_id==current_user.id).all()
    results = [FILES.query.filter(FILES.id==x.file_id).one() for x in visited_pages_query]
    rows = results[(page - 1)*10: page*10]
    pagination = Pagination(page=page, total=len(results), per_page=10, css_framework="BULMA")

    return render_template('user-pages/filelist.html', title="閲覧履歴", rows=rows, pagination=pagination)

@logined_bp.route('/helpful_pages', methods=['GET'])
@login_required
def helpful_pages():
    page = request.args.get(get_page_parameter(), type=int, default=1)
    votes = VOTES.query.filter(VOTES.user_id==current_user.id)
    helpful_study_ids = [vote.study_id for vote in votes if vote.helpful]
    helpful_pages = STUDIES.query.filter(STUDIES.id.in_(helpful_study_ids)).all()

    rows = helpful_pages[(page - 1)*10: page*10]
    pagination = Pagination(page=page, total=len(helpful_pages), per_page=10, css_framework="BULMA")

    return render_template('user-pages/pagelist.html', title="高評価したページ", rows=rows, pagination=pagination)