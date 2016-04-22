from os.path import abspath, dirname
import sys

sys.path.insert(0, abspath(dirname(__file__)))
print(sys.path)

from application import app as application
