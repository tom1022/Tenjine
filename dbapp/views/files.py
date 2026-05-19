import os
import logging
from ulid import ULID
from flask import Blueprint, render_template, request, abort, url_for, redirect, flash
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from cv2 import VideoCapture
from PIL import Image, UnidentifiedImageError
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from dbapp import app, db
from dbapp.models.tables import USERS, FILES, STUDIES
from dbapp.form import UploadForm, FileEditForm
from dbapp.file_operation.pdf import PDF_extractor
from dbapp.tools import sha256_hash
from dbapp.decorators import owner_or_admin_required

logger = logging.getLogger(__name__)
files_bp = Blueprint('files_bp', __name__, template_folder='templates')


@files_bp.route('/edit_study/<parent_id>/upload', methods=['GET', 'POST'])
@login_required
@owner_or_admin_required('parent_id')
def upload(parent_id):
    form = UploadForm()
    if request.method == 'GET':
        return render_template('user-pages/upload.jinja2', title='ファイルの追加', form=form, parent_id=parent_id)
    if request.method == 'POST':
        if form.validate_on_submit():
            status = 'success'
            reason = ''
            savepath = ''
            file_id = str(ULID())
            try:
                form_summary = form.summary.data
                form_type = form.type.data
                form_pubyear = form.pubyear.data

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
                            raise ValueError("PDFドキュメントの解析に失敗しました。PDFドキュメントが破損している可能性があります。")
                        content = pdf["content"]

                elif file_extension == ".mp4":
                    check_mp4 = VideoCapture(savepath)
                    if not check_mp4.isOpened():
                        raise ValueError("MP4動画の解析に失敗しました。MP4動画が破損している可能性があります。")
                    form_type = 5
                    check_mp4.release()

                elif file_extension == ".png":
                    check_png = Image.open(savepath)
                    check_png.verify()
                    form_type = 6
                    check_png.close()

                else:
                    raise ValueError("不正なファイルがアップロードされました")

                filehash = sha256_hash(savepath)
                if FILES.query.filter(FILES.hashsum == filehash).one_or_none() is not None:
                    raise ValueError("このファイルはすでにアップロードされています")

                user = USERS.query.filter(USERS.id == str(current_user.id)).one()

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

                parent = STUDIES.query.filter(STUDIES.id == parent_id).one()
                parent.update_at = datetime.now()

                db.session.flush()
                db.session.commit()

                name = add_file.name

            except UnidentifiedImageError:
                logger.warning("UnidentifiedImageError for file in study %s", parent_id)
                status = 'failed'
                reason = 'PNG画像の解析に失敗しました。PNG画像が破損している可能性があります'
                name = form.file.data.filename
                if os.path.exists(savepath):
                    os.remove(savepath)
                db.session.rollback()

            except (ValueError, Exception) as e:
                if isinstance(e, ValueError):
                    logger.warning("Upload validation error in study %s: %s", parent_id, e)
                else:
                    logger.exception("Unexpected error in upload for study %s", parent_id)
                status = 'failed'
                reason = str(e)
                name = form.file.data.filename
                if os.path.exists(savepath):
                    os.remove(savepath)
                db.session.rollback()

            result = {'status': status, 'name': name, 'reason': reason, 'id': file_id, 'parent_id': parent_id}
            return render_template('user-pages/result_page.jinja2', title='結果', result=result)

        return render_template('user-pages/upload.jinja2', title='ファイルの追加(エラー)', form=form, parent_id=parent_id)


@files_bp.route('/edit_file/<id>', methods=['GET', 'POST'])
@login_required
def edit_file(id):
    file = FILES.query.filter(FILES.id == id).one_or_none()
    if not file:
        abort(404)

    if file.study_id not in [x.id for x in current_user.studies] \
            and not current_user.has_role('Admin'):
        abort(403)

    form = FileEditForm()
    if request.method == 'GET':
        return render_template('user-pages/edit_file.jinja2', title='ファイルの追加', form=form, file_id=file.id, file=file)
    if request.method == 'POST':
        if form.validate_on_submit():
            try:
                file.summary = form.summary.data
                file.type = form.type.data
                file.pubyear = form.pubyear.data

                parent = STUDIES.query.filter(STUDIES.id == file.study_id).one()
                parent.update_at = datetime.now()

                db.session.flush()
                db.session.commit()

            except Exception as e:
                logger.exception("Unexpected error in edit_file for file %s", id)
                flash(str(e))
                db.session.rollback()

            return redirect(url_for('files_bp.edit_file', id=id))

        return render_template('user-pages/edit_file.jinja2', title='ファイルの更新(エラー)', form=form, file_id=file.id, file=file)
