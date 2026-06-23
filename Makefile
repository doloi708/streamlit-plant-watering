.PHONY: install streamlitapp

VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

install:
	python3 -m venv $(VENV)
	$(PYTHON) -m pip install --upgrade pip
	@if [ -f /proc/device-tree/model ] && grep -qi 'Raspberry Pi' /proc/device-tree/model; then \
		tmp_requirements=$$(mktemp); \
		grep -v '^streamlit$$' requirements.txt > $$tmp_requirements; \
		$(PIP) install -r $$tmp_requirements; \
		rm -f $$tmp_requirements; \
		$(PIP) install RPi-GPIO; \
	else \
		$(PIP) install -r requirements.txt; \
	fi

streamlitapp:
	$(PYTHON) -m streamlit run main_streamlitapp.py