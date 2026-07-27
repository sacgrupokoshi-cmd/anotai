# ============================================================
# config.py — Configurações Centrais do Anotaí
# ============================================================
import os
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# TOKENS E CHAVES
# ============================================================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# ============================================================
# BANCO DE DADOS
# ============================================================
DATABASE_PATH = os.path.join(os.path.dirname(__file__), "data", "anotai.db")

# ============================================================
# MODELO DE IA
# ============================================================
CLAUDE_MODEL = "claude-haiku-4-5"

# ============================================================
# CESTOS PADRÃO — PESSOA FÍSICA
# Edgard: para ajustar os percentuais, edite os números abaixo.
# A soma deve ser sempre 100%.
# ============================================================
CESTOS_PF = {
    "Pagar a Si Mesmo":    {"percentual": 10, "emoji": "🏆"},
    "Despesas Essenciais": {"percentual": 60, "emoji": "🏠"},
    "Enriquecer":          {"percentual": 10, "emoji": "📈"},
    "Poupar para Sonhos":  {"percentual": 10, "emoji": "✨"},
    "Generosidade":        {"percentual": 5,  "emoji": "💝"},
    "Torrar sem Dó":       {"percentual": 5,  "emoji": "🎉"},
}

# ============================================================
# CATEGORIAS DE GASTOS
# ============================================================
CATEGORIAS = [
    "Mercado", "Restaurante", "Transporte", "Combustível",
    "Saúde", "Farmácia", "Educação", "Lazer", "Roupas",
    "Tecnologia", "Assinatura", "Moradia", "Conta de Luz",
    "Conta de Água", "Internet", "Telefone", "Investimento",
    "Doação", "Salário", "Freelance", "Renda Extra", "Outro",
]