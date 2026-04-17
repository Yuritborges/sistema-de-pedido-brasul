"""
corrigir_empresa_banco.py
=========================
Corrige o campo empresa_faturadora nos pedidos históricos importados.
Execute UMA VEZ após o importar_planilhas.py.

Como usar:
    python corrigir_empresa_banco.py
"""

import os, sqlite3
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, 'database', 'cotacao.db')

PLANILHAS = [
    f for f in os.listdir(BASE_DIR)
    if f.lower().endswith('.xlsx') and not f.startswith('~')
]

def _limpar(v, padrao=''):
    s = str(v or '').strip()
    return padrao if s in ('nan','NaN','None','') else s

print("=" * 55)
print("  CORREÇÃO DE EMPRESA — Banco Brasul")
print("=" * 55)

if not PLANILHAS:
    print("❌  Nenhuma planilha .xlsx encontrada na pasta.")
    exit(1)

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

atualizados = 0
for arq in PLANILHAS:
    caminho = os.path.join(BASE_DIR, arq)
    print(f"\n  Lendo {arq}...")
    try:
        df = pd.read_excel(caminho, sheet_name='LANÇAMENTO', header=1)
    except Exception as e:
        print(f"  ⚠  Erro: {e}"); continue

    df.columns = [str(c).strip() for c in df.columns]
    df = df.dropna(subset=['PEDIDO', 'FATURAMENTO'])
    df['PEDIDO'] = df['PEDIDO'].astype(str).str.strip().str.replace('.0','',regex=False)

    # Agrupa por pedido pegando o faturamento
    grupos = df.groupby('PEDIDO')['FATURAMENTO'].first().reset_index()

    for _, row in grupos.iterrows():
        num = str(row['PEDIDO']).strip()
        emp = _limpar(row['FATURAMENTO'])
        if not num or not emp: continue

        cur = conn.execute(
            "UPDATE pedidos SET empresa_faturadora=? WHERE numero=? AND (empresa_faturadora IS NULL OR empresa_faturadora='' OR empresa_faturadora='—')",
            (emp, num))
        atualizados += cur.rowcount

conn.commit()

total = conn.execute("SELECT COUNT(*) FROM pedidos WHERE empresa_faturadora IS NOT NULL AND empresa_faturadora != '' AND empresa_faturadora != '—'").fetchone()[0]
conn.close()

print(f"\n  ✅ {atualizados} pedidos atualizados com empresa faturadora")
print(f"  Total com empresa preenchida: {total}")
print("\n  Reinicie o sistema para ver os dados atualizados.")
