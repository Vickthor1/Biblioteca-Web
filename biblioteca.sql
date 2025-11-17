-- Tabelas
DROP TABLE IF EXISTS emprestimos CASCADE;
DROP TABLE IF EXISTS usuarios CASCADE;
DROP TABLE IF EXISTS livros CASCADE;
DROP TABLE IF EXISTS log_emprestimos CASCADE;

CREATE TABLE usuarios (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(200) NOT NULL,
    tipo VARCHAR(50) NOT NULL, -- ex: aluno, funcionario
    email VARCHAR(200) UNIQUE
);

CREATE TABLE livros (
    id SERIAL PRIMARY KEY,
    titulo VARCHAR(300) NOT NULL,
    autor VARCHAR(200),
    isbn VARCHAR(40) UNIQUE,
    quantidade INTEGER DEFAULT 1 CHECK (quantidade >= 0)
);

CREATE TABLE emprestimos (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE RESTRICT,
    livro_id INTEGER NOT NULL REFERENCES livros(id) ON DELETE RESTRICT,
    data_emprestimo DATE NOT NULL DEFAULT CURRENT_DATE,
    data_devolucao DATE,
    devolvido BOOLEAN NOT NULL DEFAULT FALSE
);

-- índice parcial substituindo a constraint antiga
CREATE UNIQUE INDEX idx_unica_nao_devolvida
ON emprestimos(usuario_id, livro_id)
WHERE devolvido = FALSE;

-- Tabela de log
CREATE TABLE log_emprestimos (
    id SERIAL PRIMARY KEY,
    operacao VARCHAR(10) NOT NULL, -- INSERT, UPDATE, DELETE
    registro_id INTEGER,
    usuario_db VARCHAR(200), -- current_user
    quando TIMESTAMP WITH TIME ZONE DEFAULT now(),
    dados_antes JSONB,
    dados_depois JSONB
);

-- Função e trigger para log de operações na tabela emprestimos
CREATE OR REPLACE FUNCTION fn_log_emprestimos() RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO log_emprestimos(operacao, registro_id, usuario_db, dados_depois)
        VALUES (TG_OP, NEW.id, current_user, to_jsonb(NEW));
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO log_emprestimos(operacao, registro_id, usuario_db, dados_antes, dados_depois)
        VALUES (TG_OP, NEW.id, current_user, to_jsonb(OLD), to_jsonb(NEW));
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO log_emprestimos(operacao, registro_id, usuario_db, dados_antes)
        VALUES (TG_OP, OLD.id, current_user, to_jsonb(OLD));
        RETURN OLD;
    END IF;
    RETURN NULL; -- should not happen
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_log_emprestimos
AFTER INSERT OR UPDATE OR DELETE ON emprestimos
FOR EACH ROW EXECUTE FUNCTION fn_log_emprestimos();

-- View agregada
CREATE OR REPLACE VIEW vw_emprestimos_overview AS
SELECT
  e.id AS emprestimo_id,
  u.nome AS usuario_nome,
  u.tipo AS usuario_tipo,
  l.titulo AS livro_titulo,
  l.autor AS livro_autor,
  e.data_emprestimo,
  e.data_devolucao,
  e.devolvido AS status_devolvido
FROM emprestimos e
JOIN usuarios u ON u.id = e.usuario_id
JOIN livros l ON l.id = e.livro_id;

-- Usuários do PostgreSQL (roles) e permissões
-- Cria usuário administrador
DO $$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'biblioteca_admin') THEN
       CREATE ROLE biblioteca_admin WITH LOGIN PASSWORD 'admin_pass';
   END IF;
   IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'biblioteca_leitor') THEN
       CREATE ROLE biblioteca_leitor WITH LOGIN PASSWORD 'reader_pass';
   END IF;
END$$;

-- Conceder permissões ao admin (tudo)
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO biblioteca_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO biblioteca_admin;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO biblioteca_admin;
GRANT USAGE ON SCHEMA public TO biblioteca_admin;

-- Conceder apenas SELECT na view para o leitor
GRANT SELECT ON vw_emprestimos_overview TO biblioteca_leitor;

-- Garantir que leitor não tenha acesso direto às tabelas
REVOKE ALL ON usuarios, livros, emprestimos, log_emprestimos FROM biblioteca_leitor;

-- Permitir que leitor conecte e use o banco
GRANT CONNECT ON DATABASE biblioteca_db TO biblioteca_leitor;
GRANT USAGE ON SCHEMA public TO biblioteca_leitor;

-- Exemplo de dados iniciais (para testes)
INSERT INTO usuarios(nome, tipo, email) VALUES
('Ana Silva','aluno','ana.silva@uni.edu'),
('Carlos Pereira','funcionario','carlos.p@uni.edu');

INSERT INTO livros(titulo, autor, isbn, quantidade) VALUES
('Introdução a Banco de Dados','Autor A','ISBN001',3),
('Programação em Python','Autor B','ISBN002',2);

-- Exemplo de empréstimo
INSERT INTO emprestimos(usuario_id, livro_id) VALUES (1,1);