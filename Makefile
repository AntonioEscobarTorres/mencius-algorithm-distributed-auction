.PHONY: test-all test-mencius test-socket test-leilao

PYTHON ?= python3

test-all: test-mencius test-socket test-leilao

test-mencius:
	$(PYTHON) -B tests/test_mencius_carga_balanceada.py
	$(PYTHON) -B tests/test_mencius_efeito_elastico.py

test-socket:
	$(PYTHON) -B tests/test_atomic_broadcast.py

test-leilao:
	$(PYTHON) -B tests/test_leilao_app.py
