# 🐉 XuLang Web Compiler  
Um ambiente completo de **edição, compilação e execução** de programas escritos na linguagem **XuLang**, convertendo-os para C via um compilador implementado em **Python + PLY**, e rodando tudo automaticamente em um backend **Node.js** dentro de um container Docker.

Este projeto contém:

- 🖥 **Frontend** em React + CodeMirror  
- ⚙️ **Backend** em Node.js (Express)  
- 🐍 **Compilador XuLang → C** (Python + PLY)  
- 🔧 Execução automatizada via **gcc** dentro do container  
- 🔌 Comunicação frontend ↔ backend via fetch  
- 🐳 Configuração completa com **Docker Compose**

## 🚀 Funcionalidades

### 📘 **1. Editor de Código XuLang**
- Interface moderna com CodeMirror.
- Realce de sintaxe.
- Exemplo inicial de programa XuLang carregado automaticamente.

### 🎯 **2. Detecção automática dos comandos `LEIA`**
O frontend analisa o código em tempo real e detecta todos os comandos `LEIA`, gerando automaticamente os campos de entrada na ordem correta.

Esses valores são enviados como **stdin para o programa C compilado**.

### 🛠 **3. Compilação XuLang → C**
O backend usa:

- `python3`
- `xu_compiler.py` (seu compilador em PLY)
- Redireciona stdout do compilador para gerar `out.c`

### ⚡ **4. Compilação C para binário**
Após gerar `out.c`, o backend executa:

```
gcc out.c -o program
```

Em seguida, roda o binário:

```
./program
```

### 🌐 **5. Execução Sandbox**
Cada requisição cria uma pasta isolada em `/tmp/xu_XXXXXX`, contendo:

- `program.xu`
- `out.c`
- `program`  
- `stdin.txt` (caso haja entradas)

Após a execução, essa pasta é automaticamente removida.

### 🖥 **6. UI de Execução**
O frontend possui:

- Botão **Compilar e Executar**
- Painel **Entradas (LEIA)**
- Painel de **Logs / Saída**
- Erros léxicos, sintáticos e semânticos são exibidos claramente

## 🧱 Estrutura do Projeto

```
/
├── backend/
│   ├── server.js
│   ├── xu_compiler.py
│   ├── Dockerfile
│   └── package.json
│
├── frontend/
│   ├── src/
│   ├── public/
│   └── Dockerfile
│
├── docker-compose.yml
└── README.md
```

## 🐳 Como rodar com Docker

### 1. Instale Docker Desktop

### 2. Execute:

```
docker compose up --build
```

### 3. Acesse:

```
http://localhost:5173
```

## 🧠 Fluxo de Execução Completo

### 1️⃣ Frontend envia:

```json
POST /api/compile
{
  "code": "<codigo XuLang>",
  "inputs": ["valor1", "valor2"]
}
```

### 2️⃣ Backend:

- Cria tempdir  
- Salva programa  
- Executa Python  
- Compila C  
- Executa binário  

E retorna:

```json
{
  "errors": [],
  "c_code": "...",
  "run_stdout": "resultado"
}
```

## 📄 Sobre o Compilador XuLang
Implementado com **PLY**, contendo:

- Lexer  
- Parser  
- Tabela de símbolos  
- Geração de C  
- Erros semânticos e sintáticos  

### Exemplos suportados:

```
idade : INTEIRO
LEIA idade
SE idade >= 18 ENTAO ...
```

## 🛡 Erros suportados

- Variáveis não declaradas  
- Tipos incorretos  
- Erros de sintaxe  
- Comentários `#`

## 🧪 Exemplo XuLang

```
: DECLARACOES
idade : INTEIRO

: PROGRAMA
LEIA idade
SE idade >= 18 ENTAO
    ESCREVA "Maior de idade"
FIM
```

## 🤝 Contribuição
Pull requests são bem-vindos!

## 📜 Licença
MIT
