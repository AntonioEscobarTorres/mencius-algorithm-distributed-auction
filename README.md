# Leilão Distribuído com Atomic Broadcast


Universidade Federal de Santa Catarina — UFSC<br>
Departamento de Informática e Estatística — INE<br>
Semestre 2026/1 — Trabalho 2: Aplicação Distribuída baseada em Building Blocks

## Autores

- Antônio Escobar Torres
- Lucas Brand Samuel Martins
- Patrícia Bardini Arigoni

## Como executar

### Requisitos

- Python 3;
- suporte a sockets TCP;
- portas `5000`, `5001` e `5002` disponíveis.

O projeto utiliza apenas a biblioteca padrão do Python.

### Aplicação interativa

Abra três terminais na raiz do projeto e inicie todos os nós antes de enviar
qualquer evento.

```bash
# Terminal 1
python3 -B auction_node.py 0

# Terminal 2
python3 -B auction_node.py 1

# Terminal 3
python3 -B auction_node.py 2
```

Em qualquer nó, utilize:

```text
bid <usuario> <valor>   envia um lance
close                   fecha o leilão
status                  exibe o estado da réplica
help                    exibe os comandos
quit                    encerra o processo
```

Encerre cada nó com `quit`, `Ctrl+C` ou `Ctrl+Z`. Esses comandos finalizam o
processo e liberam sua porta TCP.

Exemplo:

```text
bid Alice 1000
bid Bob 1200
status
close
```

O comando `status` deve mostrar o mesmo resultado nas três réplicas.

### Testes

```bash
make test-all           # executa os testes principais
make test-mencius       # carga balanceada e efeito elástico com SKIP
make test-socket        # comunicação entre três processos via TCP
make test-leilao        # regras e convergência do leilão
make test-concorrencia  # lances concorrentes
```

## Estrutura do projeto

```text
.
├── auction_node.py
├── LeilaoApp.py
├── AtomicBroadcast.py
├── SocketNode.py
├── Makefile
├── README.md
└── tests/
```

### Arquivos principais

- `auction_node.py`: ponto de entrada da aplicação. Configura os três nós,
  conecta as camadas do sistema, inicia o servidor TCP e disponibiliza os
  comandos interativos do leilão.

- `LeilaoApp.py`: implementa as regras e mantém o estado local do leilão,
  incluindo maior lance, vencedor, fechamento e histórico. Publica eventos pelo
  Atomic Broadcast e aplica os eventos entregues em ordem total.

- `AtomicBroadcast.py`: implementa o building block inspirado no Mencius.
  Distribui os slots entre os nós, cria mensagens `deliver` e `skip`, armazena
  mensagens fora de ordem e entrega os eventos à aplicação na ordem global.

- `SocketNode.py`: implementa a camada de comunicação entre processos usando
  sockets TCP. Envia mensagens JSON, aceita conexões e encaminha os pacotes
  recebidos para o Atomic Broadcast.

- `Makefile`: reúne atalhos para executar os testes e cenários de demonstração
  do projeto.

- `README.md`: contém a documentação, as instruções de execução, o modelo de
  sistema, a arquitetura e as limitações da implementação.

- `tests/`: contém os testes automatizados e os cenários de demonstração. Seus
  arquivos não fazem parte da execução interativa da aplicação.

## Visão geral

Este projeto implementa um leilão distribuído replicado sobre um building block
de **Atomic Broadcast** inspirado no algoritmo Mencius.

Cada processo mantém uma réplica do leilão. Lances e solicitações de fechamento
podem ser enviados por qualquer réplica e são difundidos para todos os processos.
O Atomic Broadcast determina uma ordem global para esses eventos, fazendo com
que todas as réplicas os apliquem na mesma ordem e cheguem ao mesmo estado final.

O sistema utiliza três processos independentes e comunicação real por sockets
TCP, atendendo aos requisitos do trabalho.

## Building block: Atomic Broadcast

O Atomic Broadcast oferece a seguinte propriedade central:

> Todos os processos participantes entregam as mensagens na mesma ordem.

Neste projeto, a ordenação é feita por uma sequência global de slots. A
responsabilidade pelos slots é distribuída de forma rotativa entre os nós:

```text
Nó 0: slots 0, 3, 6, 9, ...
Nó 1: slots 1, 4, 7, 10, ...
Nó 2: slots 2, 5, 8, 11, ...
```

Quando um nó publica um evento, ele utiliza o próximo slot sob sua
responsabilidade e envia a mensagem para todos os participantes.

Se uma mensagem de um slot futuro for recebida, os proprietários dos slots
anteriores que ficaram ociosos enviam mensagens `SKIP`. Um `SKIP` ocupa uma
posição vazia na sequência, permitindo que a entrega avance sem repassar um
evento para a aplicação.

Mensagens recebidas fora de ordem permanecem em um buffer até que todos os
slots anteriores tenham sido preenchidos por uma mensagem `deliver` ou `skip`.

## Modelo de sistema

A implementação adota as seguintes premissas:

- o sistema possui um conjunto fixo e previamente conhecido de processos;
- cada processo possui um identificador único;
- todos os processos conhecem os identificadores e endereços dos demais;
- todos utilizam a mesma lista ordenada de participantes;
- os três nós devem estar ativos antes do início do envio de eventos;
- os nós não falham durante a execução do leilão;
- mensagens enviadas entre nós ativos são eventualmente entregues;
- não há entrada ou saída dinâmica de participantes;
- não são considerados processos maliciosos ou falhas bizantinas.

A configuração atual possui três processos:

| Nó | Endereço | Porta |
|---:|:---------|------:|
| 0 | 127.0.0.1 | 5000 |
| 1 | 127.0.0.1 | 5001 |
| 2 | 127.0.0.1 | 5002 |

## Arquitetura

O sistema está dividido em três camadas:

```text
LeilaoApp
    ↓ broadcast(evento)
AtomicBroadcast
    ↓ envio de deliver/skip
SocketNode
    ↓ TCP
Outros processos
```

### Aplicação de leilão

`LeilaoApp.py` contém as regras da aplicação e o estado replicado:

- maior lance;
- vencedor atual;
- estado aberto ou fechado do leilão;
- histórico de eventos aplicados.

Um lance é aceito somente quando o leilão está aberto e seu valor é maior que o
maior lance atual. Após o fechamento, novos lances são rejeitados.

### Atomic Broadcast

`AtomicBroadcast.py` implementa o building block e é independente das regras do
leilão. Suas responsabilidades são:

- atribuir slots aos eventos locais;
- difundir mensagens `deliver`;
- produzir mensagens `skip` para slots ociosos;
- armazenar mensagens recebidas fora de ordem;
- entregar eventos para a aplicação segundo a ordem global;
- evitar a entrega repetida de um mesmo slot.

### Comunicação

`SocketNode.py` implementa a comunicação TCP usando Berkeley sockets. Cada nó
executa um servidor em uma porta própria e cria uma conexão para cada envio. As
mensagens são serializadas em JSON.

### Inicialização

`auction_node.py` conecta as três camadas, inicia o servidor do nó e fornece a
interface de linha de comando.

## Fluxo de um lance

1. O usuário executa `bid Alice 1000`.
2. `LeilaoApp` cria um evento de lance.
3. A aplicação chama `AtomicBroadcast.broadcast(evento)`.
4. O nó atribui ao evento seu próximo slot global.
5. Uma mensagem `deliver` é enviada a todos os nós por TCP.
6. Cada nó armazena a mensagem recebida.
7. Slots ociosos anteriores são preenchidos com mensagens `SKIP`.
8. Os eventos são entregues em ordem crescente de slot.
9. Cada réplica aplica o mesmo evento ao estado local.

## API do building block

Criação de uma instância:

```python
atomic = AtomicBroadcast(id=node_id, nodes=[0, 1, 2])
```

Registro da função responsável pelo envio:

```python
atomic.register_send_callback(socket_node.send)
```

Registro da função chamada quando um evento pode ser aplicado:

```python
atomic.register_deliver_callback(app.apply_event)
```

Publicação de um evento:

```python
atomic.broadcast(event)
```

## Limitações

Esta é uma implementação didática inspirada no Mencius, e não uma implementação
completa e tolerante a falhas do protocolo.

- não há retransmissão de mensagens;
- não há confirmação de recebimento no nível da aplicação;
- não há recuperação de nós após falha ou reinicialização;
- não há persistência de mensagens ou do estado do leilão;
- não há detecção de falhas;
- não há reconfiguração dinâmica do conjunto de participantes;
- não há tolerância a falhas bizantinas;
- uma mensagem enviada enquanto um nó está desligado não será recuperada;
- a perda de um slot necessário pode impedir o avanço da entrega.

Por essas razões, todos os nós devem ser iniciados antes do uso e permanecer
ativos durante a demonstração.

## Conclusão

O projeto demonstra o uso de Atomic Broadcast como parte central de uma
aplicação distribuída funcional. A ordem total dos eventos permite que réplicas
independentes do leilão processem lances concorrentes de maneira determinística
e mantenham estados equivalentes.

A simplificação adotada torna visíveis os principais mecanismos de slots,
liderança rotativa, buffering e `SKIP`, mas transfere a tolerância a falhas para
as restrições do modelo de sistema.
