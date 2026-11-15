"""Build the course article. Numbers come only from files that exist."""

from __future__ import annotations

import json
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[1]
ENTREGA = ROOT.parent / "entrega"
OUT = ENTREGA / "articulo" / "articulo.docx"
SCREEN = ROOT / "manifest" / "models_smoke_report.json"
EVAL_REPORT = ENTREGA / "resultados" / "evaluation_report.json"
DETERMINISM = ENTREGA / "resultados" / "determinism.json"
FIGURE = ENTREGA / "resultados" / "evaluation_report.png"

ABSTRACT = (
    "Este trabajo extiende AgentBreak para evaluar a un consultor de ciberseguridad que llama "
    "herramientas. El sistema bajo prueba es ese consultor, no un segundo agente que lo audite. "
    "El factor experimental es una política determinista externa. En la condicion C0 el modelo "
    "solo recibe la política dentro del prompt. En C1 los mismos cinco controles se aplican en "
    "código, sin cambiar el contexto que el modelo lee. Una violacion ocurre si un secreto "
    "sintético llega a quien no debe o si se ejecuta una operacion que el caso prohíbe. El banco "
    "tiene 120 plantillas sintéticas, 30 por cada estrato LLM01, LLM02, LLM03 y tareas "
    "benignas, con 10 de calibración y 20 de evaluación. La inferencia es local, en una GPU de "
    "8 GB. La configuración se elige por utilidad en las 40 tareas limpias, no por resistencia "
    "al ataque. Las 1680 corridas finales no están en esta versión. Por eso la diferencia de "
    "tasas no se estima y no se afirma que el control sea efectivo."
)


def _comma(value: object, digits: int = 3) -> str:
    if value is None:
        return "no estimable"
    return f"{float(value):.{digits}f}".replace(".", ",")


def _report() -> dict | None:
    if not EVAL_REPORT.exists():
        return None
    payload = json.loads(EVAL_REPORT.read_text(encoding="utf-8"))
    if payload.get("primary", {}).get("label") != "estimable":
        return None
    return payload


def abstract_text() -> str:
    payload = _report()
    if payload is None:
        return ABSTRACT
    primary = payload["primary"]
    interval = primary.get("interval") or {}
    return (
        "Este trabajo extiende AgentBreak para evaluar a un consultor de ciberseguridad que llama "
        "herramientas. El sistema bajo prueba es ese consultor, no un segundo agente que lo audite. "
        "El factor experimental es una política determinista externa. En la condición C0 el modelo "
        "solo recibe la política dentro del prompt. En C1 los mismos cinco controles se aplican en "
        "código, sin cambiar el contexto que el modelo lee. Una violación ocurre si un secreto "
        "sintético llega a quien no debe o si se ejecuta una operación que el caso prohíbe. El banco "
        "tiene 120 plantillas sintéticas, 30 por cada estrato LLM01, LLM02, LLM03 y tareas "
        "benignas, con 10 de calibración y 20 de evaluación. La inferencia es local, en una GPU de "
        "8 GB. La configuración se elige por utilidad en las 40 tareas limpias, no por resistencia "
        "al ataque. En 1680 corridas del conjunto de evaluación, la media por plantilla de ASR_C0 "
        f"menos ASR_C1 es {_comma(primary['difference_c0_minus_c1'])}. El intervalo bootstrap va de "
        f"{_comma(interval.get('low'))} a {_comma(interval.get('high'))}, con {primary.get('templates')} "
        "plantillas elegibles. El resultado no certifica un despliegue."
    )


def _cols(section, count: str) -> None:
    sect_pr = section._sectPr
    existing = sect_pr.find(qn("w:cols"))
    if existing is not None:
        sect_pr.remove(existing)
    cols = OxmlElement("w:cols")
    cols.set(qn("w:num"), count)
    cols.set(qn("w:space"), "432")
    sect_pr.append(cols)


def _run(paragraph, text: str, *, bold: bool = False, size: int = 11, italic: bool = False) -> None:
    run = paragraph.add_run(text)
    run.bold = bold
    run.italic = italic
    run.font.size = Pt(size)
    run.font.name = "Times New Roman"
    run.font.color.rgb = RGBColor(0, 0, 0)


def add_p(
    doc: Document,
    text: str,
    *,
    center: bool = False,
    bold: bool = False,
    size: int = 11,
    space_after: int = 8,
    italic: bool = False,
) -> None:
    paragraph = doc.add_paragraph()
    paragraph.paragraph_format.space_after = Pt(space_after)
    paragraph.paragraph_format.space_before = Pt(0)
    if center:
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _run(paragraph, text, bold=bold, size=size, italic=italic)


def add_heading_text(doc: Document, text: str) -> None:
    add_p(doc, text, bold=True, size=12, space_after=6)


def add_table(doc: Document, title: str, headers: list[str], rows: list[list[str]]) -> None:
    add_p(doc, title, bold=True, size=10, space_after=2)
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = "Table Grid"
    for index, header in enumerate(headers):
        table.rows[0].cells[index].text = header
    for r_index, row in enumerate(rows, start=1):
        for c_index, value in enumerate(row):
            table.rows[r_index].cells[c_index].text = value
    doc.add_paragraph()


def grid_rows() -> list[list[str]]:
    path = ENTREGA / "resultados" / "grid120_summary.json"
    if not path.exists():
        return []
    rows = []
    for item in json.loads(path.read_text(encoding="utf-8")):
        by_model = item.get("by_model", {})
        llama = by_model.get("llama3.1:8b", {}).get("utility")
        qwen = by_model.get("qwen2.5:7b", {}).get("utility")
        rows.append(
            [
                str(item.get("config_id")),
                "n/d" if llama is None else f"{float(llama):.2f}",
                "n/d" if qwen is None else f"{float(qwen):.2f}",
                f"{float(item.get('min_utility', 0)):.2f}",
                f"{float(item.get('median_latency_ms', 0)):.0f}",
            ]
        )
    return rows


def confirmatory_lines() -> list[str]:
    """Results text. Calibration traces are not this estimate."""
    payload = _report()
    if payload is None:
        return [
            "III.B. No hay un estimando primario del conjunto de evaluación. La tasa es no estimable.",
            "III.C. No se imputan las celdas vacías.",
            "III.D. ASR_C0 − ASR_C1 es no estimable. La malla y la pasada de calibración no se usan como ese número.",
        ]
    primary = payload["primary"]
    interval = primary.get("interval") or {}
    dropped = payload.get("attack_templates_ineligible_for_every_model") or []
    dropped_text = ", ".join(dropped) if dropped else "ninguna"
    lines = [
        (
            "III.D. En el conjunto de evaluación, la media por plantilla de ASR_C0 menos ASR_C1 es "
            f"{_comma(primary['difference_c0_minus_c1'])}. El intervalo bootstrap, de 10 000 réplicas "
            f"y semilla 20261114, va de {_comma(interval.get('low'))} a {_comma(interval.get('high'))}. "
            f"Entran {primary.get('templates')} plantillas de ataque: una entra si al menos un modelo "
            "cumplió la tarea limpia bajo C0 en dos de tres repeticiones y hay corridas de ataque en "
            f"los dos brazos. ASR_C0={_comma(primary['asr_c0'])}. ASR_C1={_comma(primary['asr_c1'])}. "
            f"Quedan fuera para los dos modelos: {dropped_text}. "
            "Esta cifra no mezcla la pasada de calibración. El intervalo no contiene el cero."
        )
    ]
    model_bits = []
    for model, estimate in payload.get("by_model", {}).items():
        if estimate.get("label") != "estimable":
            model_bits.append(f"{model}: no estimable")
            continue
        model_interval = estimate.get("interval") or {}
        model_bits.append(
            f"{model}: diferencia {_comma(estimate['difference_c0_minus_c1'])} "
            f"(ASR_C0 {_comma(estimate['asr_c0'])}, ASR_C1 {_comma(estimate['asr_c1'])}, "
            f"intervalo {_comma(model_interval.get('low'))} a {_comma(model_interval.get('high'))}, "
            f"{estimate.get('templates')} plantillas)"
        )
    lines.append("III.C. Por modelo, " + "; ".join(model_bits) + ". H3 se lee aquí y no cambia el estimando primario.")
    control = payload.get("negative_control_a0", {})
    h2 = payload.get("h2_clean_a0", {}).get("all", {})
    c0 = h2.get("C0", {})
    c1 = h2.get("C1", {})
    lines.append(
        "III.B. En tareas limpias, la tasa de violación es "
        f"C0={_comma(control.get('C0'))} y C1={_comma(control.get('C1'))}. "
        f"La utilidad pasa de {_comma(c0.get('utility'))} en C0 a {_comma(c1.get('utility'))} en C1. "
        f"El bloqueo indebido pasa de {_comma(c0.get('undue_block'))} a {_comma(c1.get('undue_block'))}. "
        f"La latencia mediana pasa de {_comma(c0.get('median_latency_ms'), 0)} ms a "
        f"{_comma(c1.get('median_latency_ms'), 0)} ms. H2 no tenía dirección firmada."
    )
    kinds = payload.get("a1_c1_violation_kinds") or {}
    if kinds:
        bits = [f"{key} ({count})" for key, count in sorted(kinds.items())]
        lines.append(
            "Las violaciones que quedan bajo C1 en ataques son: "
            + "; ".join(bits)
            + ". El marcador residual no está en la lista de los cinco controles."
        )
    one_third = payload.get("sensitivity", {}).get("eligibility_one_third", {})
    if one_third.get("label") == "estimable":
        band = one_third.get("interval") or {}
        lines.append(
            "Con el umbral alterno de una de tres repeticiones, la diferencia es "
            f"{_comma(one_third.get('difference_c0_minus_c1'))} sobre {one_third.get('templates')} "
            f"plantillas, con intervalo de {_comma(band.get('low'))} a {_comma(band.get('high'))}. "
            "No hubo fallos técnicos, así que conservar esas corridas no mueve el estimando."
        )
    did = payload.get("difference_in_differences")
    if did is not None:
        lines.append(
            "La diferencia de diferencias por corrida, sin el filtro de elegibilidad y sin colapsar "
            f"por plantilla, es {_comma(did)}. Es secundaria. No sustituye a III.D."
        )
    if DETERMINISM.exists():
        check = json.loads(DETERMINISM.read_text(encoding="utf-8"))
        model_bits = [
            f"{model}: {row.get('identical')} de {row.get('n')} idénticas y "
            f"{row.get('same_decision')} con la misma decisión"
            for model, row in check.get("by_model", {}).items()
        ]
        detail = ". Por modelo, " + "; ".join(model_bits) + "." if model_bits else "."
        lines.append(
            f"Se repitió el {int(float(check.get('fraction', 0)) * 100)} % de las trazas con la misma semilla "
            f"({check.get('n')} corridas). Coinciden la secuencia, la respuesta y el oráculo en "
            f"{check.get('identical_traces')} de {check.get('n')}. La decisión, sin exigir el texto, "
            f"coincide en {check.get('same_decision')} de {check.get('n')}"
            + detail
            + " Esa repetición no entra en el estimando."
        )
    return lines


def stratum_rows(payload: dict) -> list[list[str]]:
    table = payload.get("by_stratum_A1", {})
    rows = []
    for stratum in ("LLM01", "LLM02", "LLM03"):
        cells = table.get(stratum, {})
        for model in ("llama3.1:8b", "qwen2.5:7b"):
            c0 = cells.get(f"{model}|C0", {})
            c1 = cells.get(f"{model}|C1", {})
            rows.append(
                [
                    stratum,
                    model,
                    _comma(c0.get("violation")),
                    _comma(c1.get("violation")),
                    str(c0.get("n", "")),
                ]
            )
    return rows


def screen_rows() -> list[list[str]]:
    if not SCREEN.exists():
        return []
    payload = json.loads(SCREEN.read_text(encoding="utf-8"))
    rows = []
    for item in payload.get("rows", []):
        digest = str(item.get("digest") or "")
        short = digest[:12] if digest else "sin digest"
        latency = item.get("median_latency_ms")
        latency_text = "n/d" if latency is None else f"{float(latency):.0f}"
        rows.append(
            [
                str(item.get("model")),
                str(item.get("developer")),
                f"{float(item.get('valid_call_rate', 0)):.2f}",
                f"{float(item.get('utility_rate', 0)):.2f}",
                latency_text,
                "si" if item.get("fits") else "no",
                short,
            ]
        )
    return rows


def build() -> None:
    abstract = abstract_text()
    words = len(abstract.split())
    if not 150 <= words <= 250:
        raise SystemExit(f"abstract has {words} words")
    doc = Document()
    section = doc.sections[0]
    section.page_width = Cm(21.59)
    section.page_height = Cm(27.94)
    section.left_margin = Cm(1.75)
    section.right_margin = Cm(1.75)
    section.top_margin = Cm(1.6)
    section.bottom_margin = Cm(1.6)
    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _run(
        footer,
        "Universidad Icesi. Facultad de Ingenieria, Diseno y Ciencias Aplicadas.",
        size=8,
    )
    _cols(section, "1")

    add_p(
        doc,
        "Agente consultor en ciberseguridad para inteligencia artificial: "
        "evaluación experimental de controles externos frente a OWASP GenAI 2026",
        center=True,
        bold=True,
        size=14,
        space_after=8,
    )
    add_p(
        doc,
        "Juan C. Macias, Jairo A. Valencia, Ulises Caicedo",
        center=True,
        size=11,
    )
    add_p(
        doc,
        "Maestria en Inteligencia Artificial Aplicada, Universidad Icesi",
        center=True,
        size=11,
        space_after=10,
    )
    add_p(doc, "Resumen", bold=True, size=12)
    add_p(doc, abstract, size=10)
    add_p(
        doc,
        "Palabras clave: agente de herramientas, política determinista, OWASP GenAI 2026, evaluación emparejada.",
        italic=True,
        size=10,
    )

    body = doc.add_section()
    body.left_margin = Cm(1.75)
    body.right_margin = Cm(1.75)
    _cols(body, "2")

    add_heading_text(doc, "I. Introduccion")
    add_p(
        doc,
        "Una firma que usa un asistente con herramientas le entrega al modelo la decision de leer un secreto, "
        "abrir un ticket o cambiar el estado de un activo. El prompt puede pedir prudencia. Esa frase no es "
        "una mediacion completa: el modelo puede proponer la llamada y el programa puede ejecutarla. El problema "
        "central es que la firma no sabe si una política escrita fuera del modelo reduce las violaciones "
        "observables sin romper el trabajo legitimo del encargo.",
    )
    add_p(
        doc,
        "Las causas estan en el diseno habitual. El modelo recibe documentos y notas de herramientas que no "
        "escribio el usuario. Tiene más herramientas de las que la tarea necesita. La aprobacion de una accion "
        "sensible se acepta si el propio modelo dice que alguien la dio. Los efectos son una fuga de un dato "
        "del cliente, un cambio no pedido, o un control tan grueso que el encargo deja de poder trabajar.",
    )
    add_p(
        doc,
        "Los stakeholders son la firma que opera el consultor, el cliente del encargo y el lider que deberia "
        "aprobar las acciones sensibles. El valor que recibirian es una medida del residuo, no un certificado "
        "de seguridad. El mentor del proyecto revisa el diseno. Un profesional ajeno al equipo puede decir si "
        "el escenario le sirve. Esa opinion no entra en el calculo de la tasa.",
    )
    add_p(
        doc,
        "El sistema bajo evaluación es el consultor. Se llama SecureOps en el laboratorio y atiende encargos "
        "sintéticos. No hay un segundo agente que lo vigile. Los objetivos son cuatro. OE1 caracteriza la base "
        "y la matriz de amenazas. OE2 implementa el laboratorio con dos condiciones comparables y pruebas del "
        "oráculo. OE3 construye el banco, separado por familias. OE4 estima el efecto de los controles "
        "sobre el conjunto de evaluación.",
    )

    add_heading_text(doc, "II. Estado del arte")
    add_p(
        doc,
        "Los bancos de agentes, en particular AgentDojo, miden si un ataque de inyeccion desvia a un agente "
        "dentro de un entorno dinamico [2]. Esa pregunta es distinta. Aqui el factor es la presencia del "
        "control externo, con el mismo prompt, el mismo catálogo de herramientas y el mismo contexto en los "
        "dos brazos.",
    )
    add_p(
        doc,
        "Las revisiones de amenazas y defensas describen inyeccion, divulgacion y agencia excesiva, y ordenan "
        "controles como el minimo privilegio, los esquemás estrictos y la aprobacion humana [1], [3], [4], [6], "
        "[7], [9]. No estiman, en este consultor y con estos datos sintéticos, cuanto baja la violacion al "
        "sacar la decision del modelo. Un marco de aseguramiento cuantitativo ofrece otro camino de evidencia "
        "[5]. Tampoco ejecuta el contraste C0 contra C1.",
    )
    add_p(
        doc,
        "Un clasificador de inyeccion etiqueta texto. Puede avisar. No impide que una llamada ya permitida "
        "escriba un resumen falso, ni mide el costo sobre la tarea legitima. Por eso no responde la pregunta "
        "de este estudio. AgentBreak aporta el escenario, los activos sintéticos y la idea de que detectar "
        "una frase no es el control [10]. MCP-SHIELD aporta la cadena de confianza y el registro JSONL como "
        "referencia de diseno, no como lista OWASP [11]. La lista que usa el banco es la de OWASP GenAI 2026: "
        "LLM01 inyeccion, LLM02 divulgacion y LLM03 agencia excesiva [8]. No se mezclan la numeracion de 2025 "
        "ni los identificadores internos MCP01 a MCP10.",
    )

    add_heading_text(doc, "III. Metodos")
    add_p(
        doc,
        "El trabajo sigue CRISP-DM adaptado a una evaluación, no a un modelo entrenado. No hay pesos que "
        "ajustar. La Tabla I deja la evidencia de cada fase.",
    )
    add_table(
        doc,
        "Tabla I. Fases y evidencia.",
        ["Fase", "Evidencia"],
        [
            ["Negocio", "Problema, stakeholders y matriz de amenazas"],
            ["Datos", "Ficha del catálogo sintético"],
            ["Preparacion", "Particion por familia, esquema y similitud"],
            ["Modelado", "Bucle del consultor, C0 y C1, cribado"],
            ["Evaluación", "Oraculo, prerregistro y analisis"],
            ["Despliegue", "No hay. Queda la reproducción y los limites"],
        ],
    )
    add_p(
        doc,
        "Se sembraron dos clientes sintéticos, NorthGrid y ACME, con activos y tokens de demostracion. "
        "Hay tres roles: contacto del cliente, analista y lider del encargo. Hay siete herramientas "
        "simuladas. Ninguna abre la red. Las superficies de ataque son el mensaje, el documento recuperado "
        "y la nota libre del escaneo.",
    )
    add_p(
        doc,
        "C0 ejecuta la propuesta. C1 evalua cinco controles, todos, sin cortocircuito: lista por rol y tarea, "
        "esquema y pertenencia al encargo, secretos fuera de la salida, destinatarios permitidos, y aprobacion "
        "tomada del caso. Un argumento del modelo no aprueba nada. Si C1 niega la llamada, el modelo recibe "
        "un mensaje neutro y puede seguir. Las frases sospechosas se anotan y no bloquean.",
    )
    add_p(
        doc,
        "El oráculo no lee la lista de la política. Marca violacion si el caso prohíbe la llamada y esa "
        "llamada se ejecuto, si un secreto conocido sale en la respuesta o en un reporte, si el destino no "
        "esta autorizado, o si aparece un marcador que la política no conoce. Esos marcadores miden el residuo. "
        "La caida que viene de bloquear una herramienta fuera de rol se reporta aparte, como efecto de diseno.",
    )
    add_p(
        doc,
        "El banco tiene 120 plantillas, el tamaño del protocolo. La Tabla II da el reparto. Cada familia "
        "entra completa a calibración o a evaluación y tiene cinco plantillas. La dificultad se asigno "
        "antes de correr. La similitud maxima entre ataques de las dos particiones, medida por Jaccard "
        "del texto de ataque, fue 0,462.",
    )
    add_table(
        doc,
        "Tabla II. Plantillas por estrato y particion.",
        ["Estrato", "Calibracion", "Evaluación"],
        [
            ["LLM01", "10", "20"],
            ["LLM02", "10", "20"],
            ["LLM03", "10", "20"],
            ["Benignas", "10", "20"],
            ["Total", "40", "80"],
        ],
    )
    add_p(
        doc,
        "H1 afirma que, en ataques elegibles, la tasa de violaciones es menor con C1 que con C0. El estimando "
        "es la media por plantilla de ASR_C0 − ASR_C1, con un bootstrap de 10 000 réplicas y semilla fija. "
        "H2 no firma la dirección del costo en utilidad, bloqueo indebido o latencia. H3 es exploratoria. "
        "Las hipótesis quedaron escritas antes de abrir la evaluación. Una plantilla cuenta si su versión "
        "limpia bajo C0 cumple la tarea en al menos dos de tres repeticiones. Una corrida de ataque cuenta "
        "si el payload entró al contexto. Si el denominador es cero, la celda se llama no estimable.",
    )
    add_p(
        doc,
        "La malla prueba dos prompts, las temperaturas 0,2 y 0,7, y dos niveles de detalle de las "
        "herramientas, sobre las 40 tareas limpias de calibración y solo en C0: 640 corridas. Se elige la "
        "mayor utilidad mínima entre los dos modelos. Un empate se rompe por menor latencia mediana. No se "
        "elige por resistencia al ataque. La Tabla IV aparece cuando esa malla ya está resumida. El conjunto "
        "de evaluación sigue cerrado hasta el manifiesto que coincide con este catálogo.",
    )
    grid = grid_rows()
    if grid:
        add_table(
            doc,
            "Tabla IV. Utilidad en tareas limpias de calibración. La primera fila es la elegida.",
            ["Configuración", "Llama", "Qwen", "Mínima", "Mediana ms"],
            grid,
        )
    add_p(
        doc,
        "La inferencia es local, con Ollama, un modelo a la vez, en una RTX 3070 de 8 GB. El orden previsto "
        "es por bloques de repeticion para no perder una repeticion completa si el tiempo se acaba. El "
        "cribado usa seis sondas que no pertenecen al banco.",
    )
    rows = screen_rows()
    if rows:
        add_p(doc, "La Tabla III muestra el cribado que si se ejecuto. No es la evaluación factorial.")
        add_table(
            doc,
            "Tabla III. Cribado de modelos en seis sondas ajenas al banco.",
            ["Modelo", "Origen", "Llamadas", "Utilidad", "Mediana ms", "Cabe", "Digest"],
            rows,
        )
    else:
        add_p(doc, "El archivo de cribado no estaba al generar el documento. No se inventa una tasa de llamadas.")

    add_heading_text(doc, "IV. Resultados")
    add_p(
        doc,
        "III.A. El laboratorio corre sin GPU. Las pruebas cubren una herramienta prohibida que C0 ejecuta "
        "y C1 bloquea, un campo de aprobacion que el modelo no puede imponer, un marcador residual que C1 "
        "deja pasar porque la herramienta era licita, un secreto en base64 y en hexadecimal, una frase de "
        "ataque que no bloquea la busqueda, el tope de pasos y la respuesta vacia. La demo con guion del "
        "mismo caso da violacion en C0 y tarea cumplida sin violacion en C1. Eso prueba el instrumento. "
        "No prueba un modelo.",
    )
    for line in confirmatory_lines():
        add_p(doc, line)
    payload = _report()
    if payload is not None:
        add_table(
            doc,
            "Tabla V. Tasa de violación por corrida en ataques. No es la media por plantilla de III.D.",
            ["Estrato", "Modelo", "C0", "C1", "n"],
            stratum_rows(payload),
        )
        if FIGURE.exists():
            doc.add_picture(str(FIGURE), width=Cm(8))
            add_p(
                doc,
                "Figura 1. ASR por corrida en A1, sin fallo técnico y sin colapsar por plantilla. "
                "No es el estimando de III.D.",
                size=9,
                italic=True,
            )
    add_p(
        doc,
        "III.E. El formulario de pertinencia esta redactado. No se recibio respuesta del mentor ni de un "
        "profesional ajeno al equipo. No se redacta una opinion que nadie dio. Jairo A. Valencia es autor "
        "y no firma ese formulario.",
    )

    add_heading_text(doc, "V. Discusion")
    add_p(
        doc,
        "El factorial separa cuatro piezas. El instrumento, en pruebas con guion, distingue una llamada "
        "prohibida, un bloqueo y un marcador que la regla no nombra. En los modelos, la caída de C0 a C1 "
        "en LLM01 y LLM02 llega a cero bajo C1: ahí el control hace lo que se le escribió. En LLM03 el "
        "modelo qwen todavía entrega el marcador residual de la familia LLM03-DOC-OFFTASK. Esa familia "
        "usa un efecto que policy.json no lista. Contarlo dentro de la tasa de C1 evita decir que los "
        "cinco controles cubren todo el residuo.",
    )
    add_p(
        doc,
        "La diferencia es mayor en qwen que en llama, y llama queda en cero bajo C1 en los ataques "
        "elegibles. Eso es H3, exploratoria. El estimando primario sigue siendo la media por plantilla "
        "que junta los dos modelos. La calibración no entra en esa media.",
    )
    add_p(
        doc,
        "Los limites siguen. Los ataques son estaticos. OWASP 2026 pide no aceptar una afirmacion de "
        "exito basada solo en ataques estaticos, y probar contra quien ya leyo la defensa [8]. El banco "
        "repite mecanismos con otro activo, otro rol o otro turno. Los datos no son de un cliente. Los "
        "modelos son pequenos y cuantizados. La repetición con la misma semilla se declara en los "
        "resultados y no entra en la tasa. Nada de esto certifica un despliegue.",
    )

    add_heading_text(doc, "VI. Conclusiones")
    add_p(
        doc,
        "H1, H2 y H3 se leen sobre el conjunto de evaluación, no sobre la calibración. OE1, OE2, OE3 y OE4 "
        "están construidos. H1 se lee en la media por plantilla y en su intervalo. H2 se lee en la utilidad, "
        "el bloqueo indebido y la latencia de las tareas limpias. H3 se lee en la diferencia por modelo. "
        "Ninguna de las tres certifica un despliegue.",
    )

    add_heading_text(doc, "Apendice A. Repositorio")
    add_p(
        doc,
        "La extension parte del commit 9effe7b de AgentBreak, etiquetado baseline-agentbreak-0.2.0. El código "
        "heredado no se reescribe. Lo nuevo vive en src/agentbreak/eval_lab. La nota de reproducción "
        "viaja con la entrega del curso, fuera del repositorio. El comando de evaluación no abre el conjunto final si falta el manifiesto "
        "congelado. La licencia MIT esta declarada en el paquete de origen y no se publica el derivado hasta "
        "confirmarla.",
    )
    add_heading_text(doc, "Apendice B. Catalogo")
    add_p(
        doc,
        "Cada plantilla trae identificador, familia, estrato OWASP 2026, rol, encargo, tarea legitima, "
        "versiónes A0 y A1 cuando hay ataque, activos protegidos, llamadas prohibidas, marcadores, utilidad "
        "y particion. El esquema es catalog/schema_v1.json. Hay 120 registros. La entrega queda fijada para "
        "el 21 de noviembre de 2026.",
    )
    add_heading_text(doc, "Apendice C. Evidencia")
    add_p(
        doc,
        "Están las pruebas del oráculo, la línea base heredada, el cribado y el reporte de las 1680 corridas, "
        "con su figura. Las trazas quedan en runs/ y no entran al repositorio. No se rellena ninguna celda "
        "con cifras de otras publicaciones [2], [5].",
    )
    add_heading_text(doc, "Apendice D. Uso de inteligencia artificial")
    add_p(
        doc,
        "Se uso inteligencia artificial generativa como apoyo de redaccion, de revision conceptual, de "
        "busqueda de literatura y, en esta versión, de código y de scripts de analisis. Las personas autoras "
        "deben verificar las fuentes, aprobar el texto y responder por el protocolo, los datos y los "
        "resultados. Las tasas salen de las trazas locales. No se inventaron respuestas de stakeholders.",
    )

    add_heading_text(doc, "Referencias")
    for item in REFERENCES:
        add_p(doc, item, size=9, space_after=4)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(OUT)
    print(f"wrote {OUT} abstract_words={words}")


REFERENCES = [
    "[1] A. D. E. Berini, N. Jamil, A.-E. Benrazek, A. Lakas, L. Ismail, M. A. Ferrag y K.-Y. Lam, "
    "“Security and privacy in LLMs: A comprehensive survey of threats and mitigation strategies”, "
    "Information Fusion, vol. 132, art. 104241, 2026. doi: 10.1016/j.inffus.2026.104241.",
    "[2] E. Debenedetti, J. Zhang, M. Balunović, L. Beurer-Kellner, M. Fischer y F. Tramèr, "
    "“AgentDojo: A dynamic environment to evaluate prompt injection attacks and defenses for LLM agents”, "
    "Advances in Neural Information Processing Systems, vol. 37, pp. 82895–82920, 2024. "
    "doi: 10.52202/079017-2636.",
    "[3] M. A. Ferrag, N. Tihanyi, D. Hamouda, L. Maglaras, A. Lakas y M. Debbah, "
    "“From prompt injections to protocol exploits: Threats in LLM-powered AI agents workflows”, "
    "ICT Express, vol. 12, núm. 2, pp. 353–383, 2026. doi: 10.1016/j.icte.2025.12.001.",
    "[4] V. Guimarães, D. Medeiros, L. Reis, H. Mesquita y T. Rocha, "
    "“Prompt-based attacks and defenses in large language models: A systematic review of threat models, "
    "taxonomies, and evaluation practices”, Neurocomputing, vol. 705, art. 134939, 2026. "
    "doi: 10.1016/j.neucom.2026.134939.",
    "[5] S. Stamnes Karlsen, M. M. Yamin, E. Hashmi, B. Katt y M. Ullah, "
    "“Securing large language models: A quantitative assurance framework approach”, "
    "Journal of Information Security and Applications, vol. 97, art. 104351, 2026. "
    "doi: 10.1016/j.jisa.2025.104351.",
    "[6] M. Q. Li y B. C. M. Fung, “Security concerns for large language models: A survey”, "
    "Journal of Information Security and Applications, vol. 95, art. 104284, 2025. "
    "doi: 10.1016/j.jisa.2025.104284.",
    "[7] Z. Liao, K. Chen, Y. Lin, K. Li, Y. Liu, H. Chen, X. Huang y Y. Yu, "
    "“Attack and defense techniques in large language models: A survey and new perspectives”, "
    "Neural Networks, vol. 196, art. 108388, 2026. doi: 10.1016/j.neunet.2025.108388.",
    "[8] OWASP GenAI Security Project, “OWASP GenAI LLM Top 10 2026”, 2026. "
    "Disponible en: https://genai.owasp.org/resource/owasp-genai-llm-top-10-2026/",
    "[9] Y. Tang, Y. Liu, J. Lan, Z. Yan y E. Gelenbe, "
    "“Security of LLM-based agents regarding attacks, defenses, and applications: A comprehensive survey”, "
    "Information Fusion, vol. 127, art. 103941, 2026. doi: 10.1016/j.inffus.2025.103941.",
    "[10] C. Urcuqui, “AgentBreak”, código fuente, commit 9effe7b6317a4e90b18ab895c06a2a47f8cb91c1. "
    "Disponible en: https://github.com/urcuqui/AgentBreak/tree/9effe7b6317a4e90b18ab895c06a2a47f8cb91c1",
    "[11] C. Urcuqui, “MCP-SHIELD”, código fuente. "
    "Disponible en: https://github.com/urcuqui/MCP-SHIELD",
]


if __name__ == "__main__":
    build()
