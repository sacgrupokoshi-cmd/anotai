# ============================================================
# database.py — Banco de Dados do Anotaí (PostgreSQL)
# ============================================================
import os
import psycopg2
import psycopg2.extras
from datetime import datetime
from config import CESTOS_PF

DATABASE_URL = os.getenv("DATABASE_URL")


def get_connection():
    """Abre a conexão com o banco PostgreSQL."""
    conn = psycopg2.connect(DATABASE_URL)
    return conn


def criar_tabelas():
    """Cria todas as tabelas do banco se não existirem."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id SERIAL PRIMARY KEY,
            telegram_id TEXT UNIQUE NOT NULL,
            nome TEXT,
            tipo_perfil TEXT DEFAULT 'PF',
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lancamentos (
            id SERIAL PRIMARY KEY,
            usuario_id INTEGER NOT NULL,
            tipo TEXT NOT NULL,
            valor REAL NOT NULL,
            categoria TEXT,
            cesto TEXT,
            conta TEXT,
            descricao TEXT,
            data DATE DEFAULT CURRENT_DATE,
            hora TIME DEFAULT CURRENT_TIME,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cestos_saldo (
            id SERIAL PRIMARY KEY,
            usuario_id INTEGER NOT NULL,
            nome_cesto TEXT NOT NULL,
            saldo REAL DEFAULT 0,
            mes TEXT NOT NULL,
            UNIQUE(usuario_id, nome_cesto, mes),
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        )
    """)

    conn.commit()
    cursor.close()
    conn.close()
    print("✅ Banco de dados pronto!")


def get_ou_criar_usuario(telegram_id: str, nome: str = None) -> dict:
    """Busca o usuário ou cria se não existir."""
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cursor.execute("SELECT * FROM usuarios WHERE telegram_id = %s", (str(telegram_id),))
    usuario = cursor.fetchone()

    if not usuario:
        cursor.execute(
            "INSERT INTO usuarios (telegram_id, nome) VALUES (%s, %s) RETURNING *",
            (str(telegram_id), nome)
        )
        usuario = cursor.fetchone()
        conn.commit()
        print(f"👤 Novo usuário: {nome}")

    cursor.close()
    conn.close()
    return dict(usuario)


def salvar_lancamento(usuario_id: int, dados: dict) -> int:
    """Salva um lançamento no banco e retorna o ID criado."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO lancamentos
            (usuario_id, tipo, valor, categoria, cesto, conta, descricao)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (
        usuario_id,
        dados.get("tipo", "saida"),
        dados.get("valor", 0),
        dados.get("categoria", "Outro"),
        dados.get("cesto", ""),
        dados.get("conta", ""),
        dados.get("descricao", ""),
    ))

    lancamento_id = cursor.fetchone()[0]
    conn.commit()
    cursor.close()
    conn.close()
    return lancamento_id


def buscar_lancamentos(usuario_id: int, limite: int = 10) -> list:
    """Busca os últimos lançamentos do usuário."""
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cursor.execute("""
        SELECT * FROM lancamentos
        WHERE usuario_id = %s
        ORDER BY criado_em DESC
        LIMIT %s
    """, (usuario_id, limite))

    resultados = [dict(row) for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return resultados


def distribuir_nos_cestos(usuario_id: int, valor_entrada: float):
    """Distribui automaticamente nos cestos quando entra dinheiro."""
    conn = get_connection()
    cursor = conn.cursor()
    mes_atual = datetime.now().strftime("%Y-%m")

    for nome_cesto, config in CESTOS_PF.items():
        valor_cesto = round(valor_entrada * (config["percentual"] / 100), 2)

        cursor.execute("""
            INSERT INTO cestos_saldo (usuario_id, nome_cesto, saldo, mes)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (usuario_id, nome_cesto, mes)
            DO UPDATE SET saldo = cestos_saldo.saldo + %s
        """, (usuario_id, nome_cesto, valor_cesto, mes_atual, valor_cesto))

    conn.commit()
    cursor.close()
    conn.close()


def abater_do_cesto(usuario_id: int, nome_cesto: str, valor: float):
    """Abate o valor do cesto quando o usuário gasta."""
    conn = get_connection()
    cursor = conn.cursor()
    mes_atual = datetime.now().strftime("%Y-%m")

    cursor.execute("""
        INSERT INTO cestos_saldo (usuario_id, nome_cesto, saldo, mes)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (usuario_id, nome_cesto, mes)
        DO UPDATE SET saldo = cestos_saldo.saldo - %s
    """, (usuario_id, nome_cesto, -valor, mes_atual, valor))

    conn.commit()
    cursor.close()
    conn.close()


def buscar_saldo_cestos(usuario_id: int) -> dict:
    """Retorna o saldo atual de todos os cestos do mês."""
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    mes_atual = datetime.now().strftime("%Y-%m")

    cursor.execute("""
        SELECT nome_cesto, saldo
        FROM cestos_saldo
        WHERE usuario_id = %s AND mes = %s
    """, (usuario_id, mes_atual))

    resultados = {row["nome_cesto"]: row["saldo"] for row in cursor.fetchall()}
    cursor.close()
    conn.close()
    return resultados


def buscar_totais_mes(usuario_id: int) -> dict:
    """Retorna o total de entradas e saídas do mês atual."""
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    mes_atual = datetime.now().strftime("%Y-%m")

    cursor.execute("""
        SELECT tipo, SUM(valor) as total
        FROM lancamentos
        WHERE usuario_id = %s
        AND TO_CHAR(data, 'YYYY-MM') = %s
        GROUP BY tipo
    """, (usuario_id, mes_atual))

    totais = {row["tipo"]: row["total"] for row in cursor.fetchall()}
    cursor.close()
    conn.close()
    return totais