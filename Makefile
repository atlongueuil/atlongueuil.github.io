serve:
	docker run --rm --interactive --tty --volume $(PWD):/src --workdir /src --publish 8080:8080 \
	    python:3 bash -c " \
			python3 -m venv .env && \
	        source .env/bin/activate && \
			python3 -m pip install --upgrade pip && \
			python3 -m pip install --no-cache-dir ruff markdown jinja2 && \
            python3 make-site.py && \
            python3 -m http.server 8080"
