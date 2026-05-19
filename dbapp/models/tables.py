from flask_login import UserMixin
from dbapp import db, ma, app
from datetime import datetime
from sqlalchemy.orm import relationship
from sqlalchemy.sql.schema import ForeignKey
from ulid import ULID


def ulid_new_str():
    return str(ULID())


class STUDIES(db.Model):
    __tablename__ = 'studies'
    id = db.Column(db.String(26), primary_key=True, default=ulid_new_str)
    create_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    update_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    name = db.Column(db.String(255), unique=True)
    summary = db.Column(db.Text())
    raw_markdown = db.Column(db.Text())
    field = db.Column(db.Integer)
    grave_data = db.Column(db.Boolean, default=False)

    tags = relationship('TAGS', secondary='study_tag', back_populates='studies')
    files = relationship('FILES', back_populates='study')
    authors = relationship('USERS', secondary='study_user', back_populates='studies')

    def get_total_access_count(self):
        return sum(file.access_count for file in self.files)

    def get_total_preview_count(self):
        return sum(file.preview_count for file in self.files)


class STUDYGRAVES(db.Model):
    __tablename__ = 'studygraves'
    id = db.Column(db.String(26), primary_key=True, default=ulid_new_str)
    create_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    study_id = db.Column(db.String(26), ForeignKey('studies.id'))
    reason = db.Column(db.Text(), nullable=False)
    deleted = db.Column(db.Boolean, default=False)


class FILES(db.Model):
    __tablename__ = 'files'
    id = db.Column(db.String(26), primary_key=True, default=ulid_new_str)
    create_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    hashsum = db.Column(db.Text(), unique=True)
    name = db.Column(db.String(255))
    summary = db.Column(db.Text())
    type = db.Column(db.Integer, default=0)
    filename = db.Column(db.Text())
    pubyear = db.Column(db.Integer)
    access_count = db.Column(db.Integer, default=0)
    preview_count = db.Column(db.Integer, default=0)
    content = db.Column(db.Text())
    grave_data = db.Column(db.Boolean, default=False)

    study_id = db.Column(db.String(26), ForeignKey('studies.id'))
    study = relationship('STUDIES')

    author = relationship('USERS', secondary='user_file', back_populates='files')


class FILEGRAVES(db.Model):
    __tablename__ = 'filegraves'
    id = db.Column(db.String(26), primary_key=True, default=ulid_new_str)
    create_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    file_id = db.Column(db.String(26), ForeignKey('files.id'))
    reason = db.Column(db.Text(), nullable=False)
    deleted = db.Column(db.Boolean, default=False)


class TAGS(db.Model):
    __tablename__ = 'tags'
    id = db.Column(db.String(26), primary_key=True, default=ulid_new_str)
    create_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    name = db.Column(db.String(255))
    tips = db.Column(db.Text)

    studies = relationship('STUDIES', secondary='study_tag', back_populates='tags')


class VOTES(db.Model):
    __tablename__ = 'votes'
    id = db.Column(db.String(26), primary_key=True, default=ulid_new_str)
    create_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    user_id = db.Column(db.String(26), db.ForeignKey('users.id'), nullable=False, primary_key=True)
    study_id = db.Column(db.String(26), db.ForeignKey('studies.id'), nullable=False, primary_key=True)
    helpful = db.Column(db.Boolean(), nullable=False)


class FILEACCESS(db.Model):
    __tablename__ = 'fileaccess'
    id = db.Column(db.String(26), primary_key=True, default=ulid_new_str)
    user_id = db.Column(db.String(26), db.ForeignKey('users.id'))
    file_id = db.Column(db.String(26), db.ForeignKey('files.id'))
    accessed_at = db.Column(db.DateTime, default=datetime.now)


class FILEPREVIEW(db.Model):
    __tablename__ = 'filepreview'
    id = db.Column(db.String(26), primary_key=True, default=ulid_new_str)
    user_id = db.Column(db.String(26), db.ForeignKey('users.id'))
    file_id = db.Column(db.String(26), db.ForeignKey('files.id'))
    previewed_at = db.Column(db.DateTime, default=datetime.now)


class NEWS(db.Model):
    __tablename__ = 'news'
    id = db.Column(db.String(26), primary_key=True, default=ulid_new_str)
    create_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    name = db.Column(db.String(255), unique=True)
    content = db.Column(db.Text())
    raw_markdown = db.Column(db.Text())

    author = relationship('USERS', secondary='user_news', back_populates='news')


class ExtUserMixin(UserMixin):
    def get_id(self):
        return self.id

    def has_role(self, role):
        return role in [r.name for r in self.roles]


class USERS(db.Model, ExtUserMixin):
    __tablename__ = 'users'
    id = db.Column(db.String(26), primary_key=True, default=ulid_new_str)
    create_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    name = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(2048))
    display_name = db.Column(db.String(100))

    studies = db.relationship('STUDIES', secondary='study_user', back_populates='authors')
    files = db.relationship('FILES', secondary='user_file', back_populates='author')
    roles = db.relationship('ROLES', secondary='user_role', back_populates='users')
    news = db.relationship('NEWS', secondary='user_news', back_populates='author')


class ROLES(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.String(26), primary_key=True, default=ulid_new_str)
    create_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    name = db.Column(db.String(50), unique=True)

    users = db.relationship('USERS', secondary='user_role', back_populates='roles')


class STUDY_USER(db.Model):
    __tablename__ = 'study_user'
    id = db.Column(db.String(26), primary_key=True, default=ulid_new_str)
    create_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    user_id = db.Column(db.String(26), ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    study_id = db.Column(db.String(26), ForeignKey('studies.id', ondelete='CASCADE'), primary_key=True)


class STUDY_TAG(db.Model):
    __tablename__ = 'study_tag'
    id = db.Column(db.String(26), primary_key=True, default=ulid_new_str)
    create_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    study_id = db.Column(db.String(26), ForeignKey('studies.id', ondelete='CASCADE'), primary_key=True)
    tag_id = db.Column(db.String(26), ForeignKey('tags.id', ondelete='CASCADE'), primary_key=True)


class USER_FILE(db.Model):
    __tablename__ = 'user_file'
    id = db.Column(db.String(26), primary_key=True, default=ulid_new_str)
    create_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    user_id = db.Column(db.String(26), ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    file_id = db.Column(db.String(26), ForeignKey('files.id', ondelete='CASCADE'), primary_key=True)


class USER_ROLE(db.Model):
    __tablename__ = 'user_role'
    id = db.Column(db.String(26), primary_key=True, default=ulid_new_str)
    create_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    user_id = db.Column(db.String(26), ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    role_id = db.Column(db.String(26), ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True)


class USER_NEWS(db.Model):
    __tablename__ = 'user_news'
    id = db.Column(db.String(26), primary_key=True, default=ulid_new_str)
    create_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    user_id = db.Column(db.String(26), ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    news_id = db.Column(db.String(26), ForeignKey('news.id', ondelete='CASCADE'), primary_key=True)


class STUDIESSchema(ma.SQLAlchemyAutoSchema):
    class Meta():
        model = STUDIES
        include_relationships = True
        load_instance = True


class TAGSSchema(ma.SQLAlchemyAutoSchema):
    class Meta():
        model = TAGS
        include_relationships = True
        load_instance = True


class FILESchema(ma.SQLAlchemyAutoSchema):
    class Meta():
        model = FILES
        include_relationships = True
        load_instance = True


class USERSSchema(ma.SQLAlchemyAutoSchema):
    class Meta():
        model = USERS
        include_relationships = True
        load_instance = True


class NEWSSchema(ma.SQLAlchemyAutoSchema):
    class Meta():
        model = NEWS
        include_relationships = True
        load_instance = True
