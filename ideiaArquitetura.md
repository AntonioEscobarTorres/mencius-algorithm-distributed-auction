# Ideia de arquitetura

Este projeto pode ser organizado em três camadas principais:

```text
Aplicação final / testes
Atomic Broadcast
SocketNode
```

A ideia mais importante é que cada parte tenha uma responsabilidade diferente.

## 1. Aplicação final e testes

A aplicação final é o sistema que usa o Atomic Broadcast. Neste repositório,
ela está implementada em `LeilaoApp.py`, enquanto `auction_node.py` fornece a
interface interativa para executar uma réplica do leilão em cada terminal.
Os arquivos em `tests/` verificam tanto o building block quanto as regras do
leilão.

Por exemplo:

```text
LeilaoApp
FlightReservationApp
ChatApp
```

Essa camada sabe o significado das mensagens.

Em um sistema de leilão, ela sabe o que é:

```text
- um lance
- um usuário
- um item
- o maior valor atual
- o vencedor
```

Exemplo de mensagem da aplicação:

```python
{
    "op": "bid",
    "auction_id": "A1",
    "user": "Antonio",
    "value": 150,
    "origin_node": 0
}
```

A aplicação não envia essa mensagem diretamente pelo socket. Ela chama:

```python
atomic_broadcast.broadcast(message)
```

## 2. AtomicBroadcast

O `AtomicBroadcast.py` é a biblioteca do building block.

Ele não precisa saber se a aplicação é de leilão, reserva de voo ou chat.

Ele só precisa garantir que todos os processos entreguem as mensagens na mesma ordem.

Responsabilidades:

```text
- receber broadcast(message)
- escolher o próximo seq_id pertencente ao próprio nó
- difundir a mensagem ordenada para todos
- enviar SKIP para slots próprios que ficaram ociosos
- receber mensagens JSON da rede
- guardar mensagens fora de ordem em waiting_messages
- entregar mensagens na ordem correta
```

Existem dois tipos de mensagem usados pelo Atomic Broadcast:

```text
deliver
skip
```

### Liderança rotativa

O algoritmo usa a ideia do Mencius: não existe um líder único.
Cada nó é líder de alguns IDs globais.

Com três nós:

```text
node 0: seq_id 0, 3, 6, 9...
node 1: seq_id 1, 4, 7, 10...
node 2: seq_id 2, 5, 8, 11...
```

Quando um nó chama:

```python
atomic_broadcast.broadcast(message)
```

ele usa diretamente o próximo `seq_id` que pertence a ele e envia para todos.
Cada nó decide seus próprios slots de forma independente.

### deliver

Um `deliver` é uma mensagem que um nó já colocou no seu slot global.

```json
{
    "type": "deliver",
    "seq_id": 2,
    "data": {
        "op": "bid",
        "auction_id": "A1",
        "user": "Bob",
        "value": 200
    }
}
```

Significado:

```text
Todos os processos devem entregar essa mensagem na posição seq_id = 2.
```

### skip

Um `skip` ocupa um slot vazio quando o dono daquele slot não tem mensagem de aplicação para enviar.
Ele destrava a entrega, mas não é repassado para a aplicação.

Exemplo:

```json
{
    "type": "skip",
    "seq_id": 0,
    "sender_id": 0
}
```

Significado:

```text
O slot 0 está vazio e pode ser pulado.
```

O campo `seq_id` define a ordem global.

Se chegarem mensagens assim:

```text
seq_id = 0
seq_id = 1
seq_id = 2
```

todos os processos devem entregar nessa mesma ordem.

## 3. SocketNode

O `SocketNode.py` é a camada de comunicação.

Ele não sabe o que é leilão.

Ele também não decide a ordem das mensagens.

Responsabilidades:

```text
- abrir socket
- escutar conexões
- enviar string JSON para outro nó
- receber string JSON de outro nó
- entregar a string JSON recebida ao AtomicBroadcast
```

Quando recebe algo pela rede, ele chama:

```python
atomic_broadcast._on_receive_from_network(packet_json)
```

Quando o Atomic Broadcast quer enviar algo, ele chama o callback:

```python
send_callback(node_id, packet_json)
```

No projeto, esse callback é o método:

```python
socket_node.send
```

## Fluxo completo

Exemplo: usuário faz um lance em um leilão.

```text
1. Usuário faz lance de 200

2. LeilaoApp cria a mensagem:
   {"op": "bid", "user": "Bob", "value": 200}

3. LeilaoApp chama:
   atomic_broadcast.broadcast(message)

4. AtomicBroadcast escolhe o próximo seq_id pertencente ao próprio nó

5. SocketNode envia o deliver para todos os nós

6. Cada nó recebe o deliver

7. Se existirem slots anteriores vazios pertencentes a um nó, esse nó envia skip

8. AtomicBroadcast guarda mensagens fora de ordem até poder avançar

9. AtomicBroadcast entrega as mensagens reais na ordem correta

10. LeilaoApp aplica o lance
```

## Relação entre os arquivos

```text
AtomicBroadcast.py
    ordena mensagens
    usa send_callback para enviar JSON

LeilaoApp.py
    mantém o estado replicado do leilão
    publica lances e fechamento
    aplica eventos entregues em ordem total

auction_node.py
    conecta LeilaoApp, AtomicBroadcast e SocketNode
    oferece os comandos interativos bid, close, status, help e quit

SocketNode.py
    implementa o send_callback
    recebe JSON pela rede
    chama AtomicBroadcast._on_receive_from_network()

tests/test_atomic_broadcast.py
    monta três SocketNode reais em localhost
    verifica que todos entregam a mesma sequência

tests/test_mencius_carga_balanceada.py
    demonstra o caso ideal sem SKIP

tests/test_mencius_efeito_elastico.py
    demonstra rajada de um nó e SKIPs dos nós ociosos

tests/test_leilao_app.py
    verifica as regras do leilão e a convergência das réplicas

Makefile
    oferece atalhos para todos os testes
```

## Exemplo de conexão no código

```python
atomic = AtomicBroadcast(
    id=node_id,
    nodes=[0, 1, 2]
)

socket_node = SocketNode(node_id, nodes_config, atomic)
auction = LeilaoApp(
    node_id,
    atomic,
    auction_id="A1",
    item="Notebook"
)

atomic.register_send_callback(socket_node.send)
socket_node.start()
```

O construtor de `LeilaoApp` registra `auction.apply_event` como callback de
entrega. Esse método é chamado quando uma mensagem já foi ordenada e pode ser
aplicada ao estado replicado do leilão.

Nos testes do `AtomicBroadcast`, o callback pode ser uma função que salva a
mensagem em uma lista:

```python
atomic.register_deliver_callback(
    lambda message, node_id=node_id: delivered_messages[node_id].append(message)
)
```

## Por que separar assim?

Essa separação ajuda porque cada arquivo fica simples:

```text
Aplicação final, por exemplo LeilaoApp
    regra de negócio do domínio

AtomicBroadcast.py
    algoritmo distribuído

SocketNode.py
    comunicação por socket
```

Assim, se a aplicação mudar de leilão para reserva de voo, o `AtomicBroadcast.py` e o `SocketNode.py` continuam praticamente iguais.

## O que demonstrar no trabalho

Para demonstrar Atomic Broadcast, o ponto principal é mostrar que todos os processos entregam as mensagens na mesma ordem.

Exemplo de saída esperada:

```text
node 0:
  0: lance Alice 100
  1: lance Bob 200
  2: lance Carol 150

node 1:
  0: lance Alice 100
  1: lance Bob 200
  2: lance Carol 150

node 2:
  0: lance Alice 100
  1: lance Bob 200
  2: lance Carol 150
```

Mesmo que as mensagens cheguem em ordens diferentes pela rede, a entrega final deve ser igual em todos os nós.

## Como executar as demonstrações atuais

Os testes didáticos principais rodam com:

```bash
make test-mencius
```

Esse comando executa:

```text
tests/test_mencius_carga_balanceada.py
tests/test_mencius_efeito_elastico.py
```

Todos os testes rodam com:

```bash
make test-all
```

O teste com sockets reais roda com:

```bash
make test-socket
```

O teste da aplicação de leilão em memória roda com:

```bash
make test-leilao
```

## Aplicação interativa

Para executar três réplicas reais, abra três terminais e inicie todos os nós
antes de enviar lances:

```bash
# terminal 1
python3 -B auction_node.py 0

# terminal 2
python3 -B auction_node.py 1

# terminal 3
python3 -B auction_node.py 2
```

Os nós usam TCP em `127.0.0.1`, nas portas `5000`, `5001` e `5002`. Em qualquer
terminal, estão disponíveis os comandos:

```text
bid <usuario> <valor>
close
status
help
quit
```

Como não existe retransmissão, mensagens enviadas enquanto uma réplica estiver
desligada não são recuperadas quando ela iniciar.
