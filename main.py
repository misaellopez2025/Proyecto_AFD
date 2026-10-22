"""AFD Studio: native Python desktop application with a live Graphviz diagram."""
import copy
import html
from pathlib import Path
import sys
sys.dont_write_bytecode = True

from PySide6.QtCore import QRectF, QSignalBlocker, QStringListModel, Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QColor, QDesktopServices, QFont, QFontMetrics, QKeySequence, QPainter, QPainterPath, QRegion
from PySide6.QtWidgets import (
    QApplication, QAbstractItemView, QBoxLayout, QCompleter, QFileDialog, QFrame,
    QGraphicsDropShadowEffect, QGridLayout, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QMainWindow, QMenu, QMessageBox, QPlainTextEdit, QPushButton,
    QScrollArea, QSizePolicy, QStyledItemDelegate, QStyle, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)
from afd_core import DEFAULT_AFD, EXAMPLES, parse_txt, serialize, trace, validate, word_group
from diagram import AutomatonView, GraphvizError, calculate_layout, find_dot
from theme import COLORS, STYLE
from ui_components import Background, DerivationList, FlowLayout, ModalOverlay, label, restyle

APP_DIR = Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent))
MANUAL_PDF = APP_DIR/'docs'/'Manual_de_usuario.pdf'

BLANK_AFD = ('nombre: Mi AFD\nestados: q0,q1\nalfabeto: a,b\ninicial: q0\n'
             'finales: q1\ntransiciones:\nq0,a,q1\nq0,b,q0\nq1,a,q1\nq1,b,q0\ncadenas:\nab\na\n')


def button(text,command,primary=False):
    item = QPushButton(text); item.setCursor(Qt.CursorShape.PointingHandCursor)
    if primary: item.setObjectName('primary')
    item.clicked.connect(command)
    if primary:
        effect = QGraphicsDropShadowEffect(item); effect.setBlurRadius(16); effect.setOffset(0,7)
        effect.setColor(QColor(29,29,31,35)); item.setGraphicsEffect(effect)
    return item


def panel():
    item = QFrame(); item.setObjectName('panel')
    effect = QGraphicsDropShadowEffect(item); effect.setBlurRadius(50); effect.setOffset(0,22)
    effect.setColor(QColor(29,29,31,24)); item.setGraphicsEffect(effect)
    layout = QVBoxLayout(item); layout.setContentsMargins(25,25,25,25); layout.setSpacing(0)
    return item,layout


class TableDelegate(QStyledItemDelegate):
    def paint(self,painter,option,index):
        self.initStyleOption(option,index)
        active = index.data(Qt.ItemDataRole.UserRole) == 'active'
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        painter.save()
        painter.fillRect(option.rect,QColor(COLORS['active' if active else 'selected' if selected else 'panel']))
        if index.row() < index.model().rowCount()-1:
            painter.setPen(QColor(COLORS['line'])); painter.drawLine(option.rect.bottomLeft(),option.rect.bottomRight())
        foreground = index.data(Qt.ItemDataRole.ForegroundRole)
        painter.setPen(QColor(COLORS['active_text']) if active else foreground.color() if foreground else QColor(COLORS['text']))
        font = option.font; font.setPixelSize(13); painter.setFont(font)
        rect = option.rect.adjusted(12,0,-12,0)
        text = option.fontMetrics.elidedText(option.text,Qt.TextElideMode.ElideRight,max(0,rect.width()))
        painter.drawText(rect,Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter,text)
        painter.restore()


class StudioTable(QTableWidget):
    def __init__(self,columns):
        super().__init__(0,len(columns)); self.setHorizontalHeaderLabels(columns)
        self.empty_message = ''; self._sizing = False; self._column_sizes = None

    def rebalance(self):
        if self._sizing: return
        self._sizing = True
        font = QFont('Segoe UI'); font.setPixelSize(13); metrics = QFontMetrics(font)
        header_font = QFont(font); header_font.setBold(True); header_metrics = QFontMetrics(header_font)
        sizes = self._column_sizes
        if sizes is None:
            sizes = []
            for col in range(self.columnCount()):
                header = self.horizontalHeaderItem(col)
                size = header_metrics.horizontalAdvance(header.text() if header else '')+24
                for row in range(self.rowCount()):
                    item = self.item(row,col)
                    if item: size = max(size,min(2000,metrics.horizontalAdvance(item.text())+24))
                sizes.append(max(24,size))
            self._column_sizes = sizes
        total = sum(sizes); available = self.viewport().width()
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        widths = sizes
        if total and available > total:
            widths = [int(size*available/total) for size in sizes]
            widths[-1] += available-sum(widths)
        for col,width in enumerate(widths): self.setColumnWidth(col,width)
        self._sizing = False

    def resizeEvent(self,event):
        super().resizeEvent(event); self.rebalance()
        clip = QPainterPath(); clip.addRoundedRect(QRectF(self.rect()),14,14)
        self.setMask(QRegion(clip.toFillPolygon().toPolygon()))

    def paintEvent(self,event):
        super().paintEvent(event)
        if not self.rowCount() and self.empty_message:
            painter = QPainter(self.viewport()); painter.setPen(QColor(COLORS['text']))
            font = QFont('Segoe UI'); font.setPixelSize(13); painter.setFont(font)
            painter.drawText(self.viewport().rect().adjusted(12,11,-12,-11),Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignTop,self.empty_message)


def table(columns):
    item = StudioTable(columns)
    item.verticalHeader().hide(); item.verticalHeader().setDefaultSectionSize(40)
    item.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter)
    item.horizontalHeader().setFixedHeight(40)
    item.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    item.horizontalHeader().setMinimumSectionSize(24)
    item.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    item.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    item.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    item.setShowGrid(False); item.setFrameShape(QFrame.Shape.NoFrame); item.setItemDelegate(TableDelegate(item))
    wrap = QFrame(); wrap.setObjectName('tableWrap')
    layout = QVBoxLayout(wrap); layout.setContentsMargins(1,1,1,1); layout.addWidget(item)
    return item,wrap


class Studio(QMainWindow):
    def __init__(self,initial_afd=None):
        super().__init__(); self.setWindowTitle('Simulador AFD')
        self.resize(1330,940); self.setMinimumSize(560,540); self.setStyleSheet(STYLE)
        self.afd = copy.deepcopy(DEFAULT_AFD if initial_afd is None else initial_afd); self.selected = 0; self.step = 0
        self.filename = 'automata.txt'; self._trace = None; self._trace_word = None
        self._graph_signature = None; self._compact = None; self._active_cell = None
        self._show_all_derivations = False
        self._traces = {}; self._word_indices = {}
        self._derivation_groups = {}; self._invalid_derivation_entries = {}; self._derivation_group = None
        self.editor_dialog = None
        self.timer = QTimer(self); self.timer.setInterval(650); self.timer.timeout.connect(self.tick)
        self.setup_ui(); self.load_afd(self.afd)

    def setup_ui(self):
        self.page_scroll = QScrollArea(); self.page_scroll.setObjectName('pageScroll')
        self.page_scroll.viewport().setObjectName('pageViewport')
        self.page_scroll.setWidgetResizable(True); self.page_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.page_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setCentralWidget(self.page_scroll)
        self.background = Background(); self.page_scroll.setWidget(self.background)
        outer = QHBoxLayout(self.background); outer.setContentsMargins(0,0,0,0); outer.setSpacing(0)
        outer.addStretch(); self.app_page = QWidget(); self.app_page.setObjectName('app'); self.app_page.setMaximumWidth(1330)
        self.page_layout = QVBoxLayout(self.app_page); self.page_layout.setContentsMargins(26,32,26,55); self.page_layout.setSpacing(16)
        outer.addWidget(self.app_page,1); outer.addStretch()

        self.header = QWidget(); self.header_layout = QBoxLayout(QBoxLayout.Direction.LeftToRight,self.header)
        self.header_layout.setContentsMargins(0,0,0,0); self.header_layout.setSpacing(15)
        brand = QWidget(); brand_layout = QVBoxLayout(brand); brand_layout.setContentsMargins(0,0,0,0); brand_layout.setSpacing(0)
        brand.setMinimumHeight(57)
        logo = label('AFD','logo'); brand_layout.addWidget(logo,0,Qt.AlignmentFlag.AlignTop)
        brand_layout.addStretch()
        self.header_layout.addWidget(brand,1)
        self.nav = QWidget(); nav_layout = QHBoxLayout(self.nav); nav_layout.setContentsMargins(0,0,0,0); nav_layout.setSpacing(7)
        self.actions = {}; self.example_actions = []; self.nav_buttons = []
        for title in ('Archivo','Ejemplos','Acerca de'):
            menu_button = QPushButton(title+' ▾'); menu_button.setObjectName('nav'); menu_button.setCursor(Qt.CursorShape.PointingHandCursor)
            menu = QMenu(menu_button); menu_button.setMenu(menu); nav_layout.addWidget(menu_button); self.nav_buttons.append(menu_button)
            if title == 'Archivo':
                for text,command,shortcut in [('Abrir TXT',self.open_file,'Ctrl+O'),('Nuevo',self.edit_afd,'Ctrl+E'),('Guardar TXT',self.save_file,'Ctrl+S'),('Salir',self.exit,'')]:
                    action = QAction(text,self); action.triggered.connect(command)
                    if shortcut: action.setShortcut(QKeySequence(shortcut)); self.addAction(action)
                    menu.addAction(action); self.actions[text] = action
                self.actions['Nuevo / Editar'] = self.actions['Nuevo']
            elif title == 'Ejemplos':
                for i,text in enumerate(('Termina en 11','Contiene ab','Número par de 1')):
                    action = menu.addAction(text); action.triggered.connect(lambda checked=False,i=i: self.try_load_example(i)); self.example_actions.append(action)
            else:
                menu.addAction('Acerca de',self.about); menu.addAction('Ayuda',self.help)
                menu.addAction('Manual de usuario (PDF)',self.open_manual)
        self.header_layout.addWidget(self.nav,0,Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignVCenter)
        self.page_layout.addWidget(self.header)

        self.grid_widget = QWidget(); self.grid = QGridLayout(self.grid_widget)
        self.grid.setContentsMargins(0,0,0,0); self.grid.setSpacing(20)
        self.diagram_panel,self.diagram_layout = panel()
        head = QHBoxLayout(); head.addWidget(label('Diagrama del autómata','heading')); head.addStretch()
        self.name = label('','pill'); self.name.setWordWrap(True); head.addWidget(self.name); self.diagram_layout.addLayout(head); self.diagram_layout.addSpacing(14)
        drawing_frame = QFrame(); drawing_frame.setObjectName('drawingFrame')
        drawing_layout = QVBoxLayout(drawing_frame); drawing_layout.setContentsMargins(1,1,1,1)
        self.canvas = AutomatonView(); self.canvas.setFixedHeight(368); drawing_layout.addWidget(self.canvas)
        self.diagram_layout.addWidget(drawing_frame)
        self.diagram_layout.addSpacing(12); self.info = label('','message'); self.info.setMinimumHeight(22); self.info.setWordWrap(True)
        self.diagram_layout.addWidget(self.info); self.diagram_layout.addSpacing(13)
        controls = FlowLayout()
        self.back = button('← Anterior',self.previous)
        self.next = button('Siguiente →',self.forward,True)
        self.play = button('▶ Reproducir',self.toggle_play)
        self.restart_button = button('Reiniciar',self.restart)
        for item in (self.back,self.next,self.play,self.restart_button): controls.addWidget(item)
        self.diagram_layout.addLayout(controls); self.diagram_layout.addSpacing(12)
        self.status = label('','status'); self.status.setWordWrap(True); self.diagram_layout.addWidget(self.status); self.diagram_layout.addStretch()
        self.play.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.play.customContextMenuRequested.connect(self.playback_menu)
        self.canvas.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.canvas.customContextMenuRequested.connect(self.diagram_menu)
        self.canvas.setToolTip('Rueda hacia arriba: acercar · Arrastrar: desplazar · Clic derecho: opciones del dibujo')

        self.evaluate_panel,self.evaluate_layout = panel()
        head = QHBoxLayout(); head.addWidget(label('Evaluar cadenas','heading')); head.addStretch()
        self.words_badge = label('','muted'); head.addWidget(self.words_badge); self.evaluate_layout.addLayout(head); self.evaluate_layout.addSpacing(14)
        self.evaluate_layout.addWidget(label('Cadena para evaluar','muted')); self.evaluate_layout.addSpacing(8)
        field = QHBoxLayout(); field.setSpacing(9)
        self.word = QLineEdit(); self.word.setMinimumWidth(0)
        self.word.setMaxLength(2**31-1)
        self.word.textChanged.connect(self.manual_input); self.word.returnPressed.connect(self.evaluate)
        self.suggestions = QStringListModel(self); completer = QCompleter(self.suggestions,self.word)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseSensitive); self.word.setCompleter(completer)
        self.evaluate_button = button('Evaluar',self.evaluate,True); field.addWidget(self.word,1); field.addWidget(self.evaluate_button)
        self.evaluate_layout.addLayout(field); self.evaluate_layout.addSpacing(13)
        imports = QHBoxLayout(); imports.setSpacing(9)
        self.file_info = label('Podés cargar un AFD completo con sus cadenas.','fileInfo'); self.file_info.setWordWrap(True); self.file_info.setMinimumHeight(44)
        imports.addWidget(self.file_info,1); self.evaluate_layout.addLayout(imports); self.evaluate_layout.addSpacing(13)
        instructions = label('Seleccioná una cadena de la tabla para ver su recorrido en el dibujo.','muted'); instructions.setWordWrap(True)
        self.evaluate_layout.addWidget(instructions); self.evaluate_layout.addSpacing(13)
        self.words,self.words_wrap = table(['#','Cadena','Resultado']); self.words.itemSelectionChanged.connect(self.select_word)
        self.words.itemClicked.connect(lambda item: self.select_word(force=True))
        self.words.empty_message = 'Todavía no hay cadenas. Ingresá una arriba.'
        self.evaluate_layout.addWidget(self.words_wrap); self.evaluate_layout.addSpacing(25)
        derivation_head = QHBoxLayout(); derivation_head.setSpacing(12)
        heading = QVBoxLayout(); heading.setSpacing(3)
        for text,role in [('Derivaciones de la cadena','deriveHeading'),('Cómo avanza el autómata al leer cada símbolo','deriveSub')]:
            item = label(text,role); item.setWordWrap(True); heading.addWidget(item)
            if role == 'deriveHeading': self.derivation_title = item
        derivation_head.addLayout(heading,1); self.derivation_count = label('','deriveCount'); derivation_head.addWidget(self.derivation_count)
        self.evaluate_layout.addLayout(derivation_head); self.evaluate_layout.addSpacing(12)
        self.derivations = DerivationList(); self.derivations.step_selected.connect(self.scrub)
        self.derivations.chain_step_selected.connect(self.select_derivation)
        self.evaluate_layout.addWidget(self.derivations); self.evaluate_layout.addStretch()

        self.transitions_panel,self.transitions_layout = panel()
        head = QHBoxLayout(); head.addWidget(label('Tabla de transiciones','heading')); head.addStretch()
        head.addWidget(label('Se resalta la transición de cada paso','muted')); self.transitions_layout.addLayout(head); self.transitions_layout.addSpacing(14)
        self.transitions,self.transitions_wrap = table(['Estado']); self.transitions_layout.addWidget(self.transitions_wrap)
        self.page_layout.addWidget(self.grid_widget)
        self.page_layout.addWidget(label('AFD · Proyecto de Autómatas y Lenguajes Formales','foot'),0,Qt.AlignmentFlag.AlignHCenter)
        self.page_layout.addStretch()
        self.overlay = ModalOverlay(self); self.overlay.closed.connect(lambda: setattr(self,'editor_dialog',None))
        self.adapt_layout()
        for shortcut,command in [('Ctrl++',lambda: self.canvas.zoom(1.2)),('Ctrl+0',self.canvas.fit_diagram)]:
            action = QAction(self); action.setShortcut(QKeySequence(shortcut)); action.triggered.connect(command); self.addAction(action)

    def adapt_layout(self):
        compact = self.width() <= 800
        if compact == self._compact: return
        self._compact = compact
        for widget in (self.diagram_panel,self.evaluate_panel,self.transitions_panel): self.grid.removeWidget(widget)
        self.header_layout.setDirection(QBoxLayout.Direction.TopToBottom if compact else QBoxLayout.Direction.LeftToRight)
        self.header_layout.setAlignment(self.nav,Qt.AlignmentFlag.AlignLeft if compact else Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignVCenter)
        self.page_layout.setContentsMargins(12 if compact else 26,17 if compact else 32,12 if compact else 26,35 if compact else 55)
        for layout in (self.diagram_layout,self.evaluate_layout,self.transitions_layout): layout.setContentsMargins(*([17 if compact else 25]*4))
        self.grid.addWidget(self.diagram_panel,0,0)
        self.grid.addWidget(self.evaluate_panel,1 if compact else 0,0 if compact else 1)
        self.grid.addWidget(self.transitions_panel,2 if compact else 1,0,1,1 if compact else 2)
        self.grid.setColumnStretch(0,1 if compact else 134); self.grid.setColumnStretch(1,0 if compact else 92)
        self.grid.setColumnMinimumWidth(1,0 if compact else 320)
        self.canvas.setFixedHeight(298 if compact else 368)

    def resizeEvent(self,event):
        super().resizeEvent(event)
        if hasattr(self,'grid'): self.adapt_layout()
        if hasattr(self,'overlay') and self.overlay.isVisible():
            self.overlay.setGeometry(self.rect()); self.overlay.fit_panel()

    def graph_signature(self,a):
        return (tuple(a['states']),tuple(a['alphabet']),a['initial'],tuple(a['finals']),
                tuple((s,c,a['transitions'].get(s,{}).get(c)) for s in a['states'] for c in a['alphabet']))

    def load_afd(self,a):
        a = validate(copy.deepcopy(a)); signature = self.graph_signature(a)
        layout = calculate_layout(a) if signature != self._graph_signature else None
        self.stop(); self.afd = a; self.selected = 0 if a['words'] else None; self.step = 0
        self._show_all_derivations = False
        self._traces = {}; self._word_indices = {}
        self._derivation_groups = {}; self._invalid_derivation_entries = {}; self._derivation_group = None
        self.derivations.invalidate()
        self._trace = None; self._trace_word = None; self._active_cell = None
        name = a.get('name','Autómata')
        self.name.setText(name); self.name.setVisible(bool(name.strip()) and name.strip().casefold() != 'autómata importado')
        self.set_word(a['words'][0] if a['words'] else '')
        if layout is not None: self.canvas.set_layout(a,layout); self._graph_signature = signature
        self.file_info.setText(f'{len(a["states"])} estados · {len(a["alphabet"])} símbolos')
        self.suggestions.setStringList(list(dict.fromkeys(w for w in a['words'] if w)))
        self.build_transitions(); self.refresh_words(); self.refresh_derivations(); self.render()

    def try_load_example(self,index):
        try: self.load_afd(EXAMPLES[index]); self.filename = 'automata.txt'
        except (OSError,ValueError) as error: self.show_error('No se pudo cargar el ejemplo',error)

    def set_word(self,value):
        with QSignalBlocker(self.word): self.word.setText(value)

    def manual_input(self,*_):
        self.stop(); word = self.word.text(); self.selected = self._word_indices.get(word)
        self.step = 0; self._trace = None
        with QSignalBlocker(self.words):
            self.words.clearSelection(); self.words.setCurrentItem(None)
            if self.selected is not None: self.words.selectRow(self.selected)
        self.refresh_derivations(); self.render()

    def current(self):
        return self.word.text() if self.selected is None else self.afd['words'][self.selected]

    def current_trace(self):
        word = self.current()
        if self._trace is None or self._trace_word != word:
            self._trace = self.trace_word(word,cache=word in self._word_indices); self._trace_word = word
        return self._trace

    def trace_word(self,word,cache=True):
        if word in self._traces: return self._traces[word]
        t = trace(self.afd,word)
        if cache: self._traces[word] = t
        return t

    @staticmethod
    def set_cells(widget,row,values):
        widget._column_sizes = None
        for col,value in enumerate(values):
            item = QTableWidgetItem(str(value)); item.setTextAlignment(Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter)
            item.setToolTip(str(value)); widget.setItem(row,col,item)

    def size_table(self,widget,wrap):
        wrap.setFixedHeight(min(340,44+max(1,widget.rowCount())*40))

    def build_transitions(self):
        self.transitions._column_sizes = None
        a = self.afd; self.transitions.setColumnCount(1+len(a['alphabet']))
        self.transitions.setHorizontalHeaderLabels(['Estado']+a['alphabet']); self.transitions.setRowCount(len(a['states']))
        self.transitions.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch if len(a['alphabet']) <= 8 else QHeaderView.ResizeMode.Interactive)
        for row,state in enumerate(a['states']):
            prefix = ('→ ' if state == a['initial'] else '')+('◎ ' if state in a['finals'] else '')
            self.set_cells(self.transitions,row,[prefix+state]+[a['transitions'].get(state,{}).get(c,'—') for c in a['alphabet']])
        self.size_table(self.transitions,self.transitions_wrap)
        self.transitions.rebalance()

    def refresh_words(self):
        self.words._column_sizes = None
        groups = {'numbers':[], 'letters':[], 'empty':[]}; invalid_entries = {}; indices = {}
        with QSignalBlocker(self.words):
            self.words.setRowCount(len(self.afd['words']))
            for i,word in enumerate(self.afd['words']):
                t = self.trace_word(word); accepted = t['valid'] and t['accepted']
                entry = (i,word,t); group = word_group(word); indices.setdefault(word,i)
                if group == 'invalid': invalid_entries[i] = [entry]
                elif group == 'empty':
                    for entries in groups.values(): entries.append(entry)
                else: groups[group].append(entry)
                answer = 'Aceptada' if accepted else 'Rechazada'
                self.set_cells(self.words,i,[i+1,word or 'ε (vacía)',answer])
                self.words.item(i,2).setForeground(QColor(COLORS['accepted' if accepted else 'rejected']))
                font = self.words.item(i,2).font(); font.setWeight(QFont.Weight.Bold); self.words.item(i,2).setFont(font)
                self.words.item(i,2).setToolTip(t['error'] or answer)
            if self.selected is not None: self.words.selectRow(self.selected)
        self._derivation_groups = groups; self._invalid_derivation_entries = invalid_entries; self._word_indices = indices
        count = len(self.afd['words']); self.words_badge.setText(f'{count} cadena'+('' if count == 1 else 's'))
        self.size_table(self.words,self.words_wrap)
        self.words.rebalance(); self.words.viewport().update()

    def refresh_derivations(self):
        word = self.current(); group = word_group(word)
        if group in ('numbers','letters'): self._derivation_group = group
        elif group == 'empty':
            group = self._derivation_group or word_group(''.join(self.afd['alphabet']))
            if group not in ('numbers','letters'): group = 'empty'
        if self._show_all_derivations:
            entries = (self._invalid_derivation_entries.get(self.selected) if group == 'invalid'
                       else self._derivation_groups.get(group,self._derivation_groups['empty']))
            if entries is not None:
                self.derivations.rebuild_all(entries,self.afd['finals'],self.selected)
                count = len(entries); self.derivation_count.setText(f'{count} cadena'+('' if count == 1 else 's'))
                self.derivation_title.setText('Derivaciones de las cadenas'); return
        empty = not self.afd['words'] and not word
        self.derivations.rebuild(word,self.current_trace(),self.afd['finals'],empty)
        self.derivation_count.setText('0 pasos' if empty else str(len(word))+' símbolo'+('' if len(word) == 1 else 's'))
        self.derivation_title.setText('Derivaciones de la cadena')

    def render(self):
        a = self.afd; t = self.current_trace(); w = self.current(); self.step = min(max(0,self.step),len(t['path'])-1)
        self.derivations.select_step(self.step,self.selected)
        self.transitions.selectRow(a['states'].index(t['path'][self.step]))
        if self._active_cell is not None:
            item = self.transitions.item(*self._active_cell)
            if item: item.setData(Qt.ItemDataRole.UserRole,None); item.setBackground(QColor(COLORS['panel'])); item.setForeground(QColor(COLORS['text'])); item.setFont(QFont())
        self._active_cell = None
        if self.step:
            self._active_cell = (a['states'].index(t['path'][self.step-1]),a['alphabet'].index(w[self.step-1])+1)
            item = self.transitions.item(*self._active_cell); item.setData(Qt.ItemDataRole.UserRole,'active')
            item.setBackground(QColor(COLORS['active'])); item.setForeground(QColor(COLORS['active_text']))
            font = item.font(); font.setWeight(QFont.Weight.Bold); item.setFont(font)
        self.back.setEnabled(self.step > 0); self.next.setEnabled(self.step < len(t['path'])-1); self.play.setEnabled(len(t['path']) > 1)
        finished = self.step == len(t['path'])-1; result = ('ok' if t['accepted'] else 'no') if finished else ''
        if not a['words'] and not w: message = 'Ingresá una cadena para comenzar.'; result = ''
        elif finished and t['error']: message = t['error']
        elif finished: message = ('Cadena aceptada' if t['accepted'] else 'Cadena rechazada')+' · Estado final: '+t['path'][self.step]
        else: message = f'Paso {self.step} de {len(w)} · Estado: {t["path"][self.step]}'+(f' · Símbolo leído: {w[self.step-1]}' if self.step else '')
        self.status.setText(message); self.status.setProperty('result',result); restyle(self.status)
        self.draw()
        self.info.setText(f'{len(a["states"])} estados · Inicial: {a["initial"]} · Finales: {", ".join(a["finals"]) or "ninguno"}')

    def draw(self):
        t = self.current_trace(); edge = (t['path'][self.step-1],t['path'][self.step]) if self.step else None
        symbol = self.current()[self.step-1] if self.step else None
        visited_edges = set(zip(t['path'][:self.step],t['path'][1:self.step+1],self.current()[:self.step]))
        self.canvas.highlight(t['path'][self.step],edge,symbol,set(t['path'][:self.step]),visited_edges)

    def select_word(self,force=False):
        rows = self.words.selectionModel().selectedRows()
        if not rows or (rows[0].row() == self.selected and not force): return
        self.stop(); self.selected = rows[0].row(); self.step = 0; self._trace = None
        self.set_word(self.current()); self.refresh_derivations(); self.render()

    def scrub(self,step):
        self.stop()
        if step == self.step: return
        self.step = step; self.render()

    def select_derivation(self,chain_index,step):
        if not 0 <= chain_index < len(self.afd['words']): return
        self.stop(); self.selected = chain_index; self._trace = None
        self.set_word(self.afd['words'][chain_index]); self.step = step
        with QSignalBlocker(self.words): self.words.selectRow(chain_index)
        self.refresh_derivations(); self.render()

    def evaluate(self):
        self.stop(); word = self.word.text()
        if word not in self._word_indices:
            self.selected = len(self.afd['words']); self.afd['words'].append(word)
            self._word_indices[word] = self.selected
        elif self.selected is None or self.afd['words'][self.selected] != word:
            self.selected = self._word_indices[word]
        self._trace = None
        self._show_all_derivations = True
        self.step = 1 if word and self.current_trace()['valid'] else 0
        self.refresh_words(); self.refresh_derivations(); self.render()
        self.suggestions.setStringList(list(dict.fromkeys(w for w in self.afd['words'] if w)))
        if not self.current_trace()['valid']: self.word.setFocus()

    def previous(self): self.stop(); self.step = max(0,self.step-1); self.render()
    def forward(self): self.stop(); self.step = min(len(self.current_trace()['path'])-1,self.step+1); self.render()
    def restart(self): self.stop(); self.step = 0; self.render()

    def stop(self):
        self.timer.stop()
        if hasattr(self,'play'): self.play.setText('▶ Reproducir')

    def toggle_play(self):
        if self.timer.isActive(): self.stop(); return
        if len(self.current_trace()['path']) < 2: return
        if self.step >= len(self.current_trace()['path'])-1: self.step = 0; self.render()
        self.play.setText('Ⅱ Pausar'); self.timer.start()

    def tick(self):
        self.step = min(self.step+1,len(self.current_trace()['path'])-1); self.render()
        if self.step >= len(self.current_trace()['path'])-1: self.stop()

    def playback_menu(self,pos):
        menu = QMenu(self.play)
        for text,interval in [('0.5×',1300),('1×',650),('2×',325),('4×',163)]:
            action = menu.addAction(text); action.setCheckable(True); action.setChecked(self.timer.interval() == interval)
            action.triggered.connect(lambda checked=False,interval=interval: self.timer.setInterval(interval))
        menu.exec(self.play.mapToGlobal(pos))

    def diagram_menu(self,pos):
        menu = QMenu(self.canvas); menu.addAction('Acercar',lambda: self.canvas.zoom(1.2))
        menu.addAction('Alejar',lambda: self.canvas.zoom(1/1.2)); menu.addAction('Ajustar diagrama',self.canvas.fit_diagram)
        menu.exec(self.canvas.mapToGlobal(pos))

    def show_error(self,title,error,parent=None):
        self.stop(); self.overlay.open(title)
        message = label(str(error)); message.setWordWrap(True); self.overlay.content_layout.addWidget(message)
        note = label('El archivo debe incluir estados, alfabeto, inicial, finales, transiciones y cadenas. Usá Archivo → Nuevo para ver o modificar el formato admitido.','muted')
        note.setWordWrap(True); self.overlay.content_layout.addWidget(note); self.overlay.adjust_height(280)

    def import_file(self,path):
        a = parse_txt(Path(path).read_text(encoding='utf-8-sig'),self.afd)
        self.load_afd(a); self.filename = str(path)

    def open_file(self):
        path,_ = QFileDialog.getOpenFileName(self,'Abrir autómata o cadenas','','Archivos TXT (*.txt);;Archivos JSON (*.json);;Todos los archivos (*)')
        if not path: return
        try: self.import_file(path)
        except (OSError,ValueError,KeyError) as error: self.show_error('No se pudo abrir el TXT',error)

    def save_file(self):
        path,_ = QFileDialog.getSaveFileName(self,'Guardar autómata',self.filename,'Archivos TXT (*.txt)')
        if not path: return
        if not Path(path).suffix: path += '.txt'
        try: Path(path).write_text(serialize(self.afd),encoding='utf-8'); self.filename = path
        except (OSError,ValueError) as error: self.show_error('No se pudo guardar el TXT',error)

    def edit_afd(self):
        self.stop(); self.overlay.open('Nuevo / Editar autómata')
        description = label('Editá la definición completa en TXT. El formato es el mismo que se abre y guarda desde Archivo.','muted'); description.setWordWrap(True)
        self.overlay.content_layout.addWidget(description)
        editor = QPlainTextEdit(); editor.setPlainText(serialize(self.afd)); editor.setMinimumHeight(290)
        editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap); self.overlay.content_layout.addWidget(editor)
        error_label = label('','modalError'); error_label.setWordWrap(True)
        def apply():
            try: self.load_afd(parse_txt(editor.toPlainText(),self.afd)); self.overlay.close_overlay()
            except (OSError,ValueError,KeyError) as error: error_label.setText(str(error))
        actions = QWidget(); row = QHBoxLayout(actions); row.setContentsMargins(0,0,0,0); row.setSpacing(9)
        apply_button = button('Aplicar cambios',apply,True); row.addWidget(apply_button)
        row.addWidget(button('Crear desde cero',lambda: editor.setPlainText(BLANK_AFD))); row.addStretch()
        self.overlay.content_layout.addWidget(actions); self.overlay.content_layout.addWidget(error_label)
        self.overlay.editor = editor; self.overlay.apply_button = apply_button; self.overlay.error_label = error_label
        self.editor_dialog = self.overlay; self.overlay.adjust_height(535)

    def informational_modal(self,title,content,height):
        self.stop(); self.overlay.open(title)
        text = QLabel(content); text.setTextFormat(Qt.TextFormat.RichText); text.setWordWrap(True)
        text.setStyleSheet('font-size:14px;'); self.overlay.content_layout.addWidget(text); self.overlay.adjust_height(height)

    def help(self):
        self.informational_modal('Ayuda',
            '<p><b>1.</b> Abrí un archivo TXT desde <b>Archivo → Abrir TXT</b> o con <b>Ctrl+O</b>.</p>'
            '<p><b>2.</b> Seleccioná una cadena en la tabla o escribí otra en <b>Cadena para evaluar</b>.</p>'
            '<p><b>3.</b> Usá <b>Siguiente</b>, <b>Anterior</b> o <b>Reproducir</b> para ver cada transición marcada en el dibujo y la tabla.</p>'
            '<p><b>4.</b> Desde <b>Archivo → Nuevo</b> podés crear o editar el AFD usando TXT y <b>Guardar</b> permite exportarlo.</p>'
            '<p><b>5.</b> Encontrarás tres AFD predeterminados en el menú <b>Ejemplos</b>.</p>'
            '<p><b>Formato TXT admitido:</b></p><pre>'+html.escape(serialize(EXAMPLES[0]))+'</pre>'
            '<p>También se admite el formato con <b>matriz de transiciones</b>: una fila por estado (en el orden de <i>Estados</i>) '
            'y una columna por símbolo (en el orden de <i>Simbolos</i>). Use <b>-</b> cuando no exista transición.</p>'
            '<pre>Simbolos: 0,1\nEstados: Q0,Q1\nEstado inicial: Q0\nEstados de aceptacion: Q1\nTransiciones:\nQ1,Q0\nQ1,-\nCadenas a analizar:\n1,0,1\n0,0</pre>'
            '<p>El alfabeto puede tener cualquier símbolo de un carácter (letras, dígitos u otros). Las cadenas se escriben juntas (<i>abba</i>) o separadas por comas (<i>a,b,b,a</i>).</p>'
            '<p>Si la cadena tiene un símbolo fuera del alfabeto o llega a una transición inexistente, se marca como <b>Rechazada</b> y se explica el motivo.</p>'
            '<p>En el diagrama, el estado actual y la flecha usada se pintan de <b>verde</b>; lo ya recorrido queda en verde claro. '
            'En la tabla de transiciones se resaltan la fila del estado actual y la celda de la transición aplicada.</p>'
            '<p>Rueda del mouse o clic derecho sobre el dibujo: acercar, alejar o ajustar. Arrastrar: desplazar.</p>'
            '<p>ε representa la cadena vacía.</p>'
            '<p>El manual completo está en <b>Acerca de → Manual de usuario (PDF)</b>.</p>',650)

    def open_manual(self):
        if not MANUAL_PDF.is_file() or not QDesktopServices.openUrl(QUrl.fromLocalFile(str(MANUAL_PDF))):
            self.help()

    def about(self):
        self.informational_modal('Acerca de','<b>AFD</b><p>Proyecto del curso de Autómatas y Lenguajes Formales.</p>'
            '<p>Universidad: Universidad Mariano Gálvez de Guatemala</p><p>Fecha: octubre de 2026</p>'
            '<p><b>Integrantes:</b><br>'
            'Roger Felipe Sosa Osorio — Carné: 1890-17-8391<br>'
            'Ever Misael Lopez Perez — Carné: 1890-24-3260<br>'
            'Vieri Alexander Ixtecoc López — Carné: 1890-23-3479<br>' 
            'Henry Leonel Perez Cruz — Carné: 1890-24-4996<br>' 
            'Edgar Emanuel Contreras Gaitan — Carné: 1890-17-17069<br>'
            'Dennis Rodrigo Melgar Perez — Carné: 1890-24-9352</p>'
            '<p>Simulador interactivo de autómatas finitos deterministas.</p>',390)

    def exit(self): self.close()
    def closeEvent(self,event): self.stop(); self.overlay.close_overlay(); event.accept()


def run():
    app = QApplication(sys.argv); app.setApplicationName('AFD'); app.setStyle('Fusion')
    app.setFont(QFont('Segoe UI',10))
    try: find_dot(); window = Studio()
    except (GraphvizError,OSError) as error:
        QMessageBox.critical(None,'AFD — Configuración',str(error)); return 1
    if len(sys.argv) > 1:
        try: window.import_file(sys.argv[1])
        except (OSError,ValueError,KeyError) as error: window.show_error('No se pudo abrir el TXT',error)
    window.show(); return app.exec()


if __name__ == '__main__': sys.exit(run())
