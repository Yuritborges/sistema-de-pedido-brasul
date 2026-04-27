"""
corrigir_banco_iury.py
----------------------
Corrige o pedido #2593 que esta no banco sem dados (fornecedor e valor zerados).
Execute UMA VEZ no seu PC:

    python corrigir_banco_iury.py
"""

import sqlite3
import os

DB_PATH = r"Z:\0 OBRAS\brasul_pedidos\cotacao_rede.db"

def main():
    if not os.path.exists(DB_PATH):
        print(f"ERRO: Banco nao encontrado em:\n  {DB_PATH}")
        input("\nPressione Enter para sair...")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    # ── Verifica situação atual do #2593 ──────────────────────────────────────
    row = conn.execute(
        "SELECT id, fornecedor_nome, valor_total FROM pedidos WHERE numero = '2593'"
    ).fetchone()

    if not row:
        print("Pedido #2593 nao encontrado no banco. Inserindo...")
        _inserir(conn)
    elif not row["fornecedor_nome"] or float(row["valor_total"] or 0) == 0:
        print(f"Pedido #2593 encontrado mas incompleto (fornecedor='{row['fornecedor_nome']}', valor={row['valor_total']}). Corrigindo...")
        _atualizar(conn, row["id"])
    else:
        print(f"Pedido #2593 ja esta correto: {row['fornecedor_nome']} — R$ {row['valor_total']:.2f}")

    conn.commit()
    conn.close()

    print("\n" + "="*50)
    print("Concluido! Feche e abra o programa novamente.")
    print("="*50)
    input("\nPressione Enter para sair...")


def _atualizar(conn, pedido_id):
    conn.execute("""
        UPDATE pedidos SET
            fornecedor_nome    = 'DEPOSITO PADRÃO',
            fornecedor_razao   = 'DEPOSITO E COMERCIO PADRAO LOJA 2 LTDA',
            empresa_faturadora = 'INTERIORANA',
            condicao_pagamento = '7',
            forma_pagamento    = 'BOLETO',
            prazo_entrega      = 0,
            comprador          = 'IURY',
            valor_total        = 118.68,
            caminho_pdf        = 'Z:\\0 OBRAS\\brasul_pedidos\\Iury\\pdfs de pedidos\\PC-2593-INTERIORANA-MARIA_RITA_ARAÚJO.pdf',
            status             = 'emitido',
            obra_nome          = 'MARIA RITA ARAÚJO',
            data_pedido        = '24/04/2026'
        WHERE id = ?
    """, (pedido_id,))

    # Limpa itens antigos (se existirem zerados) e reinsere
    conn.execute("DELETE FROM itens_pedido WHERE pedido_id = ?", (pedido_id,))
    _inserir_itens(conn, pedido_id)
    print(f"  [OK] Pedido #2593 atualizado com sucesso.")


def _inserir(conn):
    cur = conn.execute("""
        INSERT INTO pedidos (
            numero, data_pedido, obra_nome, escola,
            fornecedor_nome, fornecedor_razao,
            empresa_faturadora, condicao_pagamento, forma_pagamento,
            prazo_entrega, comprador, valor_total,
            caminho_pdf, status, emitido_em
        ) VALUES ('2593','24/04/2026','MARIA RITA ARAÚJO','',
                  'DEPOSITO PADRÃO','DEPOSITO E COMERCIO PADRAO LOJA 2 LTDA',
                  'INTERIORANA','7','BOLETO',
                  0,'IURY',118.68,
                  'Z:\\0 OBRAS\\brasul_pedidos\\Iury\\pdfs de pedidos\\PC-2593-INTERIORANA-MARIA_RITA_ARAÚJO.pdf',
                  'emitido','2026-04-24 09:00:00')
    """)
    _inserir_itens(conn, cur.lastrowid)
    print("  [OK] Pedido #2593 inserido com sucesso.")


def _inserir_itens(conn, pedido_id):
    itens = [
        ("DISCO DIAMANTADO SEGMENTADO ECO 110MM", 4, "UNID.", 16.57, 66.28),
        ("SERRA CIRCULAR WIDEA 110X20X24 -- GOZILLA", 4, "UNID.", 13.10, 52.40),
    ]
    for desc, qtd, unid, vunit, vtotal in itens:
        conn.execute("""
            INSERT INTO itens_pedido (pedido_id, descricao, quantidade, unidade, valor_unitario, valor_total)
            VALUES (?,?,?,?,?,?)
        """, (pedido_id, desc, qtd, unid, vunit, vtotal))


if __name__ == "__main__":
    main()
