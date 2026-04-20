"""
app/core/funcionarios.py
=========================
Gerencia a lista de compradores/funcionários do sistema.
Persistido em assets/funcionarios.json.
Funções:
    listar()        → lista de nomes
    adicionar(nome) → True se adicionou, False se já existe
    remover(nome)   → True se removeu
"""

import os, json

_ASSETS = os.path.normpath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'assets')
)
_JSON = os.path.join(_ASSETS, 'funcionarios.json')

# Funcionários padrão — criados na primeira execução
_PADRAO = ["IURY", "THAMYRES"]


def _carregar() -> list:
    try:
        with open(_JSON, encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                return [str(n).strip().upper() for n in data if str(n).strip()]
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"[funcionarios] erro ao carregar: {e}")
    return list(_PADRAO)


def _salvar(lista: list):
    os.makedirs(_ASSETS, exist_ok=True)
    with open(_JSON, 'w', encoding='utf-8') as f:
        json.dump(lista, f, ensure_ascii=False, indent=2)


def listar() -> list:
    """Retorna lista de nomes em maiúsculas, ordenada."""
    func = _carregar()
    return sorted(func)


def adicionar(nome: str) -> bool:
    """Adiciona funcionário. Retorna False se já existir."""
    nome = nome.strip().upper()
    if not nome:
        return False
    func = _carregar()
    if nome in func:
        return False
    func.append(nome)
    _salvar(sorted(func))
    return True


def remover(nome: str) -> bool:
    """Remove funcionário. Retorna False se não existir."""
    nome = nome.strip().upper()
    func = _carregar()
    if nome not in func:
        return False
    func.remove(nome)
    _salvar(func)
    return True
