# ============================================================
# interface/dashboard.py — Dashboard Visual do Anotaí
# ============================================================
import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DATABASE_PATH, CESTOS_PF

# ============================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================
st.set_page_config(
    page_title="Anotaí — Dashboard",
    page_icon="🧺",
    layout="wide"
)

# Reduz espaço do topo
st.markdown("<style>div.block-container{padding-top:1rem;}</style>", unsafe_allow_html=True)

# ============================================================
# FUNÇÕES DE DADOS
# ============================================================

def get_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def buscar_usuarios():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM usuarios")
    usuarios = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return usuarios


def buscar_saldo_cestos(usuario_id: int) -> dict:
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


def buscar_lancamentos(usuario_id: int) -> list:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM lancamentos
        WHERE usuario_id = ?
        ORDER BY criado_em DESC
        LIMIT 50
    """, (usuario_id,))
    resultados = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return resultados


def buscar_totais_mes(usuario_id: int) -> dict:
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


# ============================================================
# INTERFACE
# ============================================================

st.title("🧺 Anotaí — Dashboard Financeiro")
st.markdown("---")

# Verifica se o banco existe
if not os.path.exists(DATABASE_PATH):
    st.error("❌ Banco de dados não encontrado. Rode o bot primeiro!")
    st.stop()

# Busca usuários
usuarios = buscar_usuarios()

if not usuarios:
    st.warning("Nenhum usuário encontrado. Mande /start no bot primeiro!")
    st.stop()

# Seletor de usuário
nomes = {u["nome"]: u["id"] for u in usuarios}
usuario_selecionado = st.selectbox("👤 Usuário", list(nomes.keys()))
usuario_id = nomes[usuario_selecionado]

# Mês em português
meses = {
    "January": "Janeiro", "February": "Fevereiro", "March": "Março",
    "April": "Abril", "May": "Maio", "June": "Junho",
    "July": "Julho", "August": "Agosto", "September": "Setembro",
    "October": "Outubro", "November": "Novembro", "December": "Dezembro"
}
mes_en = datetime.now().strftime("%B")
mes_atual = f"{meses[mes_en]}/{datetime.now().strftime('%Y')}"

st.subheader(f"📅 {mes_atual}")

# ============================================================
# CARDS DE RESUMO
# ============================================================
totais = buscar_totais_mes(usuario_id)
total_entrada = totais.get("entrada", 0)
total_saida = totais.get("saida", 0)
saldo_mes = total_entrada - total_saida

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        label="💚 Total Entradas",
        value=f"R$ {total_entrada:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    )

with col2:
    st.metric(
        label="🔴 Total Saídas",
        value=f"R$ {total_saida:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    )

with col3:
    st.metric(
        label="💰 Saldo do Mês",
        value=f"R$ {saldo_mes:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    )

st.markdown("---")

# ============================================================
# CESTOS
# ============================================================
st.subheader("🧺 Status dos Cestos")

saldos = buscar_saldo_cestos(usuario_id)

if not saldos:
    st.info("Nenhum cesto movimentado ainda. Registre uma entrada no bot!")
else:
    for nome, config in CESTOS_PF.items():
        emoji = config["emoji"]
        saldo = saldos.get(nome, 0)

        col_nome, col_barra, col_valor = st.columns([2, 4, 2])

        with col_nome:
            st.write(f"{emoji} **{nome}**")

        with col_barra:
            if total_entrada > 0:
                orcamento = total_entrada * (config["percentual"] / 100)
                percentual_usado = min((1 - saldo/orcamento) * 100, 100) if orcamento > 0 else 0
                percentual_usado = max(percentual_usado, 0)
                st.progress(percentual_usado / 100)
            else:
                st.progress(0)

        with col_valor:
            saldo_fmt = f"R$ {saldo:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            cor = "🟢" if saldo > 0 else "🔴"
            st.write(f"{cor} {saldo_fmt}")

st.markdown("---")

# ============================================================
# ÚLTIMOS LANÇAMENTOS
# ============================================================
st.subheader("📋 Últimos Lançamentos")

lancamentos = buscar_lancamentos(usuario_id)

if not lancamentos:
    st.info("Nenhum lançamento registrado ainda.")
else:
    df = pd.DataFrame(lancamentos)
    df = df[["data", "tipo", "valor", "categoria", "cesto", "conta", "descricao"]]
    df.columns = ["Data", "Tipo", "Valor (R$)", "Categoria", "Cesto", "Conta", "Descrição"]
    df["Tipo"] = df["Tipo"].map({"entrada": "💚 Entrada", "saida": "🔴 Saída"})
    st.dataframe(df, use_container_width=True, hide_index=True)

st.markdown("---")
st.caption("Anotaí — Sistema Inteligente de Destinação Financeira")