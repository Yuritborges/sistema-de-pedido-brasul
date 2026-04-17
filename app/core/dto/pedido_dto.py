"""
app/core/dto/pedido_dto.py
Data Transfer Objects — estruturas de dados que trafegam entre UI e serviços.
Sem lógica de negócio, sem acesso a banco. Só dados.
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class ItemPedidoDTO:
    """Representa uma linha do pedido de compra."""
    descricao:      str
    quantidade:     float
    unidade:        str
    valor_unitario: float

    @property
    def valor_total(self) -> float:
        return round(self.quantidade * self.valor_unitario, 2)

    def __post_init__(self):
        self.descricao  = self.descricao.upper().strip()
        self.unidade    = self.unidade.upper().strip()
        self.quantidade = float(self.quantidade)
        self.valor_unitario = float(self.valor_unitario)


@dataclass
class PedidoDTO:
    """Representa um pedido de compra completo, pronto para gerar PDF."""

    # Identificação
    numero:             str
    data_pedido:        str          # "09/04/2026"
    empresa_faturadora: str          # "BRASUL" | "JB" | "B&B" | "INTERIORANA" | "INTERBRAS"
    comprador:          str

    # Obra / destino
    obra:               str
    escola:             str
    endereco_entrega:   str
    bairro_entrega:     str
    cep_entrega:        str
    cidade_entrega:     str
    uf_entrega:         str
    contrato_obra:      str = "0"

    # Fornecedor
    fornecedor_nome:     str = ""
    fornecedor_razao:    str = ""
    fornecedor_email:    str = ""
    fornecedor_vendedor: str = ""
    fornecedor_telefone: str = ""

    # Condições comerciais
    prazo_entrega:         int  = 5
    condicao_pagamento:    str  = "14"
    forma_pagamento:       str  = "BOLETO"
    observacao_extra:      str  = ""
    desconto:              float = 0.0

    # Itens
    itens: List[ItemPedidoDTO] = field(default_factory=list)

    @property
    def subtotal(self) -> float:
        return round(sum(i.valor_total for i in self.itens), 2)

    @property
    def total(self) -> float:
        return round(self.subtotal - self.desconto, 2)

    @property
    def data_prevista_entrega(self) -> str:
        """Calcula data prevista somando prazo_entrega dias à data_pedido."""
        from datetime import datetime, timedelta
        try:
            dt = datetime.strptime(self.data_pedido, "%d/%m/%Y")
            dt_prev = dt + timedelta(days=self.prazo_entrega)
            return dt_prev.strftime("%d/%m/%y")
        except Exception:
            return ""

    @property
    def estimativa_vencimento(self) -> str:
        """Estimativa de vencimento baseada na condição de pagamento (primeiro prazo)."""
        from datetime import datetime, timedelta
        try:
            primeiro_prazo = int(self.condicao_pagamento.split("/")[0])
            dt = datetime.strptime(self.data_pedido, "%d/%m/%Y")
            return (dt + timedelta(days=primeiro_prazo)).strftime("%d/%m/%y")
        except Exception:
            return ""