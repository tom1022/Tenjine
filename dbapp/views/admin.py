from flask import Blueprint, render_template, request, abort, session, jsonify, redirect, url_for, flash
from flask_login import login_required
from flask_paginate import Pagination, get_page_parameter
from dbapp import app, db, admin_required
from dbapp.models.tables import NEWS, TAGS, STUDIES, STUDYGRAVES, FILES, FILEGRAVES, USERS, ROLES, USER_ROLE
from dbapp.form import PostNewsForm, TagForm, DeleteForm, AddRoleForm, DelRoleForm
import os
import shutil
import psutil

admin_bp = Blueprint('admin_bp', __name__, template_folder='templates')


@admin_bp.route('/')
@login_required
@admin_required
def index():
    return render_template(
        'admin-pages/index.jinja2',
        title='管理者ページ'
        )

@admin_bp.route('/edit_tag/<id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_tag(id):
    data = TAGS.query.filter(TAGS.id==id).one_or_none()
    form = TagForm()
    if not data:
        abort(404)
    if request.method == 'GET':
        return render_template('admin-pages/edit_tag.jinja2', title='タグの編集', data=data, form=form, tag_id=data.id)
    if request.method == 'POST':
        try:
            data.tag = form.title.data
            data.tips = form.tips.data

            db.session.flush()
            db.session.commit()
        
        except Exception as e:
            flash(e)
            db.session.rollback()

        return redirect(url_for('admin_bp.edit_tag', id=id))

    return render_template('admin-pages/edit_tag.jinja2', title='タグの編集(エラー)', data=data, form=form, tag_id=data.id)


@admin_bp.route('/result')
@login_required
@admin_required
def upload_result():
    id = request.args.get("id")
    try:
        result = session["results"][id]
    except KeyError:
        abort(400)

    return render_template('admin-pages/result.jinja2', title="結果", result=result)

@admin_bp.route('/user')
@login_required
@admin_required
def user_list():
    users = USERS.query.all()
    page = request.args.get(get_page_parameter(), type=int, default=1)
    rows = users[(page - 1)*50: page*50]
    pagination = Pagination(page=page, total=len(users), per_page=50, css_framework="BULMA")
    return render_template(
        'admin-pages/user_list.jinja2',
        title='ユーザーの一覧',
        rows=rows,
        pagination=pagination
    )

@admin_bp.route('/user/<id>')
@login_required
@admin_required
def user_detail(id):
    user = USERS.query.filter(USERS.id==id).one_or_none()
    if not user:
        abort(404)
    return render_template('admin-pages/user_detail.jinja2', title='ユーザーの詳細', user=user)


@admin_bp.route('/role', methods=['GET'])
@login_required
@admin_required
def role():
    admins = (
        db.session.query(USERS)
        .join(USER_ROLE, USER_ROLE.user_id == USERS.id)
        .join(ROLES, ROLES.id == USER_ROLE.role_id)
        .filter(ROLES.name == 'Admin')
        .all()
    )
    add_form = AddRoleForm()
    del_form = DelRoleForm()
    return render_template('admin-pages/role.jinja2', title='管理者権限の管理', admins=admins, add_form=add_form, del_form=del_form)

@admin_bp.route('/addrole', methods=['POST'])
@login_required
@admin_required
def addrole():
    admins = (
        db.session.query(USERS)
        .join(USER_ROLE, USER_ROLE.user_id == USERS.id)
        .join(ROLES, ROLES.id == USER_ROLE.role_id)
        .filter(ROLES.name == 'Admin')
        .all()
    )
    add_form = AddRoleForm()
    del_form = DelRoleForm()
    if add_form.validate_on_submit():
        user_id = add_form.add_user_id.data
        user = USERS.query.filter(USERS.id==user_id).one_or_none()
        admin = ROLES.query.filter(ROLES.name=='Admin').one_or_none()
        if not user:
            abort(404)

        if not user.has_role('Admin'):
            user_role_relation = USER_ROLE(user_id=user.id, role_id=admin.id)
            db.session.add(user_role_relation)
            db.session.commit()

        return redirect(url_for('admin_bp.role'))
    
    return render_template('admin-pages/role.jinja2', title='管理者権限の管理(エラー)', admins=admins, add_form=add_form, del_form=del_form)

@admin_bp.route('/delrole', methods=['POST'])
@login_required
@admin_required
def delrole():
    admins = (
        db.session.query(USERS)
        .join(USER_ROLE, USER_ROLE.user_id == USERS.id)
        .join(ROLES, ROLES.id == USER_ROLE.role_id)
        .filter(ROLES.name == 'Admin')
        .all()
    )
    add_form = AddRoleForm()
    del_form = DelRoleForm()
    if del_form.validate_on_submit():
        user_id = del_form.del_user_id.data
        user = USERS.query.filter(USERS.id==user_id).one_or_none()
        admin = ROLES.query.filter(ROLES.name=='Admin').one_or_none()
        if not user:
            abort(404)
        
        if user.has_role('Admin'):
            existing_relation = USER_ROLE.query.filter_by(user_id=user.id, role_id=admin.id).first()
            db.session.delete(existing_relation)
            db.session.flush()
            db.session.commit()

        return redirect(url_for('admin_bp.role'))
    
    return render_template('admin-pages/role.jinja2', title='管理者権限の管理(エラー)', admins=admins, add_form=add_form, del_form=del_form)



@admin_bp.route('/postnews/', methods=['GET'])
@login_required
@admin_required
def postnews():
    form = PostNewsForm()
    return render_template('admin-pages/postnews.jinja2', title="お知らせ作成", form=form)

@admin_bp.route('/postnews', methods=['POST'])
@login_required
@admin_required
def postnews_receive():
    add_news = NEWS(
        name = request.form.get('title'),
        content = request.form.get('content'),
        raw_markdown = request.form.get('raw_markdown')
    )

    db.session.add(add_news)
    db.session.commit()

    return redirect(url_for('user_bp.news', id=add_news.id))


@admin_bp.route('/delete/', methods=['GET', 'POST'])
@login_required
@admin_required
def delete():
    form = DeleteForm()
    message = ''
    status = ''
    if request.method == 'GET':
        return render_template('admin-pages/delete.jinja2', title="レコードの削除", form=form)

    if request.method == 'POST':
        if form.validate_on_submit():
            form_type = form.type.data
            form_id = form.id.data

            deleted = False

            status = 'is-success'
            message = '操作に成功しました'
            if form_type == "STUDY":
                form_reason = form.reason.data
                form_delete = form.delete.data

                try:
                    study = STUDIES.query.filter(STUDIES.id==form_id).one_or_none()
                    if form_delete:
                        filepath = os.path.join(app.config['UPLOAD_FOLDER'], str(form_id))
                        deleted = True

                    grave_check = STUDYGRAVES.query.filter(STUDYGRAVES.study_id==study.id).one_or_none()
                    if grave_check is not None:
                        if grave_check.deleted:
                            raise Exception("研究グループはすでに削除されています")
                        
                        elif not grave_check.deleted and not form_delete:
                            raise Exception("研究グループはすでに非公開です")

                        else:
                            grave_check.deleted = True

                    else:
                        grave = STUDYGRAVES(
                            study_id=form_id,
                            reason=form_reason,
                            deleted=deleted
                        )

                        study.grave_data = True

                        db.session.add(grave)

                    db.session.flush()
                    if form_delete:
                        shutil.rmtree(filepath)
                    db.session.commit()

                except Exception as e:
                    status = 'is-danger'
                    message = e
                    db.session.rollback()

            if form_type == "FILE":
                form_reason = form.reason.data
                form_delete = form.delete.data

                try:
                    file = FILES.query.filter(FILES.id==form_id).one_or_none()
                    if form_delete:
                        filepath = os.path.join(app.config['UPLOAD_FOLDER'], str(file.study_id), str(file.filename))
                        deleted = True

                    grave_check = FILEGRAVES.query.filter(FILEGRAVES.file_id==file.id).one_or_none()
                    if grave_check is not None:
                        if grave_check.deleted:
                            raise Exception("ファイルはすでに削除されています")
                        
                        elif not grave_check.deleted and not form_delete:
                            raise Exception("ファイルはすでに非公開です")

                        else:
                            grave_check.deleted = True

                    else:
                        grave = FILEGRAVES(
                            file_id=form_id,
                            reason=form_reason,
                            deleted=deleted
                        )

                        file.grave_data = True

                        db.session.add(grave)

                    db.session.flush()
                    db.session.commit()
                    if form_delete:
                        os.remove(filepath)

                except Exception as e:
                    status = 'is-danger'
                    message = e
                    db.session.rollback()

            if form_type == "NEWS":
                news = NEWS.query.filter(NEWS.id==form_id).one_or_none()
                try:
                    if news is None:
                        raise Exception("お知らせが存在しません")

                    db.session.delete(news)
                    db.session.flush()
                    db.session.commit()

                except Exception as e:
                    status = 'is-danger'
                    message = e
                    db.session.rollback()

            if form_type == "TAG":
                tag = TAGS.query.filter(TAGS.id==form_id).one_or_none()

                try:
                    if tag is None:
                        raise Exception("タグが存在しません")

                    db.session.delete(tag)
                    db.session.flush()
                    db.session.commit()
                except Exception as e:
                    status = 'is-danger'
                    message = e
                    db.session.rollback()

    if message:
        flash(message, status)
    return render_template('admin-pages/delete.jinja2', title="レコードの削除", form=form)