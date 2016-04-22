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
FONTS = join(app.root_path, 'static', 'fonts')
#UPLOADS = join(app.root_path, 'uploads')


#if not exists(UPLOADS):
    #os.mkdir(UPLOADS)


def generate(original_photo, context):
    mask = Image.open(MASK)
    photo = ImageOps.fit(original_photo, mask.size)
    mask = mask.convert('RGBA')
    photo = photo.convert('L')
    photo = ImageOps.equalize(photo)
    photo = ImageOps.colorize(photo, context['black'], context['white'])
    photo = photo.convert('RGBA')

    composition = Image.alpha_composite(photo, mask)

    font_path = join(FONTS, 'SourceSansPro-Bold.ttf')
    text_coords = (250, 530)
    text_color = (0, 0, 0, 255)
    font = ImageFont.truetype(font_path, context['size'])
    draw = ImageDraw.Draw(composition)
    draw.multiline_text(text_coords, context['title'], text_color, font)

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


@app.route('/', methods=['POST', 'GET'])
def index():
    context = {}
    if request.method == 'POST':
        try:
            size = int(request.form['size'].strip())
        except:
            size = 20
        context['title'] = request.form['title'].replace('\r', '')
        context['url'] = request.form['url']
        context['white'] = request.form['white']
        context['black'] = request.form['black']
        context['size'] = size
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
        context['white'] = '#ffffff'
        context['black'] = '#000000'
        context['size'] = 20
    return render_template('application.html', **context)


if __name__ == '__main__':
    app.run(debug=True)
