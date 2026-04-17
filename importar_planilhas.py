"""
importar_planilhas.py - Brasul Construtora
Detecta automaticamente todos os .xlsx na pasta raiz e importa tudo.
Pode ser rodado múltiplas vezes sem duplicar dados.
"""
import os, sys, json, sqlite3
import pandas as pd

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
OBRAS_JSON = os.path.join(BASE_DIR, 'assets', 'obras.json')
DB_PATH    = os.path.join(BASE_DIR, 'database', 'cotacao.db')
PLANILHAS  = [os.path.join(BASE_DIR,f) for f in os.listdir(BASE_DIR)
              if f.lower().endswith('.xlsx') and not f.startswith('~')]

def _s(v,d=''): s=str(v or '').strip(); return d if s in('nan','NaN','None','') else s
def _f(v):
    try: return float(str(v or '0').strip().replace(',','.'))
    except: return 0.0
def _i(v):
    try: f=_f(v); return int(f) if f==f else 0
    except: return 0

def importar_obras():
    print("\n[1/2] Importando obras...")
    existentes = {}
    if os.path.exists(OBRAS_JSON):
        try:
            with open(OBRAS_JSON,encoding='utf-8') as f: existentes=json.load(f)
        except: pass
    novas = 0
    for arq in PLANILHAS:
        try: df=pd.read_excel(arq,sheet_name='DADOS DAS OBRAS',header=0)
        except: continue
        df.columns=[str(c).strip() for c in df.columns]
        for _,row in df.iterrows():
            nome=_s(row.get('OBRA','')).upper()
            if not nome or nome in existentes: continue
            existentes[nome]={
                "escola":_s(row.get('ESCOLA','')),
                "faturamento":_s(row.get('FATURAMENTO','')),
                "endereco":_s(row.get('Local de Entrega:','')),
                "bairro":_s(row.get('Bairro:','')),
                "cep":_s(row.get('CEP:','')).replace(' ',''),
                "cidade":_s(row.get('Cidade:','')),
                "uf":_s(row.get('UF:',''),'SP'),
                "contrato":_s(row.get('Contrato Obra:',''),'0'),
            }
            novas+=1
    os.makedirs(os.path.dirname(OBRAS_JSON),exist_ok=True)
    with open(OBRAS_JSON,'w',encoding='utf-8') as f: json.dump(existentes,f,ensure_ascii=False,indent=2)
    print(f"  ✅ {novas} obras novas | Total: {len(existentes)}")

def importar_pedidos():
    print("\n[2/2] Importando pedidos e itens...")
    os.makedirs(os.path.dirname(DB_PATH),exist_ok=True)
    conn=sqlite3.connect(DB_PATH); conn.row_factory=sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS pedidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT NOT NULL UNIQUE, data_pedido TEXT,
            obra_nome TEXT, escola TEXT, fornecedor_nome TEXT,
            fornecedor_razao TEXT, empresa_faturadora TEXT,
            condicao_pagamento TEXT, forma_pagamento TEXT,
            prazo_entrega INTEGER, comprador TEXT,
            valor_total REAL, caminho_pdf TEXT,
            status TEXT DEFAULT 'historico',
            emitido_em TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS itens_pedido (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pedido_id INTEGER NOT NULL REFERENCES pedidos(id),
            descricao TEXT NOT NULL, quantidade REAL,
            unidade TEXT, valor_unitario REAL, valor_total REAL, categoria TEXT
        );
        CREATE TABLE IF NOT EXISTS contador_pedidos (
            id INTEGER PRIMARY KEY CHECK (id=1), ultimo INTEGER NOT NULL DEFAULT 2548
        );
        INSERT OR IGNORE INTO contador_pedidos (id,ultimo) VALUES (1,2548);
    """)
    conn.commit()
    tp=0; ti=0
    for arq in PLANILHAS:
        print(f"  Lendo {os.path.basename(arq)}...")
        try: df=pd.read_excel(arq,sheet_name='LANÇAMENTO',header=1)
        except Exception as e: print(f"  ⚠ {e}"); continue
        df.columns=[str(c).strip() for c in df.columns]
        df['PEDIDO_STR']=df['PEDIDO'].astype(str).str.strip().str.replace('.0','',regex=False)
        df['OBRA_UP']=df['OBRA'].astype(str).str.strip().str.upper()
        df['VT_NUM']=df['VALOR TOTAL'].apply(_f)
        df=df[df['PEDIDO_STR'].notna()&(df['PEDIDO_STR']!='nan')]
        grupos=df.groupby('PEDIDO_STR').agg(
            obra_nome=('OBRA_UP','first'),empresa=('FATURAMENTO','first'),
            fornecedor=('FORNECEDOR','first'),valor_total=('VT_NUM','sum'),
            data_pedido=('DATA PEDIDO','first'),condicao=('CONDIÇÃO PAGAMENTO','first'),
            forma=('FORMA DE PAGAMENTO','first'),prazo=('PRAZO','first'),
        ).reset_index()
        for _,row in grupos.iterrows():
            num=str(row['PEDIDO_STR']).strip()
            if not num or num=='nan': continue
            try: data=pd.to_datetime(row['data_pedido']).strftime('%d/%m/%Y')
            except: data=''
            try:
                conn.execute("""
                    INSERT INTO pedidos (numero,data_pedido,obra_nome,fornecedor_nome,
                    empresa_faturadora,condicao_pagamento,forma_pagamento,
                    prazo_entrega,valor_total,status)
                    VALUES (?,?,?,?,?,?,?,?,?,'historico')
                    ON CONFLICT(numero) DO UPDATE SET
                        obra_nome=excluded.obra_nome,
                        fornecedor_nome=excluded.fornecedor_nome,
                        empresa_faturadora=excluded.empresa_faturadora,
                        valor_total=excluded.valor_total
                """,(num,data,_s(row['obra_nome']).upper(),_s(row['fornecedor']).upper(),
                     _s(row['empresa']),_s(row['condicao']),_s(row['forma']),
                     _i(row['prazo']),round(_f(row['valor_total']),2)))
                tp+=1
                pid=conn.execute("SELECT id FROM pedidos WHERE numero=?",(num,)).fetchone()[0]
                conn.execute("DELETE FROM itens_pedido WHERE pedido_id=?",(pid,))
                for _,item in df[df['PEDIDO_STR']==num].iterrows():
                    desc=_s(item.get('DESCRIÇÃO MATERIAL',item.get('MATERIAL SOLICITADO','')))
                    if not desc: continue
                    conn.execute("""INSERT INTO itens_pedido
                        (pedido_id,descricao,quantidade,unidade,valor_unitario,valor_total,categoria)
                        VALUES (?,?,?,?,?,?,?)""",
                        (pid,desc.upper()[:200],_f(item.get('QTDADE',0)),
                         _s(item.get('UNID','UNID.')),_f(item.get('VALOR UNITARIO',0)),
                         _f(item.get('VALOR TOTAL',0)),_s(item.get('ITEM',''))))
                    ti+=1
            except Exception as e: print(f"    ⚠ Pedido {num}: {e}")
    conn.commit()
    tp2=conn.execute("SELECT COUNT(*) FROM pedidos").fetchone()[0]
    ti2=conn.execute("SELECT COUNT(*) FROM itens_pedido").fetchone()[0]
    conn.close()
    print(f"  ✅ {tp} pedidos processados | {ti} itens importados")
    print(f"  Total no banco: {tp2} pedidos, {ti2} itens")

def main():
    print("="*55)
    print("  IMPORTAÇÃO DE PLANILHAS — Brasul Construtora")
    print("="*55)
    try: import pandas, openpyxl
    except ImportError as e:
        print(f"\n❌ {e}\n  Execute: pip install pandas openpyxl"); sys.exit(1)
    encontradas=[p for p in PLANILHAS if os.path.exists(p)]
    if not encontradas:
        print("\n❌ Nenhuma planilha .xlsx encontrada."); sys.exit(1)
    print(f"\n  Planilhas encontradas: {len(encontradas)}")
    for p in encontradas: print(f"    • {os.path.basename(p)}")
    importar_obras()
    importar_pedidos()
    print("\n"+"="*55)
    print("  ✅  Concluído! Reinicie o sistema.")
    print("="*55)

if __name__=='__main__': main()
