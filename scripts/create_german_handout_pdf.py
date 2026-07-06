from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
REPO_OUTPUT = ROOT / "output" / "pdf"
TEMP = ROOT / "tmp" / "pdfs"
CODEX_OUTPUT = Path(
    r"C:\Users\tukib\Documents\Codex\2026-07-06\c-users-tukib-onedrive-bbw-ch\outputs"
)
PDF_NAME = "market_regime_detector_handout_de.pdf"


def pct(value: float | str | None, digits: int = 1) -> str:
    if value in (None, ""):
        return "n/a"
    return f"{float(value) * 100:.{digits}f}%"


def num(value: float | str | None, digits: int = 1) -> str:
    if value in (None, ""):
        return "n/a"
    return f"{float(value):.{digits}f}"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def load_manifest() -> dict:
    return json.loads((ROOT / "public" / "manifest.json").read_text(encoding="utf-8"))


def latest_rows(manifest: dict) -> list[list[str]]:
    preferred = ["BTC-USD_1d", "ETH-USD_1d", "GSPC_1d", "SSMI_1d", "000300_SS_1d", "HSI_1d"]
    runs = {run["id"]: run for run in manifest["runs"]}
    rows = [["Markt", "Zeitrahmen", "Aktuelles Regime", "Rendite p.a.", "Volatilitaet p.a."]]
    for run_id in preferred:
        run = runs.get(run_id)
        if not run:
            continue
        latest = run["latest"] or {}
        rows.append(
            [
                f"{run['assetName']} ({run['symbol']})",
                run["timeframeLabel"],
                latest.get("regimeName", "n/a"),
                pct(latest.get("annualizedReturn")),
                pct(latest.get("annualizedVolatility")),
            ]
        )
    return rows


def build_styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="TitleBig",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=28,
            leading=32,
            textColor=colors.HexColor("#172026"),
            alignment=TA_CENTER,
            spaceAfter=14,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Subtitle",
            parent=styles["BodyText"],
            fontSize=12,
            leading=17,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#53616B"),
            spaceAfter=20,
        )
    )
    styles.add(
        ParagraphStyle(
            name="H1Custom",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=23,
            textColor=colors.HexColor("#172026"),
            spaceBefore=8,
            spaceAfter=9,
        )
    )
    styles.add(
        ParagraphStyle(
            name="H2Custom",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=17,
            textColor=colors.HexColor("#2C7A54"),
            spaceBefore=8,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BodyCustom",
            parent=styles["BodyText"],
            fontSize=9.6,
            leading=13.2,
            textColor=colors.HexColor("#24332C"),
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Small",
            parent=styles["BodyText"],
            fontSize=8.3,
            leading=11,
            textColor=colors.HexColor("#53616B"),
            spaceAfter=4,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Formula",
            parent=styles["BodyText"],
            fontName="Courier",
            fontSize=8.8,
            leading=11.5,
            backColor=colors.HexColor("#EEF3EF"),
            borderColor=colors.HexColor("#DDE8E1"),
            borderPadding=6,
            textColor=colors.HexColor("#172026"),
            spaceBefore=5,
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Callout",
            parent=styles["BodyText"],
            fontSize=9.3,
            leading=13,
            backColor=colors.HexColor("#FFF7E0"),
            borderColor=colors.HexColor("#F0B429"),
            borderPadding=8,
            textColor=colors.HexColor("#172026"),
            spaceBefore=5,
            spaceAfter=8,
        )
    )
    return styles


def bullet_list(items: list[str], styles) -> ListFlowable:
    return ListFlowable(
        [ListItem(Paragraph(item, styles["BodyCustom"]), leftIndent=10) for item in items],
        bulletType="bullet",
        start="circle",
        leftIndent=15,
        bulletFontSize=6,
    )


def styled_table(data: list[list[str]], col_widths=None, font_size: float = 8.2) -> Table:
    table = Table(data, colWidths=col_widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#172026")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), font_size),
                ("LEADING", (0, 0), (-1, -1), font_size + 2),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D9E3DD")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7FAF8")]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def chart(path: Path, width_cm: float, height_cm: float | None = None) -> Image:
    image = Image(str(path), width=width_cm * cm, height=height_cm * cm if height_cm else None)
    image.hAlign = "CENTER"
    return image


def on_page(canvas, doc):
    canvas.saveState()
    width, height = A4
    canvas.setFillColor(colors.HexColor("#2CA25F"))
    canvas.rect(0, height - 0.35 * cm, width, 0.35 * cm, stroke=0, fill=1)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#53616B"))
    canvas.drawString(1.6 * cm, 1.0 * cm, "Market Regime Detector - Fachliches Handout")
    canvas.drawRightString(width - 1.6 * cm, 1.0 * cm, f"Seite {doc.page}")
    canvas.restoreState()


def add_title(story, styles):
    story.append(Spacer(1, 2.6 * cm))
    story.append(Paragraph("Market Regime Detector", styles["TitleBig"]))
    story.append(
        Paragraph(
            "Fachliches Handout zu Marktregimen, Zeitreihen-Features und Hidden Markov Models",
            styles["Subtitle"],
        )
    )
    story.append(Spacer(1, 0.4 * cm))
    story.append(
        styled_table(
            [
                ["Ziel", "Was du nach diesem Handout koennen solltest"],
                [
                    "Intuition",
                    "Erklaeren, was ein Marktregime ist und warum es fuer Asset Management relevant ist.",
                ],
                [
                    "Methodik",
                    "Returns, Volatilitaet, Momentum, Drawdown und HMMs fachlich einordnen.",
                ],
                [
                    "Interpretation",
                    "Charts, Regime-Statistiken und Transition-Matrizen korrekt lesen.",
                ],
                [
                    "Kritik",
                    "Look-ahead Bias, Overfitting und Grenzen des Modells sauber benennen.",
                ],
            ],
            [3.2 * cm, 12.6 * cm],
        )
    )
    story.append(Spacer(1, 0.5 * cm))
    story.append(
        Paragraph(
            "Educational disclaimer: Dieses Dokument ist eine Lernunterlage und keine Anlageberatung.",
            styles["Small"],
        )
    )
    story.append(PageBreak())


def add_basics(story, styles):
    story.append(Paragraph("1. Was sind Marktregime?", styles["H1Custom"]))
    story.append(
        Paragraph(
            "Ein Marktregime ist eine Phase, in der sich ein Markt statistisch aehnlich verhaelt. "
            "Beispiele sind ein ruhiger Aufwaertstrend, ein starker Stressmarkt oder eine volatile "
            "Seitwaertsphase. Der Punkt ist nicht, perfekte Namen fuer die Zukunft zu finden, sondern "
            "historische Daten in verstaendliche Zustandsmuster zu strukturieren.",
            styles["BodyCustom"],
        )
    )
    story.append(
        bullet_list(
            [
                "<b>Calm / bull:</b> niedrige Schwankungen, positive Renditen, oft anhaltender Trend.",
                "<b>High-volatility / sideways:</b> viel Bewegung, aber kein klarer positiver Trend.",
                "<b>Bear / drawdown:</b> negative Renditen und deutlicher Abstand vom Hoch.",
                "<b>Stress / bear:</b> seltenere, sehr volatile Stressphasen mit grossen Verlusten.",
            ],
            styles,
        )
    )
    story.append(
        Paragraph(
            "Analogie: Wetter statt einzelner Regentropfen. Ein einzelner Tagesverlust sagt wenig. "
            "Viele Beobachtungen zusammen koennen aber auf 'Sturm', 'ruhiges Wetter' oder 'wechselhaft' "
            "hindeuten.",
            styles["Callout"],
        )
    )
    story.append(Paragraph("Warum ist das fuer Asset Management interessant?", styles["H2Custom"]))
    story.append(
        bullet_list(
            [
                "Risiko ist nicht konstant. In Stressphasen steigen Korrelationen und Volatilitaeten oft gleichzeitig.",
                "Strategien funktionieren nicht in jedem Umfeld gleich gut.",
                "Regime helfen, historische Performance nicht als einen einzigen Durchschnitt zu betrachten.",
                "Fuer nicht-quantitative Stakeholder sind Regime eine verstaendliche Bruecke zwischen Daten und Marktstory.",
            ],
            styles,
        )
    )


def add_features(story, styles):
    story.append(PageBreak())
    story.append(Paragraph("2. Von Preisen zu Features", styles["H1Custom"]))
    story.append(
        Paragraph(
            "Ein Modell sieht nicht direkt 'Panik' oder 'Optimismus'. Es sieht numerische Merkmale, "
            "sogenannte Features. Aus Preiszeitreihen werden deshalb Rendite, Volatilitaet, Momentum "
            "und Drawdown konstruiert.",
            styles["BodyCustom"],
        )
    )
    story.append(
        styled_table(
            [
                ["Feature", "Definition", "Intuition"],
                ["Log Return", "ln(P_t / P_{t-1})", "Tages- oder Bar-Rendite, gut addierbar."],
                [
                    "Rolling Return",
                    "P_t / P_{t-k} - 1",
                    "Richtung ueber ein Fenster, z.B. 21 Tage.",
                ],
                [
                    "Realized Volatility",
                    "std(log returns) * sqrt(periods per year)",
                    "Annualisierte Schwankungsintensitaet.",
                ],
                ["Momentum", "P_t / P_{t-m} - 1", "Mittelfristiger Trend."],
                [
                    "Drawdown",
                    "P_t / rolling_max(P) - 1",
                    "Abstand vom letzten Hoch, typischerweise negativ.",
                ],
            ],
            [3.1 * cm, 6.1 * cm, 6.2 * cm],
        )
    )
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph("Mini-Beispiel: Rendite und Volatilitaet", styles["H2Custom"]))
    story.append(
        Paragraph(
            "Angenommen ein Index steigt von 100 auf 102. Die einfache Rendite ist 2%. "
            "Der Log Return ist ln(102/100) = ca. 1.98%. Bei kleinen Renditen sind einfache "
            "Rendite und Log Return fast gleich.",
            styles["BodyCustom"],
        )
    )
    story.append(
        Paragraph(
            "annualisierte Volatilitaet = Standardabweichung der Tagesrenditen * sqrt(252)",
            styles["Formula"],
        )
    )
    story.append(
        Paragraph(
            "Wenn die Tagesvolatilitaet 1% betraegt, ergibt sich ungefaehr 1% * sqrt(252) = 15.9% "
            "Volatilitaet pro Jahr. Bei Krypto-Intraday-Daten ist diese Annualisierung oft extrem, "
            "weil sehr viele Perioden pro Jahr hochgerechnet werden.",
            styles["BodyCustom"],
        )
    )


def add_hmm(story, styles):
    story.append(PageBreak())
    story.append(Paragraph("3. Warum ein Hidden Markov Model?", styles["H1Custom"]))
    story.append(
        Paragraph(
            "Ein Hidden Markov Model (HMM) nimmt an, dass es nicht direkt beobachtbare Zustaende gibt. "
            "Diese Zustaende erzeugen beobachtbare Features. Im Projekt sind die versteckten Zustaende "
            "die Marktregime, und die beobachtbaren Features sind z.B. Volatilitaet, Momentum und Drawdown.",
            styles["BodyCustom"],
        )
    )
    story.append(
        styled_table(
            [
                ["Baustein", "Bedeutung im Projekt"],
                ["Hidden State", "Das nicht direkt sichtbare Regime, z.B. Stress / bear."],
                ["Emission", "Die Feature-Werte, die in einem Regime typisch sind."],
                ["Transition Matrix", "Wahrscheinlichkeit, morgen in ein anderes Regime zu wechseln."],
                ["Start Probability", "Wahrscheinlichkeit, dass die Zeitreihe in einem Regime beginnt."],
            ],
            [4.0 * cm, 11.8 * cm],
        )
    )
    story.append(Paragraph("Trade-offs gegenueber Alternativen", styles["H2Custom"]))
    story.append(
        styled_table(
            [
                ["Methode", "Vorteil", "Nachteil"],
                ["K-Means", "Einfach, schnell, gut erklaerbar.", "Ignoriert zeitliche Persistenz."],
                ["Gaussian Mixture", "Weiche Cluster-Wahrscheinlichkeiten.", "Keine explizite Uebergangsdynamik."],
                ["HMM", "Modelliert Regime und Wechselwahrscheinlichkeiten.", "Mehr Annahmen, sensibel auf Features."],
            ],
            [3.0 * cm, 6.2 * cm, 6.6 * cm],
        )
    )
    story.append(
        Paragraph(
            "Warum HMM hier passt: Marktregime sind meist persistent. Ein ruhiger Markt wird nicht "
            "zufaellig jeden Tag komplett neu gewuerfelt. Die Transition Matrix bildet genau diese "
            "Persistenz ab.",
            styles["Callout"],
        )
    )


def add_model_selection(story, styles, manifest):
    story.append(PageBreak())
    story.append(Paragraph("4. Wie viele Regime?", styles["H1Custom"]))
    story.append(
        Paragraph(
            "Die Anzahl der Regime wird nicht einfach geraten. Das Projekt testet mehrere HMMs und "
            "vergleicht sie mit Informationskriterien wie AIC und BIC. Beide belohnen gute Anpassung "
            "an die Daten, bestrafen aber zusaetzliche Komplexitaet.",
            styles["BodyCustom"],
        )
    )
    story.append(
        Paragraph(
            "BIC = -2 * log likelihood + k * ln(n)<br/>"
            "k = Anzahl Parameter, n = Anzahl Beobachtungen. Tiefer ist besser.",
            styles["Formula"],
        )
    )
    gspc = next(run for run in manifest["runs"] if run["id"] == "GSPC_1d")
    selection = read_csv(ROOT / "public" / gspc["paths"]["modelSelection"].lstrip("/"))
    rows = [["States", "Log Likelihood", "AIC", "BIC"]]
    for row in selection:
        rows.append(
            [
                row["n_states"],
                num(row["log_likelihood"], 1),
                num(row["aic"], 0),
                num(row["bic"], 0),
            ]
        )
    story.append(Paragraph("Beispiel aus dem Projekt: S&P 500 Daily", styles["H2Custom"]))
    story.append(styled_table(rows, [2.3 * cm, 4.2 * cm, 4.2 * cm, 4.2 * cm]))
    story.append(
        Paragraph(
            "Wichtig: Wenn man beliebig viele Zustaende erlaubt, kann das Modell historische Daten "
            "immer feiner aufteilen. Fuer ein Portfolio-Projekt ist Interpretierbarkeit wichtig. "
            "Darum wird die Suche standardmaessig auf einen kleinen Bereich begrenzt.",
            styles["Callout"],
        )
    )


def add_interpretation(story, styles, manifest):
    story.append(PageBreak())
    story.append(Paragraph("5. Dashboard richtig lesen", styles["H1Custom"]))
    story.append(
        Paragraph(
            "Die wichtigste Visualisierung ist der Preisverlauf mit farbig hinterlegten Regimen. "
            "Die Linie zeigt den Marktpreis, der Hintergrund zeigt das vom Modell erkannte Regime. "
            "Eine Farbe ist also keine Prognose, sondern eine historische Klassifikation.",
            styles["BodyCustom"],
        )
    )
    story.append(chart(ROOT / "public" / "reports" / "figures" / "BTC-USD_1d_price_regimes.png", 16.0, 8.1))
    story.append(Paragraph("Beispielhafte aktuelle Regime aus den generierten Reports", styles["H2Custom"]))
    story.append(styled_table(latest_rows(manifest), [4.4 * cm, 2.6 * cm, 4.3 * cm, 2.4 * cm, 2.4 * cm], 7.6))
    story.append(
        Paragraph(
            "Interpretation: Ein Markt kann im neuesten Label ein negatives Regime haben, obwohl der "
            "Preis langfristig gestiegen ist. Das Regime beschreibt die aktuelle statistische Umgebung, "
            "nicht die gesamte Historie.",
            styles["Small"],
        )
    )


def add_transition_stats(story, styles):
    story.append(PageBreak())
    story.append(Paragraph("6. Transition Matrix und Regime-Statistiken", styles["H1Custom"]))
    story.append(
        Paragraph(
            "Die Transition Matrix ist eine Matrix von Wechselwahrscheinlichkeiten. Die Zeile ist das "
            "heutige Regime, die Spalte ist das naechste Regime. Werte auf der Diagonale zeigen, wie "
            "persistent ein Regime ist.",
            styles["BodyCustom"],
        )
    )
    story.append(chart(ROOT / "public" / "reports" / "figures" / "GSPC_1d_transition_matrix.png", 12.5, 8.2))
    story.append(
        Paragraph(
            "Beispiel: Wenn ein diagonaler Wert 96% betraegt, heisst das: Laut Modell bleibt der Markt "
            "mit 96% Wahrscheinlichkeit in diesem Zustand fuer die naechste Periode. Das ist kein sicherer "
            "Forecast, sondern eine aus der Historie geschaetzte Uebergangswahrscheinlichkeit.",
            styles["Callout"],
        )
    )
    stats = read_csv(ROOT / "public" / "reports" / "tables" / "GSPC_1d_regime_stats.csv")
    rows = [["Regime", "Freq.", "Return p.a.", "Vol p.a.", "Avg duration"]]
    for row in stats:
        rows.append(
            [
                row["regime_name"],
                pct(row["frequency_pct"]),
                pct(row["annualized_return"]),
                pct(row["annualized_volatility"]),
                f"{float(row['avg_duration_days']):.1f} Bars",
            ]
        )
    story.append(styled_table(rows, [4.4 * cm, 2.2 * cm, 2.6 * cm, 2.6 * cm, 3.1 * cm], 7.6))


def add_strategy_bias(story, styles):
    story.append(PageBreak())
    story.append(Paragraph("7. Strategie-Diagnostik und Bias", styles["H1Custom"]))
    story.append(
        Paragraph(
            "Das Projekt testet eine einfache Trendfolge-Regel: Long, wenn der Preis ueber dem gleitenden "
            "Durchschnitt liegt, sonst Cash. Der Zweck ist nicht, eine fertige Trading-Strategie zu bauen, "
            "sondern zu fragen: Veraendert sich die Performance einer Regel je nach Regime?",
            styles["BodyCustom"],
        )
    )
    story.append(chart(ROOT / "public" / "reports" / "figures" / "BTC-USD_1d_strategy_by_regime.png", 12.8, 7.0))
    story.append(Paragraph("Look-ahead Bias", styles["H2Custom"]))
    story.append(
        Paragraph(
            "Der Standard-Report fitttet das HMM auf der gesamten Historie und labelt danach die gesamte "
            "Zeitreihe. Damit nutzt die Regime-Zuordnung indirekt Informationen aus der Zukunft. Fuer "
            "historische Erklaerung ist das okay, fuer Live-Trading nicht.",
            styles["BodyCustom"],
        )
    )
    story.append(
        bullet_list(
            [
                "<b>Illustrativ:</b> Full-sample fit, gut fuer Storytelling und Lernen.",
                "<b>Naehere Praxis:</b> Expanding window - bis Zeitpunkt t fitten, dann t+1 labeln.",
                "<b>Strenger Backtest:</b> Transaktionskosten, Slippage, Cash-Zins und Rebalancing einbauen.",
                "<b>Governance:</b> Jede Modellwahl dokumentieren und nicht nachtraeglich auf das beste Ergebnis optimieren.",
            ],
            styles,
        )
    )


def add_walkthrough_glossary(story, styles):
    story.append(PageBreak())
    story.append(Paragraph("8. Praktischer Ablauf und Glossar", styles["H1Custom"]))
    story.append(
        styled_table(
            [
                ["Schritt", "Was passiert?", "Typische Frage"],
                ["1. Daten", "Preise von Yahoo Finance laden.", "Ist der Ticker liquide und breit genug?"],
                ["2. Features", "Rolling Return, Volatilitaet, Momentum, Drawdown.", "Erfassen die Features Trend und Risiko?"],
                ["3. Standardisierung", "Features vergleichbar skalieren.", "Dominiert keine Spalte nur wegen Einheit?"],
                ["4. HMM fitten", "Mehrere State-Zahlen testen.", "Ist das Modell stabil und plausibel?"],
                ["5. Labels", "Jeder Zeitpunkt bekommt ein Regime.", "Passen die Regime zu bekannten Krisenphasen?"],
                ["6. Reporting", "Charts, Matrix, Stats, Strategie-Diagnostik.", "Kann ein Nicht-Quant die Aussage verstehen?"],
            ],
            [2.2 * cm, 7.1 * cm, 6.4 * cm],
            7.4,
        )
    )
    story.append(Paragraph("Glossar", styles["H2Custom"]))
    story.append(
        bullet_list(
            [
                "<b>Regime:</b> statistischer Zustand eines Marktes.",
                "<b>Feature:</b> berechnete Modell-Eingabe aus Rohdaten.",
                "<b>Volatilitaet:</b> Schwankungsintensitaet der Renditen.",
                "<b>Drawdown:</b> Verlust relativ zum vorherigen Hoch.",
                "<b>HMM:</b> Modell fuer versteckte Zustaende mit Uebergangswahrscheinlichkeiten.",
                "<b>BIC:</b> Kriterium fuer Modellwahl, bestraft Komplexitaet.",
                "<b>Look-ahead Bias:</b> Zukunftsinformation wird unbewusst in historische Signale eingebaut.",
            ],
            styles,
        )
    )
    story.append(
        Paragraph(
            "Merksatz: Das Modell liefert keine Wahrheit ueber den Markt. Es liefert eine strukturierte, "
            "reproduzierbare Brille, durch die man Marktphasen analysieren und erklaeren kann.",
            styles["Callout"],
        )
    )


def build_pdf() -> Path:
    REPO_OUTPUT.mkdir(parents=True, exist_ok=True)
    TEMP.mkdir(parents=True, exist_ok=True)
    CODEX_OUTPUT.mkdir(parents=True, exist_ok=True)

    manifest = load_manifest()
    styles = build_styles()
    pdf_path = REPO_OUTPUT / PDF_NAME

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        rightMargin=1.6 * cm,
        leftMargin=1.6 * cm,
        topMargin=1.4 * cm,
        bottomMargin=1.5 * cm,
        title="Market Regime Detector Handout",
        author="Tuki",
    )
    story = []
    add_title(story, styles)
    add_basics(story, styles)
    add_features(story, styles)
    add_hmm(story, styles)
    add_model_selection(story, styles, manifest)
    add_interpretation(story, styles, manifest)
    add_transition_stats(story, styles)
    add_strategy_bias(story, styles)
    add_walkthrough_glossary(story, styles)
    story.append(PageBreak())
    story.append(Paragraph("9. Kurz-Checkliste fuer deine Praesentation", styles["H1Custom"]))
    story.append(
        bullet_list(
            [
                "Ich kann erklaeren, warum Regime nicht von Hand gelabelt werden.",
                "Ich kann jedes Feature in einem Satz begruenden.",
                "Ich kann sagen, warum ein HMM besser passt als reines Clustering.",
                "Ich kann die Transition Matrix als Persistenz- und Wechselwahrscheinlichkeit lesen.",
                "Ich kann Look-ahead Bias ehrlich benennen.",
                "Ich kann klar sagen: Das ist ein Analyse- und Lernprojekt, keine Anlageberatung.",
            ],
            styles,
        )
    )
    story.append(Spacer(1, 0.35 * cm))
    story.append(
        Paragraph(
            "Quellen im Projekt: Python-Pipeline, generierte CSV-Reports und Dashboard-Visualisierungen "
            "aus dem Repository market_regime_detector.",
            styles["Small"],
        )
    )

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    final_copy = CODEX_OUTPUT / PDF_NAME
    shutil.copy2(pdf_path, final_copy)
    return pdf_path


if __name__ == "__main__":
    path = build_pdf()
    print(path)
