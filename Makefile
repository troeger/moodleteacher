.PHONY: build check-venv

# Make Python wheels
default: build

# Prepare VirtualEnv by installing project dependencies
venv/bin/activate: requirements.txt 
	test -d venv || python3 -m venv venv
	venv/bin/pip install -r requirements.txt
	touch venv/bin/activate

# Shortcut for preparation of VirtualEnv
venv: venv/bin/activate

check-venv:
ifndef VIRTUAL_ENV
	$(error Please create a VirtualEnv with 'make venv' and activate it)
endif

# Build the Python wheel install packages.
build:
	python ./setup.py bdist_wheel

# Update version numbers, commit and tag 
bumpversion:
	bumpversion patch

# Upload built packages to PyPI.
# Assumes valid credentials in ~/.pypirc
pypi-push: check-venv build
	twine upload dist/moodleteacher-0.0.11-py3-none-any.whl

# Run test suite
test:
	nosetests


# Clean temporary files
clean:
	rm -fr  build
	rm -fr  dist
	rm -fr  *egg-info
	find . -name "*.bak" -delete
	find . -name "__pycache__" -delete
