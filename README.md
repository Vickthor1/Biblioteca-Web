# 📘 Biblioteca Universitária Web

Este documento reúne **toda a documentação essencial** do sistema de Biblioteca Universitária, cobrindo:

* ✔️ Estrutura e funcionamento da **Web UI**
* ✔️ Descrição completa do **banco de dados SQL**
* ✔️ Como instalar, configurar e utilizar
* ✔️ Fluxo geral do sistema

---

# 📌 1. Visão Geral do Sistema

O projeto implementa uma solução completa para gerenciamento de biblioteca, incluindo:

### 🎨 **Interface Web (web_ui.html)**

* Abas laterais com navegação moderna
* CRUD completo de Usuários, Livros e Empréstimos
* Login com token
* Filtro de empréstimos
* Visualização de logs

### 🛢️ **Banco de Dados PostgreSQL (biblioteca.sql)**

* Estrutura completa com tabelas normalizadas
* Integridade garantida com constraints e triggers
* View agregando informações completas dos empréstimos
* Sistema de logs automatizado
* Roles para controle de permissões (admin e leitor)

---

# 📁 2. Estrutura Geral do Projeto

```
📦 projeto-biblioteca
├── backend_full.py        # API em Flask (opcional, caso esteja usando backend)
├── web_ui.html            # Interface Web completa
├── biblioteca.sql         # Estrutura do banco de dados
└── README.md              # Este documento
```

---

# 🌐 3. Web UI — Funcionamento

A interface Web é completamente estática (HTML + CSS + JS) e possui integração com API backend.

A navegação é realizada por uma barra lateral com abas:

## 🔐 3.1 Login

* Entrada de usuário e senha
* Envia requisição para `/auth/login`
* Salva token no `localStorage`
* Determina se o usuário é **admin** ou **leitor**

## 🧭 3.2 Dashboard

* Área inicial
* Pode futuramente conter gráficos, relatórios e KPIs

## 👥 3.3 Usuários (CRUD)

Funcionalidades:

* Adicionar usuário
* Editar usuário
* Remover usuário
* Listar todos os usuários

Campos:

* Nome
* Tipo (aluno, funcionário, etc.)
* E-mail

Ações disponíveis apenas para **admin**.

## 📚 3.4 Livros (CRUD)

Permite:

* Registrar novos livros
* Atualizar dados
* Excluir títulos
* Visualizar estoque

Campos:

* Título
* Autor
* ISBN
* Quantidade

## 📘 3.5 Empréstimos

Inclui:

* Registrar empréstimo
* Atualizar registros
* Excluir registros
* Registrar devolução
* Filtro: somente "em andamento"
* Exibição através da view `vw_emprestimos_overview`

## 📝 3.6 Logs

Exibe as 500 últimas ações registradas na tabela `log_emprestimos`.
Gerações automáticas são feitas via trigger no banco.

---

# 🛢️ 4. Banco de Dados — Explicação Completa

Abaixo está a explicação do arquivo **biblioteca.sql**.

## 🧱 4.1 Tabelas Criadas

### **1. usuarios**

Armazena todas as pessoas cadastradas.
Campos principais:

* id
* nome
* tipo
* email

### **2. livros**

Registra o acervo da biblioteca.
Campos:

* id
* titulo
* autor
* isbn
* quantidade

### **3. emprestimos**

Registra um empréstimo individual.
Campos:

* usuario_id (FK)
* livro_id (FK)
* data_emprestimo
* data_devolucao
* devolvido (TRUE/FALSE)

Tem também um índice único que impede duplicações de empréstimos não devolvidos:

```
CREATE UNIQUE INDEX idx_unica_nao_devolvida
ON emprestimos(usuario_id, livro_id)
WHERE devolvido = FALSE;
```

### **4. log_emprestimos**

Tabela de auditoria gerada automaticamente por trigger.
Registra:

* operação (INSERT, UPDATE, DELETE)
* valores antes/depois
* usuário do banco que executou
* timestamp

---

# 🔄 4.2 Trigger de Log

Sempre que um empréstimo é:

* criado
* alterado
* apagado

A trigger salva as informações na tabela `log_emprestimos`.

---

# 👁️ 4.3 View vw_emprestimos_overview

View que combina dados do empréstimo com informações do usuário e do livro.

Campos retornados:

* emprestimo_id
* usuario_nome
* usuario_tipo
* livro_titulo
* livro_autor
* status_devolvido

Facilita exibição na interface Web.

---

# 🛡️ 4.4 Roles e Permissões

O SQL cria dois usuários internos no PostgreSQL:

### **1️⃣ biblioteca_admin**

* Acesso total
* Pode usar CRUD completo
* Pode logar como administrador

### **2️⃣ biblioteca_leitor**

* Pode apenas consultar view `vw_emprestimos_overview`
* Não possui acesso direto às tabelas
* Não pode alterar registros

Também são aplicados vários `GRANT` e `REVOKE` garantindo segurança.

---

# 📚 5. Dados Iniciais Inseridos

O SQL já insere dados para testes:

### Usuários

* Ana Silva
* Carlos Pereira

### Livros

* Introdução a Banco de Dados
* Programação em Python

### Empréstimo padrão

* Livro ID 1 emprestado para Usuário ID 1

---

# ⚙️ 6. Como Executar o Banco de Dados

1. Abra o terminal do PostgreSQL:

```
psql -U postgres
```

2. Crie o banco:

```
CREATE DATABASE biblioteca_db;
```

3. Importe o SQL:

```
\i caminho/do/arquivo/biblioteca.sql
```

Pronto! O banco está criado com estrutura, permissões e dados iniciais.

---

# 🌎 7. Como Executar a Web UI

A Web UI pode funcionar:

* via backend Flask (abrindo automaticamente em `/`)
* abrindo manualmente o arquivo `web_ui.html` no navegador

Se usar o backend Flask:

```
python backend_full.py
```

Acesse:

```
http://localhost:5001/
```

---

# 🔑 8. Como Logar no Sistema

O login reflete os usuários de **roles do PostgreSQL**, e não os usuários da tabela `usuarios`.

Usuários padrão criados pelo SQL:

### 👑 Administrador

```
Usuário: biblioteca_admin
Senha: admin_pass
```

### 📗 Leitor

```
Usuário: biblioteca_leitor
Senha: reader_pass
```

Após logar:

* o token é armazenado no navegador
* a interface libera ou bloqueia recursos conforme o perfil

---

# ✔️ 9. Final
