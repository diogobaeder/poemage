deploy:
	ssh webfaction 'bash -s' < deploy.sh

freeze:
	pip freeze > requirements.txt
