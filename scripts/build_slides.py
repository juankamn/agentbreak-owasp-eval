"""Slides for the defense. Short lines. No invented rates."""

from __future__ import annotations

import json
from pathlib import Path

from pptx import Presentation
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
ENTREGA = ROOT.parent / "entrega"
TEMPLATE = Path(
    r"C:\Users\Usuario\Documents\ICESI\Maestria Inteligencia Artificial aplicada"
    r"\SEMESTRE 2\Proyecto II\1\Icesi_para_diapositivas.pptx"
)
OUT = ENTREGA / "sustentacion" / "diapositivas.pptx"
SCREEN = ROOT / "manifest" / "models_smoke_report.json"
EVAL_REPORT = ENTREGA / "resultados" / "evaluation_report.json"


def _screen_line() -> str:
    if not SCREEN.exists():
        return "Cribado: archivo ausente. No se inventa una tasa."
    payload = json.loads(SCREEN.read_text(encoding="utf-8"))
    bits = []
    for item in payload.get("rows", []):
        bits.append(
            f"{item['model']}: llamadas {float(item['valid_call_rate']):.2f}, "
            f"utilidad {float(item['utility_rate']):.2f}"
        )
    rule = payload.get("decision", {}).get("rule", "sin regla")
    return "Sondas, no el factorial. " + " | ".join(bits) + f". Regla: {rule}."


def _result_lines() -> list[str]:
    base = [
        "Configuracion elegida por utilidad limpia: v1, temperatura 0,7, detalle bajo.",
        "La calibracion no se presenta como el estimando.",
    ]
    if not EVAL_REPORT.exists():
        return base + ["ASR del conjunto de evaluacion: no estimable."]
    payload = json.loads(EVAL_REPORT.read_text(encoding="utf-8"))
    primary = payload.get("primary", {})
    if primary.get("label") != "estimable":
        return base + ["ASR del conjunto de evaluacion: no estimable."]
    interval = primary.get("interval") or {}
    difference = f"{float(primary['difference_c0_minus_c1']):.3f}".replace(".", ",")
    low = f"{float(interval.get('low', 0)):.3f}".replace(".", ",")
    high = f"{float(interval.get('high', 0)):.3f}".replace(".", ",")
    return base + [
        f"1680 corridas. Diferencia por plantilla: {difference}.",
        f"Intervalo bootstrap: {low} a {high}. Plantillas: {primary.get('templates')}.",
        "Ese numero no certifica un despliegue.",
    ]


def _add(prs: Presentation, title: str, lines: list[str]) -> None:
    layout = prs.slide_layouts[1] if len(prs.slide_layouts) > 1 else prs.slide_layouts[0]
    slide = prs.slides.add_slide(layout)
    slide.shapes.title.text = title
    body = None
    for shape in slide.placeholders:
        if shape.placeholder_format.idx == 1:
            body = shape
            break
    if body is None:
        box = slide.shapes.add_textbox(Inches(0.6), Inches(1.6), Inches(8.5), Inches(4.5))
        text = box.text_frame
    else:
        text = body.text_frame
    text.clear()
    for index, line in enumerate(lines):
        paragraph = text.paragraphs[0] if index == 0 else text.add_paragraph()
        paragraph.text = line
        paragraph.level = 0
        paragraph.font.size = Pt(20)


def _drop_existing(prs: Presentation) -> None:
    """Remove template sample slides and their package parts."""
    from pptx.oxml.ns import qn

    for slide in list(prs.slides):
        rel_id = None
        for rel in prs.part.rels.values():
            if rel.reltype.endswith("/slide") and rel._target is slide.part:
                rel_id = rel.rId
                break
        if rel_id is None:
            continue
        prs.part.drop_rel(rel_id)
        for child in list(prs.slides._sldIdLst):
            if child.get(qn("r:id")) == rel_id:
                prs.slides._sldIdLst.remove(child)


def build() -> None:
    prs = Presentation(TEMPLATE) if TEMPLATE.exists() else Presentation()
    _drop_existing(prs)
    _add(
        prs,
        "Agente consultor y controles externos",
        [
            "Objetivo: medir si una politica fuera del modelo baja violaciones observables.",
            "El sistema bajo prueba es el consultor.",
            "Juan C. Macias, Jairo A. Valencia, Ulises Caicedo",
        ],
    )
    _add(
        prs,
        "Agenda",
        [
            "Problema de negocio",
            "Diseno C0 y C1",
            "Banco y oraculo",
            "Lo que ya se midio",
            "Limites y cierre",
        ],
    )
    _add(
        prs,
        "Problema",
        [
            "Causa: el modelo decide llamadas que el programa ejecuta.",
            "Problema: no se sabe si el control externo reduce violaciones sin frenar el encargo.",
            "Efecto: fuga, cambio no pedido, o un control que impide trabajar.",
        ],
    )
    _add(
        prs,
        "Diseno",
        [
            "Mismo prompt y mismo contexto en C0 y en C1.",
            "C0 ejecuta. C1 aplica cinco controles deterministicos.",
            "La aprobacion sale del caso, no de un argumento del modelo.",
            "La frase sospechosa se anota y no bloquea.",
        ],
    )
    _add(
        prs,
        "Banco",
        [
            "120 plantillas sinteticas. 40 de calibracion y 80 de evaluacion.",
            "LLM01, LLM02 y LLM03 de OWASP 2026, mas tareas limpias.",
            "El oraculo usa la tabla del caso. No usa la lista de la politica.",
        ],
    )
    _add(
        prs,
        "Instrumento",
        [
            "Sin GPU: C0 ejecuta el aislamiento. C1 lo bloquea y la tarea legitima sigue.",
            "Eso no es un resultado de modelo.",
            _screen_line(),
        ],
    )
    _add(
        prs,
        "Resultado del factorial",
        _result_lines(),
    )
    _add(
        prs,
        "Limites",
        [
            "Ataques estaticos. OWASP 2026 pide probar a quien ya leyo la defensa.",
            "Banco pequeno y datos sinteticos.",
            "Dos modelos locales de hasta 9B. La repeticion con semilla no es total.",
        ],
    )
    _add(
        prs,
        "Cierre",
        [
            "OE1 a OE4 estan construidos.",
            "H1 se lee en la diferencia por plantilla.",
            "H2 y H3 se leen en el reporte. No hay certificado de despliegue.",
        ],
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    prs.save(OUT)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    build()
