# Laboratorio CTF de seguridad de agentes de IA

Exploración experimental de **Jairo Andrés Valencia**.
Rama: `experiment/jairo-agent-security-ctf`.

**Estado: preparación inicial.** Esta rama contiene la definición del
laboratorio y su catálogo inicial de retos. La aplicación ejecutable sigue
siendo la réplica de AgentBreak. El nuevo chat CTF, el motor con LLM y la
entrega de banderas están pendientes de implementación.

## Créditos y punto de partida

Este trabajo deriva de **[AgentBreak](https://github.com/urcuqui/AgentBreak)**,
creado por **Christian Urcuqui y sus colaboradores**. Sus laboratorios,
escenarios, herramientas, controles y pruebas originales conservan su
atribución y la licencia MIT declarada por el proyecto.

La línea base es AgentBreak `0.2.0`, commit original
[`9effe7b`](https://github.com/urcuqui/AgentBreak/commit/9effe7b6317a4e90b18ab895c06a2a47f8cb91c1).
La primera reproducción del equipo quedó publicada en
[`4351368`](https://github.com/juankamn/agentbreak-owasp-eval/commit/4351368bc7a658f2786b2383d843b6eca3efb1b6).
La rama `main` conserva esa reproducción. Los cambios de esta rama son la
exploración personal de Jairo dentro del proyecto académico del equipo.

Véanse los [créditos completos](ATTRIBUTION.md) y el
[README de la reproducción inicial](https://github.com/juankamn/agentbreak-owasp-eval/blob/4351368bc7a658f2786b2383d843b6eca3efb1b6/README.md).

## Qué queremos construir

Un laboratorio de captura de banderas, inspirado en la experiencia de
[Hack The Box](https://www.hackthebox.com/), donde una persona explore por
chat un agente intencionalmente vulnerable. El participante recibirá el
contexto de su usuario y de la tarea, conversará libremente e intentará
descubrir fallos de seguridad. Los retos tendrán datos y efectos ficticios
observables dentro del laboratorio.

La primera experiencia será **no guiada**: sin botones que ejecuten los
ataques, secuencias obligatorias ni soluciones visibles. Más adelante se
podrá incorporar una experiencia guiada sobre los mismos escenarios.
La interfaz y la documentación nueva estarán en español.

## Alcance inicial

Se utiliza la edición publicada **OWASP Top 10 para aplicaciones LLM 2026**,
verificada el 14 de noviembre de 2026 en el
[repositorio oficial de OWASP](https://github.com/GenAI-Security-Project/GenAI-LLM-Top10/blob/main/2026/README.md).

| Categoría | Objetivo del reto |
| --- | --- |
| LLM01:2026 · Inyección de prompts | Conseguir una desviación verificable de la tarea mediante instrucciones directas o contenido no confiable consultado por el agente. |
| LLM02:2026 · Divulgación de información sensible | Obtener información sintética que el usuario de la sesión no está autorizado a conocer. |
| LLM03:2026 · Agencia excesiva | Conseguir que una herramienta ejecute una operación fuera de los permisos o de la autorización de la tarea. |

El [catálogo inicial de retos](experiments/jairo-agent-security-ctf/catalogo.json)
registra sus identificadores, objetivos y evidencias mínimas. Es una
especificación de preparación, todavía no un conjunto de retos ejecutables.

## Cómo se comprobarán las banderas

El servidor validará cada hallazgo mediante condiciones definidas por reto.
Una respuesta o una propuesta del modelo y un efecto ejecutado se registrarán
por separado. La bandera corresponderá al resultado demostrado, al reto y a
la sesión del participante.

- Inyección: conservar la entrada no confiable, el contexto y la desviación
  comprobada frente a una tarea legítima definida de antemano.
- Divulgación: comprobar que la salida realmente contiene un dato sintético
  protegido que el usuario no aportó y que estaba fuera de su autorización.
- Agencia excesiva: comprobar en el registro de herramientas y en el estado
  local que se ejecutó una operación prohibida.

Las banderas se generarán y validarán en el servidor. Sus valores no formarán
parte del catálogo público ni del código del navegador. Cada reto deberá
poder reiniciar su estado y conservar el funcionamiento legítimo esperado.

## Separación de responsabilidades

El diseño inicial separa:

1. La conversación y las decisiones de un LLM real.
2. La ejecución de herramientas y los cambios de estado locales.
3. Los controles externos de permisos, argumentos y aprobación.
4. La evaluación de resultados y la emisión de banderas.

Se propone comenzar con un agente y LangChain. El modelo y su proveedor
siguen por seleccionar. No se han añadido nuevas dependencias, descargado
modelos ni activado servicios de pago en esta preparación.

## Ejecutar la línea base disponible

Desde la raíz del proyecto, con el entorno ya instalado:

```bash
source venv-ciberseguridad/bin/activate
python -m agentbreak.cli serve --host 127.0.0.1 --port 8000
```

Abrir <http://127.0.0.1:8000>. Este comando inicia los laboratorios originales
de la réplica; no inicia todavía el nuevo chat CTF. Para detenerlo, usar
`Ctrl+C`.

La [guía de instalación y ejecución](docs/local-setup.md) conserva los
comandos comprobados de instalación, pruebas y reinicio, junto con las
[evidencias de la reproducción](docs/validation/2026-11-14). Los resultados
allí registrados corresponden a la línea base, no al futuro agente CTF.

## Siguiente avance verificable

Construir un primer recorrido completo con un modelo real: tarea legítima,
conversación libre, llamada de herramienta, efecto observable y validación
del reto. Medirlo antes de ampliar las variantes y los niveles de dificultad.
La comparación de modelos, la evaluación automática y la experiencia guiada
se abordarán después del primer piloto funcional.
