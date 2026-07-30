# ============================================================
# interface/dashboard.py — Dashboard Visual do Anotaí
# ============================================================
import streamlit as st
import psycopg2
import psycopg2.extras
import pandas as pd
from datetime import datetime
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import CESTOS_PF

DATABASE_URL = os.getenv("DATABASE_URL")

st.set_page_config(
    page_title="Anotaí — Dashboard",
    page_icon="🧺",
    layout="wide"
)

st.markdown("<style>div.block-container{padding-top:1rem;}</style>", unsafe_allow_html=True)


def get_connection():
    return psycopg2.connect(DATABASE_URL)


def buscar_usuarios():
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("SELECT * FROM usuarios")
    usuarios = [dict(row) for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return usuarios


def buscar_saldo_cestos(usuario_id):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    mes_atual = datetime.now().strftime("%Y-%m")
    cursor.execute("""
        SELECT nome_cesto, saldo FROM cestos_saldo
        WHERE usuario_id = %s AND mes = %s
    """, (usuario_id, mes_atual))
    resultados = {row["nome_cesto"]: row["saldo"] for row in cursor.fetchall()}
    cursor.close()
    conn.close()
    return resultados


def buscar_lancamentos(usuario_id):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("""
        SELECT * FROM lancamentos
        WHERE usuario_id = %s
        ORDER BY criado_em DESC LIMIT 50
    """, (usuario_id,))
    resultados = [dict(row) for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return resultados


def buscar_totais_mes(usuario_id):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    mes_atual = datetime.now().strftime("%Y-%m")
    cursor.execute("""
        SELECT tipo, SUM(valor) as total FROM lancamentos
        WHERE usuario_id = %s AND TO_CHAR(data, 'YYYY-MM') = %s
        GROUP BY tipo
    """, (usuario_id, mes_atual))
    totais = {row["tipo"]: row["total"] for row in cursor.fetchall()}
    cursor.close()
    conn.close()
    return totais


def buscar_gastos_por_categoria(usuario_id):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    mes_atual = datetime.now().strftime("%Y-%m")
    cursor.execute("""
        SELECT categoria, SUM(valor) as total FROM lancamentos
        WHERE usuario_id = %s
        AND tipo = 'saida'
        AND TO_CHAR(data, 'YYYY-MM') = %s
        GROUP BY categoria
        ORDER BY total DESC
    """, (usuario_id, mes_atual))
    resultados = [dict(row) for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return resultados


# ============================================================
# INTERFACE
# ============================================================

st.title("🧺 Anotaí — Dashboard Financeiro")
st.markdown("---")

if not DATABASE_URL:
    st.error("❌ DATABASE_URL não configurada!")
    st.stop()

try:
    usuarios = buscar_usuarios()
except Exception as e:
    st.error(f"❌ Erro ao conectar ao banco: {e}")
    st.stop()

if not usuarios:
    st.warning("Nenhum usuário encontrado. Mande /start no bot primeiro!")
    st.stop()

nomes = {u["nome"]: u["id"] for u in usuarios}
usuario_selecionado = st.selectbox("👤 Usuário", list(nomes.keys()))
usuario_id = nomes[usuario_selecionado]

meses = {
    "01": "Janeiro", "02": "Fevereiro", "03": "Março",
    "04": "Abril", "05": "Maio", "06": "Junho",
    "07": "Julho", "08": "Agosto", "09": "Setembro",
    "10": "Outubro", "11": "Novembro", "12": "Dezembro"
}
mes_num = datetime.now().strftime("%m")
ano = datetime.now().strftime("%Y")
mes_atual = f"{meses[mes_num]}/{ano}"

st.subheader(f"📅 {mes_atual}")

# ============================================================
# CARDS DE RESUMO
# ============================================================
totais = buscar_totais_mes(usuario_id)
total_entrada = totais.get("entrada", 0) or 0
total_saida = totais.get("saida", 0) or 0
saldo_mes = total_entrada - total_saida

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("💚 Total Entradas", f"R$ {total_entrada:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
with col2:
    st.metric("🔴 Total Saídas", f"R$ {total_saida:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
with col3:
    st.metric("💰 Saldo do Mês", f"R$ {saldo_mes:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

st.markdown("---")

# ============================================================
# GRÁFICOS
# ============================================================
saldos = buscar_saldo_cestos(usuario_id)
gastos_categoria = buscar_gastos_por_categoria(usuario_id)

if saldos or gastos_categoria:
    col_graf1, col_graf2 = st.columns(2)

    # Gráfico de pizza — Distribuição dos Cestos
    with col_graf1:
        st.subheader("🧺 Distribuição dos Cestos")
        if saldos:
            nomes_cestos = []
            valores_cestos = []
            for nome, config in CESTOS_PF.items():
                if total_entrada > 0:
                    valor = total_entrada * (config["percentual"] / 100)
                    nomes_cestos.append(f"{config['emoji']} {nome}")
                    valores_cestos.append(valor)

            if valores_cestos:
                df_pizza = pd.DataFrame({
                    "Cesto": nomes_cestos,
                    "Valor": valores_cestos
                })
                st.bar_chart(df_pizza.set_index("Cesto"))
        else:
            st.info("Registre uma entrada para ver a distribuição.")

    # Gráfico de barras — Gastos por Categoria
    with col_graf2:
        st.subheader("📊 Gastos por Categoria")
        if gastos_categoria:
            df_cat = pd.DataFrame(gastos_categoria)
            df_cat.columns = ["Categoria", "Valor (R$)"]
            st.bar_chart(df_cat.set_index("Categoria"))
        else:
            st.info("Registre um gasto para ver as categorias.")

    st.markdown("---")

# ============================================================
# CESTOS COM BARRAS DE PROGRESSO
# ============================================================
st.subheader("🧺 Status dos Cestos")

if not saldos:
    st.info("Nenhum cesto movimentado ainda.")
else:
    for nome, config in CESTOS_PF.items():
        emoji = config["emoji"]
        saldo = saldos.get(nome, 0) or 0
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