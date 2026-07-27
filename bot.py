# ============================================================
# bot.py — Bot do Telegram — Anotaí (Fase 4)
# ============================================================
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

from config import TELEGRAM_TOKEN, CESTOS_PF
from database import (
    criar_tabelas,
    get_ou_criar_usuario,
    salvar_lancamento,
    buscar_lancamentos,
    distribuir_nos_cestos,
    abater_do_cesto,
    buscar_saldo_cestos,
    buscar_totais_mes,
)
from core.ia_classificador import classificar_lancamento, formatar_resposta

logging.basicConfig(
    format="%(asctime)s — %(levelname)s — %(message)s",
    level=logging.INFO
)


def formatar_distribuicao(valor: float) -> str:
    """Mostra como o dinheiro foi distribuído nos cestos."""
    linhas = ["", "🧺 *Distribuído nos cestos:*", ""]
    for nome, config in CESTOS_PF.items():
        emoji = config["emoji"]
        percentual = config["percentual"]
        valor_cesto = round(valor * (percentual / 100), 2)
        valor_fmt = f"R$ {valor_cesto:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        linhas.append(f"{emoji} {nome} ({percentual}%) → {valor_fmt}")
    return "\n".join(linhas)


def formatar_cestos(saldos: dict) -> str:
    """Mostra o saldo atual de cada cesto."""
    linhas = ["🧺 *Seus Cestos — Mês Atual:*", ""]

    for nome, config in CESTOS_PF.items():
        emoji = config["emoji"]
        saldo = saldos.get(nome, 0)
        sinal = "+" if saldo >= 0 else ""
        saldo_fmt = f"R$ {saldo:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

        if saldo < 0:
            status = "🚨 Estourado!"
        elif saldo == 0:
            status = "⚪ Vazio"
        else:
            status = "✅"

        linhas.append(f"{emoji} *{nome}*")
        linhas.append(f"   Saldo: {sinal}{saldo_fmt} {status}")
        linhas.append("")

    return "\n".join(linhas)


async def comando_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Responde ao /start."""
    usuario_telegram = update.effective_user
    get_ou_criar_usuario(
        telegram_id=str(usuario_telegram.id),
        nome=usuario_telegram.first_name
    )

    nome = usuario_telegram.first_name or "amigo(a)"

    mensagem = f"""
👋 Olá, *{nome}*! Bem-vindo(a) ao *Anotaí*!

💡 Sou seu assistente de destinação financeira.

Em vez de só registrar o que você gastou, eu *dou destino ao seu dinheiro antes que ele desapareça*.

━━━━━━━━━━━━━━━━━━
🧺 *Como usar:*

Me manda o que aconteceu em linguagem natural:

_"Gastei 47,80 no mercado, Nubank débito"_
_"Recebi 3000 de salário"_
_"Paguei 89 na Netflix, crédito Nubank"_

━━━━━━━━━━━━━━━━━━
📋 *Comandos:*

/start — Esta mensagem
/cestos — Ver saldo dos seus cestos
/relatorio — Relatório completo do mês
/extrato — Últimos lançamentos
/ajuda — Como usar
    """.strip()

    await update.message.reply_text(mensagem, parse_mode="Markdown")


async def comando_ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Responde ao /ajuda."""
    mensagem = """
🆘 *Como usar o Anotaí*

━━━━━━━━━━━━━━━━━━
📝 *Exemplos de saída (gasto):*
- _"Gastei 47,80 no mercado"_
- _"Paguei 120 de luz"_
- _"50 reais no ifood, Nubank crédito"_

━━━━━━━━━━━━━━━━━━
💰 *Exemplos de entrada (receita):*
- _"Recebi 3000 de salário"_
- _"Entrou 500 de freela"_

━━━━━━━━━━━━━━━━━━
🧺 *Seus Cestos:*
🏆 Pagar a Si Mesmo · 10%
🏠 Despesas Essenciais · 60%
📈 Enriquecer · 10%
✨ Poupar para Sonhos · 10%
💝 Generosidade · 5%
🎉 Torrar sem Dó · 5%
    """.strip()

    await update.message.reply_text(mensagem, parse_mode="Markdown")


async def comando_cestos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra o saldo atual dos cestos."""
    usuario_telegram = update.effective_user
    usuario = get_ou_criar_usuario(str(usuario_telegram.id))
    saldos = buscar_saldo_cestos(usuario["id"])

    if not saldos:
        await update.message.reply_text(
            "🧺 Seus cestos ainda estão vazios!\n\n"
            "Registre uma entrada primeiro:\n"
            "_'Recebi 3000 de salário'_",
            parse_mode="Markdown"
        )
        return

    mensagem = formatar_cestos(saldos)
    await update.message.reply_text(mensagem, parse_mode="Markdown")


async def comando_relatorio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gera o relatório mensal completo."""
    usuario_telegram = update.effective_user
    usuario = get_ou_criar_usuario(str(usuario_telegram.id))

    totais = buscar_totais_mes(usuario["id"])
    saldos = buscar_saldo_cestos(usuario["id"])

    total_entrada = totais.get("entrada", 0)
    total_saida = totais.get("saida", 0)
    saldo_mes = total_entrada - total_saida

    meses = {
        "01": "Janeiro", "02": "Fevereiro", "03": "Março",
        "04": "Abril", "05": "Maio", "06": "Junho",
        "07": "Julho", "08": "Agosto", "09": "Setembro",
        "10": "Outubro", "11": "Novembro", "12": "Dezembro"
    }
    mes_num = datetime.now().strftime("%m")
    ano = datetime.now().strftime("%Y")
    mes_nome = meses[mes_num]

    entrada_fmt = f"R$ {total_entrada:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    saida_fmt = f"R$ {total_saida:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    saldo_fmt = f"R$ {saldo_mes:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    linhas = [
        f"📊 *Relatório — {mes_nome}/{ano}*",
        f"",
        f"💚 *Entradas:* {entrada_fmt}",
        f"🔴 *Saídas:* {saida_fmt}",
        f"💰 *Saldo do mês:* {saldo_fmt}",
        f"",
        f"━━━━━━━━━━━━━━━━━━",
        f"🧺 *Status dos Cestos:*",
        f"",
    ]

    for nome, config in CESTOS_PF.items():
        emoji = config["emoji"]
        percentual = config["percentual"]
        saldo = saldos.get(nome, 0)
        orcamento = total_entrada * (percentual / 100)
        gasto = orcamento - saldo
        gasto = max(gasto, 0)

        orcamento_fmt = f"R$ {orcamento:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        gasto_fmt = f"R$ {gasto:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        saldo_fmt2 = f"R$ {saldo:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

        if saldo < 0:
            status = "🚨 Estourado!"
        elif saldo == 0:
            status = "⚪ Zerado"
        elif gasto == 0:
            status = "💤 Sem gastos"
        else:
            percentual_usado = (gasto / orcamento * 100) if orcamento > 0 else 0
            if percentual_usado >= 80:
                status = "⚠️ Quase no limite"
            else:
                status = "✅ Ok"

        linhas.append(f"{emoji} *{nome}* ({percentual}%) — {status}")
        linhas.append(f"   📦 Orçamento: {orcamento_fmt}")
        linhas.append(f"   💸 Gasto: {gasto_fmt}")
        linhas.append(f"   💵 Disponível: {saldo_fmt2}")
        linhas.append(f"")

    await update.message.reply_text("\n".join(linhas), parse_mode="Markdown")


async def comando_extrato(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra os últimos lançamentos."""
    usuario_telegram = update.effective_user
    usuario = get_ou_criar_usuario(str(usuario_telegram.id))
    lancamentos = buscar_lancamentos(usuario["id"], limite=10)

    if not lancamentos:
        await update.message.reply_text(
            "📭 Você ainda não tem lançamentos.\n\n"
            "Me manda o que gastou ou recebeu hoje!"
        )
        return

    linhas = ["📋 *Últimos lançamentos:*", ""]

    for l in lancamentos:
        emoji = "💚" if l["tipo"] == "entrada" else "🔴"
        sinal = "+" if l["tipo"] == "entrada" else "-"
        valor = f"R$ {l['valor']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        linhas.append(f"{emoji} {sinal}{valor} · {l['categoria']} · {l['data']}")
        if l.get("cesto"):
            linhas.append(f"   🧺 {l['cesto']}")
        linhas.append("")

    await update.message.reply_text("\n".join(linhas), parse_mode="Markdown")


async def processar_mensagem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa qualquer mensagem de texto como lançamento."""
    texto = update.message.text
    usuario_telegram = update.effective_user

    if len(texto) < 3:
        return

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )

    usuario = get_ou_criar_usuario(
        telegram_id=str(usuario_telegram.id),
        nome=usuario_telegram.first_name
    )

    dados = classificar_lancamento(texto)

    if not dados:
        await update.message.reply_text(
            "🤔 Não consegui entender.\n\n"
            "Tente assim:\n"
            "• _'Gastei 50 no mercado'_\n"
            "• _'Recebi 2000 de salário'_",
            parse_mode="Markdown"
        )
        return

    salvar_lancamento(usuario["id"], dados)

    if dados.get("tipo") == "entrada":
        distribuir_nos_cestos(usuario["id"], dados.get("valor", 0))
        resposta = formatar_resposta(dados)
        distribuicao = formatar_distribuicao(dados.get("valor", 0))
        await update.message.reply_text(
            resposta + distribuicao,
            parse_mode="Markdown"
        )
    else:
        if dados.get("cesto"):
            abater_do_cesto(usuario["id"], dados.get("cesto"), dados.get("valor", 0))
        resposta = formatar_resposta(dados)
        await update.message.reply_text(resposta, parse_mode="Markdown")


def main():
    """Inicia o bot."""
    print("🗄️  Inicializando banco de dados...")
    criar_tabelas()

    if not TELEGRAM_TOKEN:
        print("❌ TELEGRAM_TOKEN não configurado no arquivo .env!")
        return

    print("🤖 Iniciando Anotaí...")

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", comando_start))
    app.add_handler(CommandHandler("ajuda", comando_ajuda))
    app.add_handler(CommandHandler("cestos", comando_cestos))
    app.add_handler(CommandHandler("relatorio", comando_relatorio))
    app.add_handler(CommandHandler("extrato", comando_extrato))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, processar_mensagem))

    print("✅ Bot rodando! Pressione Ctrl+C para parar.\n")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()