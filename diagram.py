"""Graphviz layout once per model; live, zoomable Qt vector items per step."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from PySide6.QtCore import Property, QEasingCurve, QPointF, QRectF, Qt, QPropertyAnimation, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QPolygonF, QRadialGradient, QRegion
from PySide6.QtWidgets import QGraphicsObject, QGraphicsScene, QGraphicsView

GREEN = '#10d84c'
# En el ejecutable instalado (PyInstaller) los recursos están en sys._MEIPASS.
BASE = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))


class GraphvizError(ValueError):
    pass


def find_dot():
    """Resolve an explicit executable without changing the user's global PATH."""
    explicit = os.environ.get('AFD_DOT')
    if explicit:
        path = Path(explicit).expanduser()
        if path.is_file():
            return path.resolve()
        raise GraphvizError('AFD_DOT no apunta a un archivo dot.exe válido: ' + explicit)
    candidates = list((BASE / 'tools' / 'graphviz').glob('**/bin/dot.exe'))
    candidates += [Path(root) / 'Graphviz' / 'bin' / 'dot.exe'
                   for root in (os.environ.get('ProgramFiles', ''), os.environ.get('ProgramFiles(x86)', '')) if root]
    on_path = shutil.which('dot')
    if on_path:
        candidates.append(Path(on_path))
    for path in candidates:
        if path.is_file():
            return path.resolve()
    raise GraphvizError('No se encontró Graphviz. Ejecutá CONFIGURAR.ps1 o definí AFD_DOT con la ruta completa de dot.exe.')


def dot_quote(value):
    # Escape DOT strings; internal node IDs never depend on user input.
    return '"' + value.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '') + '"'


def grouped_edges(a):
    groups = {}
    for state in a['states']:
        for symbol in a['alphabet']:
            target = a['transitions'].get(state, {}).get(symbol)
            if target is not None: groups.setdefault((state, target), []).append(symbol)
    return groups


def calculate_layout(a):
    ids = {state: f'n{i}' for i, state in enumerate(a['states'])}
    font_size = 16
    source = ['digraph AFD {',
              'graph [rankdir=LR, splines=true, nodesep=0.45, ranksep=1.05, pad=0.3, bgcolor="transparent", charset="UTF-8"];',
              f'node [shape=circle, fontname="Segoe UI", fontsize={font_size}, width=0.82, height=0.82, margin=0.09];',
              'edge [fontname="Segoe UI", fontsize=14, arrowsize=0.85];',
              'start [shape=point, width=0.01, label=""];']
    for state in a['states']:
        source.append(f'{ids[state]} [label={dot_quote(state)}, peripheries={2 if state in a["finals"] else 1}];')
    source.append(f'start -> {ids[a["initial"]]};')
    for origin in a['states']:
        for symbol in a['alphabet']:
            target = a['transitions'].get(origin, {}).get(symbol)
            if target is None: continue
            source.append(f'{ids[origin]} -> {ids[target]} '
                          f'[label={dot_quote(symbol)}, transition_symbol={dot_quote(symbol)}];')
    source.append('}')
    try:
        result = subprocess.run([str(find_dot()), '-Tjson'], input='\n'.join(source),
                                capture_output=True, text=True, encoding='utf-8', timeout=25,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    except (OSError, subprocess.TimeoutExpired) as error:
        raise GraphvizError('No se pudo calcular el diagrama con Graphviz: ' + str(error)) from error
    if result.returncode:
        raise GraphvizError('Graphviz no pudo generar el diagrama: ' + result.stderr.strip())
    try:
        data = json.loads(result.stdout)
        names = {v: k for k, v in ids.items()}
        objects = {obj['_gvid']: obj for obj in data['objects']}
        # Attach real model identities, independent of Graphviz's object order.
        for node in data['objects']:
            node['state'] = names.get(node['name'])
            node['font_size'] = font_size
        for edge in data.get('edges', []):
            origin = objects[edge['tail']]['state']
            target = objects[edge['head']]['state']
            edge['model_key'] = (origin, target)
            edge['symbols'] = [edge['transition_symbol']] if origin is not None else []
            edge['font_size'] = 14
        return data
    except (KeyError, ValueError, TypeError) as error:
        raise GraphvizError('Graphviz devolvió un diseño no válido.') from error


def point(coords):
    return QPointF(float(coords[0]), -float(coords[1]))


def circle_boundary(node,position):
    offset = position-node.pos()
    distance = (offset.x()**2+offset.y()**2)**.5
    return node.pos()+offset*(node.radius/distance) if distance else node.pos()+QPointF(node.radius,0)


class StateItem(QGraphicsObject):
    def __init__(self, node, final):
        super().__init__()
        self.state = node['state']
        self.final = final
        self.radius = float(node['width']) * 36
        self._highlight = 0.0
        self.active = False
        self.visited = False
        self.font_size = node.get('font_size',16)
        self.setPos(point(node['pos'].split(',')))
        self.setZValue(2)
        self.setToolTip(f'Estado: {self.state}' + (' · Final' if final else ''))
        self.animation = QPropertyAnimation(self, b'highlight', self)
        self.animation.setDuration(180)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def boundingRect(self):
        r = self.radius + 12
        return QRectF(-r, -r, 2*r, 2*r)

    def get_highlight(self):
        return self._highlight

    def set_highlight(self, value):
        self._highlight = value
        self.update()

    highlight = Property(float, get_highlight, set_highlight)

    def set_active(self, active):
        if self.active == active:
            return
        self.active = active
        self.animation.stop()
        self.set_highlight(1.0 if active else 0.0)

    def set_visited(self,visited):
        if self.visited != visited: self.visited = visited; self.update()

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.radius
        mix = self._highlight
        normal, green = QColor('#62b86f' if self.visited else '#8b919a'), QColor(GREEN)
        outline = QColor.fromRgbF(*(normal.getRgbF()[i]*(1-mix)+green.getRgbF()[i]*mix for i in range(3)))
        painter.setBrush(QColor('#ecfff1' if self.active else '#f4fbf6' if self.visited else '#ffffff'))
        painter.setPen(QPen(outline,3 if self.active else 2))
        painter.drawEllipse(QPointF(), r, r)
        if self.final:
            painter.setPen(QPen(QColor(GREEN if self.active else '#8b919a'),1.8))
            painter.drawEllipse(QPointF(),r-5,r-5)
        painter.setPen(QColor('#10b43c' if self.active else '#1b2232'))
        font = QFont('Segoe UI'); font.setPixelSize(self.font_size); font.setWeight(QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(QRectF(-r+5, -r, 2*r-10, 2*r), Qt.AlignmentFlag.AlignCenter, self.state)


class EdgeItem(QGraphicsObject):
    def __init__(self, edge, nodes):
        super().__init__()
        self.key = edge['model_key']
        self.symbols = edge['symbols']
        self.active = False
        self.visited = False
        self.font_size = edge.get('font_size',14)
        draw_ops = [op for op in edge.get('_draw_', []) if op['op'].lower() == 'b' or op['op'] == 'L']
        origin = nodes.get(self.key[0]); target = nodes[self.key[1]]
        # Reflect lower connections above a horizontal row once, on load.
        # Reuse Graphviz's layout without changing nodes or transitions.
        mirror_y = None
        if origin is not None and origin is not target and abs(origin.y()-target.y()) < 1e-4:
            points = [point(p) for op in draw_ops for p in op.get('points', [])]
            if points and sum(p.y() for p in points)/len(points) > origin.y()+1e-4:
                mirror_y = origin.y()

        def edge_point(coords):
            p = point(coords)
            return QPointF(p.x(),2*mirror_y-p.y()) if mirror_y is not None else p

        self.arrows = [QPolygonF([edge_point(p) for p in op['points']])
                       for op in edge.get('_hdraw_', []) if op['op'] in ('P', 'p')]
        # Graphviz's arrow polygon can stop short of its declared endpoint.
        # Align the actual triangle with the circle drawn by Qt, once on load.
        end_anchor = None
        for arrow in self.arrows:
            tip_index = min(range(len(arrow)),key=lambda i: (arrow[i].x()-target.x())**2+(arrow[i].y()-target.y())**2)
            tip = arrow[tip_index]
            arrow.translate(circle_boundary(target,tip)-tip)
            base = [p for i,p in enumerate(arrow) if i != tip_index]
            end_anchor = sum(base,QPointF())/len(base)
        self.path = QPainterPath()
        for position,op in enumerate(draw_ops):
            points = [edge_point(p) for p in op.get('points', [])]
            if not points: continue
            if position == 0 and self.key[0] is not None:
                start = circle_boundary(nodes[self.key[0]],points[0])
                shift = start-points[0]; points[0] = start
                if op['op'].lower() == 'b' and len(points) > 1: points[1] += shift
            if position == len(draw_ops)-1 and end_anchor is not None:
                shift = end_anchor-points[-1]; points[-1] = end_anchor
                if op['op'].lower() == 'b' and len(points) > 1: points[-2] += shift
            if op['op'].lower() == 'b' and points:
                self.path.moveTo(points[0])
                for i in range(1, len(points)-2, 3):
                    self.path.cubicTo(points[i], points[i+1], points[i+2])
            elif op['op'] == 'L' and points:
                self.path.moveTo(points[0])
                for p in points[1:]: self.path.lineTo(p)
        self.label = edge.get('label', '')
        self.display_label = self.label
        self.display_symbols = list(self.symbols)
        self.label_pos = edge_point(edge.get('lp', '0,0').split(','))
        # Use Graphviz's measured label extent.
        label_width = max([op.get('width', 0) for op in edge.get('_ldraw_', [])] or [0])
        self.label_rect = QRectF(self.label_pos.x()-label_width/2-8, self.label_pos.y()-13, label_width+16, 26)
        self.bounds = self.path.boundingRect().adjusted(-12, -12, 12, 12)
        for arrow in self.arrows: self.bounds = self.bounds.united(arrow.boundingRect())
        if self.label: self.bounds = self.bounds.united(self.label_rect)
        self.setToolTip('Entrada al estado inicial' if self.key[0] is None else f'{self.key[0]} → {self.key[1]} · {self.label}')

    def boundingRect(self):
        return self.bounds

    def set_active(self, active):
        if self.active != active:
            self.active = active
            self.setZValue(1 if active else 0)
            self.update()

    def set_visited(self,visited):
        if self.visited != visited: self.visited = visited; self.update()

    def show_symbols(self,symbols):
        selected = [symbol for symbol in self.symbols if symbol in symbols]
        if selected == self.display_symbols: return
        self.display_symbols = selected; self.display_label = selected[0] if selected else ''
        self.setToolTip('Entrada al estado inicial' if self.key[0] is None
                        else f'{self.key[0]} → {self.key[1]} · {self.label}')
        self.update()

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor(GREEN if self.active else '#62b86f' if self.visited else '#20262d')
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(color,3.5 if self.active else 2.5 if self.visited else 1.9))
        painter.drawPath(self.path)
        painter.setBrush(QColor(GREEN if self.active else '#20262d')); painter.setPen(Qt.PenStyle.NoPen)
        for arrow in self.arrows: painter.drawPolygon(arrow)
        if self.display_label:
            font = QFont('Segoe UI'); font.setPixelSize(self.font_size); font.setWeight(QFont.Weight.Bold if self.active else QFont.Weight.DemiBold)
            text = QPainterPath(); text.addText(QPointF(),font,self.display_label)
            center = text.boundingRect().center(); text.translate(self.label_pos-center)
            painter.strokePath(text,QPen(QColor('#ffffff'),4))
            painter.fillPath(text,color)


class AutomatonView(QGraphicsView):
    zoom_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.TextAntialiasing)
        self.setFrameShape(QGraphicsView.Shape.NoFrame)
        self.setBackgroundBrush(QColor('#fafafb'))
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setMinimumSize(240,220)
        self.nodes = {}; self.edges = []
        self.auto_fit = True
        self.layout_count = 0

    def set_layout(self, a, layout):
        self.scene().clear(); self.nodes = {}; self.edges = []
        self.initial = a['initial']
        for node in layout['objects']:
            if node['state'] is not None:
                item = StateItem(node, node['state'] in a['finals'])
                self.nodes[item.state] = item; self.scene().addItem(item)
        for edge in layout.get('edges', []):
            item = EdgeItem(edge,self.nodes); self.edges.append(item); self.scene().addItem(item)
        self.scene().setSceneRect(self.scene().itemsBoundingRect().adjusted(-24,-24,24,24))
        self.layout_count += 1
        self.fit_diagram()

    def highlight(self,state,edge_key=None,symbol=None,visited_states=None,visited_edges=None):
        for name,item in self.nodes.items(): item.set_visited(name in (visited_states or set())); item.set_active(name == state)
        for item in self.edges:
            item.set_visited(any((*item.key,s) in (visited_edges or set()) for s in item.symbols))
            item.set_active(item.key == edge_key and symbol in item.symbols)
        if self.auto_fit and state in self.nodes: self.ensureVisible(self.nodes[state],40,40)

    def fit_diagram(self):
        self.auto_fit = True
        self.fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        # Keep state names readable in long diagrams; scrolling reaches the rest.
        scale = self.transform().m11()
        readable_scale = min(1.65,max(0.75,scale))
        if readable_scale != scale:
            self.resetTransform(); self.scale(readable_scale,readable_scale)
            self.centerOn(self.nodes[self.initial])
        self.zoom_changed.emit(round(self.transform().m11()*100))

    def zoom(self, factor):
        scale = self.transform().m11()*factor
        if 0.2 <= scale <= 5:
            self.auto_fit = False; self.scale(factor, factor)
            self.zoom_changed.emit(round(scale*100))

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta: self.zoom(1.15 if delta > 0 else 1/1.15)
        event.accept()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        clip = QPainterPath(); clip.addRoundedRect(QRectF(self.viewport().rect()),18,18)
        self.viewport().setMask(QRegion(clip.toFillPolygon().toPolygon()))
        if self.auto_fit and self.nodes: self.fit_diagram()

    def drawBackground(self, painter, rect):
        visible = self.mapToScene(self.viewport().rect()).boundingRect()
        gradient = QRadialGradient(visible.center(),max(visible.width(),visible.height())*.7)
        gradient.setColorAt(0,QColor('#ffffff')); gradient.setColorAt(.7,QColor('#fafafb')); gradient.setColorAt(1,QColor('#f1f2f5'))
        painter.fillRect(rect,gradient)
