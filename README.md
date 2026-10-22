# Simulador AFD

Aplicación de escritorio que simula paso a paso un **Autómata Finito Determinista**.
Proyecto del curso Autómatas y Lenguajes Formales — Universidad Mariano Gálvez de Guatemala, octubre de 2026.

## Funciones
- Carga del AFD desde archivo `.txt` (símbolos, estados, estado inicial, estados de aceptación, transiciones y cadenas).
- Diagrama del AFD con Graphviz, resaltando el estado y la transición de cada paso.
- Tabla de transiciones dinámica.
- Tabla de cadenas con su resultado (Aceptada / Rechazada).
- Controles: Anterior, Siguiente, Reproducir y Reiniciar.
- Menús: Archivo (Abrir, Nuevo, Guardar, Salir), Ejemplos (3 AFD) y Acerca de (Acerca de, Ayuda, Manual PDF).

## Instalación
Descargue `Instalador_Simulador_AFD.exe` desde la sección **Releases** de este repositorio y ejecútelo.
No requiere Python ni Graphviz instalados.

## Ejecutar desde el código
```powershell
powershell -ExecutionPolicy Bypass -File CONFIGURAR.ps1
.\INICIAR.bat
```

## Generar el instalador
Requiere Python 3.10+ e Inno Setup 6 (`winget install JRSoftware.InnoSetup`).
```powershell
powershell -ExecutionPolicy Bypass -File CONSTRUIR_INSTALADOR.ps1
```
El resultado queda en `instalador\Instalador_Simulador_AFD.exe`.

## Formato del archivo de entrada
```
Simbolos: 0,1
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
0,0,1,0,1
```
Cada fila de `Transiciones` corresponde a un estado (en el orden de `Estados`) y cada columna a un símbolo. Use `-` si no hay transición.
Más ejemplos en la carpeta [`ejemplos/`](ejemplos/). El manual completo está en [`docs/Manual_de_usuario.pdf`](docs/Manual_de_usuario.pdf).

## Integrantes
| Nombre | Carné |
|---|---|
| Roger Felipe Sosa Osorio | 1890-17-8391 |
| Ever Misael Lopez Perez | 1890-24-3260 |
| Vieri Alexander Ixtecoc López | 1890-23-3479 |
| Henry Leonel Perez Cruz | 1890-24-4996 |
| Edgar Emanuel Contreras Gaitan | 1890-17-17069 |
| Dennis Rodrigo Melgar Perez | 1890-24-9352 |
