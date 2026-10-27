"""Geração de PDFs com ReportLab: formulário de ausência e relatório consolidado do RH."""
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from ..constants import ROLE_LABELS, STATUS_LABELS, TYPE_LABELS
from ..models import AbsenceRequest
from ..utils import fmt_date, fmt_dt, now
from ..workflow import EVENT_LABELS
from .signature_service import is_valid

NAVY = colors.HexColor("#14285a")
GREY = colors.HexColor("#f1f4f9")
_ss = getSampleStyleSheet()
BODY = ParagraphStyle("body", parent=_ss["BodyText"], fontSize=9, leading=12)
SMALL = ParagraphStyle("small", parent=BODY, fontSize=7, leading=9)
MONO = ParagraphStyle("mono", parent=SMALL, fontName="Courier", fontSize=6.5, leading=8)
H1 = ParagraphStyle("h1", parent=_ss["Title"], fontSize=14, textColor=NAVY, spaceAfter=2)
H2 = ParagraphStyle("h2", parent=_ss["Heading2"], fontSize=10.5, textColor=NAVY, spaceBefore=10, spaceAfter=4)


def P(text, style=BODY):
    return Paragraph(escape(str(text if text is not None else "-")).replace("\n", "<br/>"), style)


def _table(data, widths, header=True):
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    st = [("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c5cddb")),
          ("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    if header:
        st += [("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white)]
    t.setStyle(TableStyle(st))
    return t


def _hdr(text):
    return Paragraph(f"<font color='white'><b>{escape(text)}</b></font>", SMALL)


def _footer(label):
    def draw(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.grey)
        w, _ = doc.pagesize
        canvas.drawString(1.5 * cm, 1 * cm, f"{label} — Documento gerado eletronicamente. Contém dados pessoais protegidos pela LGPD (Lei 13.709/2018).")
        canvas.drawRightString(w - 1.5 * cm, 1 * cm, f"Página {doc.page}")
        canvas.restoreState()
    return draw


def build_request_pdf(req: AbsenceRequest, show_reason: bool) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=1.5 * cm, rightMargin=1.5 * cm, topMargin=1.5 * cm, bottomMargin=1.8 * cm,
                            title=f"Solicitação {req.protocol}")
    W = A4[0] - 3 * cm
    el = [Paragraph("Centro Universitário Salesiano — UniSales", H1),
          Paragraph("FORMULÁRIO DE SOLICITAÇÃO DE AUSÊNCIA DOCENTE", ParagraphStyle("s", parent=BODY, textColor=NAVY, fontSize=10)),
          Spacer(1, 6)]
    info = [
        [P("Protocolo"), P(req.protocol), P("Status"), P(STATUS_LABELS[req.status])],
        [P("Docente"), P(req.teacher.name), P("Curso"), P(req.course.name)],
        [P("Tipo"), P(TYPE_LABELS[req.type]), P("Período"), P(f"{fmt_date(req.start_date)} a {fmt_date(req.end_date)} ({req.days} dia(s))")],
        [P("Substituto"), P(req.substitute.name if req.substitute else "Não indicado"), P("Aberta em"), P(fmt_dt(req.created_at))],
    ]
    t = _table(info, [2.6 * cm, W / 2 - 2.6 * cm, 2.6 * cm, W / 2 - 2.6 * cm], header=False)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (0, -1), GREY), ("BACKGROUND", (2, 0), (2, -1), GREY)]))
    el += [t, Paragraph("Disciplinas / turmas afetadas", H2), P(req.subjects)]
    el += [Paragraph("Motivo", H2),
           P(req.reason if show_reason else "Informação restrita (LGPD): visível apenas ao docente, à Coordenação e ao RH.")]
    if show_reason and req.notes:
        el += [Paragraph("Observações", H2), P(req.notes)]
    if show_reason and req.attachment_name:
        el += [Spacer(1, 4), P(f"Anexo: {req.attachment_name}")]

    el.append(Paragraph("Assinaturas eletrônicas (simuladas)", H2))
    if req.signatures:
        rows = [[_hdr("Assinante"), _hdr("Papel"), _hdr("Data/hora"), _hdr("IP"), _hdr("Hash SHA-256 do conteúdo")]]
        for s in req.signatures:
            ok = is_valid(req, s)
            rows.append([P(s.user.name, SMALL), P(ROLE_LABELS.get(s.role, s.role), SMALL), P(fmt_dt(s.signed_at), SMALL), P(s.ip, SMALL),
                         Paragraph(escape(s.content_hash) + ("" if ok else "<br/><font color='#b00020'>conteúdo alterado após esta assinatura</font>"), MONO)])
        el.append(_table(rows, [3.2 * cm, 2.6 * cm, 2.6 * cm, 2.2 * cm, W - 10.6 * cm]))
    else:
        el.append(P("Ainda não assinada."))

    el.append(Paragraph("Histórico de tramitação (auditoria)", H2))
    rows = [[_hdr("Data/hora"), _hdr("Responsável"), _hdr("Ação"), _hdr("Status"), _hdr("Observação")]]
    for e in req.events:
        mv = STATUS_LABELS[e.to_status] if e.from_status == e.to_status or not e.from_status else f"{STATUS_LABELS[e.from_status]} → {STATUS_LABELS[e.to_status]}"
        rows.append([P(fmt_dt(e.created_at), SMALL), P(e.user.name if e.user else "Sistema", SMALL),
                     P(EVENT_LABELS.get(e.action, e.action), SMALL), P(mv, SMALL), P(e.note or "", SMALL)])
    el.append(_table(rows, [2.5 * cm, 3 * cm, 3.4 * cm, 4.4 * cm, W - 13.3 * cm]))
    doc.build(el, onFirstPage=_footer(req.protocol), onLaterPages=_footer(req.protocol))
    return buf.getvalue()


def build_report_pdf(rows: list[dict], totals: dict, filters_desc: str, generated_by: str) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=1.2 * cm, rightMargin=1.2 * cm, topMargin=1.3 * cm, bottomMargin=1.6 * cm,
                            title="Relatório consolidado de ausências")
    W = landscape(A4)[0] - 2.4 * cm
    el = [Paragraph("UniSales — Relatório consolidado de ausências docentes (RH)", H1),
          P(f"Filtros: {filters_desc}", SMALL), P(f"Gerado por {generated_by} em {fmt_dt(now())}", SMALL),
          Spacer(1, 6)]
    summ = [[_hdr("Total de solicitações"), _hdr("Total de dias de ausência")],
            [P(totals["count"]), P(totals["days"])]]
    el.append(_table(summ, [5 * cm, 5 * cm]))
    for title, key in (("Totais por tipo", "by_type"), ("Totais por curso", "by_course"), ("Totais por status", "by_status")):
        data = [[_hdr(title.replace("Totais por ", "").capitalize()), _hdr("Solicitações"), _hdr("Dias")]]
        for k, v in totals[key].items():
            data.append([P(k), P(v["count"]), P(v["days"])])
        el += [Spacer(1, 6), _table(data, [8 * cm, 3 * cm, 3 * cm])]
    el.append(Paragraph("Detalhamento", H2))
    data = [[_hdr(h) for h in ("Protocolo", "Docente", "Curso", "Tipo", "Início", "Fim", "Dias", "Status", "Devol.")]]
    for r in rows:
        data.append([P(r["protocol"], SMALL), P(r["teacher"], SMALL), P(r["course"], SMALL), P(r["type"], SMALL), P(r["start_date"], SMALL),
                     P(r["end_date"], SMALL), P(r["days"], SMALL), P(r["status"], SMALL), P(r["returns"], SMALL)])
    el.append(_table(data, [2.9 * cm, 5 * cm, 4.2 * cm, 2.8 * cm, 2.2 * cm, 2.2 * cm, 1.2 * cm, W - 22.5 * cm, 1.5 * cm]))
    doc.build(el, onFirstPage=_footer("Relatório RH"), onLaterPages=_footer("Relatório RH"))
    return buf.getvalue()
