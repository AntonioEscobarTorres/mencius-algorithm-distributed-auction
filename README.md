# Distributed Auction

Projeto didático de **Atomic Broadcast** inspirado no Mencius, usando liderança rotativa por slots e mensagens `SKIP` para destravar posições vazias.

Para a explicação completa da arquitetura, do algoritmo, dos tipos de mensagem e do fluxo de entrega, veja [ideiaArquitetura.md](ideiaArquitetura.md).

## Estrutura

```text
AtomicBroadcast.py
    Building block de ordenação total.

LeilaoApp.py
    Aplicação final: leilão replicado sobre Atomic Broadcast.

auction_node.py
    Programa interativo para executar um processo do leilão.

SocketNode.py
    Camada de comunicação TCP entre nós.

tests/
    Testes didáticos em memória e teste com sockets reais.

Makefile
    Atalhos para execução dos testes principais.

ideiaArquitetura.md
    Documento detalhado da arquitetura e do funcionamento do algoritmo.
```

## Requisito

```text
Python 3
```

O projeto usa apenas a biblioteca padrão do Python.

## Como Rodar

Executar os testes didáticos principais:

```bash
make test-mencius
```

Executar todos os testes:

```bash
make test-all
```

Executar o teste com sockets TCP reais:

```bash
make test-socket
```

Executar a aplicação de leilão em memória:

```bash
make test-leilao
```

Executar a aplicação de leilão com três processos reais:

```bash
python3 -B auction_node.py 0
python3 -B auction_node.py 1
python3 -B auction_node.py 2
```

Em qualquer terminal, use comandos como:

```text
bid Alice 1000
bid Bob 1200
status
close
```

Executar testes individuais:

```bash
python3 -B tests/test_mencius_carga_balanceada.py
python3 -B tests/test_mencius_efeito_elastico.py
python3 -B tests/test_leilao_app.py
```

## Observação

Esta é uma implementação didática. Ela demonstra ordenação total, slots rotativos e `SKIP`, mas não implementa recuperação de falhas, persistência, retransmissão ou consenso completo tolerante a falhas.
