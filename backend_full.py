# backend_full.py
import os
import uuid
import time
from functools import wraps
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor

# -------------------------
# Configuração (ajuste se necessário)
# -------------------------
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'port': int(os.environ.get('DB_PORT', 5432)),
    'database': os.environ.get('DB_NAME', 'biblioteca_db'),
    'user': os.environ.get('DB_USER', 'biblioteca_admin'),   # usuário de serviço (utilizado para executar queries)
    'password': os.environ.get('DB_PASS', 'senha')
}

# Tempo de validade do token (segundos)
TOKEN_TTL = 60 * 60  # 1 hora

app = Flask(__name__, static_folder='web')
CORS(app)

# sessions: token -> {user, role, expires_at}
SESSIONS = {}

# -------------------------
# Helpers
# -------------------------
def get_conn():
    return psycopg2.connect(**DB_CONFIG)

def create_temp_conn(user, password):
    """Tenta criar conexão com credenciais informadas — usado para autenticação."""
    try:
        return psycopg2.connect(host=DB_CONFIG['host'], port=DB_CONFIG['port'],
                                dbname=DB_CONFIG['database'], user=user, password=password)
    except Exception:
        return None

def require_token(min_role=None):
    """
    Decorator to require authentication.
    min_role: None -> any authenticated user
              'reader' -> any
              'admin' -> only admin
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            token = request.headers.get('X-Auth-Token') or request.args.get('token')
            if not token:
                return jsonify({'error':'missing token'}), 401
            s = SESSIONS.get(token)
            if not s or s['expires_at'] < time.time():
                return jsonify({'error':'invalid or expired token'}), 401
            # check role
            role = s['role']
            if min_role == 'admin' and role != 'admin':
                return jsonify({'error':'admin required'}), 403
            # attach session info
            request.session_user = s['user']
            request.session_role = s['role']
            return f(*args, **kwargs)
        return wrapper
    return decorator

# -------------------------
# Auth endpoints
# -------------------------
@app.route('/auth/login', methods=['POST'])
def auth_login():
    """
    Body: { user: str, password: str }
    Tries to open a DB connection with provided credentials. If OK, determines role membership (biblioteca_admin) and
    returns a token to be used in X-Auth-Token header in subsequent calls.
    """
    data = request.json or {}
    user = data.get('user')
    password = data.get('password')
    if not user or not password:
        return jsonify({'error':'user and password required'}), 400

    conn = create_temp_conn(user, password)
    if conn is None:
        return jsonify({'error':'invalid credentials'}), 401
    try:
        cur = conn.cursor()
        # determine membership in biblioteca_admin role
        cur.execute("SELECT pg_has_role(current_user, 'biblioteca_admin', 'member') AS is_admin;")
        is_admin = cur.fetchone()[0]
    except Exception:
        is_admin = False
    finally:
        try:
            conn.close()
        except:
            pass

    role = 'admin' if is_admin else 'reader'
    token = str(uuid.uuid4())
    expires_at = time.time() + TOKEN_TTL
    SESSIONS[token] = {'user': user, 'role': role, 'expires_at': expires_at}
    return jsonify({'token': token, 'role': role, 'expires_in': TOKEN_TTL})

@app.route('/auth/logout', methods=['POST'])
def auth_logout():
    data = request.json or {}
    token = data.get('token') or request.headers.get('X-Auth-Token')
    if token and token in SESSIONS:
        SESSIONS.pop(token, None)
    return jsonify({'ok': True})

# -------------------------
# Serve web UI (static)
# -------------------------
@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'web_ui.html')

@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory(app.static_folder, filename)

# -------------------------
# Users CRUD
# -------------------------
@app.route('/api/users', methods=['GET'])
@require_token(min_role=None)
def api_users_list():
    try:
        conn = get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT id, nome, tipo, email FROM usuarios ORDER BY id")
        rows = cur.fetchall()
        cur.close(); conn.close()
        return jsonify(rows)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users', methods=['POST'])
@require_token(min_role='admin')
def api_users_create():
    data = request.json or {}
    nome = data.get('nome'); tipo = data.get('tipo'); email = data.get('email')
    if not nome or not tipo:
        return jsonify({'error':'nome e tipo obrigatórios'}), 400
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("INSERT INTO usuarios(nome,tipo,email) VALUES (%s,%s,%s) RETURNING id;", (nome, tipo, email))
        new_id = cur.fetchone()[0]
        conn.commit(); cur.close(); conn.close()
        return jsonify({'id': new_id}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/<int:user_id>', methods=['PUT'])
@require_token(min_role='admin')
def api_users_update(user_id):
    data = request.json or {}
    nome = data.get('nome'); tipo = data.get('tipo'); email = data.get('email')
    try:
        conn = get_conn(); cur = conn.cursor()
        cur.execute("UPDATE usuarios SET nome=%s, tipo=%s, email=%s WHERE id=%s;", (nome, tipo, email, user_id))
        conn.commit(); cur.close(); conn.close()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@require_token(min_role='admin')
def api_users_delete(user_id):
    try:
        conn = get_conn(); cur = conn.cursor()
        cur.execute("DELETE FROM usuarios WHERE id=%s;", (user_id,))
        conn.commit(); cur.close(); conn.close()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# -------------------------
# Books CRUD
# -------------------------
@app.route('/api/books', methods=['GET'])
@require_token(min_role=None)
def api_books_list():
    try:
        conn = get_conn(); cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT id, titulo, autor, isbn, quantidade FROM livros ORDER BY id;")
        rows = cur.fetchall(); cur.close(); conn.close()
        return jsonify(rows)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/books', methods=['POST'])
@require_token(min_role='admin')
def api_books_create():
    data = request.json or {}
    titulo = data.get('titulo'); autor = data.get('autor'); isbn = data.get('isbn'); quantidade = data.get('quantidade') or 1
    if not titulo:
        return jsonify({'error':'titulo obrigatório'}), 400
    try:
        conn = get_conn(); cur = conn.cursor()
        cur.execute("INSERT INTO livros(titulo,autor,isbn,quantidade) VALUES (%s,%s,%s,%s) RETURNING id;", (titulo, autor, isbn, int(quantidade)))
        new_id = cur.fetchone()[0]; conn.commit(); cur.close(); conn.close()
        return jsonify({'id': new_id}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/books/<int:book_id>', methods=['PUT'])
@require_token(min_role='admin')
def api_books_update(book_id):
    data = request.json or {}
    titulo = data.get('titulo'); autor = data.get('autor'); isbn = data.get('isbn'); quantidade = data.get('quantidade')
    try:
        conn = get_conn(); cur = conn.cursor()
        cur.execute("UPDATE livros SET titulo=%s, autor=%s, isbn=%s, quantidade=%s WHERE id=%s;", (titulo, autor, isbn, quantidade, book_id))
        conn.commit(); cur.close(); conn.close()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/books/<int:book_id>', methods=['DELETE'])
@require_token(min_role='admin')
def api_books_delete(book_id):
    try:
        conn = get_conn(); cur = conn.cursor()
        cur.execute("DELETE FROM livros WHERE id=%s;", (book_id,))
        conn.commit(); cur.close(); conn.close()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# -------------------------
# Empréstimos (usar view e tabela)
# -------------------------
@app.route('/api/emprestimos', methods=['GET'])
@require_token(min_role=None)
def api_emprestimos_list():
    # optional query param ?status=andamento|devolvido
    st = request.args.get('status')
    try:
        conn = get_conn(); cur = conn.cursor(cursor_factory=RealDictCursor)
        if st == 'andamento':
            cur.execute("SELECT * FROM vw_emprestimos_overview WHERE status_devolvido = false ORDER BY emprestimo_id;")
        elif st == 'devolvido':
            cur.execute("SELECT * FROM vw_emprestimos_overview WHERE status_devolvido = true ORDER BY emprestimo_id;")
        else:
            cur.execute("SELECT * FROM vw_emprestimos_overview ORDER BY emprestimo_id;")
        rows = cur.fetchall(); cur.close(); conn.close()
        return jsonify(rows)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/emprestimos', methods=['POST'])
@require_token(min_role='admin')
def api_emprestimos_create():
    data = request.json or {}
    usuario_id = data.get('usuario_id'); livro_id = data.get('livro_id')
    if not usuario_id or not livro_id:
        return jsonify({'error':'usuario_id e livro_id obrigatórios'}), 400
    try:
        conn = get_conn(); cur = conn.cursor()
        cur.execute("INSERT INTO emprestimos(usuario_id, livro_id) VALUES (%s,%s) RETURNING id;", (usuario_id, livro_id))
        new_id = cur.fetchone()[0]; conn.commit(); cur.close(); conn.close()
        return jsonify({'id': new_id}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/emprestimos/<int:emp_id>', methods=['PUT'])
@require_token(min_role='admin')
def api_emprestimos_update(emp_id):
    data = request.json or {}
    usuario_id = data.get('usuario_id'); livro_id = data.get('livro_id'); data_devolucao = data.get('data_devolucao')
    try:
        conn = get_conn(); cur = conn.cursor()
        cur.execute("UPDATE emprestimos SET usuario_id=%s, livro_id=%s, data_devolucao=%s WHERE id=%s;", (usuario_id, livro_id, data_devolucao, emp_id))
        conn.commit(); cur.close(); conn.close()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/emprestimos/<int:emp_id>', methods=['DELETE'])
@require_token(min_role='admin')
def api_emprestimos_delete(emp_id):
    try:
        conn = get_conn(); cur = conn.cursor()
        cur.execute("DELETE FROM emprestimos WHERE id=%s;", (emp_id,))
        conn.commit(); cur.close(); conn.close()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/emprestimos/<int:emp_id>/devolver', methods=['POST'])
@require_token(min_role='admin')
def api_emprestimos_devolver(emp_id):
    from datetime import date
    hoje = date.today().isoformat()
    try:
        conn = get_conn(); cur = conn.cursor()
        cur.execute("UPDATE emprestimos SET devolvido = TRUE, data_devolucao = %s WHERE id=%s;", (hoje, emp_id))
        conn.commit(); cur.close(); conn.close()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# -------------------------
# Logs
# -------------------------
@app.route('/api/logs', methods=['GET'])
@require_token(min_role=None)
def api_logs():
    try:
        conn = get_conn(); cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM log_emprestimos ORDER BY id DESC LIMIT 500;")
        rows = cur.fetchall(); cur.close(); conn.close()
        return jsonify(rows)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# -------------------------
# Health
# -------------------------
@app.route('/api/health', methods=['GET'])
def api_health():
    return jsonify({'ok': True})

# -------------------------
# Run
# -------------------------
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    print(f"backend_full rodando em http://127.0.0.1:{port}/")
    app.run(debug=True, port=port)
