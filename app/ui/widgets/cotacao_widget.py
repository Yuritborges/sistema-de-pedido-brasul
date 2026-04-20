"""
app/ui/widgets/cotacao_widget.py  — v4 CLEAN
============================================
CORREÇÕES:
  - Adicionar item: insere linha na tabela diretamente, numera 1,2,3... automaticamente
  - Foco vai para a coluna Descrição da nova linha
  - Delete/Backspace apaga linha selecionada
  - Botão "Apagar selecionado" funciona corretamente
  - Botão "Limpar tudo" com confirmação
  - Cálculo não pula linhas
  - Empresa auto-preenchida pela obra
  - PDF: extração gratuita + modo visual lado a lado
"""

import os, json
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QComboBox, QGraphicsDropShadowEffect, QPushButton,
    QSplitter, QScrollArea, QMessageBox, QDialog,
    QAbstractItemView, QFileDialog, QProgressDialog,
    QApplication, QStyledItemDelegate, QTextEdit,
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal
from PySide6.QtGui import QColor, QFont, QBrush

from app.ui.style import (
    RED, GRAY, WHITE, BG, BDR, TXT, TXT_S, SEL, HOV, GREEN, BLUE,
    CSS_INPUT, CSS_COMBO, CORES_EMPRESA,
    btn_solid, btn_outline, card_container,
)

_ASSETS   = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'assets'))
_OBR_JSON = os.path.join(_ASSETS, 'obras.json')

# Cores F1/F2/F3
COR_F = ["#1A5276", "#1E8449", "#784212"]

# Cores de destaque da tabela
COR_MELHOR    = QColor("#D5F5E3")
COR_MELHOR_FG = QColor("#1A7A3C")
COR_PIOR      = QColor("#FDFEFE")
COR_VAZIO     = QColor("#F4F6F7")

CSS_TABLE = f"""
    QTableWidget {{
        background:{WHITE}; border:none; font-size:12px; color:#1A1A1A;
        selection-background-color:#FADBD8; selection-color:#2C2C2C;
        outline:none; gridline-color:#E5E5E5;
    }}
    QTableWidget::item {{ padding:2px 8px; border-bottom:1px solid #ECECEC; color:#1A1A1A; }}
    QTableWidget::item:hover    {{ background:#EBF5FB; }}
    QTableWidget::item:selected {{ background:#FADBD8; color:#2C2C2C; }}
    QHeaderView::section {{
        background:#2C2C2C; color:#FFFFFF; font-size:10px; font-weight:bold;
        padding:8px 6px; border:none; border-right:1px solid #444;
        border-bottom:2px solid #C0392B;
    }}
    QScrollBar:vertical   {{ background:transparent; width:6px;  border-radius:3px; }}
    QScrollBar:horizontal {{ background:transparent; height:6px; border-radius:3px; }}
    QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
        background:#C0C0C0; border-radius:3px; min-height:20px; min-width:20px;
    }}
    QScrollBar::add-line, QScrollBar::sub-line {{ width:0; height:0; }}
"""
CSS_EDIT = f"""
    QLineEdit {{
        color:#1A1A1A; background:{WHITE};
        border:1.5px solid #C0392B; border-radius:3px;
        padding:2px 6px; font-size:12px;
    }}
"""


# ══════════════════════════════════════════════════════════════════════════════
# THREAD — extração gratuita de PDF
# ══════════════════════════════════════════════════════════════════════════════

class PDFExtractorThread(QThread):
    resultado      = Signal(list)
    texto_extraido = Signal(str)
    erro           = Signal(str)
    progresso      = Signal(str)

    def __init__(self, caminho, fi):
        super().__init__()
        self.caminho = caminho
        self.fi      = fi

    def run(self):
        try:
            self.progresso.emit("Lendo PDF...")
            texto = self._ler()
            if not texto.strip():
                self.erro.emit(
                    "Não foi possível extrair texto deste PDF.\n\n"
                    "O arquivo pode ser uma foto/scan.\n\n"
                    "Use o Modo Visual para preencher manualmente.")
                return
            self.progresso.emit("Detectando itens e preços...")
            itens = self._extrair(texto)
            if itens:
                self.resultado.emit(itens)
            else:
                self.texto_extraido.emit(texto)
        except Exception as e:
            self.erro.emit(f"Erro ao processar PDF:\n{e}")

    def _ler(self):
        try:
            import pdfplumber
            txt = ""
            with pdfplumber.open(self.caminho) as pdf:
                for p in pdf.pages:
                    t = p.extract_text()
                    if t: txt += t + "\n"
            if txt.strip(): return txt
        except Exception:
            pass
        from pypdf import PdfReader
        return "\n".join(p.extract_text() or "" for p in PdfReader(self.caminho).pages)

    def _num(self, s):
        try: return float(str(s).replace(".","").replace(",","."))
        except: return None

    def _extrair(self, texto):
        """
        Detecta o formato automaticamente e extrai apenas
        descrição, quantidade e preço unitário.
        Sem tentar entender toda a estrutura do PDF.
        """
        cab = " ".join(texto.split("\n")[:20]).upper()

        # Formato UEHARA: CODIGO DESCRICAO UND BARRAS NCM QTDE UNITARIO TOTAL
        if any(x in cab for x in ["CÓDIGODESCRIÇÃO", "UEHARA", "COTAÇÃO DE PREÇOS"]):
            itens = self._uehara(texto)
            if itens: return itens

        # Formato SIRO: N CODIGO QTDE UN DESCRICAO BARRAS(13) NCM PRECO 0,00 TOTAL
        if any(x in cab for x in ["S.TRIB", "VLR. UNIT", "SIRO", "PROPOSTA COMERCIAL"]):
            itens = self._siro(texto)
            if itens: return itens

        # Formato AREA: N CODIGO DESCRICAO CODFAB MARCA QTDE.UN R$PRECO R$TOTAL
        if "R$" in texto[:2000] and any(x in cab for x in ["DDL", "AREA", "DISTRIBUIDORA"]):
            itens = self._area(texto)
            if itens: return itens

        # Fallback: tenta os 3 formatos e retorna o que tiver mais itens
        resultados = [self._uehara(texto), self._siro(texto), self._area(texto)]
        melhor = max(resultados, key=len)
        return melhor

    def _uehara(self, texto):
        """CODIGO DESCRICAO UND BARRAS NCM QTDE PRECO TOTAL — Ex: UEHARA Elétrica"""
        import re
        itens = []
        UNIDS = r"(PCT|PC|MT|RL|BR|CF|UN|CX|KG|SC|M2|M3|VB|JG|CT|BD|LT|CAR|GR)"
        for linha in texto.split("\n"):
            linha = linha.strip()
            m = re.match(r"^\d{6}\s+(.+?)\s+" + UNIDS + r"\s+", linha)
            if not m: continue
            resto = linha[m.end():]
            nums = [v for tok in resto.split()
                    for v in [self._num(tok)] if v and 0 < v < 100000]
            if len(nums) < 2: continue
            preco = nums[-2]; qtd = nums[-3] if len(nums) >= 3 else 1.0
            desc  = m.group(1).upper().strip()
            if preco > 0 and len(desc) > 3:
                itens.append({"descricao": desc[:80], "quantidade": qtd,
                               "unidade": m.group(2), "preco_unitario": preco})
        return itens

    def _siro(self, texto):
        """N CODIGO QTDE UN DESCRICAO BARRAS(13) NCM PRECO 0,00 TOTAL — Ex: SIRO Materiais"""
        import re
        itens = []
        UNIDS = r"(PC|MT|BR|CF|UN|RL|CT|KG|SC|M2|M3|CX|LT|BD)"
        PAT = re.compile(
            r"^\d{1,3}\s+[\d.]+\s+([\d,]+)\s+" + UNIDS +
            r"\s+(.+?)\s+\d{13}\s+[\d.]+\s+([\d.,]+)\s+0,00")
        for linha in texto.split("\n"):
            m = PAT.match(linha.strip())
            if not m: continue
            qtd   = self._num(m.group(1))
            unid  = m.group(2)
            desc  = re.sub(r"\s+-\s+-.*$", "", m.group(3)).upper().strip()
            preco = self._num(m.group(4))
            if preco and preco > 0 and len(desc) > 3:
                itens.append({"descricao": desc[:80], "quantidade": qtd or 1.0,
                               "unidade": unid, "preco_unitario": preco})
        return itens

    def _area(self, texto):
        """N CODIGO DESCRICAO CODFAB MARCA QTDE.UN R$PRECO R$TOTAL — Ex: AEA Distribuidora"""
        import re
        itens = []
        UNIDS = r"(PC|MT|BR|CF|UN|RL|CT|KG|SC|M2|M3|CX|LT|BD|UNIDADE)"
        PAT = re.compile(
            r"^\d{1,3}\s+\d+\s+(.+?)\s+([\d,]+)" + UNIDS +
            r"\s+R\$([\d.,]+)\s+R\$[\d.,]+")
        for linha in texto.split("\n"):
            m = PAT.match(linha.strip())
            if not m: continue
            desc_raw = m.group(1).upper().strip()
            qtd   = self._num(m.group(2))
            unid  = m.group(3)
            preco = self._num(m.group(4))
            if not preco or preco <= 0: continue
            # Remove código de fábrica (tokens alfanuméricos sem espaço)
            desc = " ".join(
                p for p in desc_raw.split()
                if not re.match(r"^[A-Z]{2,}\d+[A-Z0-9]*$", p)
            ).strip()
            if len(desc) < 4: continue
            itens.append({"descricao": desc[:80], "quantidade": qtd or 1.0,
                           "unidade": unid, "preco_unitario": preco})
        return itens


class PDFVisualDialog(QDialog):
    def __init__(self, texto, fi, nome_forn, itens, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Modo Visual — {nome_forn}")
        self.setMinimumSize(1000, 600)
        self.setStyleSheet(f"background:{WHITE}; color:{TXT};")
        self.precos: dict[int, float] = {}
        self._itens = itens; self._fi = fi
        self._build(texto, nome_forn)

    def _build(self, texto, nome):
        vl = QVBoxLayout(self); vl.setContentsMargins(14,12,14,12); vl.setSpacing(10)
        lbl = QLabel(f"📄  <b>{nome}</b> — veja o orçamento à esquerda e digite os preços à direita")
        lbl.setStyleSheet(f"font-size:12px; color:{GRAY}; background:transparent;")
        vl.addWidget(lbl)

        sp = QSplitter(Qt.Horizontal); sp.setHandleWidth(5)

        tv = QTextEdit(); tv.setReadOnly(True); tv.setPlainText(texto)
        tv.setStyleSheet("QTextEdit{background:#FAFAFA;color:#111;border:1px solid #DDD;"
                         "border-radius:6px;font-family:Consolas,monospace;font-size:11px;padding:8px;}")
        sp.addWidget(tv)

        right = QFrame(); right.setStyleSheet("background:transparent;border:none;")
        vr = QVBoxLayout(right); vr.setContentsMargins(8,0,0,0); vr.setSpacing(6)
        lbr = QLabel("Digite o preço unitário de cada item:")
        lbr.setStyleSheet(f"font-size:11px;font-weight:bold;color:{GRAY};background:transparent;")
        vr.addWidget(lbr)

        self._tbl = QTableWidget(len(self._itens), 5)
        self._tbl.setHorizontalHeaderLabels(["#","Descrição","Qtd","Unid",f"Preço {nome[:10]}"])
        self._tbl.setStyleSheet(CSS_TABLE); self._tbl.verticalHeader().setVisible(False)
        hh = self._tbl.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Fixed); self._tbl.setColumnWidth(0,30)
        hh.setSectionResizeMode(1, QHeaderView.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.Fixed); self._tbl.setColumnWidth(2,55)
        hh.setSectionResizeMode(3, QHeaderView.Fixed); self._tbl.setColumnWidth(3,60)
        hh.setSectionResizeMode(4, QHeaderView.Fixed); self._tbl.setColumnWidth(4,95)

        for r, it in enumerate(self._itens):
            self._tbl.setRowHeight(r, 30)
            def ro(t, a=Qt.AlignCenter):
                i2 = QTableWidgetItem(str(t)); i2.setTextAlignment(a)
                i2.setFlags(i2.flags() & ~Qt.ItemIsEditable)
                i2.setForeground(QBrush(QColor("#333"))); return i2
            self._tbl.setItem(r,0,ro(r+1)); self._tbl.setItem(r,1,ro(it.descricao or "—",Qt.AlignLeft|Qt.AlignVCenter))
            self._tbl.setItem(r,2,ro(it.quantidade)); self._tbl.setItem(r,3,ro(it.unidade))
            p = it.precos[self._fi]
            ep = QTableWidgetItem(f"{p:.2f}".replace(".",",") if p else "")
            ep.setTextAlignment(Qt.AlignRight|Qt.AlignVCenter)
            ep.setForeground(QBrush(QColor("#1A1A1A")))
            self._tbl.setItem(r,4,ep)
        vr.addWidget(self._tbl,1)
        dica = QLabel("💡  Tab avança para o próximo item")
        dica.setStyleSheet("font-size:10px;color:#666;background:transparent;")
        vr.addWidget(dica)
        sp.addWidget(right); sp.setSizes([500,480]); vl.addWidget(sp,1)

        sep = QFrame(); sep.setFrameShape(QFrame.HLine); sep.setStyleSheet("background:#E0E0E0;")
        vl.addWidget(sep)
        hl = QHBoxLayout(); hl.addStretch()
        bc = btn_outline("Cancelar"); bc.clicked.connect(self.reject); hl.addWidget(bc)
        bo = btn_solid("✅  Aplicar preços", GREEN, h=36); bo.clicked.connect(self._aplicar); hl.addWidget(bo)
        vl.addLayout(hl)

    def _aplicar(self):
        def p(t):
            try: return float(str(t).replace("R$","").replace(" ","").replace(".","").replace(",","."))
            except: return None
        for r in range(self._tbl.rowCount()):
            it = self._tbl.item(r,4)
            if it:
                v = p(it.text())
                if v and v > 0: self.precos[r] = v
        self.accept()


# ══════════════════════════════════════════════════════════════════════════════
# DELEGATE — Tab/Enter navegam entre colunas editáveis
# ══════════════════════════════════════════════════════════════════════════════

class NavDelegate(QStyledItemDelegate):
    def __init__(self, tabela, cb_nova_linha, parent=None):
        super().__init__(parent)
        self._t  = tabela
        self._nl = cb_nova_linha

    def createEditor(self, parent, option, index):
        e = QLineEdit(parent); e.setStyleSheet(CSS_EDIT)
        if index.column() == 1:
            e.textChanged.connect(
                lambda txt, w=e: (w.blockSignals(True), w.setText(txt.upper()),
                                   w.blockSignals(False)) if txt != txt.upper() else None)
        return e

    def eventFilter(self, editor, event):
        if event.type() == event.Type.KeyPress:
            key = event.key()
            if key in (Qt.Key_Tab, Qt.Key_Return, Qt.Key_Enter):
                idx = self._t.currentIndex()
                row, col = idx.row(), idx.column()
                COLS = [1, 2, 3, 4, 6, 8]
                self.commitData.emit(editor)
                self.closeEditor.emit(editor, QStyledItemDelegate.NoHint)
                if col in COLS:
                    ni = COLS.index(col) + 1
                    if ni < len(COLS):
                        nc = COLS[ni]
                        QTimer.singleShot(0, lambda r=row, c=nc: (
                            self._t.setCurrentCell(r, c),
                            self._t.edit(self._t.model().index(r, c))
                        ))
                    else:
                        if row + 1 >= self._t.rowCount():
                            QTimer.singleShot(0, self._nl)
                        else:
                            QTimer.singleShot(0, lambda r=row+1: (
                                self._t.setCurrentCell(r, 1),
                                self._t.edit(self._t.model().index(r, 1))
                            ))
                return True
        return super().eventFilter(editor, event)


# ══════════════════════════════════════════════════════════════════════════════
# MODELOS DE DADOS
# ══════════════════════════════════════════════════════════════════════════════

class ItemCotacao:
    def __init__(self, desc="", qtd=1.0, unid="UNID."):
        self.descricao  = desc
        self.quantidade = float(qtd) if qtd else 1.0
        self.unidade    = unid
        self.precos     = [None, None, None]

    def subtotal(self, i):
        try:
            p = float(self.precos[i])
            return round(p * self.quantidade, 2) if p > 0 else None
        except (TypeError, ValueError):
            return None

    def melhor_idx(self):
        subs = [(i, self.subtotal(i)) for i in range(3) if self.subtotal(i) is not None]
        return min(subs, key=lambda x: x[1])[0] if subs else None

    def melhor_sub(self):
        i = self.melhor_idx()
        return self.subtotal(i) if i is not None else None


class ResultadoFornecedor:
    def __init__(self, nome, idx):
        self.nome=nome; self.idx=idx
        self.itens_cotados=0; self.itens_baratos=0
        self.total_itens=0; self.subtotal_val=0.0
        self.frete=0.0; self.desconto=0.0

    @property
    def total_final(self):
        return max(0.0, self.subtotal_val + self.frete - self.desconto)

    def status(self, n):
        if self.itens_cotados == n: return "✓ Completo"
        if self.itens_cotados > 0:  return f"Parcial ({self.itens_cotados}/{n})"
        return "Sem cotação"


# ══════════════════════════════════════════════════════════════════════════════
# WIDGET PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════

class CotacaoWidget(QWidget):

    def __init__(self):
        super().__init__()
        self._itens: list[ItemCotacao] = []
        self._fretes    = [0.0, 0.0, 0.0]
        self._descontos = [0.0, 0.0, 0.0]
        self._obras     = {}
        self._bloqueio  = False
        self._progress  = None
        self._build()
        self._carregar_obras()
        # Inicia com 1 item vazio
        self._itens.append(ItemCotacao())
        self._inserir_linha(0, self._itens[0])
        self._atualizar_contador()

    # ══════════════════════════════════════════════════════════════════════════
    # BUILD
    # ══════════════════════════════════════════════════════════════════════════

    def _build(self):
        self.setStyleSheet(f"background:{BG};")
        vl = QVBoxLayout(self); vl.setContentsMargins(24,20,24,16); vl.setSpacing(14)

        # Cabeçalho
        hl = QHBoxLayout()
        tv = QVBoxLayout(); tv.setSpacing(2)
        t = QLabel("Cotação Comparativa")
        t.setStyleSheet(f"font-size:20px;font-weight:bold;color:{GRAY};background:transparent;")
        s = QLabel("Compare fornecedores item a item e gere o pedido do vencedor")
        s.setStyleSheet(f"font-size:11px;color:#555;background:transparent;")
        tv.addWidget(t); tv.addWidget(s); hl.addLayout(tv); hl.addStretch()
        bn = btn_outline("🗑  Nova cotação"); bn.clicked.connect(self._nova_cotacao); hl.addWidget(bn)
        vl.addLayout(hl)
        vl.addWidget(self._build_cab())

        sp = QSplitter(Qt.Horizontal)
        sp.setStyleSheet("QSplitter::handle{background:#C0C0C0;width:5px;}QSplitter::handle:hover{background:#C0392B;}")
        sp.setHandleWidth(6); sp.setChildrenCollapsible(False)
        sp.addWidget(self._build_tabela()); sp.addWidget(self._build_dashboard())
        sp.setSizes([760,440]); vl.addWidget(sp,1)

    def _build_cab(self):
        box = QFrame()
        box.setStyleSheet(f"QFrame{{background:{WHITE};border-radius:10px;border:1px solid #DDD;}}")
        hl = QHBoxLayout(box); hl.setContentsMargins(16,12,16,12); hl.setSpacing(14)

        def grp(lbl_txt, widget):
            vl2 = QVBoxLayout(); vl2.setSpacing(4)
            l = QLabel(lbl_txt.upper())
            l.setStyleSheet("font-size:9px;font-weight:700;color:#444;background:transparent;letter-spacing:1px;")
            vl2.addWidget(l); vl2.addWidget(widget); return vl2

        self._cb_obra = QComboBox(); self._cb_obra.setMinimumWidth(200); self._cb_obra.setStyleSheet(CSS_COMBO)
        self._cb_obra.currentTextChanged.connect(self._on_obra)
        hl.addLayout(grp("Obra", self._cb_obra))

        self._cb_emp = QComboBox(); self._cb_emp.setMinimumWidth(130); self._cb_emp.setStyleSheet(CSS_COMBO)
        for e in ["BRASUL","JB","B&B","INTERIORANA","INTERBRAS"]: self._cb_emp.addItem(e)
        hl.addLayout(grp("Empresa faturadora", self._cb_emp))
        hl.addWidget(self._vsep())

        self._e_forn = []; self._btn_pdf = []
        for i in range(3):
            cor = COR_F[i]
            vf = QVBoxLayout(); vf.setSpacing(4)
            lf = QLabel(f"FORNECEDOR {i+1}")
            lf.setStyleSheet(f"font-size:9px;font-weight:700;color:{cor};background:transparent;letter-spacing:1px;")
            vf.addWidget(lf)
            hf = QHBoxLayout(); hf.setSpacing(4)
            e = QLineEdit(); e.setPlaceholderText(f"Nome F{i+1}"); e.setMinimumWidth(115); e.setStyleSheet(CSS_INPUT)
            e.textChanged.connect(lambda txt,idx=i: self._on_forn(idx,txt))
            self._e_forn.append(e)
            bp = QPushButton("📄 PDF"); bp.setFixedHeight(32); bp.setFixedWidth(58)
            bp.setCursor(Qt.PointingHandCursor)
            bp.setStyleSheet(f"QPushButton{{background:{cor};color:white;font-size:10px;font-weight:bold;border-radius:5px;border:none;}}QPushButton:hover{{background:{cor}CC;}}")
            bp.clicked.connect(lambda _,idx=i: self._importar_pdf(idx))
            self._btn_pdf.append(bp)
            hf.addWidget(e); hf.addWidget(bp); vf.addLayout(hf); hl.addLayout(vf)

        hl.addWidget(self._vsep())
        self._e_frete = []
        for i in range(3):
            e = QLineEdit("0,00"); e.setMaximumWidth(80); e.setStyleSheet(CSS_INPUT)
            e.textChanged.connect(lambda t,idx=i: self._on_frete(idx,t))
            self._e_frete.append(e); hl.addLayout(grp(f"Frete F{i+1}", e))

        hl.addWidget(self._vsep())
        self._e_desc = []
        for i in range(3):
            e = QLineEdit("0,00"); e.setMaximumWidth(80); e.setStyleSheet(CSS_INPUT)
            e.textChanged.connect(lambda t,idx=i: self._on_desc(idx,t))
            self._e_desc.append(e); hl.addLayout(grp(f"Desc. F{i+1}", e))

        hl.addStretch(); return box

    def _build_tabela(self):
        frame = card_container()
        sh = QGraphicsDropShadowEffect(); sh.setBlurRadius(14); sh.setOffset(0,2); sh.setColor(QColor(0,0,0,15))
        frame.setGraphicsEffect(sh)
        vl = QVBoxLayout(frame); vl.setContentsMargins(0,0,0,0); vl.setSpacing(0)

        # Barra de ações
        hl = QHBoxLayout(); hl.setContentsMargins(14,10,14,8); hl.setSpacing(10)
        lbl = QLabel("Itens da Cotação")
        lbl.setStyleSheet(f"font-size:13px;font-weight:bold;color:{GRAY};background:transparent;")
        self._lbl_n = QLabel("0 itens")
        self._lbl_n.setStyleSheet("font-size:11px;color:#555;background:transparent;")
        hl.addWidget(lbl); hl.addWidget(self._lbl_n); hl.addStretch()

        b1 = btn_solid("＋  Adicionar", GREEN, h=30)
        b1.setToolTip("Adicionar novo item (ou Enter na última coluna)")
        b1.clicked.connect(self._adicionar_item)

        b2 = btn_solid("🗑  Apagar selecionado", "#C0392B", h=30)
        b2.setToolTip("Remove a linha selecionada (ou tecla Delete)")
        b2.clicked.connect(self._apagar_selecionado)

        b3 = btn_solid("✕  Limpar tudo", "#7F8C8D", h=30)
        b3.setToolTip("Remove todos os itens")
        b3.clicked.connect(self._limpar_tudo)

        b4 = btn_solid("⚡  Calcular", "#2C3E50", h=30)
        b4.setToolTip("Recalcula comparativos")
        b4.clicked.connect(self._calcular)

        for b in [b1,b2,b3,b4]: hl.addWidget(b)
        vl.addLayout(hl)

        sep = QFrame(); sep.setFrameShape(QFrame.HLine); sep.setStyleSheet("background:#E0E0E0;"); sep.setFixedHeight(1)
        vl.addWidget(sep)

        self._tbl = QTableWidget(0, 12)
        self._tbl.setHorizontalHeaderLabels([
            "#","Descrição do Material","Qtd","Unid",
            "Preço F1","Sub F1","Preço F2","Sub F2","Preço F3","Sub F3",
            "✓ Melhor","Fornecedor"
        ])
        self._tbl.setStyleSheet(CSS_TABLE)
        self._tbl.setSelectionBehavior(QTableWidget.SelectRows)
        self._tbl.setEditTriggers(QTableWidget.DoubleClicked|QTableWidget.EditKeyPressed)
        self._tbl.verticalHeader().setVisible(False)
        self._tbl.setShowGrid(True); self._tbl.setFrameShape(QFrame.NoFrame)
        self._tbl.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self._tbl.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)

        self._delegate = NavDelegate(self._tbl, self._adicionar_item, self._tbl)
        self._tbl.setItemDelegate(self._delegate)

        hh = self._tbl.horizontalHeader()
        hh.setHighlightSections(False); hh.setMinimumSectionSize(40)
        hh.setStretchLastSection(False); hh.setSectionResizeMode(QHeaderView.Interactive)
        for col, w in enumerate([28,220,55,65,85,85,85,85,85,85,90,110]):
            self._tbl.setColumnWidth(col, w)

        self._tbl.keyPressEvent = self._key_press
        self._tbl.itemChanged.connect(self._on_changed)
        vl.addWidget(self._tbl, 1)

        sep2 = QFrame(); sep2.setFrameShape(QFrame.HLine); sep2.setStyleSheet("background:#E0E0E0;"); sep2.setFixedHeight(1)
        vl.addWidget(sep2)

        hl2 = QHBoxLayout(); hl2.setContentsMargins(14,8,14,10); hl2.setSpacing(24)
        self._lbl_tot = [QLabel(f"F{i+1}: —") for i in range(3)]
        self._lbl_melhor = QLabel("✓ Melhor item a item: —")
        self._lbl_melhor.setStyleSheet(f"font-size:11px;font-weight:bold;color:{GREEN};background:transparent;")
        for i, lb in enumerate(self._lbl_tot):
            lb.setStyleSheet(f"font-size:11px;font-weight:600;color:{COR_F[i]};background:transparent;")
            hl2.addWidget(lb)
        hl2.addWidget(self._lbl_melhor); hl2.addStretch()
        vl.addLayout(hl2); return frame

    def _build_dashboard(self):
        frame = card_container()
        sh = QGraphicsDropShadowEffect(); sh.setBlurRadius(14); sh.setOffset(0,2); sh.setColor(QColor(0,0,0,15))
        frame.setGraphicsEffect(sh)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background:transparent;")
        inner = QWidget(); inner.setStyleSheet(f"background:{WHITE};")
        vl = QVBoxLayout(inner); vl.setContentsMargins(18,16,18,16); vl.setSpacing(12)

        lbl = QLabel("Resultado da Análise")
        lbl.setStyleSheet(f"font-size:14px;font-weight:bold;color:{GRAY};background:transparent;")
        vl.addWidget(lbl)
        sep = QFrame(); sep.setFrameShape(QFrame.HLine); sep.setStyleSheet("background:#E0E0E0;")
        vl.addWidget(sep)

        self._frame_ven = QFrame()
        self._frame_ven.setStyleSheet(f"QFrame{{background:#FEF9F9;border-radius:10px;border-left:5px solid {RED};border-top:1px solid #EEE;border-right:1px solid #EEE;border-bottom:1px solid #EEE;}}")
        vv = QVBoxLayout(self._frame_ven); vv.setContentsMargins(14,12,14,12); vv.setSpacing(5)
        lt = QLabel("🏆  EMPRESA VENCEDORA")
        lt.setStyleSheet("font-size:9px;font-weight:700;color:#555;background:transparent;letter-spacing:1px;")
        self._lbl_ven = QLabel("—")
        self._lbl_ven.setStyleSheet(f"font-size:22px;font-weight:bold;color:{RED};background:transparent;")
        self._lbl_mot = QLabel("Preencha os preços e clique em Calcular")
        self._lbl_mot.setStyleSheet("font-size:10px;color:#555;background:transparent;")
        self._lbl_mot.setWordWrap(True)
        vv.addWidget(lt); vv.addWidget(self._lbl_ven); vv.addWidget(self._lbl_mot)
        vl.addWidget(self._frame_ven)

        lc = QLabel("COMPARATIVO")
        lc.setStyleSheet("font-size:9px;font-weight:700;color:#444;background:transparent;letter-spacing:1px;")
        vl.addWidget(lc)

        self._cards = [self._make_card(i) for i in range(3)]
        for c in self._cards: vl.addWidget(c)

        self._lbl_obs = QLabel("")
        self._lbl_obs.setStyleSheet("font-size:10px;color:#555;background:#F8F8F8;border-radius:6px;padding:8px;border:1px solid #DDD;")
        self._lbl_obs.setWordWrap(True); self._lbl_obs.setVisible(False)
        vl.addWidget(self._lbl_obs)

        sep2 = QFrame(); sep2.setFrameShape(QFrame.HLine); sep2.setStyleSheet("background:#E0E0E0;")
        vl.addWidget(sep2)

        self._btn_ven = btn_solid("📋  Gerar Pedido do Vencedor", RED, h=42)
        self._btn_ven.setEnabled(False); self._btn_ven.clicked.connect(self._gerar_pedido)
        vl.addWidget(self._btn_ven)

        self._btn_ii = btn_solid("🔀  Gerar Pedido Item a Item", GREEN, h=38)
        self._btn_ii.setEnabled(False); self._btn_ii.clicked.connect(self._gerar_item_item)
        vl.addWidget(self._btn_ii)
        vl.addStretch()
        scroll.setWidget(inner)
        ol = QVBoxLayout(frame); ol.setContentsMargins(0,0,0,0); ol.addWidget(scroll)
        return frame

    def _make_card(self, i):
        c = QFrame()
        c.setStyleSheet("QFrame{background:#F8F8F8;border-radius:8px;border:1px solid #E0E0E0;}")
        vl = QVBoxLayout(c); vl.setContentsMargins(12,10,12,10); vl.setSpacing(4)
        ht = QHBoxLayout()
        ln = QLabel(f"Fornecedor {i+1}")
        ln.setStyleSheet(f"font-size:12px;font-weight:bold;color:{COR_F[i]};background:transparent;")
        ln.setObjectName(f"cn_{i}")
        ls = QLabel("—"); ls.setStyleSheet("font-size:10px;color:#555;background:transparent;")
        ls.setObjectName(f"cs_{i}")
        ht.addWidget(ln); ht.addStretch(); ht.addWidget(ls); vl.addLayout(ht)
        hm = QHBoxLayout(); hm.setSpacing(14)
        for key,cor,obj in [("ITENS",BLUE,f"ci_{i}"),("+ BARATOS",GREEN,f"cb_{i}"),("TOTAL",RED,f"ct_{i}")]:
            vm = QVBoxLayout(); vm.setSpacing(1)
            lt = QLabel(key); lt.setStyleSheet("font-size:8px;font-weight:700;color:#444;background:transparent;letter-spacing:1px;")
            lv = QLabel("—"); lv.setStyleSheet(f"font-size:15px;font-weight:bold;color:{cor};background:transparent;")
            lv.setObjectName(obj); vm.addWidget(lt); vm.addWidget(lv); hm.addLayout(vm)
        hm.addStretch(); vl.addLayout(hm); return c

    # ══════════════════════════════════════════════════════════════════════════
    # DADOS
    # ══════════════════════════════════════════════════════════════════════════

    def _carregar_obras(self):
        try:
            with open(_OBR_JSON, encoding='utf-8') as f: self._obras = json.load(f)
        except Exception: self._obras = {}
        self._cb_obra.blockSignals(True); self._cb_obra.clear()
        self._cb_obra.addItem("— Selecione a obra —")
        for n in sorted(self._obras): self._cb_obra.addItem(n)
        self._cb_obra.blockSignals(False)

    def _on_obra(self, nome):
        fat = self._obras.get(nome, {}).get("faturamento", "")
        if fat:
            idx = self._cb_emp.findText(fat)
            if idx >= 0: self._cb_emp.setCurrentIndex(idx)

    # ══════════════════════════════════════════════════════════════════════════
    # TABELA — inserção e gestão
    # ══════════════════════════════════════════════════════════════════════════

    def _inserir_linha(self, row: int, item: ItemCotacao):
        """Insere UMA linha na tabela. Quem chama deve controlar blockSignals."""
        nomes  = [e.text().strip() or f"F{i+1}" for i,e in enumerate(self._e_forn)]
        melhor = item.melhor_idx()

        self._tbl.insertRow(row)
        self._tbl.setRowHeight(row, 34)

        def ro(txt, align=Qt.AlignCenter, cor="#666"):
            it = QTableWidgetItem(str(txt)); it.setTextAlignment(align)
            it.setFlags(it.flags() & ~Qt.ItemIsEditable)
            it.setForeground(QBrush(QColor(cor))); return it

        def ed(txt, align=Qt.AlignVCenter|Qt.AlignLeft, cor="#1A1A1A"):
            it = QTableWidgetItem(str(txt)); it.setTextAlignment(align)
            it.setFlags(it.flags() | Qt.ItemIsEditable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            it.setForeground(QBrush(QColor(cor))); return it

        # Coluna 0: número sequencial automático
        self._tbl.setItem(row, 0, ro(str(row+1)))
        # Colunas editáveis
        self._tbl.setItem(row, 1, ed(item.descricao))
        self._tbl.setItem(row, 2, ed(self._fn(item.quantidade), Qt.AlignCenter))
        self._tbl.setItem(row, 3, ed(item.unidade, Qt.AlignCenter, "#555"))

        for fi in range(3):
            cp, cs = 4+fi*2, 5+fi*2
            preco = item.precos[fi]; sub = item.subtotal(fi)
            bst   = (melhor == fi) and sub is not None
            bgp   = COR_MELHOR if bst else (COR_VAZIO if preco is None else COR_PIOR)

            ip = ed(self._fb(preco) if preco is not None else "",
                    Qt.AlignRight|Qt.AlignVCenter, "#1A7A3C" if bst else "#1A1A1A")
            ip.setBackground(QBrush(bgp))
            if bst: ff=QFont(); ff.setBold(True); ip.setFont(ff)
            self._tbl.setItem(row, cp, ip)

            is2 = ro(self._fb(sub) if sub is not None else "—",
                     Qt.AlignRight|Qt.AlignVCenter, "#1A7A3C" if bst else "#555")
            is2.setBackground(QBrush(COR_MELHOR if bst else COR_VAZIO))
            if bst: ff=QFont(); ff.setBold(True); is2.setFont(ff)
            self._tbl.setItem(row, cs, is2)

        ms = item.melhor_sub()
        im = ro(self._fb(ms) if ms else "—", Qt.AlignRight|Qt.AlignVCenter,
                "#1A7A3C" if ms else "#999")
        im.setBackground(QBrush(COR_MELHOR if ms else COR_VAZIO))
        if ms: ff=QFont(); ff.setBold(True); im.setFont(ff)
        self._tbl.setItem(row, 10, im)

        vn = nomes[melhor] if melhor is not None else "—"
        iv = ro(vn, Qt.AlignCenter, "#1A7A3C" if melhor is not None else "#999")
        if melhor is not None: ff=QFont(); ff.setBold(True); iv.setFont(ff)
        self._tbl.setItem(row, 11, iv)

    def _renumerar(self):
        """Renumera a coluna # após remoção."""
        self._bloqueio = True
        self._tbl.blockSignals(True)
        for r in range(self._tbl.rowCount()):
            it = self._tbl.item(r, 0)
            if it: it.setText(str(r+1))
        self._tbl.blockSignals(False)
        self._bloqueio = False

    def _rebuild(self):
        """Reconstrói a tabela completa (após cálculo ou carga de PDF)."""
        self._bloqueio = True
        self._tbl.blockSignals(True)
        self._tbl.setRowCount(0)
        for r, item in enumerate(self._itens):
            self._inserir_linha(r, item)
        self._tbl.blockSignals(False)
        self._bloqueio = False
        self._atualizar_contador()
        self._atualizar_totais()

    def _atualizar_contador(self):
        n = len(self._itens)
        self._lbl_n.setText(f"{n} item{'ns' if n!=1 else ''}")

    def _adicionar_item(self, item=None):
        """Adiciona linha — RÁPIDO, sem reconstruir a tabela inteira."""
        if item is None: item = ItemCotacao()
        self._itens.append(item)
        r = len(self._itens) - 1
        self._bloqueio = True
        self._tbl.blockSignals(True)
        self._inserir_linha(r, item)
        self._tbl.blockSignals(False)
        self._bloqueio = False
        self._atualizar_contador()

        def foca():
            self._tbl.scrollTo(self._tbl.model().index(r, 1))
            self._tbl.setCurrentCell(r, 1)
            self._tbl.edit(self._tbl.model().index(r, 1))
        QTimer.singleShot(30, foca)

    def _apagar_selecionado(self):
        """Apaga a linha selecionada (ou a última se nada selecionado)."""
        row = self._tbl.currentRow()
        n   = len(self._itens)

        if n == 1:
            # Só 1 item: limpa em vez de remover
            self._itens[0] = ItemCotacao()
            self._rebuild(); return

        if row < 0 or row >= n:
            # Nada selecionado: remove o último
            self._itens.pop()
            self._tbl.removeRow(self._tbl.rowCount()-1)
        else:
            self._itens.pop(row)
            self._tbl.removeRow(row)

        self._renumerar(); self._atualizar_contador(); self._atualizar_totais()
        nr = min(row if row >= 0 else n-2, len(self._itens)-1)
        if nr >= 0: self._tbl.setCurrentCell(nr, 1)

    def _limpar_tudo(self):
        if QMessageBox.question(self, "Limpar tudo",
                "Deseja remover todos os itens?\nDados dos fornecedores são mantidos.",
                QMessageBox.Yes|QMessageBox.No, QMessageBox.No) != QMessageBox.Yes: return
        self._itens = [ItemCotacao()]; self._rebuild()

    def _key_press(self, event):
        """Delete/Backspace apaga item selecionado."""
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            if self._tbl.state() != QTableWidget.EditingState:
                self._apagar_selecionado(); return
        QTableWidget.keyPressEvent(self._tbl, event)

    def _on_changed(self, ti):
        if self._bloqueio: return
        row, col = ti.row(), ti.column()
        if row >= len(self._itens): return
        item = self._itens[row]; txt = ti.text().strip()

        if col == 1:
            item.descricao = txt.upper()
        elif col == 2:
            v = self._pn(txt); item.quantidade = v if v and v > 0 else 1.0
            # Atualiza subtotais da linha sem rebuild completo
            self._atualizar_linha_calc(row, item)
            self._atualizar_dashboard()
        elif col == 3:
            item.unidade = txt.upper() or "UNID."
        elif col in (4, 6, 8):
            fi = (col - 4) // 2
            item.precos[fi] = self._pn(txt)
            # Atualiza só os subtotais/melhor desta linha
            self._atualizar_linha_calc(row, item)
            self._atualizar_dashboard()

    def _atualizar_linha_calc(self, row: int, item: ItemCotacao):
        """Atualiza só as células calculadas (subtotais, melhor) de uma linha."""
        if row >= self._tbl.rowCount(): return
        melhor = item.melhor_idx()
        nomes  = [e.text().strip() or f"F{i+1}" for i, e in enumerate(self._e_forn)]

        self._bloqueio = True
        self._tbl.blockSignals(True)

        for fi in range(3):
            cs = 5 + fi * 2
            sub = item.subtotal(fi)
            bst = (melhor == fi) and sub is not None
            is2 = self._tbl.item(row, cs)
            if not is2:
                is2 = QTableWidgetItem()
                is2.setFlags(is2.flags() & ~Qt.ItemIsEditable)
                self._tbl.setItem(row, cs, is2)
            is2.setText(self._fb(sub) if sub is not None else "—")
            is2.setBackground(QBrush(COR_MELHOR if bst else COR_VAZIO))
            fg = QColor("#1A7A3C") if bst else QColor("#555555")
            is2.setForeground(QBrush(fg))
            if bst:
                ff = QFont(); ff.setBold(True); is2.setFont(ff)
            else:
                is2.setFont(QFont())
            # Também atualiza o fundo da célula de preço para refletir melhor
            ip = self._tbl.item(row, cs - 1)
            if ip:
                preco = item.precos[fi]
                bgp = COR_MELHOR if bst else (COR_VAZIO if preco is None else COR_PIOR)
                ip.setBackground(QBrush(bgp))
                ip.setForeground(QBrush(QColor("#1A7A3C") if bst else QColor("#1A1A1A")))
                if bst:
                    ff = QFont(); ff.setBold(True); ip.setFont(ff)
                else:
                    ip.setFont(QFont())

        # Melhor subtotal (col 10)
        ms = item.melhor_sub()
        im = self._tbl.item(row, 10)
        if not im:
            im = QTableWidgetItem()
            im.setFlags(im.flags() & ~Qt.ItemIsEditable)
            self._tbl.setItem(row, 10, im)
        im.setText(self._fb(ms) if ms else "—")
        im.setBackground(QBrush(COR_MELHOR if ms else COR_VAZIO))
        im.setForeground(QBrush(QColor("#1A7A3C") if ms else QColor("#999999")))
        if ms:
            ff = QFont(); ff.setBold(True); im.setFont(ff)
        else:
            im.setFont(QFont())

        # Fornecedor vencedor do item (col 11)
        iv = self._tbl.item(row, 11)
        if not iv:
            iv = QTableWidgetItem()
            iv.setFlags(iv.flags() & ~Qt.ItemIsEditable)
            self._tbl.setItem(row, 11, iv)
        vn = nomes[melhor] if melhor is not None else "—"
        iv.setText(vn)
        iv.setForeground(QBrush(QColor("#1A7A3C") if melhor is not None else QColor("#999999")))
        if melhor is not None:
            ff = QFont(); ff.setBold(True); iv.setFont(ff)
        else:
            iv.setFont(QFont())

        self._tbl.blockSignals(False)
        self._bloqueio = False
        self._atualizar_totais()

    def _on_forn(self, i, txt):
        n = txt.strip().upper() or f"F{i+1}"
        self._tbl.setHorizontalHeaderItem(4+i*2, QTableWidgetItem(f"Preço {n[:10]}"))
        self._tbl.setHorizontalHeaderItem(5+i*2, QTableWidgetItem(f"Sub {n[:10]}"))
        self._atualizar_dashboard()

    def _on_frete(self, i, t): self._fretes[i] = self._pn(t) or 0.0; self._atualizar_dashboard()
    def _on_desc(self, i, t):  self._descontos[i] = self._pn(t) or 0.0; self._atualizar_dashboard()

    # ══════════════════════════════════════════════════════════════════════════
    # CÁLCULO
    # ══════════════════════════════════════════════════════════════════════════

    def _calcular(self): self._rebuild(); self._atualizar_dashboard()

    def _atualizar_totais(self):
        nomes = [e.text().strip() or f"F{i+1}" for i,e in enumerate(self._e_forn)]
        for fi in range(3):
            tot = sum((it.subtotal(fi) or 0) for it in self._itens) + self._fretes[fi] - self._descontos[fi]
            self._lbl_tot[fi].setText(f"{nomes[fi]}: R$ {self._f(tot)}")
        mt = sum((it.melhor_sub() or 0) for it in self._itens)
        self._lbl_melhor.setText(f"✓ Melhor item a item: R$ {self._f(mt)}")

    def _calcular_res(self):
        res = []
        for fi in range(3):
            nome = self._e_forn[fi].text().strip() or f"Fornecedor {fi+1}"
            r = ResultadoFornecedor(nome, fi)
            r.total_itens = len(self._itens); r.frete = self._fretes[fi]; r.desconto = self._descontos[fi]
            for it in self._itens:
                sub = it.subtotal(fi)
                if sub is not None: r.itens_cotados += 1; r.subtotal_val += sub
                if it.melhor_idx() == fi: r.itens_baratos += 1
            res.append(r)
        return res

    def _vencedor(self, res):
        n = len(self._itens)
        val = [r for r in res if r.itens_cotados > 0]
        if not val: return None,"Preencha os preços e clique em Calcular",""
        comp = [r for r in val if r.itens_cotados == n]
        if comp:
            v = min(comp, key=lambda r: (r.total_final, -r.itens_baratos))
            return v, f"Cobertura total ({n}/{n}) — Total R$ {self._f(v.total_final)}", ""
        mc = max(r.itens_cotados for r in val)
        top = [r for r in val if r.itens_cotados == mc]
        v = min(top, key=lambda r: (r.total_final, -r.itens_baratos))
        return v, f"Maior cobertura ({mc}/{n})", "⚠️  Nenhum fornecedor cotou todos os itens. Negocie os itens faltantes."

    def _atualizar_dashboard(self):
        res = self._calcular_res()
        v, mot, obs = self._vencedor(res)
        if v is None:
            self._lbl_ven.setText("—"); self._lbl_mot.setText(mot)
            self._btn_ven.setEnabled(False); self._btn_ii.setEnabled(False); return
        self._venc_idx = v.idx; self._resultados = res
        cor = CORES_EMPRESA.get(v.nome.upper(), RED)
        self._lbl_ven.setText(v.nome.upper())
        self._lbl_ven.setStyleSheet(f"font-size:22px;font-weight:bold;color:{cor};background:transparent;")
        self._lbl_mot.setText(mot)
        self._frame_ven.setStyleSheet(f"QFrame{{background:#F8FFFE;border-radius:10px;border-left:5px solid {cor};border-top:1px solid #DDD;border-right:1px solid #DDD;border-bottom:1px solid #DDD;}}")
        for fi, r in enumerate(res):
            c = self._cards[fi]
            for obj,val in [(f"cn_{fi}",r.nome),(f"cs_{fi}",r.status(len(self._itens))),
                            (f"ci_{fi}",f"{r.itens_cotados}/{len(self._itens)}"),
                            (f"cb_{fi}",str(r.itens_baratos)),(f"ct_{fi}",f"R$ {self._f(r.total_final)}")]:
                lb = c.findChild(QLabel, obj)
                if lb: lb.setText(val)
            c.setStyleSheet(f"QFrame{{background:{'#F0FFF4' if fi==v.idx else '#F8F8F8'};border-radius:8px;border:{'2px solid '+cor if fi==v.idx else '1px solid #E0E0E0'};}}")
        self._lbl_obs.setText(obs); self._lbl_obs.setVisible(bool(obs))
        self._btn_ven.setEnabled(True); self._btn_ii.setEnabled(True)
        self._atualizar_totais()

    # ══════════════════════════════════════════════════════════════════════════
    # GERAR PEDIDO
    # ══════════════════════════════════════════════════════════════════════════

    def _gerar_pedido(self):
        if not hasattr(self,'_venc_idx'): return
        fi = self._venc_idx; nome = self._e_forn[fi].text().strip()
        if not nome: QMessageBox.warning(self,"Atenção","Preencha o nome do fornecedor vencedor."); return
        itens = [{"descricao":it.descricao,"quantidade":it.quantidade,"unidade":it.unidade,
                  "valor_unitario":it.precos[fi],"valor_total":it.subtotal(fi)}
                 for it in self._itens if it.subtotal(fi) is not None]
        if not itens: QMessageBox.warning(self,"Atenção",f"'{nome}' não tem preços preenchidos."); return
        self._abrir_form(nome, itens)

    def _gerar_item_item(self):
        if not hasattr(self,'_resultados'): return
        grupos = {}
        for it in self._itens:
            mi = it.melhor_idx()
            if mi is not None: grupos.setdefault(mi,[]).append(it)
        if not grupos: QMessageBox.warning(self,"Atenção","Nenhum item com preço preenchido."); return
        nomes = [e.text().strip() or f"Fornecedor {i+1}" for i,e in enumerate(self._e_forn)]
        msg = "Serão gerados pedidos para:\n\n" + "\n".join(f"• {nomes[fi]}: {len(its)} item(s)" for fi,its in grupos.items()) + "\n\nContinuar?"
        if QMessageBox.question(self,"Confirmar",msg,QMessageBox.Yes|QMessageBox.No) != QMessageBox.Yes: return
        for fi, its in grupos.items():
            itens = [{"descricao":it.descricao,"quantidade":it.quantidade,"unidade":it.unidade,
                      "valor_unitario":it.precos[fi],"valor_total":it.subtotal(fi)}
                     for it in its if it.subtotal(fi) is not None]
            if itens: self._abrir_form(nomes[fi], itens)

    def _abrir_form(self, fornecedor, itens):
        obra = self._cb_obra.currentText(); obra = "" if obra.startswith("—") else obra
        emp  = self._cb_emp.currentText()
        try:
            mw = self.window()
            if hasattr(mw,'_pages') and 'pedido' in mw._pages:
                pw = mw._pages['pedido']
                if hasattr(pw,'preencher_da_cotacao'):
                    pw.preencher_da_cotacao(fornecedor=fornecedor, obra=obra, empresa=emp, itens=itens)
                    if hasattr(mw,'_nav'): mw._nav('pedido')
                    QMessageBox.information(self,"Formulário preenchido!",
                        f"✅  Pedido para <b>{fornecedor}</b> pré-preenchido.<br>Revise na aba <b>Pedido de Compra</b>.")
                    return
        except Exception as e: print(f"[Cotação] {e}")
        QMessageBox.information(self,"Pronto",
            f"Fornecedor: {fornecedor}\nObra: {obra or '—'}\nItens: {len(itens)}\n\nVá para Pedido de Compra.")

    # ══════════════════════════════════════════════════════════════════════════
    # PDF
    # ══════════════════════════════════════════════════════════════════════════

    def _importar_pdf(self, fi):
        nome = self._e_forn[fi].text().strip() or f"Fornecedor {fi+1}"
        cam, _ = QFileDialog.getOpenFileName(self, f"Orçamento — {nome}",
                                              os.path.expanduser("~"), "PDF (*.pdf)")
        if not cam: return
        self._progress = QProgressDialog("Lendo PDF...", None, 0, 0, self)
        self._progress.setWindowTitle("Importando orçamento")
        self._progress.setWindowModality(Qt.WindowModal)
        self._progress.setMinimumWidth(320); self._progress.setMinimumDuration(0)
        self._progress.setValue(0); self._progress.show(); QApplication.processEvents()

        self._thr = PDFExtractorThread(cam, fi)
        self._thr.progresso.connect(lambda m: self._progress.setLabelText(m))
        self._thr.resultado.connect(lambda its: self._pdf_ok(its, fi, nome))
        self._thr.texto_extraido.connect(lambda txt: self._pdf_visual(txt, fi, nome))
        self._thr.erro.connect(self._pdf_err)
        self._thr.finished.connect(lambda: self._progress.close() if self._progress else None)
        self._thr.start()

    def _pdf_ok(self, itens, fi, nome):
        self._progress.close()
        prev = "\n".join(f"  • {it['descricao'][:45]}  {it['quantidade']} {it['unidade']}  R$ {it['preco_unitario']:.2f}" for it in itens[:8])
        if len(itens)>8: prev += f"\n  ... e mais {len(itens)-8} itens"
        if QMessageBox.question(self, f"✅  {len(itens)} itens detectados",
                f"<b>{nome}</b><br><br>Encontrei <b>{len(itens)} itens</b>.<br>"
                f"<pre style='font-size:10px;'>{prev}</pre><br>Aplicar na cotação?",
                QMessageBox.Yes|QMessageBox.No, QMessageBox.Yes) != QMessageBox.Yes: return
        while len(self._itens) < len(itens): self._itens.append(ItemCotacao())
        for i, it in enumerate(itens):
            item = self._itens[i]
            if not item.descricao:
                item.descricao=str(it.get("descricao","")).upper()
                item.quantidade=float(it.get("quantidade") or 1)
                item.unidade=str(it.get("unidade","UNID.")).upper()
            item.precos[fi] = float(it.get("preco_unitario") or 0)
        self._rebuild(); self._atualizar_dashboard()
        QMessageBox.information(self,"Importado!",f"✅  {len(itens)} itens aplicados.\nRevise e clique em ⚡ Calcular.")

    def _pdf_visual(self, texto, fi, nome):
        self._progress.close()
        QMessageBox.information(self,"Modo Visual",
            f"<b>{nome}</b><br><br>Não detectei padrão automático.<br>"
            f"Abrindo Modo Visual: veja o orçamento à esquerda e preencha os preços à direita.",
            QMessageBox.Ok)
        dlg = PDFVisualDialog(texto, fi, nome, self._itens, self)
        if dlg.exec() == QDialog.Accepted:
            for i, p in dlg.precos.items():
                if i < len(self._itens) and p: self._itens[i].precos[fi] = p
            self._rebuild(); self._atualizar_dashboard()

    def _pdf_err(self, msg):
        if self._progress: self._progress.close()
        QMessageBox.warning(self, "Erro na importação", msg)

    # ══════════════════════════════════════════════════════════════════════════
    # NOVA COTAÇÃO
    # ══════════════════════════════════════════════════════════════════════════

    def _nova_cotacao(self):
        if QMessageBox.question(self,"Nova cotação","Deseja limpar todos os dados?",
                QMessageBox.Yes|QMessageBox.No, QMessageBox.No) != QMessageBox.Yes: return
        self._itens = []
        for e in self._e_forn: e.clear()
        for e in self._e_frete: e.setText("0,00")
        for e in self._e_desc:  e.setText("0,00")
        self._fretes=[0.0,0.0,0.0]; self._descontos=[0.0,0.0,0.0]
        self._lbl_ven.setText("—"); self._lbl_mot.setText("Preencha os preços e clique em Calcular")
        self._btn_ven.setEnabled(False); self._btn_ii.setEnabled(False)
        self._adicionar_item()

    # ══════════════════════════════════════════════════════════════════════════
    # HELPERS
    # ══════════════════════════════════════════════════════════════════════════

    @staticmethod
    def _vsep():
        s = QFrame(); s.setFrameShape(QFrame.VLine)
        s.setStyleSheet("background:#CCC;border:none;"); s.setFixedWidth(1); s.setFixedHeight(38); return s

    @staticmethod
    def _pn(txt):
        if not txt: return None
        try: return float(str(txt).replace("R$","").replace(" ","").replace(".","").replace(",","."))
        except: return None

    @staticmethod
    def _f(v):
        try: return f"{float(v):,.2f}".replace(",","X").replace(".",",").replace("X",".")
        except: return "0,00"

    @staticmethod
    def _fb(v):
        try: return f"{float(v):,.2f}".replace(",","X").replace(".",",").replace("X",".")
        except: return ""

    @staticmethod
    def _fn(v):
        try:
            f = float(v)
            return str(int(f)) if f==int(f) else f"{f:.3f}".rstrip("0")
        except: return "1"

    def showEvent(self, e):
        super().showEvent(e)
        QTimer.singleShot(0, self._carregar_obras)
