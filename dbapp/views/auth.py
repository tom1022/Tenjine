from flask import Blueprint, flash, render_template, request, url_for, redirect, session
from flask_login import login_required, login_user, logout_user, current_user
from werkzeug.security import check_password_hash
from urllib.parse import urlsplit
from dbapp import app, db, config_watcher
from dbapp.models.tables import USERS, ROLES, FILEACCESS, FILEPREVIEW
from dbapp.form import LoginForm

auth = Blueprint('auth_bp', __name__, template_folder='templates')

config = config_watcher.get_config()
ad_config = config["ADServer"]

from ldap3 import Server, Connection, ALL, NTLM
import re

server = Server('ldap://{}'.format(ad_config["address"]), get_info=ALL)


def ADAuth(username, password):
    conn = Connection(server, user='{}\\{}'.format(".".join(ad_config["domains"]), username), password=password, authentication=NTLM)

    if conn.bind():
        conn.search(",".join(["dc=" + x for x in ad_config["domains"]]), '(sAMAccountName={})'.format(username), attributes=['memberOf', 'displayName'])
        result = conn.entries[0]
        security_groups = [re.search('CN=(.+?),', x).group(1) for x in result.memberOf if 'CN=' in x]
        full_name = result.displayName
        return {"groups": security_groups, "fullname": str(full_name).replace('displayName: ', '')}
    else:
        return None


@auth.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if request.method == 'GET':
        return render_template('auth-pages/login.html', title="ログイン", form=form)

    if request.method == 'POST':
        if form.validate_on_submit():
            if current_user.is_authenticated:
                if current_user.has_role('Admin'):
                    url = 'admin_bp.index'
                else:
                    url = 'logined_bp.mypage'
                return redirect(url_for(url))

            form_name = request.form.get('name')
            form_passwd = request.form.get('password')
            form_ad = request.form.get('ad_disable')
            user = USERS.query.filter(USERS.name == form_name).one_or_none()

            if form_ad == "False" and ad_config["use"]:
                ADUser = ADAuth(form_name, form_passwd)
            else:
                ADUser = None

            if user is not None or ADUser is not None:
                if user is None:
                    if ad_config['groups']['Admin'] in ADUser['groups']:
                        role = 'Admin'
                    elif ad_config['groups']['Student'] in ADUser['groups']:
                        role = 'Student'

                    role = ROLES.query.filter(ROLES.name == role).one()

                    user = USERS(
                        name=form_name,
                        display_name=ADUser['fullname'],
                        password="unnecessary"
                    )
                    user.roles.append(role)
                    db.session.add(user)
                    db.session.commit()

                if check_password_hash(user.password, form_passwd) or ADUser:
                    login_user(user, remember=True)
                    next_page = request.args.get('next')
                    if not next_page or urlsplit(next_page).netloc != '':
                        if user.has_role('Admin'):
                            next_page = url_for('admin_bp.index')
                        else:
                            next_page = url_for('logined_bp.mypage')

                    if 'accessed_files' in session:
                        for file_id in session['accessed_files']:
                            access_history = FILEACCESS(
                                user_id=current_user.id,
                                file_id=file_id
                            )
                            db.session.add(access_history)
                            db.session.commit()

                    if 'previewed_files' in session:
                        for file_id in session['previewed_files']:
                            preview_history = FILEPREVIEW(
                                user_id=current_user.id,
                                file_id=file_id
                            )
                            db.session.add(preview_history)
                            db.session.commit()

                    return redirect(next_page)

    flash('アカウントが存在しないかパスワードが間違っています')
    return render_template('auth-pages/login.html', title="ログイン", form=form)


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('user_bp.index'))
