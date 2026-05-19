import os, re
import logging
from ulid import ULID
from flask import Blueprint, render_template, request, abort, url_for, redirect, flash
from flask_login import login_required, current_user
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from dbapp import app, db
from dbapp.models.tables import USERS, STUDIES, TAGS
from dbapp.form import StudyForm, AddAuthorForm, DelAuthorForm
from dbapp.tools import wikipedia_summary, convertMarkdown
from dbapp.decorators import owner_or_admin_required

logger = logging.getLogger(__name__)
studies_bp = Blueprint('studies_bp', __name__, template_folder='templates')


def _build_tag_list(form_tags):
    tag_list = []
    for tag in form_tags:
        tag = tag.replace('"', '')
        tag_obj = TAGS.query.filter(TAGS.name == tag).first()
        if tag_obj is None:
            tagtip = wikipedia_summary(tag)
            tag_obj = TAGS(name=tag, tips=tagtip)
            db.session.add(tag_obj)
            db.session.flush()
        tag_list.append(tag_obj)
    return tag_list


@studies_bp.route('/create_study', methods=['GET', 'POST'])
@login_required
def create_study():
    form = StudyForm()
    if request.method == 'GET':
        return render_template('user-pages/create_study.jinja2', title='研究グループの作成', form=form)
    if request.method == 'POST':
        if form.validate_on_submit():
            status = 'success'
            reason = ''
            id = None
            form_title = ''

            try:
                form_title = form.title.data
                form_raw_markdown = form.raw_markdown.data
                form_tags = re.sub(r"(\[|'|\]|\s)", '', form.tags.data).split(',')
                form_field = int(form.field.data)
                id = str(ULID())

                user = USERS.query.filter(USERS.id == str(current_user.id)).one()
                tag_list = _build_tag_list(form_tags)

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

            except IntegrityError as e:
                logger.warning("IntegrityError creating study: %s", e.orig)
                status = 'failed'
                reason = 'その名前の研究グループはすでに存在します'
                db.session.rollback()
            except OSError as e:
                logger.error("Filesystem error creating study directory: %s", e)
                status = 'failed'
                reason = 'ディレクトリの作成に失敗しました'
                db.session.rollback()
            except Exception as e:
                logger.exception("Unexpected error in create_study")
                status = 'failed'
                reason = str(e)
                db.session.rollback()

            result = {'status': status, 'reason': reason, 'id': id, 'name': form_title}
            return render_template('user-pages/result_study.jinja2', title='結果', result=result)

        return render_template('user-pages/create_study.jinja2', title='研究フループの作成(エラー)', form=form)


@studies_bp.route('/edit_study/<id>', methods=['GET'])
@login_required
@owner_or_admin_required()
def edit_study(id):
    study = STUDIES.query.filter(STUDIES.id == id).one_or_none()
    if study is None:
        abort(404)

    summary = convertMarkdown(study.raw_markdown)
    study_form = StudyForm()
    add_author_form = AddAuthorForm()
    del_author_form = DelAuthorForm()
    return render_template(
        'user-pages/edit_study.jinja2',
        title='研究グループの編集',
        id=id,
        summary=summary,
        study_form=study_form,
        add_author_form=add_author_form,
        del_author_form=del_author_form,
        data=study
    )


@studies_bp.route('/edit_study/<id>/update', methods=['POST'])
@login_required
@owner_or_admin_required()
def edit_study_update(id):
    study = STUDIES.query.filter(STUDIES.id == id).one_or_none()
    if study is None:
        abort(404)
    study_form = StudyForm()
    add_author_form = AddAuthorForm()
    del_author_form = DelAuthorForm()
    if study_form.validate_on_submit():
        try:
            form_title = study_form.title.data
            form_raw_markdown = study_form.raw_markdown.data
            form_tags = re.sub(r"(\[|'|\]|\s)", '', study_form.tags.data).split(',')
            form_field = int(study_form.field.data)

            tag_list = _build_tag_list(form_tags)

            study.name = form_title
            study.raw_markdown = form_raw_markdown
            study.field = form_field
            study.tags = tag_list

            study.update_at = datetime.now()

            db.session.flush()
            db.session.commit()

        except IntegrityError as e:
            logger.warning("IntegrityError updating study %s: %s", id, e.orig)
            flash('その名前の研究グループはすでに存在します')
            db.session.rollback()
        except Exception as e:
            logger.exception("Unexpected error in edit_study_update for study %s", id)
            flash(str(e))
            db.session.rollback()

        return redirect(url_for('studies_bp.edit_study', id=id))

    summary = convertMarkdown(study.raw_markdown)
    return render_template(
        'user-pages/edit_study.jinja2',
        title='研究グループの編集(エラー)',
        study_form=study_form,
        add_author_form=add_author_form,
        del_author_form=del_author_form,
        data=study,
        summary=summary
    )


@studies_bp.route('/edit_study/<id>/del_author', methods=['POST'])
@login_required
@owner_or_admin_required()
def edit_study_del_author(id):
    study = STUDIES.query.filter(STUDIES.id == id).one_or_none()
    if study is None:
        abort(404)
    study_form = StudyForm()
    add_author_form = AddAuthorForm()
    del_author_form = DelAuthorForm()
    if del_author_form.validate_on_submit():
        form_user_id = del_author_form.del_author_id.data

        try:
            study.authors.remove(USERS.query.filter(USERS.id == form_user_id).one())
            db.session.flush()
            db.session.commit()

        except Exception as e:
            logger.exception("Unexpected error in edit_study_del_author for study %s", id)
            flash(str(e))
            db.session.rollback()

        return redirect(url_for('studies_bp.edit_study', id=id))

    summary = convertMarkdown(study.raw_markdown)
    return render_template(
        'user-pages/edit_study.jinja2',
        title='研究グループの編集(エラー)',
        study_form=study_form,
        add_author_form=add_author_form,
        del_author_form=del_author_form,
        data=study,
        summary=summary
    )


@studies_bp.route('/edit_study/<id>/add_author', methods=['POST'])
@login_required
@owner_or_admin_required()
def edit_study_add_author(id):
    study = STUDIES.query.filter(STUDIES.id == id).one_or_none()
    if study is None:
        abort(404)
    study_form = StudyForm()
    add_author_form = AddAuthorForm()
    del_author_form = DelAuthorForm()
    if add_author_form.validate_on_submit():
        form_user_id = add_author_form.add_author_id.data

        try:
            study.authors.append(USERS.query.filter(USERS.id == form_user_id).one())
            db.session.flush()
            db.session.commit()

        except Exception as e:
            logger.exception("Unexpected error in edit_study_add_author for study %s", id)
            flash(str(e))
            db.session.rollback()

        return redirect(url_for('studies_bp.edit_study', id=id))

    summary = convertMarkdown(study.raw_markdown)
    return render_template(
        'user-pages/edit_study.jinja2',
        title='研究グループの編集(エラー)',
        study_form=study_form,
        add_author_form=add_author_form,
        del_author_form=del_author_form,
        data=study,
        summary=summary
    )
