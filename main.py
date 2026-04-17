"""
Sistema de Cotação e Pedidos de Compra - Brasul Construtora
Execute: python main.py

COMO ESTE ARQUIVO FUNCIONA (para estudantes):
    Este é o ponto de entrada do programa. Quando você roda 'python main.py'
    ou clica no iniciar.bat, Python começa aqui.

    O fluxo é:
        1. init_db()     → cria/verifica o banco de dados SQLite
        2. QApplication  → inicializa o framework de interface gráfica (PySide6)
        3. MainWindow()  → cria a janela principal com as abas
        4. app.exec()    → entra no loop de eventos (mantém a janela aberta)

    O 'if __name__ == "__main__"' garante que main() só roda quando o arquivo
    é executado diretamente — não quando é importado por outro módulo.
"""

import sys
import os

# Adiciona a pasta raiz do projeto ao PATH do Python,
# para que imports como 'from app.data.database import ...' funcionem
# independente de onde o script é executado.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.data.database import init_db
from app.ui.main_window import MainWindow

# ── CSS global aplicado em toda a aplicação ────────────────────────────────────
# O tema Fusion do Qt pode herdar cores do sistema operacional e deixar
# texto branco em fundo branco (invisível). Este CSS força texto preto
# em todos os campos, independente do tema do Windows.
GLOBAL_CSS = """
    QWidget                { color: #111827; }
    QLineEdit              { color: #111827; background: #FFFFFF;
                             selection-background-color: #BFDBFE;
                             selection-color: #1E3A5F; }
    QLineEdit:read-only    { color: #6B7280; background: #F3F4F6; }
    QComboBox              { color: #111827; background: #FFFFFF; }
    QSpinBox               { color: #111827; background: #FFFFFF; }
    QDoubleSpinBox         { color: #111827; background: #FFFFFF; }
    QTextEdit              { color: #111827; background: #FFFFFF; }
    QLabel                 { color: #111827; background: transparent; }
    QGroupBox              { color: #111827; }
    QTableWidget           { color: #111827; }
    QTableWidget::item     { color: #111827; }
    QHeaderView::section   { color: #FFFFFF; }
    QMessageBox QLabel     { color: #111827; }
    QComboBox QAbstractItemView {
        color: #111827; background: #FFFFFF;
        selection-background-color: #DBEAFE;
        selection-color: #1E3A5F;
    }
"""


def main():
    # Passo 1: inicializa o banco de dados (cria as tabelas se não existirem)
    init_db()

    try:
        from PySide6.QtWidgets import QApplication

        # Passo 2: cria a aplicação Qt (obrigatório antes de qualquer widget)
        app = QApplication(sys.argv)
        app.setApplicationName("Sistema de Cotação - Brasul")
        app.setOrganizationName("Brasul Construtora")
        app.setStyle("Fusion")          # tema visual limpo e profissional
        app.setStyleSheet(GLOBAL_CSS)   # aplica o CSS global

        # Passo 3: cria e exibe a janela principal
        window = MainWindow()
        window.show()

        # Passo 4: entra no loop de eventos — mantém a janela aberta até fechar
        sys.exit(app.exec())

    except ImportError:
        # Fallback caso PySide6 não esteja instalado: roda demo em modo texto
        print("PySide6 não instalado. Rodando demo CLI...")
        _demo_cli()


def _demo_cli():
    """
    Modo de demonstração sem interface gráfica.
    Útil para testar a geração de PDF via linha de comando.
    """
    from app.core.services.pedido_service import PedidoService
    from app.core.dto.pedido_dto import PedidoDTO, ItemPedidoDTO

    dto = PedidoDTO(
        numero="2549", data_pedido="09/04/2026",
        empresa_faturadora="BRASUL", comprador="IURY",
        obra="MARIA RITA ARAÚJO", escola="E.E Maria Rita Araújo",
        endereco_entrega="R. Ernesto Bergamasco, 665",
        bairro_entrega="Vila São Pedro", cep_entrega="13183-080",
        cidade_entrega="Hortolândia", uf_entrega="SP",
        fornecedor_nome="AZEFER MATERIAIS",
        fornecedor_razao="AZEFER MATERIAIS PARA CONSTRUÇÃO EIRELI",
        fornecedor_email="vendas@azevedoconstrucao.com.br",
        fornecedor_vendedor="Cleber", fornecedor_telefone="19 98745-3060",
        prazo_entrega=5, condicao_pagamento="14", forma_pagamento="BOLETO",
        itens=[
            ItemPedidoDTO("AREIA GROSSA MD MT", 2.0, "M3", 153.09),
            ItemPedidoDTO("CIMENTO 50KG VOTORAN CPII", 10.0, "SACO", 39.90),
            ItemPedidoDTO("TABUA PINUS BRUTA 20CM X 3.00MT", 10.0, "UNID.", 15.50),
            ItemPedidoDTO("PREGO GERDAU 17X21 COM CABECA", 1.0, "KG", 15.50),
            ItemPedidoDTO("TABUA PINUS BRUTA 05CM X 3.00MT", 10.0, "UNID.", 4.24),
            ItemPedidoDTO("MEIO METRO PEDRA I MT", 0.5, "M3", 130.80),
        ]
    )
    service = PedidoService()
    print("PDF gerado em:", service.gerar_pdf(dto))


if __name__ == "__main__":
    main()
