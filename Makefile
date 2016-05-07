deploy:
	ssh webfaction 'bash -s' < deploy.sh

freeze:
	pip freeze > requirements.txt

setup:
	pip install -r requirements.txt

run:
	python application.py
