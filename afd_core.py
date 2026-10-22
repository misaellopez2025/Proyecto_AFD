"""Motor de autómatas deterministas. Independiente de la interfaz gráfica."""
import copy
import json
import re
import unicodedata

ALLOWED_SYMBOLS = ('a','b','0','1')
# Valores que en una fila de la matriz significan "sin transición".
NO_TRANSITION = ('-','—','–','∅','_')
RESERVED_SYMBOL_CHARS = ',;'


def word_group(word):
    # Todas las cadenas forman un único grupo; cualquier alfabeto es válido.
    return 'empty' if not word else 'letters'


def symbol_names(symbols):
    names = [f'«{symbol}»' for symbol in symbols]
    return names[0] if len(names) == 1 else ', '.join(names[:-1])+' y '+names[-1]


EXAMPLES = [
    dict(name='Termina en 11', states=['q0','q1','q2'], alphabet=['0','1'], initial='q0', finals=['q2'],
         transitions={'q0':{'0':'q0','1':'q1'},'q1':{'0':'q0','1':'q2'},'q2':{'0':'q0','1':'q2'}},words=['11','1011','100','111','']),
    dict(name='Contiene ab', states=['q0','q1','q2'], alphabet=['a','b'],initial='q0', finals=['q2'],
         transitions={'q0':{'a':'q1','b':'q0'},'q1':{'a':'q1','b':'q2'},'q2':{'a':'q2','b':'q2'}},words=['ab','aabb','baba','bbbb','']),
    dict(name='Cantidad par de 1', states=['par','impar'],alphabet=['0','1'],initial='par',finals=['par'],
         transitions={'par':{'0':'par','1':'impar'},'impar':{'0':'impar','1':'par'}},words=['','0','11','101','111'])
]

DEFAULT_AFD = dict(
    name='Números o letras', states=['q0','q1','q2'], alphabet=list(ALLOWED_SYMBOLS),
    initial='q0', finals=['q1','q2'],
    transitions={
        'q0':{symbol:'q1' for symbol in ALLOWED_SYMBOLS},
        'q1':{symbol:'q2' for symbol in ALLOWED_SYMBOLS},
        'q2':{symbol:'q2' for symbol in ALLOWED_SYMBOLS},
    }, words=['0101','ababa','0','a',''])

def validate(a):
    if not isinstance(a,dict):raise ValueError('La definición del AFD debe ser un objeto.')
    states, alphabet = a.get('states'), a.get('alphabet')
    if not isinstance(states,list) or not states or any(not isinstance(s,str) or not s.strip() for s in states) or len(set(states))!=len(states):
        raise ValueError('La lista de estados no es válida.')
    if len(states)>60: raise ValueError('Máximo 60 estados para visualizar.')
    if not isinstance(alphabet,list) or not alphabet or any(not isinstance(s,str) or len(s)!=1 for s in alphabet) or len(set(alphabet))!=len(alphabet):
        raise ValueError('El alfabeto debe contener símbolos de un carácter, sin repetir.')
    unsupported = [symbol for symbol in alphabet if symbol.isspace() or symbol in RESERVED_SYMBOL_CHARS]
    if unsupported:
        raise ValueError('Los símbolos del alfabeto no pueden ser espacios, comas ni punto y coma.')
    if a.get('initial') not in states: raise ValueError('El estado inicial no existe.')
    if not isinstance(a.get('finals'),list) or any(s not in states for s in a['finals']): raise ValueError('Estados finales incorrectos.')
    trans=a.setdefault('transitions',{})
    if not isinstance(trans,dict):raise ValueError('Las transiciones deben ser un objeto.')
    if any(s not in states for s in trans):raise ValueError('Hay transiciones desde estados inexistentes.')
    for state in states:
        row = trans.setdefault(state,{})
        if not isinstance(row,dict):raise ValueError('Fila de transiciones incorrecta: '+state)
        if any(sym not in alphabet for sym in row):raise ValueError('Hay transiciones con símbolos ajenos al alfabeto.')
        # Las transiciones no definidas se permiten: la cadena se rechaza al llegar ahí.
        for sym,target in row.items():
            if target not in states:
                raise ValueError(f'El destino de δ({state}, {sym}) = {target} no es un estado definido.')
    a.setdefault('words',[])
    if not isinstance(a['words'],list) or any(not isinstance(w,str) for w in a['words']):raise ValueError('Las cadenas deben ser una lista de textos.')
    if 'name' in a and not isinstance(a['name'],str):raise ValueError('El nombre debe ser un texto.')
    return a

def trace(a, word):
    path=[a['initial']]
    for ch in word:
        if ch not in a['alphabet']:
            character = {' ':'un espacio','\t':'una tabulación','\n':'un salto de línea','\r':'un salto de línea'}.get(ch,f'«{ch}»')
            error = f'Rechazada: la cadena contiene {character}, que no pertenece al alfabeto ({symbol_names(a["alphabet"])}).'
            return dict(path=path,valid=False,accepted=False,error=error)
        target = a['transitions'].get(path[-1],{}).get(ch)
        if target is None:
            error = f'Rechazada: no existe la transición δ({path[-1]}, {ch}); el autómata se detiene.'
            return dict(path=path,valid=False,accepted=False,error=error)
        path.append(target)
    return dict(path=path,valid=True,accepted=path[-1] in a['finals'],error='')

def serialize(a):
    def items(values):
        # Quoted JSON lists preserve delimiter symbols and unusual state names.
        if any(re.search(r'[,;\s\[\]"\\]',v) for v in values):
            return json.dumps(values,ensure_ascii=False)
        return ','.join(values)
    def transition(s,c,target):
        values=[s,c,target]
        if any(re.search(r'[,;\s\[\]"\\]',v) for v in values):
            return json.dumps(values,ensure_ascii=False)
        return ','.join(values)
    def word_text(w):
        if not w:return '""' if 'ε' in a['alphabet'] else 'ε'
        if (w.strip()!=w or w.startswith(('#','//','"')) or ',' in w or ';' in w or '\n' in w or '\r' in w
            or w.lower() in ('ε','epsilon','lambda','λ','vacia','vacio','vacía','vacío')
            or re.match(r'^[^:]+:',w)):
            return json.dumps(w,ensure_ascii=False)
        return w
    return '\n'.join(['# AFD Studio Python', 'nombre: '+a.get('name','Autómata'),'estados: '+items(a['states']),
      'alfabeto: '+items(a['alphabet']),'inicial: '+a['initial'],'finales: '+items(a['finals']),'transiciones:',
      *[transition(s,c,a['transitions'][s][c]) for s in a['states'] for c in a['alphabet'] if c in a['transitions'].get(s,{})], 'cadenas:',
      *[word_text(w) for w in a['words']]])+'\n'

def parse_txt(content, current=None):
    text=content.lstrip('\ufeff').replace('\r\n','\n').replace('\r','\n')
    stripped=text.strip()
    if not stripped: raise ValueError('El archivo TXT está vacío.')
    if stripped.startswith('{'): return validate(json.loads(stripped))
    lines=[line.strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith(('#','//'))]
    obj=dict(name='Autómata importado',states=[],alphabet=[],initial='',finals=[],transitions={},words=[])
    mode=None; matrix=[]; recognized=False; orphan_lines=[]; definition=False
    def norm(s):
        return ' '.join(''.join(c for c in unicodedata.normalize('NFD',s.lower()) if unicodedata.category(c)!='Mn').replace('_',' ').replace('-',' ').split())
    def terms(s):
        if s.strip().startswith('['):
            values=json.loads(s)
            if not isinstance(values,list) or any(not isinstance(x,str) for x in values):raise ValueError('La lista debe contener textos entre comillas.')
            return values
        return [x for x in re.split(r'[,;\s]+',s.strip()) if x]
    def word(s):
        if s.startswith('"') and s!='""':
            value=json.loads(s)
            if not isinstance(value,str):raise ValueError('La cadena entre comillas debe ser un texto.')
            return value
        if norm(s) in ('ε','epsilon','lambda','λ','""',"''",'vacia','vacio'):return ''
        return ''.join(part.strip() for part in re.split(r'[,;]',s)) if ',' in s or ';' in s else s
    def add_transition(s):
        m=re.match(r'^\s*(?:δ\s*\(\s*)?([^,\s()=→-]+)\s*,\s*([^,\s()=→-]+)\s*\)?\s*(?:=|->|→)\s*([^,\s()]+)\s*$',s)
        if m: origin,symbol,target=m.groups()
        else:
            fields=terms(s)
            if len(fields)!=3 or (obj['states'] and fields[0] not in obj['states']) or (obj['alphabet'] and fields[1] not in obj['alphabet']):
                matrix.append(s);return
            origin,symbol,target=fields
        row=obj['transitions'].setdefault(origin,{})
        if symbol in row:raise ValueError(f'Transición repetida: δ({origin}, {symbol}).')
        row[symbol]=target
    keymap={
      'nombre':'name','name':'name','estados':'states','states':'states','alfabeto':'alphabet','simbolos':'alphabet','simbolo':'alphabet','alphabet':'alphabet',
      'inicial':'initial','estado inicial':'initial','initial':'initial',
      'finales':'finals','estados finales':'finals','estados de aceptacion':'finals','estados aceptacion':'finals','aceptacion':'finals',
      'transiciones':'transitions','transitions':'transitions','funcion de transicion':'transitions','tabla de transiciones':'transitions',
      'cadenas':'words','cadenas a analizar':'words','cadenas a procesar':'words','palabras':'words','words':'words','cadenas de entrada':'words'}
    for line in lines:
        m=re.match(r'^([^:]+):\s*(.*)$',line)
        key=keymap.get(norm(m.group(1))) if m else None
        if key:
            recognized=True;val=m.group(2)
            if key != 'words': definition=True
            if key in ('states','alphabet','finals'):obj[key]=terms(val);mode=None
            elif key in ('name','initial'):obj[key]=val or obj[key];mode=None
            elif key=='transitions':mode='transitions';add_transition(val) if val else None
            else:mode='words';obj['words'].append(word(val)) if val else None
        elif mode=='transitions':add_transition(line)
        elif mode=='words':obj['words'].append(word(line))
        else:
            # Plain words are permitted only if there is no AFD definition in the file.
            if recognized:raise ValueError('Línea TXT no reconocida: '+line)
            orphan_lines.append(line)
    if recognized and orphan_lines:raise ValueError('Línea TXT no reconocida: '+orphan_lines[0])
    if not definition:
        if current is None:raise ValueError('El TXT no define un AFD y no hay autómata seleccionado.')
        a=copy.deepcopy(current);a['words']=obj['words'] if recognized else [word(line) for line in lines];return validate(a)
    if matrix:
        if obj['transitions']:raise ValueError('No mezcle listas de transiciones con filas de matriz.')
        if len(matrix)!=len(obj['states']):raise ValueError('La cantidad de filas de la matriz no coincide con los estados.')
        for state,row in zip(obj['states'],matrix):
            dest=terms(row)
            if len(dest)==len(obj['alphabet'])+1 and dest[0]==state:dest=dest[1:]
            if len(dest)!=len(obj['alphabet']):raise ValueError('Fila de matriz inválida: '+row)
            obj['transitions'].setdefault(state,{}).update((c,t) for c,t in zip(obj['alphabet'],dest) if t not in NO_TRANSITION)
    return validate(obj)
