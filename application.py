import base64
import hashlib
import io
import json
import logging
import tempfile
import os
import urllib.request
from collections import OrderedDict
from contextlib import contextmanager
from os.path import dirname, exists, join
from uuid import uuid4

from flask import Flask, redirect, render_template, request, url_for
from imgurpython import ImgurClient
from PIL import Image, ImageDraw, ImageFont, ImageOps


logging.basicConfig()


app = Flask(__name__)


STATIC = join(app.root_path, 'static')
MASK = join(STATIC, 'img', 'mask.png')
FONTS_PATH = join(STATIC, 'fonts')
WHITE = '#ffffff'
BLACK = '#000000'
DEFAULT_FONT_SIZE = 36
DEFAULT_TEXT_X = 250
DEFAULT_TEXT_Y = 530
DEFAULT_OVERLAY_TEXT_X = 340
DEFAULT_OVERLAY_TEXT_Y = 20


FONTS = {
    i: font for i, font in enumerate(os.listdir(FONTS_PATH))
    if font.lower().endswith('ttf')
    and 'glyph' not in font.lower()
}
FONTS_IDS = {
    font: i for i, font in FONTS.items()
}
DEFAULT_FONT = 'SourceSansPro-Bold.ttf'
DEFAULT_FONT_ID = FONTS_IDS[DEFAULT_FONT]


STATIC_HASHES = {}


class Credentials:
    def __init__(self, service):
        self.service = service

    @classmethod
    def for_imgur(cls):
        return cls('imgur')

    def credentials_folder(self):
        path = join(dirname(__file__), 'credentials')
        os.makedirs(path, exist_ok=True)

        return path

    def credentials_file(self):
        return join(self.credentials_folder(), '{}.json'.format(self.service))

    @property
    def data(self):
        with open(self.credentials_file()) as f:
            data = json.load(f)

        return data

    @data.setter
    def data(self, data):
        with open(self.credentials_file(), 'w') as f:
            json.dump(data, f)


def new_hash_for(path):
    file_path = join(STATIC, path)

    try:
        with open(file_path, 'rb') as f:
            m = hashlib.md5()
            m.update(f.read())
            hash_ = m.hexdigest()
    except:
        hash_ = uuid4()

    url = '{}?_={}'.format(url_for('static', filename=path), hash_)
    STATIC_HASHES[path] = url

    return url


def hashed_static(path):
    if path in STATIC_HASHES:
        return STATIC_HASHES[path]

    return new_hash_for(path)


def font_path(font_id):
    font = FONTS[font_id]
    return join(FONTS_PATH, font)


def generate(original_photo, context):
    mask = Image.open(MASK)
    photo = ImageOps.fit(original_photo, mask.size)
    mask = mask.convert('RGBA')
    photo = photo.convert('RGBA')

    photo = process_image(context, photo)

    composition = Image.alpha_composite(photo, mask)

    draw_text(composition, context)

    buffer = io.BytesIO()
    composition.save(buffer, format='PNG')
    image_bytes = base64.b64encode(buffer.getvalue())

    return image_bytes.decode('ascii')


def process_image(context, photo):
    if context['process_image']:
        photo = photo.convert('L')
        photo = ImageOps.equalize(photo)
        photo = ImageOps.colorize(photo, context['black'], context['white'])
        photo = photo.convert('RGBA')
    return photo


def draw_text(composition, context):
    draw = ImageDraw.Draw(composition)

    main_font = ImageFont.truetype(
        font_path(context['font_family']), context['font_size'])
    draw.multiline_text(
        (context['text_x'], context['text_y']),
        context['title'], context['font_color'], main_font)

    overlay_font = ImageFont.truetype(
        font_path(context['overlay_font_family']),
        context['overlay_font_size'])
    draw.multiline_text(
        (context['overlay_text_x'], context['overlay_text_y']),
        context['overlay_title'], context['overlay_font_color'],
        overlay_font)


def link_for_original(original_photo):
    credentials = Credentials.for_imgur()
    data = credentials.data
    client = ImgurClient(
        data['client_id'], data['client_secret'],
        data['access_token'], data['refresh_token'],
    )
    with tempfile.NamedTemporaryFile() as f:
        original_photo.save(f, format='PNG')
        response = client.upload_from_path(f.name)

    return response['link']


def generate_from_file(file, context):
    original_photo = Image.open(file.stream)
    try:
        link = link_for_original(original_photo)
        context['url'] = link
    except Exception as e:
        logging.exception(e)
    return generate(original_photo, context)


def generate_from_url(url, context):
    buffer = io.BytesIO()
    stream = urllib.request.urlopen(context['url'])
    original_photo = Image.open(stream)
    return generate(original_photo, context)


def int_from(name, default=0):
    try:
        return int(request.form.get(name, str(default)).strip())
    except:
        return default


def clean_string(name, default=''):
    return request.form.get(name, default).replace('\r', '')


def create_context():
    context = {
        'white': clean_string('white', WHITE),
        'black': clean_string('black', BLACK),
        'url': clean_string('url'),
        'process_image': bool(request.form.get('process_image')),
        'font_families': FONTS.items(),

        # Main title
        'title': clean_string('title'),
        'font_color': clean_string('font_color', BLACK),
        'font_family': int_from('font_family', DEFAULT_FONT_ID),
        'text_x': int_from('text_x', DEFAULT_TEXT_X),
        'text_y': int_from('text_y', DEFAULT_TEXT_Y),
        'font_size': int_from('font_size', DEFAULT_FONT_SIZE),

        # Overlay title
        'overlay_title': clean_string('overlay_title'),
        'overlay_font_color': clean_string('overlay_font_color', WHITE),
        'overlay_font_family': int_from(
            'overlay_font_family', DEFAULT_FONT_ID),
        'overlay_text_x': int_from('overlay_text_x', DEFAULT_OVERLAY_TEXT_X),
        'overlay_text_y': int_from('overlay_text_y', DEFAULT_OVERLAY_TEXT_Y),
        'overlay_font_size': int_from('overlay_font_size', DEFAULT_FONT_SIZE),

        # Post text
        'post_title': clean_string('post_title'),
        'post_message': clean_string('post_message'),
    }
    return context


@app.route('/', methods=['POST', 'GET'])
def index():

    context = create_context()

    if request.method == 'POST':
        file = request.files['file']
        try:
            if file.filename:
                context['image'] = generate_from_file(file, context)
            elif context['url']:
                context['image'] = generate_from_url(context['url'], context)
        except Exception as e:
            logging.exception(e)
            context['error'] = 'Não foi possível gerar a imagem'
    else:
        context['process_image'] = True

    return render_template('application.html', **context)


@app.route('/imgur', methods=['POST', 'GET'])
def imgur():
    fields = (
        'client_id',
        'client_secret',
        'access_token',
        'refresh_token',
    )
    context = OrderedDict()
    for field in fields:
        context[field] = request.form.get(field, '')

    creds = Credentials.for_imgur()

    if request.method == 'POST':
        client_id = context['client_id']
        client_secret = context['client_secret']
        creds.data = context
        if client_id and client_secret:
            client = ImgurClient(client_id, client_secret)
            authorization_url = client.get_auth_url('code')
            return redirect(authorization_url)
    elif 'code' in request.args:
        data = creds.data
        client_id = data['client_id']
        client_secret = data['client_secret']
        client = ImgurClient(client_id, client_secret)
        code = request.args['code']

        credentials = client.authorize(code, 'authorization_code')
        client.set_user_auth(
            credentials['access_token'], credentials['refresh_token'])
        data.update(credentials)
        context.update(data)
        creds.data = data

    return render_template(
        'imgur.html', context=context, **context)


app.jinja_env.globals['hashed_static'] = hashed_static


if __name__ == '__main__':
    app.run(debug=True)
