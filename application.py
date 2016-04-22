from flask import Flask, render_template
from PIL import Image, ImageOps


app = Flask(__name__)


@app.route('/')
def index():
    return render_template('application.html')


if __name__ == '__main__':
    app.run(debug=True)
