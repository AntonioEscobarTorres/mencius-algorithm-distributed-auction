# Ideia de arquitetura

Este projeto pode ser organizado em três camadas principais:

```text
Aplicação final / testes
Atomic Broadcast
SocketNode
```

A ideia mais importante é que cada parte tenha uma responsabilidade diferente.

## 1. Aplicação final ou testes

A aplicação final é o sistema que usa o Atomic Broadcast. Neste repositório ainda não existe uma aplicação completa de leilão separada; os arquivos em `tests/` fazem esse papel de cliente do building block.

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
    "value": 150
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

SocketNode.py
    implementa o send_callback
    recebe JSON pela rede
    chama AtomicBroadcast._on_receive_from_network()

tests/test_atomic_broadcast.py
    monta três SocketNode reais em localhost
    verifica que todos entregam a mesma sequência

tests/teste_carga_balanceada.py
    demonstra o caso ideal sem SKIP

tests/teste_efeito_elastico.py
    demonstra rajada de um nó e SKIPs dos nós ociosos

tests/test_mencius_skips.py
    demonstra o mecanismo mínimo de SKIP

Makefile
    executa os testes didáticos principais com make test-mencius
```

## Exemplo de conexão no código

```python
auction = LeilaoApp()

atomic = AtomicBroadcast(
    id=node_id,
    nodes=[0, 1, 2]
)

socket_node = SocketNode(node_id, nodes_config, atomic)

atomic.register_send_callback(socket_node.send)
atomic.register_deliver_callback(auction.apply_operation)

socket_node.start()
```

Nesse exemplo:

```text
auction.apply_operation
```

é chamado quando uma mensagem já foi ordenada e pode ser aplicada pela aplicação.

Nos testes atuais, esse callback é substituído por uma função que salva a mensagem em uma lista:

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
tests/teste_carga_balanceada.py
tests/teste_efeito_elastico.py
```

O teste com sockets reais roda com:

```bash
python3 -B tests/test_atomic_broadcast.py
```
