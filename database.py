# ============================================================
# database.py — Banco de Dados do Anotaí
# ============================================================
import sqlite3
import os
from datetime import datetime
from config import DATABASE_PATH, CESTOS_PF


def get_connection():
    """Abre a conexão com o banco SQLite."""
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def criar_tabelas():
    """Cria todas as tabelas do banco se não existirem."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id TEXT UNIQUE NOT NULL,
            nome TEXT,
            tipo_perfil TEXT DEFAULT 'PF',
            criado_em TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lancamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            tipo TEXT NOT NULL,
            valor REAL NOT NULL,
            categoria TEXT,
            cesto TEXT,
            conta TEXT,
            descricao TEXT,
            data TEXT DEFAULT CURRENT_DATE,
            hora TEXT DEFAULT CURRENT_TIME,
            criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        )
    """)

    # NOVO — tabela que guarda o saldo atual de cada cesto
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cestos_saldo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            nome_cesto TEXT NOT NULL,
            saldo REAL DEFAULT 0,
            mes TEXT NOT NULL,
            UNIQUE(usuario_id, nome_cesto, mes),
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        )
    """)

    conn.commit()
    conn.close()
    print("✅ Banco de dados pronto!")


def get_ou_criar_usuario(telegram_id: str, nome: str = None) -> dict:
    """Busca o usuário ou cria se não existir."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM usuarios WHERE telegram_id = ?", (str(telegram_id),))
    usuario = cursor.fetchone()

    if not usuario:
        cursor.execute(
            "INSERT INTO usuarios (telegram_id, nome) VALUES (?, ?)",
            (str(telegram_id), nome)
        )
        conn.commit()
        cursor.execute("SELECT * FROM usuarios WHERE telegram_id = ?", (str(telegram_id),))
        usuario = cursor.fetchone()
        print(f"👤 Novo usuário: {nome}")

    conn.close()
    return dict(usuario)


def salvar_lancamento(usuario_id: int, dados: dict) -> int:
    """Salva um lançamento no banco e retorna o ID criado."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO lancamentos
            (usuario_id, tipo, valor, categoria, cesto, conta, descricao)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        usuario_id,
        dados.get("tipo", "saida"),
        dados.get("valor", 0),
        dados.get("categoria", "Outro"),
        dados.get("cesto", ""),
        dados.get("conta", ""),
        dados.get("descricao", ""),
    ))

    lancamento_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return lancamento_id


def buscar_lancamentos(usuario_id: int, limite: int = 10) -> list:
    """Busca os últimos lançamentos do usuário."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM lancamentos
        WHERE usuario_id = ?
        ORDER BY criado_em DESC
        LIMIT ?
    """, (usuario_id, limite))

    resultados = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return resultados


def distribuir_nos_cestos(usuario_id: int, valor_entrada: float):
    """
    Quando entra dinheiro, distribui automaticamente nos cestos
    conforme os percentuais configurados.
    """
    conn = get_connection()
    cursor = conn.cursor()
    mes_atual = datetime.now().strftime("%Y-%m")

    for nome_cesto, config in CESTOS_PF.items():
        valor_cesto = round(valor_entrada * (config["percentual"] / 100), 2)

        # Atualiza o saldo do cesto — se não existir, cria com o valor
        cursor.execute("""
            INSERT INTO cestos_saldo (usuario_id, nome_cesto, saldo, mes)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(usuario_id, nome_cesto, mes)
            DO UPDATE SET saldo = saldo + ?
        """, (usuario_id, nome_cesto, valor_cesto, mes_atual, valor_cesto))

    conn.commit()
    conn.close()


def abater_do_cesto(usuario_id: int, nome_cesto: str, valor: float):
    """
    Quando o usuário gasta, abate o valor do cesto correspondente.
    """
    conn = get_connection()
    cursor = conn.cursor()
    mes_atual = datetime.now().strftime("%Y-%m")

    cursor.execute("""
        INSERT INTO cestos_saldo (usuario_id, nome_cesto, saldo, mes)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(usuario_id, nome_cesto, mes)
        DO UPDATE SET saldo = saldo - ?
    """, (usuario_id, nome_cesto, -valor, mes_atual, valor))

    conn.commit()
    conn.close()


def buscar_saldo_cestos(usuario_id: int) -> dict:
    """
    Retorna o saldo atual de todos os cestos do mês.
    """
    conn = get_connection()
    cursor = conn.cursor()
    mes_atual = datetime.now().strftime("%Y-%m")

    cursor.execute("""
        SELECT nome_cesto, saldo
        FROM cestos_saldo
        WHERE usuario_id = ? AND mes = ?
    """, (usuario_id, mes_atual))

    resultados = {row["nome_cesto"]: row["saldo"] for row in cursor.fetchall()}
    conn.close()
    return resultados
def buscar_totais_mes(usuario_id: int) -> dict:
    """Retorna o total de entradas e saídas do mês atual."""
    conn = get_connection()
    cursor = conn.cursor()
    mes_atual = datetime.now().strftime("%Y-%m")

    cursor.execute("""
        SELECT tipo, SUM(valor) as total
        FROM lancamentos
        WHERE usuario_id = ?
        AND strftime('%Y-%m', data) = ?
        GROUP BY tipo
    """, (usuario_id, mes_atual))

    totais = {row["tipo"]: row["total"] for row in cursor.fetchall()}
    conn.close()
    return totais