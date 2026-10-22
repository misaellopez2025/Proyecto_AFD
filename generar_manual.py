"""Genera docs/Manual_de_usuario.pdf con capturas reales de la aplicación.

Uso:  python generar_manual.py
"""
import os
import sys
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('QT_QPA_FONTDIR', r'C:\Windows\Fonts')
sys.dont_write_bytecode = True
BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

from PySide6.QtCore import QMarginsF, QSizeF, QUrl
from PySide6.QtGui import QFont, QPageLayout, QPageSize, QPdfWriter, QTextDocument
from PySide6.QtWidgets import QApplication

import main
from afd_core import EXAMPLES, serialize

OUT = BASE / 'docs' / 'Manual_de_usuario.pdf'


def capture(app, window, width=1330, height=1320):
    window.resize(width, height); app.processEvents(); app.processEvents()
    return window.grab().toImage()


def build_images(app):
    w = main.Studio(); w.show(); app.processEvents()
    images = {}
    w.import_file(BASE / 'ejemplos' / 'ejemplo_catedratico.txt')
    images['inicio'] = capture(app, w)
    w.words.selectRow(0); w.select_word(force=True); w.forward(); w.forward()
    images['simulacion'] = capture(app, w)
    while w.next.isEnabled(): w.forward()
    images['final'] = capture(app, w)
    w.edit_afd(); images['editor'] = capture(app, w, height=900); w.overlay.close_overlay()
    w.about(); images['acerca'] = capture(app, w, height=900); w.overlay.close_overlay()
    w.close()
    return images


def img(name, width=640):
    return f'<p align="center"><img src="{name}" width="{width}"></p>'


def html():
    integrantes = ''.join(f'<tr><td>{n}</td><td>{c}</td></tr>' for n, c in [
        ('Roger Felipe Sosa Osorio', '1890-17-8391'),
        ('Ever Misael Lopez Perez', '1890-24-3260'),
        ('Vieri Alexander Ixtecoc López', '1890-23-3479'),
        ('Henry Leonel Perez Cruz', '1890-24-4996'),
        ('Edgar Emanuel Contreras Gaitan', '1890-17-17069'),
        ('Dennis Rodrigo Melgar Perez', '1890-24-9352')])
    ejemplo = serialize(EXAMPLES[0]).replace('&', '&amp;').replace('<', '&lt;')
    return f'''
<html><body style="font-family:'Segoe UI'; font-size:10pt; color:#1d1d1f;">
<h1 align="center" style="font-size:22pt;">Simulador de Autómatas Finitos Deterministas</h1>
<h2 align="center" style="font-size:15pt; color:#555;">Manual de usuario</h2>
<p align="center">Universidad Mariano Gálvez de Guatemala<br>Curso: Autómatas y Lenguajes Formales<br>Octubre de 2026</p>
<table align="center" border="1" cellspacing="0" cellpadding="5" style="border-color:#ccc;">
<tr style="background:#eef2f7;"><th>Integrante</th><th>Carné</th></tr>{integrantes}</table>

<h2>1. Instalación</h2>
<ol>
<li>Ejecute <b>Instalador_Simulador_AFD.exe</b>.</li>
<li>Elija la carpeta de instalación (o deje la predeterminada) y, si lo desea, marque <i>Crear un acceso directo en el escritorio</i>.</li>
<li>Al finalizar, abra la aplicación desde el menú Inicio o el escritorio: <b>Simulador AFD</b>.</li>
</ol>
<p>No es necesario instalar Python ni Graphviz: el instalador ya incluye todo lo que la aplicación necesita.
Para desinstalar use <i>Configuración → Aplicaciones</i> de Windows.</p>

<h2>2. Pantalla principal</h2>
{img('inicio')}
<ul>
<li><b>Diagrama del autómata</b> (izquierda): dibujo del AFD generado con Graphviz. La flecha sin origen indica el estado inicial y el doble círculo, los estados de aceptación.</li>
<li><b>Evaluar cadenas</b> (derecha): tabla con todas las cadenas del archivo y su resultado (<span style="color:#1a7f37;">Aceptada</span> / <span style="color:#c62828;">Rechazada</span>), y la lista de derivaciones paso a paso.</li>
<li><b>Tabla de transiciones</b> (abajo): una fila por estado y una columna por símbolo. «→» marca el estado inicial y «◎» los estados finales; «—» indica que no hay transición.</li>
</ul>

<h2>3. Menús</h2>
<table border="1" cellspacing="0" cellpadding="5" style="border-color:#ccc;" width="100%">
<tr style="background:#eef2f7;"><th>Menú</th><th>Opción</th><th>Función</th></tr>
<tr><td rowspan="4">Archivo</td><td>Abrir TXT (Ctrl+O)</td><td>Abre el explorador para elegir el archivo .txt con la definición del AFD.</td></tr>
<tr><td>Nuevo (Ctrl+E)</td><td>Abre un editor en pantalla para escribir o modificar la definición. «Crear desde cero» carga una plantilla; «Aplicar cambios» carga el AFD.</td></tr>
<tr><td>Guardar TXT (Ctrl+S)</td><td>Guarda en un archivo .txt el AFD que está en pantalla.</td></tr>
<tr><td>Salir</td><td>Cierra la aplicación.</td></tr>
<tr><td>Ejemplos</td><td>Termina en 11 · Contiene ab · Cantidad par de 1</td><td>Cargan tres AFD de ejemplo sin necesidad de abrir archivos.</td></tr>
<tr><td rowspan="3">Acerca de</td><td>Acerca de</td><td>Curso, universidad, fecha e integrantes del grupo.</td></tr>
<tr><td>Ayuda</td><td>Resumen rápido de uso dentro de la aplicación.</td></tr>
<tr><td>Manual de usuario (PDF)</td><td>Abre este documento.</td></tr>
</table>

<h2>4. Simulación paso a paso</h2>
<ol>
<li>Cargue un AFD (Archivo → Abrir TXT, o el menú Ejemplos).</li>
<li>Haga clic en una cadena de la tabla <b>Evaluar cadenas</b>, o escriba una nueva en <i>Cadena para evaluar</i> y presione <b>Evaluar</b>.</li>
<li>Use los controles debajo del diagrama:
  <ul>
  <li><b>Siguiente →</b>: lee el siguiente símbolo.</li>
  <li><b>← Anterior</b>: retrocede un paso.</li>
  <li><b>▶ Reproducir</b>: avanza automáticamente (clic derecho para cambiar la velocidad).</li>
  <li><b>Reiniciar</b>: vuelve al estado inicial.</li>
  </ul></li>
</ol>
<p>En cada paso:</p>
<ul>
<li>En el <b>diagrama</b>, el estado actual y la flecha recién usada se pintan de <b>verde</b>; lo recorrido queda en verde claro.</li>
<li>En la <b>tabla de transiciones</b> se resalta la fila del estado actual y la celda de la transición aplicada.</li>
<li>Debajo de los botones se indica <i>Paso X de N · Estado · Símbolo leído</i>.</li>
</ul>
{img('simulacion')}
<p>Al terminar de leer la cadena se muestra si fue <b>aceptada</b> (el último estado es de aceptación) o <b>rechazada</b>:</p>
{img('final')}
<p>Si la cadena contiene un símbolo que no está en el alfabeto, o el autómata llega a una transición no definida, la cadena se rechaza y se explica el motivo.</p>
<p>Diagrama: rueda del mouse para acercar o alejar, arrastrar para desplazar, clic derecho para <i>Ajustar diagrama</i>.</p>

<h2>5. Formato del archivo de entrada</h2>
<p>Formato con <b>matriz de transiciones</b> (una fila por estado, en el orden de <i>Estados</i>; una columna por símbolo, en el orden de <i>Simbolos</i>; «-» = sin transición):</p>
<pre style="background:#f4f5f7;">Simbolos: 0,1
Estados: Q0,Q1,Q2,Q3
Estado inicial: Q0
Estados de aceptacion: Q0
Transiciones:
Q2,Q1
Q3,Q0
Q0,Q3
Q1,Q2
Cadenas a analizar:
1,0,0,1
0,0,1,0,1</pre>
<p>Formato con <b>lista de transiciones</b> (origen, símbolo, destino), que es el que usa la opción Guardar:</p>
<pre style="background:#f4f5f7;">{ejemplo}</pre>
<p>Notas: los símbolos son de un carácter (letras, dígitos u otros). Las cadenas pueden escribirse juntas (<i>1001</i>) o separadas por comas (<i>1,0,0,1</i>).
«ε» o «vacia» representa la cadena vacía. Las líneas que inician con # son comentarios.
En la carpeta de instalación, dentro de <b>ejemplos</b>, hay archivos de prueba listos para abrir.</p>

<h2>6. Editor (Archivo → Nuevo)</h2>
{img('editor', 560)}
<p>Escriba la definición con cualquiera de los formatos anteriores y presione <b>Aplicar cambios</b>. Si hay un error, se indica debajo del editor. Luego use <b>Archivo → Guardar TXT</b> para guardarlo.</p>

<h2>7. Acerca de</h2>
{img('acerca', 560)}
</body></html>'''


def run():
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyle('Fusion'); app.setFont(QFont('Segoe UI', 10))
    images = build_images(app)
    doc = QTextDocument(); doc.setDefaultFont(QFont('Segoe UI', 10))
    for name, image in images.items():
        doc.addResource(QTextDocument.ResourceType.ImageResource, QUrl(name), image)
    doc.setHtml(html())
    OUT.parent.mkdir(exist_ok=True)
    writer = QPdfWriter(str(OUT)); writer.setResolution(96)
    writer.setTitle('Manual de usuario - Simulador AFD'); writer.setCreator('Simulador AFD')
    writer.setPageLayout(QPageLayout(QPageSize(QPageSize.PageSizeId.Letter), QPageLayout.Orientation.Portrait,
                                     QMarginsF(15, 15, 15, 15), QPageLayout.Unit.Millimeter))
    doc.setPageSize(QSizeF(writer.width(), writer.height()))
    doc.print_(writer)
    print('Manual generado en', OUT)


if __name__ == '__main__':
    run()
