.PHONY: test-mencius

PYTHON ?= python3

test-mencius:
	$(PYTHON) -B tests/teste_carga_balanceada.py
	$(PYTHON) -B tests/teste_efeito_elastico.py
