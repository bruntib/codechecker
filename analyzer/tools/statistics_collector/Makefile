# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

CURRENT_DIR = $(shell pwd)
ROOT = $(CURRENT_DIR)

BUILD_DIR = $(CURRENT_DIR)/build
STATISTICS_COLLECTOR_DIR = $(BUILD_DIR)/statistics_collector

ACTIVATE_DEV_VENV ?= . venv_dev/bin/activate
ACTIVATE_RUNTIME_VENV ?= . venv/bin/activate

VENV_DEV_REQ_FILE ?= requirements_py/dev/requirements.txt

default: all

all: package

venv:
	# Create a virtual environment which can be used to run the build package.
	virtualenv -p python3 venv && $(ACTIVATE_RUNTIME_VENV)

venv_dev:
	# Create a virtual environment for development.
	virtualenv -p python3 venv_dev && \
		$(ACTIVATE_DEV_VENV) && pip install -r $(VENV_DEV_REQ_FILE)

clean_venv_dev:
	rm -rf venv_dev

include tests/Makefile

package:
	# Install package in 'development mode'.
	python setup.py develop

build:
	python setup.py build --build-purelib $(STATISTICS_COLLECTOR_DIR)

dist:
	# Create a source distribution.
	python setup.py sdist

upload_test: dist
	# Upload package to the TestPyPI repository.
	$(eval PKG_NAME := $(shell python setup.py --name))
	$(eval PKG_VERSION := $(shell python setup.py --version))
	twine upload -r testpypi dist/$(PKG_NAME)-$(PKG_VERSION).tar.gz

upload: dist
	# Upload package to the PyPI repository.
	$(eval PKG_NAME := $(shell python setup.py --name))
	$(eval PKG_VERSION := $(shell python setup.py --version))
	twine upload -r pypi dist/$(PKG_NAME)-$(PKG_VERSION).tar.gz

clean:
	rm -rf $(BUILD_DIR)
	rm -rf dist
	rm -rf statistics_collector.egg-info