import base64
import logging
import io
import os
import urllib.request
from os.path import exists, join

from flask import Flask, render_template, request
from PIL import Image, ImageDraw, ImageFont, ImageOps


logging.basicConfig()


app = Flask(__name__)


MASK = join(app.root_path, 'static', 'img', 'mask.png')
FONTS_PATH = join(app.root_path, 'static', 'fonts')
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
DEFAULT_FONT = 'Impact.ttf'
DEFAULT_FONT_ID = FONTS_IDS[DEFAULT_FONT]


def font_path(font_id):
    font = FONTS[font_id]
    return join(FONTS_PATH, font)


def generate(original_photo, context):
    mask = Image.open(MASK)
    photo = ImageOps.fit(original_photo, mask.size)
    mask = mask.convert('RGBA')
    photo = photo.convert('RGBA')

    if context['process_image']:
        photo = photo.convert('L')
        photo = ImageOps.equalize(photo)
        photo = ImageOps.colorize(photo, context['black'], context['white'])
        photo = photo.convert('RGBA')

    composition = Image.alpha_composite(photo, mask)


    draw = ImageDraw.Draw(composition)

    main_font = ImageFont.truetype(
        font_path(context['font_family']), context['font_size'])
    draw.multiline_text(
        (context['text_x'], context['text_y']),
        context['title'], context['font_color'], main_font)

    if context['overlay_title']:
        overlay_font = ImageFont.truetype(
            font_path(context['overlay_font_family']),
            context['overlay_font_size'])
        draw.multiline_text(
            (context['overlay_text_x'], context['overlay_text_y']),
            context['overlay_title'], context['overlay_font_color'],
            overlay_font)

    buffer = io.BytesIO()
    composition.save(buffer, format='PNG')
    image_bytes = base64.b64encode(buffer.getvalue())

    return image_bytes.decode('ascii')


def generate_from_file(file, context):
    original_photo = Image.open(file.stream)
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


@app.route('/', methods=['POST', 'GET'])
def index():

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
    }

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


if __name__ == '__main__':
    app.run(debug=True)
