"""
app/ui/widgets/pedidos_widget.py

Aba "Pedidos Gerados" — visual moderno no padrão Brasul.
"""

import os, sys, subprocess, shutil
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QFileDialog, QLineEdit, QFrame, QGraphicsDropShadowEffect,
    QMenu, QDateEdit, QDialog, QDialogButtonBox,
)
from PySide6.QtCore import Qt, QTimer, QDate
from PySide6.QtGui import QColor, QFont, QAction

from config import PEDIDOS_DIR

RED   = "#C0392B"
GRAY  = "#2C2C2C"
WHITE = "#FFFFFF"
BG    = "#F0EDED"
BDR   = "#D8CCCC"
TXT   = "#1A1A1A"
TXT_S = "#6B5555"
SEL   = "#FADBD8"
HOV   = "#FEF0EF"
GREEN = "#1E8449"
BLUE  = "#2980B9"

CSS_BUSCA = f"""
    QLineEdit {{
        color:{TXT}; background:{WHITE};
        border:1.5px solid {BDR}; border-radius:6px;
        padding:4px 12px 4px 36px; font-size:12px; min-height:32px;
    }}
    QLineEdit:focus {{ border:1.5px solid {RED}; background:#FFFBFB; }}
"""

CSS_TABLE = f"""
    QTableWidget {{
        background:{WHITE}; border:none;
        font-size:12px; color:{TXT};
        selection-background-color:{SEL}; selection-color:{GRAY};
        outline:none; gridline-color:transparent;
    }}
    QTableWidget::item {{
        padding:0px 12px;
        border-bottom:1px solid #F0E8E8;
    }}
    QTableWidget::item:hover    {{ background:{HOV}; }}
    QTableWidget::item:selected {{ background:{SEL}; color:{GRAY}; }}
    QHeaderView {{ background:{WHITE}; }}
    QHeaderView::section {{
        background:{WHITE}; color:{TXT_S}; font-size:10px;
        font-weight:bold; padding:10px 12px;
        border:none; border-bottom:2px solid #E8DEDE;
    }}
    QScrollBar:vertical {{
        background:transparent; width:6px; border-radius:3px; margin:0;
    }}
    QScrollBar::handle:vertical {{
        background:#D8CCCC; border-radius:3px; min-height:30px;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}
"""


def _btn(texto, cor, h=34):
    b = QPushButton(texto); b.setFixedHeight(h)
    b.setCursor(Qt.PointingHandCursor)
    b.setStyleSheet(f"""
        QPushButton {{
            background:{cor}; color:white; font-size:11px;
            font-weight:bold; border-radius:6px; border:none; padding:0 16px;
        }}
        QPushButton:hover   {{ background:{cor}DD; }}
        QPushButton:pressed {{ background:{cor}AA; }}
    """)
    return b


def _btn_outline(texto, h=34):
    b = QPushButton(texto); b.setFixedHeight(h)
    b.setCursor(Qt.PointingHandCursor)
    b.setStyleSheet(f"""
        QPushButton {{
            background:transparent; color:{TXT_S}; font-size:11px;
            font-weight:600; border-radius:6px;
            border:1.5px solid {BDR}; padding:0 14px;
        }}
        QPushButton:hover   {{ background:{HOV}; color:{RED}; border-color:{RED}; }}
        QPushButton:pressed {{ background:{SEL}; }}
    """)
    return b


class PedidosWidget(QWidget):

    def __init__(self):
        super().__init__()
        self._todos         = []
        self._filtro_ativo  = None
        self._data_inicio   = None
        self._data_fim      = None
        self._build()
        self._carregar()

    def _build(self):
        self.setStyleSheet(f"background:{BG};")
        vl = QVBoxLayout(self)
        vl.setContentsMargins(24, 20, 24, 20)
        vl.setSpacing(16)

        # Cabeçalho
        hl_topo = QHBoxLayout()
        tv = QVBoxLayout(); tv.setSpacing(2)
        titulo = QLabel("Pedidos Gerados")
        titulo.setStyleSheet(f"font-size:20px; font-weight:bold; color:{GRAY}; background:transparent;")
        sub = QLabel("Histórico de PDFs gerados pelo sistema")
        sub.setStyleSheet(f"font-size:11px; color:{TXT_S}; background:transparent;")
        tv.addWidget(titulo); tv.addWidget(sub)
        hl_topo.addLayout(tv); hl_topo.addStretch()
        btn_pasta = _btn_outline("📂  Abrir Pasta")
        btn_pasta.setToolTip("Abre a pasta pedidos_gerados/ no Explorer")
        btn_pasta.clicked.connect(self._abrir_pasta_gerados)
        hl_topo.addWidget(btn_pasta)
        btn_att = _btn("↻  Atualizar", "#95A5A6")
        btn_att.clicked.connect(self._carregar)
        hl_topo.addWidget(btn_att)
        vl.addLayout(hl_topo)

        # Cards resumo
        cards_row = QHBoxLayout(); cards_row.setSpacing(14)
        self._card_total = self._make_card("TOTAL DE PEDIDOS", "—", RED)
        self._card_hoje  = self._make_card("GERADOS HOJE", "—", BLUE)
        cards_row.addWidget(self._card_total)
        cards_row.addWidget(self._card_hoje)
        cards_row.addStretch()
        vl.addLayout(cards_row)

        # Barra busca + filtro data
        hl_busca = QHBoxLayout(); hl_busca.setSpacing(10)

        busca_wrap = QWidget(); busca_wrap.setFixedHeight(36); busca_wrap.setMaximumWidth(380)
        bwl = QHBoxLayout(busca_wrap); bwl.setContentsMargins(0,0,0,0); bwl.setSpacing(0)
        self.e_busca = QLineEdit()
        self.e_busca.setPlaceholderText("Buscar por nº, obra ou fornecedor...")
        self.e_busca.setStyleSheet(CSS_BUSCA)
        self.e_busca.textChanged.connect(self._aplicar_filtros)
        bwl.addWidget(self.e_busca)
        ico = QLabel("🔍"); ico.setStyleSheet("background:transparent; font-size:13px; border:none;")
        ico.setFixedWidth(28); ico.setParent(busca_wrap); ico.move(8, 9); ico.raise_()
        hl_busca.addWidget(busca_wrap)

        # Botões de filtro rápido de data
        self._filtro_ativo = None  # None = todos
        self._btn_filtros = {}
        for chave, rotulo in [("hoje","Hoje"), ("semana","Esta semana"), ("mes","Este mês"), ("todos","Todos")]:
            b = QPushButton(rotulo)
            b.setFixedHeight(34)
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setStyleSheet(f"""
                QPushButton {{
                    background:{WHITE}; color:{TXT_S}; font-size:11px;
                    font-weight:600; border-radius:6px;
                    border:1.5px solid {BDR}; padding:0 14px;
                }}
                QPushButton:hover   {{ background:{HOV}; color:{RED}; border-color:{RED}; }}
                QPushButton:checked {{
                    background:{RED}; color:white;
                    border:1.5px solid {RED}; font-weight:bold;
                }}
            """)
            b.clicked.connect(lambda _, k=chave: self._set_filtro_data(k))
            hl_busca.addWidget(b)
            self._btn_filtros[chave] = b

        # Botão período personalizado
        btn_periodo = QPushButton("📅  Período")
        btn_periodo.setFixedHeight(34)
        btn_periodo.setCursor(Qt.PointingHandCursor)
        btn_periodo.setStyleSheet(f"""
            QPushButton {{
                background:{WHITE}; color:{TXT_S}; font-size:11px;
                font-weight:600; border-radius:6px;
                border:1.5px solid {BDR}; padding:0 14px;
            }}
            QPushButton:hover {{ background:{HOV}; color:{RED}; border-color:{RED}; }}
        """)
        btn_periodo.clicked.connect(self._filtro_periodo_custom)
        hl_busca.addWidget(btn_periodo)

        hl_busca.addStretch()
        self._lbl_cont = QLabel("")
        self._lbl_cont.setStyleSheet(f"font-size:11px; color:{TXT_S}; background:transparent;")
        hl_busca.addWidget(self._lbl_cont)
        vl.addLayout(hl_busca)

        # Label de período ativo
        self._lbl_filtro_ativo = QLabel("")
        self._lbl_filtro_ativo.setVisible(False)
        self._lbl_filtro_ativo.setStyleSheet(f"""
            font-size:11px; color:{RED}; background:#FEF0EF;
            border:1px solid #F5C6C0; border-radius:5px;
            padding:4px 12px; background:transparent;
        """)
        vl.addWidget(self._lbl_filtro_ativo)

        # Tabela dentro de card com sombra
        container = QFrame()
        container.setStyleSheet(f"QFrame {{ background:{WHITE}; border-radius:12px; border:1px solid #EEE5E5; }}")
        sombra = QGraphicsDropShadowEffect()
        sombra.setBlurRadius(16); sombra.setOffset(0, 2); sombra.setColor(QColor(0,0,0,18))
        container.setGraphicsEffect(sombra)
        cvl = QVBoxLayout(container); cvl.setContentsMargins(0,0,0,0); cvl.setSpacing(0)

        self.tabela = QTableWidget(0, 6)
        self.tabela.setHorizontalHeaderLabels(["Nº", "Data", "Obra", "Fornecedor", "Empresa", "Ações"])
        self.tabela.setStyleSheet(CSS_TABLE)
        self.tabela.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabela.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabela.verticalHeader().setVisible(False)
        self.tabela.setShowGrid(False)
        self.tabela.setFrameShape(QFrame.NoFrame)
        hh = self.tabela.horizontalHeader()
        hh.setHighlightSections(False)
        hh.setSectionResizeMode(0, QHeaderView.Fixed);    self.tabela.setColumnWidth(0, 70)
        hh.setSectionResizeMode(1, QHeaderView.Fixed);    self.tabela.setColumnWidth(1, 95)
        hh.setSectionResizeMode(2, QHeaderView.Stretch)
        hh.setSectionResizeMode(3, QHeaderView.Stretch)
        hh.setSectionResizeMode(4, QHeaderView.Fixed);    self.tabela.setColumnWidth(4, 115)
        hh.setSectionResizeMode(5, QHeaderView.Fixed);    self.tabela.setColumnWidth(5, 195)
        cvl.addWidget(self.tabela)
        vl.addWidget(container, 1)

        rodape = QLabel(f"📌  {PEDIDOS_DIR}")
        rodape.setStyleSheet(f"font-size:10px; color:{TXT_S}; background:transparent;")
        rodape.setWordWrap(True)
        vl.addWidget(rodape)

    def _make_card(self, titulo, valor, cor):
        card = QFrame(); card.setFixedHeight(72); card.setMinimumWidth(170); card.setMaximumWidth(210)
        card.setStyleSheet(f"""
            QFrame {{
                background:{WHITE}; border-radius:10px;
                border-left:4px solid {cor};
                border-top:1px solid #EEE5E5;
                border-right:1px solid #EEE5E5;
                border-bottom:1px solid #EEE5E5;
            }}
        """)
        vl = QVBoxLayout(card); vl.setContentsMargins(14,10,14,10); vl.setSpacing(3)
        lt = QLabel(titulo); lt.setStyleSheet(f"font-size:9px; font-weight:700; color:{TXT_S}; background:transparent; border:none; letter-spacing:1px;")
        lv = QLabel(valor);  lv.setStyleSheet(f"font-size:22px; font-weight:bold; color:{cor}; background:transparent; border:none;")
        lv.setObjectName("card_val")
        vl.addWidget(lt); vl.addWidget(lv)
        return card

    def _carregar(self):
        self._todos = []
        os.makedirs(PEDIDOS_DIR, exist_ok=True)

        # Carrega dados do banco de uma vez (número → fornecedor, valor)
        db_dados = {}
        try:
            from app.data.database import get_connection
            with get_connection() as conn:
                rows = conn.execute(
                    "SELECT numero, fornecedor_nome, valor_total, obra_nome FROM pedidos"
                ).fetchall()
                for row in rows:
                    db_dados[str(row["numero"])] = {
                        "fornecedor": row["fornecedor_nome"] or "—",
                        "valor":      row["valor_total"] or 0.0,
                        "obra_db":    row["obra_nome"] or "",
                    }
        except Exception as e:
            print(f"[PedidosWidget] Aviso ao consultar banco: {e}")

        for nome in sorted(os.listdir(PEDIDOS_DIR), reverse=True):
            if not nome.lower().endswith(".pdf"):
                continue
            caminho = os.path.join(PEDIDOS_DIR, nome)
            try:
                stat = os.stat(caminho)
                data_mod = datetime.fromtimestamp(stat.st_mtime)
            except OSError:
                continue
            empresa, numero, obra = self._parse_nome(nome)

            extra = db_dados.get(numero, {})
            fornecedor = extra.get("fornecedor", "—")
            obra_db    = extra.get("obra_db", "")
            if obra_db: obra = obra_db  # banco é mais confiável que nome do arquivo

            self._todos.append({
                "nome":       nome,
                "caminho":    caminho,
                "numero":     numero,
                "obra":       obra,
                "fornecedor": fornecedor,
                "empresa":    empresa,
                "data":       data_mod,
            })
        self._preencher_tabela(self._todos)
        self._atualizar_cards()

    def _parse_nome(self, nome):
        base   = nome.replace(".pdf","").replace(".PDF","")
        partes = base.split("-")
        numero = partes[1] if len(partes) > 1 else "—"
        empresa = "—"; obra = "—"
        for emp in ["INTERBRAS","INTERIORANA","BRASUL","B&B","JB"]:
            if emp in base.upper():
                empresa = emp
                idx  = base.upper().find(emp)
                rest = base[idx+len(emp):].lstrip("-_")
                obra = rest.replace("_"," ").strip() or "—"
                break
        return empresa, numero, obra

    def _set_filtro_data(self, chave):
        """Ativa um filtro de data rápido e atualiza os botões."""
        self._filtro_ativo = None if chave == "todos" else chave
        self._data_inicio  = None
        self._data_fim     = None
        for k, b in self._btn_filtros.items():
            b.setChecked(k == chave)
        self._lbl_filtro_ativo.setVisible(False)
        self._aplicar_filtros()

    def _filtro_periodo_custom(self):
        """Abre diálogo para escolher período personalizado."""
        dlg = QDialog(self)
        dlg.setWindowTitle("Filtrar por período")
        dlg.setMinimumWidth(320)
        dlg.setStyleSheet(f"background:{WHITE}; color:{TXT};")
        vl = QVBoxLayout(dlg); vl.setSpacing(12); vl.setContentsMargins(20,20,20,20)

        hoje = QDate.currentDate()

        hl1 = QHBoxLayout()
        lbl_de = QLabel("De:")
        lbl_de.setStyleSheet(f"font-size:12px; color:{TXT}; min-width:30px;")
        self._de = QDateEdit(hoje.addDays(-30))
        self._de.setCalendarPopup(True)
        self._de.setDisplayFormat("dd/MM/yyyy")
        self._de.setStyleSheet(f"""
            QDateEdit {{
                border:1.5px solid {BDR}; border-radius:5px;
                padding:4px 8px; font-size:12px; min-height:30px;
                background:{WHITE}; color:{TXT};
            }}
        """)
        hl1.addWidget(lbl_de); hl1.addWidget(self._de)

        hl2 = QHBoxLayout()
        lbl_ate = QLabel("Até:")
        lbl_ate.setStyleSheet(f"font-size:12px; color:{TXT}; min-width:30px;")
        self._ate = QDateEdit(hoje)
        self._ate.setCalendarPopup(True)
        self._ate.setDisplayFormat("dd/MM/yyyy")
        self._ate.setStyleSheet(self._de.styleSheet())
        hl2.addWidget(lbl_ate); hl2.addWidget(self._ate)

        vl.addLayout(hl1); vl.addLayout(hl2)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(dlg.accept); bb.rejected.connect(dlg.reject)
        bb.button(QDialogButtonBox.Ok).setStyleSheet(
            f"background:{RED}; color:white; font-weight:bold;"
            f"padding:6px 20px; border-radius:5px; border:none;")
        vl.addWidget(bb)

        if dlg.exec() != QDialog.Accepted:
            return

        self._filtro_ativo = "custom"
        self._data_inicio  = self._de.date().toPython()
        self._data_fim     = self._ate.date().toPython()

        # Desmarca todos os botões rápidos
        for b in self._btn_filtros.values(): b.setChecked(False)

        label = (f"Período: {self._data_inicio.strftime('%d/%m/%Y')} "
                 f"→ {self._data_fim.strftime('%d/%m/%Y')}")
        self._lbl_filtro_ativo.setText(f"📅  {label}   "
            f"<a href='#' style='color:{RED};'>✕ Limpar</a>")
        self._lbl_filtro_ativo.setVisible(True)
        self._lbl_filtro_ativo.linkActivated.connect(
            lambda _: self._set_filtro_data("todos"))
        self._aplicar_filtros()

    def _aplicar_filtros(self):
        """Aplica busca por texto E filtro de data simultaneamente."""
        from datetime import timedelta
        termo = self.e_busca.text().strip().lower()
        hoje  = datetime.now().date()

        resultado = self._todos

        # Filtro de texto
        if termo:
            resultado = [r for r in resultado if
                         termo in r["nome"].lower() or
                         termo in r["numero"].lower() or
                         termo in r["obra"].lower() or
                         termo in r.get("fornecedor","").lower()]

        # Filtro de data
        if self._filtro_ativo == "hoje":
            resultado = [r for r in resultado if r["data"].date() == hoje]
        elif self._filtro_ativo == "semana":
            inicio = hoje - timedelta(days=hoje.weekday())
            resultado = [r for r in resultado if r["data"].date() >= inicio]
        elif self._filtro_ativo == "mes":
            resultado = [r for r in resultado if
                         r["data"].year == hoje.year and
                         r["data"].month == hoje.month]
        elif self._filtro_ativo == "custom" and self._data_inicio and self._data_fim:
            resultado = [r for r in resultado if
                         self._data_inicio <= r["data"].date() <= self._data_fim]

        self._preencher_tabela(resultado)

    def _atualizar_cards(self):
        total = len(self._todos)
        hoje  = datetime.now().date()
        hoje_n = sum(1 for r in self._todos if r["data"].date() == hoje)
        for lv in self._card_total.findChildren(QLabel):
            if lv.objectName() == "card_val": lv.setText(str(total))
        for lv in self._card_hoje.findChildren(QLabel):
            if lv.objectName() == "card_val": lv.setText(str(hoje_n))

    def _preencher_tabela(self, registros):
        self.tabela.setRowCount(0)
        cores_emp = {"BRASUL":RED,"JB":"#A93226","B&B":"#1E8449","INTERIORANA":"#784212","INTERBRAS":"#1A5276"}

        for dados in registros:
            r = self.tabela.rowCount()
            self.tabela.insertRow(r)
            self.tabela.setRowHeight(r, 48)
            bg = WHITE if r % 2 == 0 else "#FBF7F7"

            def _it(txt, align=Qt.AlignVCenter|Qt.AlignLeft, bold=False, cor=None):
                it = QTableWidgetItem(str(txt)); it.setTextAlignment(align)
                it.setBackground(QColor(bg))
                if bold: f = QFont(); f.setBold(True); it.setFont(f)
                if cor:  it.setForeground(QColor(cor))
                return it

            self.tabela.setItem(r, 0, _it(f"#{dados['numero']}", Qt.AlignVCenter|Qt.AlignCenter, bold=True, cor=RED))
            self.tabela.setItem(r, 1, _it(dados["data"].strftime("%d/%m/%Y"), Qt.AlignVCenter|Qt.AlignCenter, cor=TXT_S))
            self.tabela.setItem(r, 2, _it(dados["obra"], bold=True))
            self.tabela.setItem(r, 3, _it(dados.get("fornecedor", "—"), cor=TXT_S))
            cor_e = cores_emp.get(dados["empresa"], TXT_S)
            self.tabela.setItem(r, 4, _it(dados["empresa"], Qt.AlignVCenter|Qt.AlignCenter, bold=True, cor=cor_e))

            cell = QWidget(); cell.setStyleSheet(f"background:{bg};")
            hl = QHBoxLayout(cell); hl.setContentsMargins(8,6,8,6); hl.setSpacing(8)
            ba = _btn("📄 Abrir", BLUE, h=30)
            ba.setToolTip("Abre o PDF no visualizador padrão")
            p = dados["caminho"]
            ba.clicked.connect(lambda _, x=p: self._abrir_pdf(x))
            hl.addWidget(ba)
            be = _btn("💾 Exportar", GREEN, h=30)
            be.setToolTip("Salva uma cópia em outra pasta")
            n = dados["nome"]
            be.clicked.connect(lambda _, x=p, y=n: self._exportar(x, y))
            hl.addWidget(be)
            self.tabela.setCellWidget(r, 5, cell)

        total = len(registros)
        self._lbl_cont.setText(f"{total} pedido{'s' if total!=1 else ''}")

        if total == 0:
            self.tabela.setRowCount(1); self.tabela.setSpan(0,0,1,6)
            it = QTableWidgetItem("Nenhum pedido encontrado. Gere um pedido na aba 'Pedido de Compra'.")
            it.setTextAlignment(Qt.AlignCenter); it.setForeground(QColor(TXT_S))
            self.tabela.setItem(0, 0, it)

    def _abrir_pdf(self, caminho):
        try:
            if sys.platform == "win32":    os.startfile(caminho)
            elif sys.platform == "darwin": subprocess.run(["open", caminho])
            else:                          subprocess.run(["xdg-open", caminho])
        except Exception as e:
            QMessageBox.warning(self, "Erro ao abrir", str(e))

    def _exportar(self, caminho_origem, nome_arquivo):
        pasta = QFileDialog.getExistingDirectory(
            self, "Escolha a pasta onde salvar a cópia do PDF",
            os.path.expanduser("~"),
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks)
        if not pasta: return
        destino = os.path.join(pasta, nome_arquivo)
        if os.path.exists(destino):
            resp = QMessageBox.question(self, "Arquivo já existe",
                f"Já existe:\n{nome_arquivo}\n\nDeseja substituir?",
                QMessageBox.Yes|QMessageBox.No, QMessageBox.No)
            if resp != QMessageBox.Yes: return
        try:
            shutil.copy2(caminho_origem, destino)
            msg = QMessageBox(self)
            msg.setWindowTitle("Exportado!")
            msg.setText(f"<b>{nome_arquivo}</b><br><br>Salvo em:<br><code>{destino}</code>")
            msg.setIcon(QMessageBox.Information)
            b_ab = msg.addButton("📂 Abrir pasta", QMessageBox.ActionRole)
            msg.addButton("OK", QMessageBox.AcceptRole); msg.exec()
            if msg.clickedButton() == b_ab: self._abrir_pasta(pasta)
        except Exception as e:
            QMessageBox.critical(self, "Erro ao exportar", str(e))

    def _abrir_pasta(self, pasta):
        try:
            if sys.platform == "win32":    os.startfile(pasta)
            elif sys.platform == "darwin": subprocess.run(["open", pasta])
            else:                          subprocess.run(["xdg-open", pasta])
        except Exception: pass

    def _abrir_pasta_gerados(self):
        os.makedirs(PEDIDOS_DIR, exist_ok=True)
        self._abrir_pasta(PEDIDOS_DIR)

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self._carregar)
