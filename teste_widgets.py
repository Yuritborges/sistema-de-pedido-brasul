from app.data.database import init_db 
from PySide6.QtWidgets import QApplication 
import sys 
init_db() 
app = QApplication(sys.argv) 
print('Carregando PedidoWidget...') 
from app.ui.widgets.formulario_pedido import PedidoWidget 
w = PedidoWidget() & print('PedidoWidget OK') 
print('Carregando PedidosWidget...') 
from app.ui.widgets.pedidos_widget import PedidosWidget 
w = PedidosWidget() & print('PedidosWidget OK') 
print('Carregando CotacaoWidget...') 
from app.ui.widgets.cotacao_widget import CotacaoWidget 
w = CotacaoWidget() & print('CotacaoWidget OK') 
print('Carregando ObrasWidget...') 
from app.ui.widgets.obras_widget import ObrasWidget 
w = ObrasWidget() & print('ObrasWidget OK') 
print('Carregando HistoricoWidget...') 
from app.ui.widgets.historico_widget import HistoricoWidget 
w = HistoricoWidget() & print('HistoricoWidget OK') 
print('Tudo OK!') 
