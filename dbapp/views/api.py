from flask import Blueprint, jsonify, request
from flask_login import login_required
from dbapp import admin_required
from dbapp.models.tables import TAGS, TAGSSchema
from sqlalchemy import or_, and_
from dbapp.file_operation.pdf import PDF_extractor
from dbapp.tools import convertMarkdown

api = Blueprint('api_bp', __name__)


@api.route('/tag_search', methods=['GET'])
def tag_search():
    query = request.args.get('query')
    results = TAGS.query.filter(or_(TAGS.name.contains(query), TAGS.tips.contains(query))).all()

    return jsonify({'status': 'ok', 'tagList': TAGSSchema(many=True, exclude=('id', )).dump(results)})


@api.route('/summarize_api', methods=['POST'])
def file_receive():
    pdf = PDF_extractor(request.files['file'])

    return jsonify({"status": "ok", "pubyear": pdf["pubyear"]})


@api.route('/convert', methods=['POST'])
def convert():
    markdown = convertMarkdown(request.form['markdown'])
    return jsonify({"status": "ok", "markdown": markdown})
