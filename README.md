# Sistema de Cotação e Pedidos de Compra
### Brasul Construtora LTDA

---

## Instalação (Windows)

### 1. Instalar Python 3.11+
Baixe em: https://www.python.org/downloads/
> Marque a opção "Add Python to PATH" durante a instalação.

### 2. Abrir o terminal na pasta do projeto
Clique com botão direito na pasta `cotacao_system` → "Abrir no Terminal"

### 3. Instalar dependências
```bash
pip install -r requirements.txt
```

### 4. Executar o sistema
```bash
python main.py
```

---

## Estrutura de pastas

```
cotacao_system/
│
├── main.py                         ← Ponto de entrada — execute este
├── config.py                       ← Dados das empresas, caminhos, constantes
├── requirements.txt                ← Dependências Python
│
├── app/
│   ├── core/                       ← Regras de negócio (sem UI, sem banco)
│   │   ├── services/
│   │   │   ├── pedido_service.py   ← Valida e orquestra geração do pedido
│   │   │   ├── cotacao_service.py  ← (Sprint 3) Lógica de comparação
│   │   │   └── comparador_service.py ← (Sprint 3) Score de fornecedores
│   │   └── dto/
│   │       └── pedido_dto.py       ← Estrutura de dados do pedido
│   │
│   ├── data/                       ← Banco de dados
│   │   ├── database.py             ← Conexão SQLite + criação de tabelas
│   │   ├── models/                 ← (Sprint 2) Modelos SQLAlchemy
│   │   └── repositories/           ← (Sprint 2) Acesso a dados
│   │
│   ├── ui/                         ← Interface gráfica PySide6
│   │   ├── main_window.py          ← Janela principal + menu lateral
│   │   ├── widgets/
│   │   │   ├── pedido_widget.py    ← Tela de geração do pedido ✅ PRONTO
│   │   │   ├── obras_widget.py     ← (Sprint 2) Cadastro de obras
│   │   │   ├── cotacao_widget.py   ← (Sprint 3) Comparação de fornecedores
│   │   │   └── historico_widget.py ← (Sprint 2) Histórico de pedidos
│   │   └── dialogs/                ← Janelas de diálogo (futuro)
│   │
│   └── infrastructure/
│       ├── pdf_generator.py        ← Geração do PDF ✅ PRONTO
│       └── ocr_stub.py             ← (Sprint 4) Leitura de PDF do fornecedor
│
├── assets/
│   └── logos/                      ← Coloque os logos das empresas aqui (.png)
│                                     logo_brasul.png, logo_jb.png, etc.
│
├── pedidos_gerados/                ← PDFs gerados ficam aqui automaticamente
│
└── database/
    └── cotacao.db                  ← Banco de dados SQLite (criado automaticamente)
```

---

## Adicionar logos das empresas

Coloque os arquivos PNG na pasta `assets/logos/`:
- `logo_brasul.png`
- `logo_jb.png`
- `logo_bb.png`
- `logo_interiorana.png`
- `logo_interbras.png`

> Tamanho recomendado: 200×80 pixels, fundo transparente ou branco.

---

## Roadmap de sprints

| Sprint | Módulo | Status |
|--------|--------|--------|
| S1 | Gerador de PDF (5 empresas) | ✅ Pronto |
| S2 | Banco de dados + importação das planilhas | 🔜 Próximo |
| S3 | Módulo de cotação com comparação inteligente | 🔜 Em breve |
| S4 | OCR — leitura automática de PDF do fornecedor | 🔜 Futuro |

---

## Configurações em `config.py`

| Parâmetro | O que faz |
|-----------|-----------|
| `ULTIMO_PEDIDO_NUMERO` | Ajuste para o número do último pedido emitido |
| `COMPRADOR_PADRAO` | Nome que aparece no campo "Comprador" |
| `EMPRESAS_FATURADORAS` | Dados de cada empresa (endereço, cor, obs) |
| `PEDIDOS_DIR` | Pasta onde os PDFs são salvos |

---

## Dúvidas e suporte
Sistema desenvolvido por Claude (Anthropic) para Brasul Construtora.
