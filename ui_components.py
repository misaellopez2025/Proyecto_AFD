"""Native Qt counterparts of the approved HTML's page, derivations and modal."""
from bisect import bisect_right
from PySide6.QtCore import QEvent, QRect, QSize, Signal, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QRadialGradient
from PySide6.QtWidgets import QAbstractScrollArea, QFrame, QHBoxLayout, QLabel, QLayout, QPushButton, QScrollArea, QSizePolicy, QVBoxLayout, QWidget


def label(text='', role=None):
    item = QLabel(text); item.setTextFormat(Qt.TextFormat.PlainText)
    if role: item.setObjectName(role)
    return item


def restyle(widget):
    widget.style().unpolish(widget); widget.style().polish(widget); widget.update()


class Background(QWidget):
    def paintEvent(self,event):
        p = QPainter(self)
        gradient = QLinearGradient(0,0,self.width(),self.height())
        gradient.setColorAt(0,QColor('#f5f5f7')); gradient.setColorAt(.6,QColor('#f0f1f4')); gradient.setColorAt(1,QColor('#e8eaee'))
        p.fillRect(self.rect(),gradient)
        light = QRadialGradient(self.width()*.87,self.height()*.03,max(self.width(),self.height())*.55)
        light.setColorAt(0,QColor(255,255,255,85)); light.setColorAt(1,QColor(255,255,255,0))
        p.fillRect(self.rect(),light)


class FullTextLabel(QLabel):
    def __init__(self,text,role):
        super().__init__(text); self.full_text = text; self.setObjectName(role)
        self.setTextFormat(Qt.TextFormat.PlainText)
        self.setSizePolicy(QSizePolicy.Policy.Preferred,QSizePolicy.Policy.Preferred)
        self.setToolTip(text)


class FlowLayout(QLayout):
    """The HTML's flex-wrap action row, including its original nine-pixel gap."""
    def __init__(self):
        super().__init__(); self.items = []; self.setContentsMargins(0,0,0,0); self.setSpacing(9)

    def addItem(self,item): self.items.append(item)
    def count(self): return len(self.items)
    def itemAt(self,index): return self.items[index] if 0 <= index < len(self.items) else None
    def takeAt(self,index): return self.items.pop(index) if 0 <= index < len(self.items) else None
    def expandingDirections(self): return Qt.Orientation(0)
    def hasHeightForWidth(self): return True
    def heightForWidth(self,width): return self.arrange(QRect(0,0,width,0),True)
    def sizeHint(self): return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self.items: size = size.expandedTo(item.minimumSize())
        return size

    def setGeometry(self,rect):
        super().setGeometry(rect); self.arrange(rect,False)

    def arrange(self,rect,measure):
        x,y,line = rect.x(),rect.y(),0
        for item in self.items:
            size = item.sizeHint()
            if x+size.width() > rect.right()+1 and line:
                x = rect.x(); y += line+self.spacing(); line = 0
            if not measure: item.setGeometry(QRect(x,y,size.width(),size.height()))
            x += size.width()+self.spacing(); line = max(line,size.height())
        return y+line-rect.y()


class DerivationRow(QFrame):
    activated = Signal(int)

    def __init__(self,index,word,state,accepted):
        super().__init__(); self.index = index; self.setObjectName('deriveRow')
        self.setCursor(Qt.CursorShape.PointingHandCursor); self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setToolTip(f'Ir al paso {index}'); self.setFixedHeight(46)
        row = QHBoxLayout(self); row.setContentsMargins(11,10,11,10); row.setSpacing(7)
        number = label(f'{index:02d}','deriveNumber'); number.setFixedWidth(max(29,number.fontMetrics().horizontalAdvance(number.text())+4))
        prefix = FullTextLabel(word or 'ε','deriveWord')
        arrow = label('→','deriveArrow'); arrow.setFixedWidth(14)
        state_label = FullTextLabel(state,'deriveState'); state_label.setMinimumWidth(42)
        state_label.setSizePolicy(QSizePolicy.Policy.Fixed,QSizePolicy.Policy.Preferred)
        result = label('Aceptada' if accepted else 'Rechazada','deriveResult')
        result.setProperty('accepted',str(accepted).lower())
        for item in (number,prefix,arrow,state_label,result):
            item.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            row.addWidget(item,1 if item is prefix else 0)

    def set_current(self,current):
        value = str(current).lower()
        if self.property('current') == value: return
        self.setProperty('current',value); restyle(self)

    def mouseReleaseEvent(self,event):
        if event.button() == Qt.MouseButton.LeftButton and self.rect().contains(event.position().toPoint()): self.activated.emit(self.index)
        super().mouseReleaseEvent(event)

    def keyPressEvent(self,event):
        if event.key() in (Qt.Key.Key_Return,Qt.Key.Key_Enter,Qt.Key.Key_Space): self.activated.emit(self.index)
        else: super().keyPressEvent(event)


def derivation_error_text(word,t):
    return t['error']


def derivation_error(word,t):
    error = label(derivation_error_text(word,t),'deriveError')
    error.setWordWrap(True)
    return error


def derivation_content_width(entries,parent):
    """Measure complete words once, without constructing every prefix row."""
    if not entries: return 0
    sample = DerivationRow(0,'ε','q0',False); sample.setParent(parent)
    parts = {role:sample.findChild(QLabel,role) for role in ('deriveNumber','deriveWord','deriveArrow','deriveState','deriveResult')}
    sample.ensurePolished()
    for part in parts.values(): part.ensurePolished()
    fixed = sample.minimumSizeHint().width()-sum(max(part.minimumWidth(),part.minimumSizeHint().width()) for part in parts.values())
    fixed += parts['deriveArrow'].width()+parts['deriveResult'].minimumSizeHint().width()
    word_metrics = parts['deriveWord'].fontMetrics(); state_metrics = parts['deriveState'].fontMetrics()
    number_metrics = parts['deriveNumber'].fontMetrics(); state_widths = {}; width = 0
    for _,word,t in entries:
        last = len(t['path'])-1
        prefix = (word if last == len(word) else word[:last]) or 'ε'
        prefix_width = word_metrics.horizontalAdvance(prefix)+2
        states = set(t['path'])
        for state in states:
            if state not in state_widths: state_widths[state] = max(42,state_metrics.horizontalAdvance(state)+2)
        number_width = max(29,number_metrics.horizontalAdvance(f'{last:02d}')+4)
        width = max(width,fixed+number_width+prefix_width+max(state_widths[state] for state in states))
    sample.deleteLater()
    return width+16


class VirtualDerivationView(QAbstractScrollArea):
    """Keep complete traces, but create widgets only for the visible rows."""
    activated = Signal(int,int)

    def __init__(self,parent):
        super().__init__(parent); self.setObjectName('deriveContent'); self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.viewport().setObjectName('deriveContent')
        self.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Ignored)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.entries = []; self.offsets = [0]; self.entry_indices = {}; self.visible_rows = {}
        self.error_heights = {}; self._offset_width = None; self.content_width = 0
        self.finals = set(); self.current = None
        self.verticalScrollBar().setSingleStep(53)
        self.horizontalScrollBar().setSingleStep(80)
        self.hide()

    def set_entries(self,entries,finals):
        self.clear_visible(); self.entries = entries; self.finals = set(finals)
        self.content_width = derivation_content_width(entries,self)
        self.current = None; self._offset_width = None; self.rebuild_offsets()
        self.update_range(); self.verticalScrollBar().setValue(0); self.horizontalScrollBar().setValue(0); self.sync_visible()

    def rebuild_offsets(self):
        width = self.viewport().width()
        if width == self._offset_width: return
        self._offset_width = width; self.offsets = [0]; self.entry_indices = {}; self.error_heights = {}
        for position,(chain_index,word,t) in enumerate(self.entries):
            self.entry_indices[chain_index] = position
            error_height = 0
            if not t['valid']:
                bounds = self.fontMetrics().boundingRect(QRect(0,0,max(1,width-31),10000),Qt.TextFlag.TextWordWrap,derivation_error_text(word,t))
                error_height = max(59,bounds.height()+28)
                self.error_heights[chain_index] = error_height
            height = len(t['path'])*53+(error_height+7 if error_height else 0)
            self.offsets.append(self.offsets[-1]+height)

    def clear_visible(self):
        for widget in self.visible_rows.values(): widget.hide(); widget.deleteLater()
        self.visible_rows = {}

    def update_range(self):
        height = self.viewport().height(); total = max(0,self.offsets[-1]-7)
        self.verticalScrollBar().setPageStep(height)
        self.verticalScrollBar().setRange(0,max(0,total-height))
        self.horizontalScrollBar().setPageStep(self.viewport().width())
        self.horizontalScrollBar().setRange(0,max(0,self.content_width-self.viewport().width()))

    def resizeEvent(self,event):
        super().resizeEvent(event); self.rebuild_offsets(); self.update_range(); self.sync_visible()

    def scrollContentsBy(self,dx,dy):
        self.sync_visible()

    def sync_visible(self):
        if not self.entries or self.viewport().height() <= 0:
            self.clear_visible(); return
        start = self.verticalScrollBar().value(); end = start+self.viewport().height()
        position = max(0,bisect_right(self.offsets,start)-1); wanted = {}
        while position < len(self.entries) and self.offsets[position] < end:
            chain_index,word,t = self.entries[position]; top = self.offsets[position]
            first = max(0,(start-top)//53); last = min(len(t['path']),max(0,(end-top+52)//53))
            for step in range(first,last):
                row_top = top+step*53
                if row_top+46 > start: wanted[(chain_index,step)] = (row_top,46,word,t)
            error_top = top+len(t['path'])*53
            error_height = self.error_heights.get(chain_index,0)
            if error_height and error_top < end and error_top+error_height > start:
                wanted[(chain_index,'error')] = (error_top,error_height,word,t)
            position += 1
        for key in list(self.visible_rows):
            if key not in wanted:
                widget = self.visible_rows.pop(key); widget.hide(); widget.deleteLater()
        viewport_width = max(0,self.viewport().width()-3)
        left = self.horizontalScrollBar().value()
        for key,(top,height,word,t) in wanted.items():
            chain_index,kind = key; widget = self.visible_rows.get(key)
            if widget is None:
                if kind == 'error': widget = derivation_error(word,t)
                else:
                    widget = DerivationRow(kind,word[:kind],t['path'][kind],t['path'][kind] in self.finals)
                    widget.setToolTip(f'Cadena: {word or "ε (vacía)"} · Paso {kind}')
                    widget.activated.connect(lambda step,chain_index=chain_index: self.activated.emit(chain_index,step))
                widget.setParent(self.viewport()); self.visible_rows[key] = widget
            if isinstance(kind,int): widget.set_current(key == self.current)
            widget.ensurePolished()
            width = max(viewport_width,widget.minimumSizeHint().width()+4)
            widget.setGeometry(0 if kind == 'error' else -left,top-start,
                               viewport_width if kind == 'error' else width,height); widget.show()

    def select_step(self,chain_index,step):
        self.current = (chain_index,step)
        position = self.entry_indices.get(chain_index)
        if position is not None and 0 <= step < len(self.entries[position][2]['path']):
            top = self.offsets[position]+step*53
            bar = self.verticalScrollBar()
            if top < bar.value(): bar.setValue(top)
            elif top+46 > bar.value()+self.viewport().height(): bar.setValue(top+46-self.viewport().height())
        self.sync_visible()
        row = self.visible_rows.get((chain_index,step))
        if row is not None:
            maximum = max(0,row.width()-self.viewport().width())
            if self.horizontalScrollBar().value() > maximum: self.horizontalScrollBar().setValue(maximum)

    def keyPressEvent(self,event):
        if self.current is not None and self.current[0] in self.entry_indices:
            chain_index,step = self.current
            if event.key() in (Qt.Key.Key_Return,Qt.Key.Key_Enter,Qt.Key.Key_Space):
                self.activated.emit(chain_index,step); return
            if event.key() in (Qt.Key.Key_Up,Qt.Key.Key_Down):
                count = len(self.entries[self.entry_indices[chain_index]][2]['path'])
                step = min(count-1,max(0,step+(1 if event.key() == Qt.Key.Key_Down else -1)))
                self.activated.emit(chain_index,step); return
        super().keyPressEvent(event)


class DerivationList(QScrollArea):
    step_selected = Signal(int)
    chain_step_selected = Signal(int,int)

    def __init__(self):
        super().__init__(); self.setObjectName('derivations'); self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.content = QWidget(); self.content.setObjectName('deriveContent'); self.setWidget(self.content)
        self.rows_layout = QVBoxLayout(self.content); self.rows_layout.setContentsMargins(0,0,3,0); self.rows_layout.setSpacing(7)
        self.rows_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.rows = []; self.groups = {}
        self._signature = None; self._current_row = None; self._all_chains = False
        self._entries = None; self._virtual = False
        self._sizing_rows = False
        self.virtual = VirtualDerivationView(self)
        self.virtual.activated.connect(self.activate_virtual_step)

    def invalidate(self):
        self._signature = None; self._entries = None

    def viewportEvent(self,event):
        result = super().viewportEvent(event)
        if event.type() == QEvent.Type.Resize and hasattr(self,'rows_layout'): self.update_row_widths()
        return result

    def update_row_widths(self):
        if getattr(self,'_virtual',False) or getattr(self,'_sizing_rows',False): return
        self._sizing_rows = True
        try:
            width = max(0,self.viewport().width()-3)
            for position in range(self.rows_layout.count()):
                widget = self.rows_layout.itemAt(position).widget()
                if widget is None: continue
                widget.ensurePolished()
                widget.setFixedWidth(width if widget.objectName() in ('deriveError','deriveEmpty')
                                     else max(width,widget.minimumSizeHint().width()+4))
        finally: self._sizing_rows = False

    def activate_virtual_step(self,chain_index,step):
        if self._all_chains: self.chain_step_selected.emit(chain_index,step)
        else: self.step_selected.emit(step)

    def use_virtual(self,enabled):
        if enabled == self._virtual: return
        previous = self.takeWidget(); previous.setParent(self); previous.hide()
        self._virtual = enabled
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff if enabled else Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff if enabled else Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setWidget(self.virtual if enabled else self.content)
        self.widget().setAutoFillBackground(False)
        self.widget().show()

    def clear_rows(self):
        self._current_row = None
        while self.rows_layout.count():
            item = self.rows_layout.takeAt(0)
            if item.widget(): item.widget().hide(); item.widget().deleteLater()
        self.rows = []; self.groups = {}
        self.virtual.set_entries([],[])

    def add_steps(self,word,t,finals,chain_index=None):
        rows = []
        for i,state in enumerate(t['path']):
            row = DerivationRow(i,word[:i],state,state in finals); row.set_current(False)
            row.setToolTip(f'Cadena: {word or "ε (vacía)"} · Paso {i}')
            if chain_index is None: row.activated.connect(self.step_selected)
            else: row.activated.connect(lambda step,chain_index=chain_index: self.chain_step_selected.emit(chain_index,step))
            self.rows_layout.addWidget(row,0,Qt.AlignmentFlag.AlignLeft); rows.append(row)
        if not t['valid']:
            self.rows_layout.addWidget(derivation_error(word,t),0,Qt.AlignmentFlag.AlignLeft)
        return rows

    def rebuild(self,word,t,finals,empty=False):
        signature = ('single',word,id(t),tuple(finals),empty)
        if signature == self._signature: return
        self._signature = signature; self.clear_rows(); self._all_chains = False
        self._entries = None
        self.use_virtual(not empty and len(t['path']) > 240)
        if empty:
            message = label('Ingresá una cadena para ver sus derivaciones.','deriveEmpty'); message.setWordWrap(True)
            self.rows_layout.addWidget(message); self.setFixedHeight(60); return
        if self._virtual:
            self.setFixedHeight(260); self.virtual.set_entries([(-1,word,t)],finals); return
        self.rows = self.add_steps(word,t,finals)
        self.update_row_widths()
        height = len(self.rows)*46+max(0,len(self.rows)-1)*7
        if not t['valid']: height += 66
        self.setFixedHeight(min(260,height))

    def rebuild_all(self,entries,finals,active_index):
        if self._all_chains and entries is self._entries:
            if not self._virtual: self.rows = self.groups.get(active_index,[])
            return
        signature = ('all',tuple((i,word,id(t)) for i,word,t in entries),tuple(finals))
        if signature == self._signature:
            self._entries = entries
            self.rows = self.groups.get(active_index,[]); return
        self._signature = signature; self.clear_rows(); self._all_chains = True
        self._entries = entries
        self.use_virtual(sum(len(t['path'])+int(not t['valid']) for _,_,t in entries) > 240)
        if self._virtual:
            self.setFixedHeight(260); self.virtual.set_entries(entries,finals); return
        height = 0
        for chain_index,word,t in entries:
            rows = self.add_steps(word,t,finals,chain_index); self.groups[chain_index] = rows
            height += len(rows)*46+(66 if not t['valid'] else 0)
        self.rows = self.groups.get(active_index,[])
        self.update_row_widths()
        self.setFixedHeight(min(260,height+max(0,self.rows_layout.count()-1)*7))

    def select_step(self,index,chain_index=None):
        if self._virtual:
            self.virtual.select_step(chain_index if self._all_chains else -1,index); return
        if self._all_chains: self.rows = self.groups.get(chain_index,[])
        current = self.rows[index] if 0 <= index < len(self.rows) else None
        if self._current_row is not current:
            if self._current_row is not None: self._current_row.set_current(False)
            if current is not None: current.set_current(True)
            self._current_row = current
        if current is not None: self.ensureWidgetVisible(current)


class ModalOverlay(QWidget):
    closed = Signal()

    def __init__(self,parent):
        super().__init__(parent); self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        root = QVBoxLayout(self); root.setContentsMargins(15,15,15,15); root.addStretch()
        center = QHBoxLayout(); center.addStretch()
        self.panel = QFrame(); self.panel.setObjectName('modal'); self.panel.setMaximumWidth(730)
        self.layout = QVBoxLayout(self.panel); self.layout.setContentsMargins(24,24,24,24); self.layout.setSpacing(16)
        head = QHBoxLayout(); self.title = label('','modalTitle'); head.addWidget(self.title,1)
        self.close_button = QPushButton('Cerrar ✕'); self.close_button.clicked.connect(self.close_overlay); head.addWidget(self.close_button)
        self.layout.addLayout(head)
        self.content = QWidget(); self.content.setObjectName('modalContent'); self.content_layout = QVBoxLayout(self.content); self.content_layout.setContentsMargins(0,0,0,0); self.content_layout.setSpacing(14)
        self.scroll = QScrollArea(); self.scroll.setObjectName('modalScroll'); self.scroll.setWidgetResizable(True); self.scroll.setWidget(self.content)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.layout.addWidget(self.scroll); center.addWidget(self.panel,1); center.addStretch(); root.addLayout(center); root.addStretch()
        self.hide()
        self.requested_height = 280

    def open(self,title):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        self.title.setText(title); self.setGeometry(self.parentWidget().rect())
        self.fit_panel()
        self.show(); self.raise_(); self.setFocus()

    def adjust_height(self,height):
        self.requested_height = height; self.fit_panel()

    def fit_panel(self):
        self.panel.setMinimumWidth(min(730,max(280,self.width()-30)))
        self.panel.setFixedHeight(min(self.requested_height,max(200,int(self.height()*.92))))

    def close_overlay(self):
        self.hide(); self.closed.emit()

    def paintEvent(self,event):
        QPainter(self).fillRect(self.rect(),QColor(29,29,31,140))

    def mouseReleaseEvent(self,event):
        if not self.panel.geometry().contains(event.position().toPoint()): self.close_overlay()

    def keyPressEvent(self,event):
        if event.key() == Qt.Key.Key_Escape: self.close_overlay()
        else: super().keyPressEvent(event)
