# Ideia de arquitetura

Este projeto pode ser organizado em três camadas principais:

```text
Aplicação final
Atomic Broadcast
SocketNode
```

A ideia mais importante é que cada parte tenha uma responsabilidade diferente.

## 1. Aplicação final

A aplicação final é o sistema que usa o Atomic Broadcast.

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
- se for líder, criar um seq_id
- se não for líder, enviar request para o líder
- receber mensagens JSON da rede
- guardar mensagens fora de ordem em waiting_messages
- entregar mensagens na ordem correta
```

Existem dois tipos de mensagem usados pelo Atomic Broadcast:

```text
request
deliver
```

### request

Um `request` é um pedido enviado por um nó comum para o líder.

Exemplo:

```json
{
    "type": "request",
    "sender_id": 2,
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
Líder, quero enviar essa mensagem para todos.
Coloque ela na ordem global.
```

### deliver

Um `deliver` é uma mensagem que o líder já ordenou.

Exemplo:

```json
{
    "type": "deliver",
    "seq_id": 0,
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
Todos os processos devem entregar essa mensagem como a mensagem número 0.
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

4. Se o nó não for líder:
   AtomicBroadcast cria um request e manda para o líder

5. SocketNode envia o request por socket

6. Líder recebe o request

7. AtomicBroadcast do líder cria um seq_id

8. Líder cria uma mensagem deliver

9. SocketNode do líder envia o deliver para todos os nós

10. Cada nó recebe o deliver

11. AtomicBroadcast entrega a mensagem na ordem correta

12. LeilaoApp aplica o lance
```

## Relação entre os arquivos

```text
LeilaoApp.py
    chama AtomicBroadcast.broadcast()
    recebe mensagens entregues pelo AtomicBroadcast

AtomicBroadcast.py
    ordena mensagens
    usa send_callback para enviar JSON

SocketNode.py
    implementa o send_callback
    recebe JSON pela rede
    chama AtomicBroadcast._on_receive_from_network()
```

## Exemplo de conexão no código

```python
auction = LeilaoApp()

atomic = AtomicBroadcast(
    id=node_id,
    nodes=[0, 1, 2],
    is_leader=(node_id == 0),
    leader_id=0
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

## Por que separar assim?

Essa separação ajuda porque cada arquivo fica simples:

```text
LeilaoApp.py
    regra de negócio

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
