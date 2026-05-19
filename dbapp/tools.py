from dbapp import db
from dbapp.models.tables import FILES, STUDIES

import markdown
import nh3

allowed_tags = {
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'div', 'p', 'span', 'a', 'br',
    'strong', 'em', 's', 'strike', 'del', 'ul', 'ol', 'li', 'table', 'thead',
    'tbody', 'th', 'tr', 'td', 'img', 'image', 'audio', 'video', 'input',
    'pre', 'code', 'blockquote', 'figure', 'figcaption', 'abbr', 'details',
    'summary', 'cite', 'sub', 'sup', 'time', 'address',
}
allowed_attributes = {
    '*': {'id'},
    'a': {'href', 'title'},
    'input': {'type', 'value', 'checked', 'disabled'},
    'code': {'class'},
    'div': {'class'},
    'span': {'class'},
    'img': {'src', 'alt'},
    'audio': {'src', 'controls'},
    'video': {'src', 'controls'},
}


def convertMarkdown(text):
    md = markdown.Markdown(extensions=['tables', 'fenced_code', 'codehilite', 'attr_list', 'footnotes', 'toc'])
    return nh3.clean(md.convert(text), tags=allowed_tags, attributes=allowed_attributes)


def FilterStudyFiles(study, admin):
    files = sorted(study.files, key=lambda file: file.create_at, reverse=True)
    if not admin:
        selected_files = [f for f in files if not f.grave_data]
        study.files = selected_files
    return study


def FilterStudiesHiddenFiles(studies, admin):
    filtered_studies = []
    for study in studies:
        files = sorted(study.files, key=lambda file: file.create_at, reverse=True)
        count = 0
        selected_files = []
        for file in files:
            if not file.grave_data or admin:
                selected_files.append(file)
                count += 1
                if count == 4:
                    break
        study.files = selected_files
        filtered_studies.append(study)
    return filtered_studies


from sqlalchemy import or_, and_


def SearchEngine(
        search_terms=None,
        ascending=True,
        update_at_range=None,
        create_at_range=None,
        field=0,
        sort_column="update_at",
        admin=False
    ):
    query = db.session.query(STUDIES).outerjoin(FILES)

    study_columns = [STUDIES.name, STUDIES.summary]
    file_columns = [FILES.summary, FILES.content]

    search_filters = []

    if search_terms:
        search_words = search_terms.split()
        search_conditions = []
        for word in search_words:
            word_conditions = []
            for column in study_columns + file_columns:
                word_conditions.append(column.ilike(f"%{word}%"))
            search_conditions.append(or_(*word_conditions))
        search_filters.append(and_(*search_conditions))

    if not admin:
        search_filters.append(STUDIES.grave_data == False)

    if update_at_range:
        start_date, end_date = update_at_range
        search_filters.append(STUDIES.update_at.between(start_date, end_date))

    if create_at_range:
        start_date, end_date = create_at_range
        search_filters.append(STUDIES.create_at.between(start_date, end_date))

    if field != 0:
        search_filters.append(STUDIES.field == field)

    if search_filters:
        query = query.filter(and_(*search_filters))

    if sort_column == 'update_at':
        query = query.order_by(STUDIES.update_at.asc() if ascending else STUDIES.update_at.desc())
    elif sort_column == 'get_total_access_count':
        query = query.order_by(STUDIES.get_total_access_count().asc() if ascending else STUDIES.get_total_access_count().desc())
    elif sort_column == 'get_total_preview_count':
        query = query.order_by(STUDIES.get_total_preview_count().asc() if ascending else STUDIES.get_total_preview_count().desc())
    else:
        query = query.order_by(STUDIES.create_at.asc() if ascending else STUDIES.create_at.desc())

    studies = query.all()
    filtered_studies = FilterStudiesHiddenFiles(studies, admin)

    if not search_terms:
        return [filtered_studies, "研究一覧"]

    for study in studies:
        study.files = db.session.query(FILES).filter(
            FILES.study_id == study.id,
            or_(*[or_(FILES.summary.contains(f"%{term}%"), FILES.content.contains(f"%{term}%")) for term in search_words])
        ).all()

    filtered_studies = FilterStudiesHiddenFiles(studies, admin)

    return [filtered_studies, '"' + search_terms + '"の検索結果']


import wikipedia
from nltk.corpus import wordnet

wikipedia.set_lang("ja")


def wikipedia_summary(word):
    page = None
    summary = "ユーザーによって追加されたタグ"
    try:
        page = wikipedia.page(word)
        summary = page.summary
        summary += "\nWikipediaより引用 - " + page.url
    except wikipedia.exceptions.DisambiguationError as e:
        wordlist = e.options
        similaritys = []
        for words in wordlist:
            try:
                similaritys.append(wordnet.synsets(word, lang="jpn")[0].path_similarity(wordnet.synsets(words, lang="jpn")[0]))
            except IndexError:
                similaritys.append(0)

        dic = dict(zip(wordlist, similaritys))
        dic = sorted(dic.items(), key=lambda x: x[1], reverse=True)
        nums = list(dict((x, y) for x, y in dic).values())

        if nums[0] >= 0.5:
            dic = list(dict((x, y) for x, y in dic).keys())
            word = dic[0]
            summary = str(wikipedia_summary(word))

    except Exception:
        pass

    try:
        similarity = wordnet.synsets(word, lang="jpn")[0].path_similarity(wordnet.synsets(page.title, lang="jpn")[0])
    except Exception:
        similarity = 0

    if page is not None:
        if word not in page.title and page.title not in word:
            summary = "ユーザーによって追加されたタグ"

    return summary


import hashlib


def sha256_hash(path):
    with open(path, "rb") as f:
        hasher = hashlib.new("sha256")
        for chunk in iter(lambda: f.read(2048 * hasher.block_size), b''):
            hasher.update(chunk)
    return hasher.hexdigest()


import re


def clean_html(html):
    tag_pattern = re.compile(r'<.*?>')
    text = re.sub(tag_pattern, '', html)
    text_with_whitespace = re.sub(r'(\w)([^\w\s])', r'\1 \2', text)
    text_with_whitespace = re.sub(r'([^\w\s])(\w)', r'\1 \2', text_with_whitespace)
    return text_with_whitespace
