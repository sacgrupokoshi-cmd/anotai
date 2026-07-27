# ============================================================
# core/ia_classificador.py — Cérebro do Anotaí
# ============================================================
import anthropic
import json
import re
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, CATEGORIAS, CESTOS_PF

cliente = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

PROMPT_SISTEMA = """
Você é o classificador financeiro do Anotaí, sistema brasileiro de gestão financeira.

Sua função é analisar mensagens de lançamento financeiro e retornar JSON estruturado.

REGRAS:
1. Responda APENAS com JSON válido, sem texto adicional.
2. Valores em formato brasileiro: 47,80 = 47.80
3. Retorne valor sempre como número decimal.

CATEGORIAS DISPONÍVEIS:
Mercado, Restaurante, Transporte, Combustível, Saúde, Farmácia,
Educação, Lazer, Roupas, Tecnologia, Assinatura, Moradia,
Conta de Luz, Conta de Água, Internet, Telefone, Investimento,
Doação, Salário, Freelance, Renda Extra, Outro

CESTOS DISPONÍVEIS:
Pagar a Si Mesmo, Despesas Essenciais, Enriquecer,
Poupar para Sonhos, Generosidade, Torrar sem Dó

REGRAS DOS CESTOS:
- Mercado, contas, moradia, saúde → Despesas Essenciais
- Investimentos → Enriquecer
- Lazer, restaurante → Torrar sem Dó
- Doações, presentes → Generosidade
- Salário, receitas → entrada (distribui nos cestos)

FORMATO DE RESPOSTA:
{
  "tipo": "saida" ou "entrada",
  "valor": 47.80,
  "categoria": "Mercado",
  "cesto": "Despesas Essenciais",
  "conta": "Nubank débito 0119",
  "descricao": "texto original",
  "confianca": "alta" ou "media" ou "baixa"
}
"""


def classificar_lancamento(texto: str) -> dict:
    """Envia o texto para o Claude e retorna os dados classificados."""
    try:
        resposta = cliente.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=500,
            system=PROMPT_SISTEMA,
            messages=[
                {"role": "user", "content": f"Classifique: {texto}"}
            ]
        )

        texto_resposta = resposta.content[0].text.strip()

        # Remove marcações markdown se o Claude adicionar
        texto_resposta = re.sub(r'```json\s*', '', texto_resposta)
        texto_resposta = re.sub(r'```\s*', '', texto_resposta)
        texto_resposta = texto_resposta.strip()

        dados = json.loads(texto_resposta)

        if not dados.get("descricao"):
            dados["descricao"] = texto

        return dados

    except Exception as e:
        print(f"❌ Erro na classificação: {e}")
        return None


def formatar_resposta(dados: dict) -> str:
    """Formata os dados numa mensagem bonita para o Telegram."""
    if not dados:
        return "❌ Não consegui entender esse lançamento. Tente descrever diferente."

    emoji_tipo = "💚" if dados.get("tipo") == "entrada" else "🔴"
    sinal = "+" if dados.get("tipo") == "entrada" else "-"

    valor = dados.get("valor", 0)
    valor_fmt = f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    linhas = [
        f"✅ *Registrado!*",
        f"",
        f"{emoji_tipo} *Tipo:* {'Entrada' if dados.get('tipo') == 'entrada' else 'Saída'}",
        f"💵 *Valor:* {sinal}{valor_fmt}",
        f"🏷️ *Categoria:* {dados.get('categoria', 'Não identificada')}",
    ]

    if dados.get("conta"):
        linhas.append(f"🏦 *Conta:* {dados.get('conta')}")

    if dados.get("cesto"):
        linhas.append(f"🧺 *Cesto:* {dados.get('cesto')}")

    return "\n".join(linhas)