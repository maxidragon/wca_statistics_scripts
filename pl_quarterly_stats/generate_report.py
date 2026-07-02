"""
Generates a PDF report with all 22 WCA Poland quarterly statistics charts.
Two sections: full history (2005–2026) and last 5 years (2022–2026).
Each chart page includes a detailed Polish description.

Usage:
    python pl_quarterly_stats/generate_report.py
    python pl_quarterly_stats/generate_report.py --output my_report.pdf
"""
import argparse
import io
import sys
import textwrap
import types
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import matplotlib
matplotlib.use("Agg")
import matplotlib.image as mpimg
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.lines import Line2D

from loader import load
from _period import apply_filter, make_year_colors

OUT = Path(__file__).parent / "output"
OUT.mkdir(exist_ok=True)

PAGE_L = (11.69, 8.27)   # A4 landscape – chart pages
PAGE_P = (8.27, 11.69)   # A4 portrait  – title / section dividers

MONTHS_PL = ["Sty", "Lut", "Mar", "Kwi", "Maj", "Cze",
             "Lip", "Sie", "Wrz", "Paź", "Lis", "Gru"]

EVENT_NAMES = {
    "333": "3x3x3", "222": "2x2x2", "444": "4x4x4", "555": "5x5x5",
    "666": "6x6x6", "777": "7x7x7", "333bf": "3x3 Blindfolded",
    "333oh": "3x3 One-Handed", "clock": "Clock", "minx": "Megaminx",
    "pyram": "Pyraminx", "skewb": "Skewb", "sq1": "Square-1",
    "444bf": "4x4 Blindfolded", "555bf": "5x5 Blindfolded",
    "333mbf": "Multi-Blind", "333ft": "3x3 With Feet",
}

DESCRIPTIONS = {
    1: (
        "Liczba zawodów WCA w Polsce w każdym kwartale (Q1 = styczeń–marzec, Q2 = kwiecień–czerwiec, "
        "Q3 = lipiec–wrzesień, Q4 = październik–grudzień). Pozwala ocenić sezonowość – zwykle Q2 i Q3 "
        "są najbardziej aktywne – oraz trend wzrostowy lub spadkowy liczby eventów rok do roku. "
        "Duże skoki mogą odzwierciedlać momenty po przerwie pandemicznej lub wzrost liczby aktywnych organizatorów."
    ),
    2: (
        "Liniowy wykres miesięczny z osobną linią dla każdego roku. Pozwala porównać aktywność "
        "w konkretnym miesiącu pomiędzy różnymi latami – np. czy czerwiec 2024 był aktywniejszy niż "
        "czerwiec 2023. Przerwy lub szczyty powtarzające się co roku wskazują na stałe wzorce sezonowe "
        "(np. wakacyjne eventy, brak zawodów w lipcu itp.)."
    ),
    3: (
        "Skumulowana liczba zawodów od początku roku (YTD). Po każdym miesiącu widać ile zawodów "
        "odbyło się łącznie od stycznia. Jeśli linia danego roku jest wyżej niż poprzedniego już "
        "w marcu, rok ten ma szybsze tempo startowe. Przydatne do porównania czy bieżący rok "
        "zmierza ku rekordowi pod względem liczby eventów."
    ),
    4: (
        "Dla każdego kwartału: średnia i mediana liczby zawodników na pojedynczych zawodach. "
        "Mediana jest tu ważniejsza niż średnia – kilka bardzo dużych eventów (np. Mistrzostwa "
        "Polski) może mocno zawyżać średnią, podczas gdy mediana pokazuje 'typowe' zawody. "
        "Rosnąca mediana świadczy o ogólnym wzroście popularności, nie tylko o organizowaniu "
        "większych eventów."
    ),
    5: (
        "Ile różnych osób wzięło udział w polskich zawodach WCA w danym kwartale. Jedna osoba "
        "liczona raz nawet jeśli pojechała na 5 eventów w kwartale. Pokazuje 'zasięg' sceny – "
        "ilu unikalnych zawodników jest aktywnych w danym okresie. Wzrost może oznaczać zarówno "
        "napływ nowicjuszy, jak i większą aktywność stałych zawodników."
    ),
    6: (
        "Każdy słupek = łączna liczba unikalnych zawodników w kwartale, podzielona na dwie grupy: "
        "nowicjusze (osoby, dla których były to pierwsze zawody WCA w życiu, gdziekolwiek na świecie) "
        "oraz powracający (wszyscy pozostali). Pozwala zobaczyć jak zmienia się proporcja nowych do "
        "stałych zawodników i czy scena opiera się głównie na nowicjuszach czy na sprawdzonych bywalcach."
    ),
    7: (
        "Procentowy udział nowicjuszy w łącznej puli zawodników per kwartał. Szara linia "
        "przerywana to średnia dla całego okresu. Jeśli wartość rośnie – scena przyciąga "
        "proporcjonalnie więcej nowych osób. Jeśli spada – baza powracających zawodników rośnie "
        "szybciej niż napływ nowych. Bardzo wysokie wartości (ponad 40%) mogą wskazywać na eventy "
        "o charakterze rekrutacyjnym lub brak stabilnej, stałej społeczności."
    ),
    8: (
        "Histogramy rozkładu liczby zawodów odwiedzonych przez każdego zawodnika w danym roku "
        "(osobny panel per rok). Oś X = liczba startów, oś Y = ilu zawodników tyle razy pojechało. "
        "Czerwona pionowa linia = mediana. Typowy rozkład: większość zawodników jedzie 1–2 razy "
        "w roku, nieliczni 10+. Zmiana mediany w czasie pokazuje czy 'przeciętny zawodnik' "
        "jest coraz bardziej zaangażowany."
    ),
    9: (
        "Zawodnicy aktywni w co najmniej 3 różnych kwartałach danego roku – czyli osoby, "
        "które można uznać za 'regularnych'. Jeden kwartał może oznaczać jednorazowy start "
        "lub sezonowe zawody; 3+ kwartały to systematyczna aktywność przez większą część roku. "
        "Rosnąca liczba regularnych zawodników świadczy o dojrzewaniu polskiej sceny speedcubingowej."
    ),
    10: (
        "Trzy linie pokazujące trend aktywności zawodników: średnia (wrażliwa na outlierów – "
        "osoby jeżdżące 15+ razy w roku), mediana (typowy zawodnik) i 75. percentyl (osoby "
        "bardziej aktywne niż 75% sceny). Jeśli wszystkie trzy rosną – scena ogólnie jest bardziej "
        "aktywna. Jeśli rośnie tylko 75. percentyl – aktywność koncentruje się u stałej grupy entuzjastów."
    ),
    11: (
        "Liczba osób, które zadebiutowały globalnie w WCA (pierwsze zawody WCA w życiu) właśnie "
        "na polskich zawodach w danym kwartale. To inaczej niż wykres 6 – tu liczymy wyłącznie "
        "czyste debiuty, nie osoby powracające do Polski po startach za granicą. Wysokie wartości "
        "oznaczają, że Polska jest ważnym 'wejściem do WCA' dla nowych zawodników – co jest "
        "pozytywnym wskaźnikiem dostępności i atrakcyjności sceny."
    ),
    12: (
        "To samo co wykres 11 (debiuty na polskich zawodach), ale w granularności miesięcznej "
        "z osobną linią dla każdego roku. Pozwala zobaczyć czy wakacje letnie (lipiec–sierpień) "
        "lub inne okresy mają wyraźny szczyt debiutów. Szczyty mogą wiązać się z większymi "
        "eventami lub sezonowym napływem nowych osób (np. po konkursach szkolnych w maju/czerwcu)."
    ),
    13: (
        "Analiza kohortowa: dla każdego kwartału debiutów sprawdzamy jaki procent tych nowicjuszy "
        "wrócił na kolejne polskie zawody w ciągu 3, 6 lub 12 miesięcy. Kohorta Q1 2022 = wszyscy "
        "co zadebiutowali w Polsce w Q1 2022. Wysoka retencja 12m (powyżej 40%) oznacza, że scena "
        "skutecznie zatrzymuje nowych zawodników. UWAGA: ostatnie kohorty mają niekompletne dane "
        "dla okna 12m – czas jeszcze nie upłynął, więc ich wartości są z definicji zaniżone."
    ),
    14: (
        "To samo co wykres 13, ale zamiast procentów – surowe liczby: ile osób z danej kohorty "
        "wróciło w ciągu 3m / 6m / 12m (słupki grupowane), plus linia z łączną liczbą nowicjuszy "
        "w kohorcie. Pozwala jednocześnie ocenić skalę kohorty i jej retencję. Mała kohorta "
        "z wysoką retencją jest często 'zdrowsza' dla sceny niż duża z niską retencją."
    ),
    15: (
        "Histogram pokazujący ile razy łącznie wrócił każdy nowicjusz ze wszystkich kohort razem. "
        "Słupek przy 0 = osoby, które nigdy nie wróciły na polskie zawody. Tytuł wykresu podaje "
        "ich odsetek. Kształt rozkładu odpowiada na pytanie: czy 'jednorazowcy' to wyjątek czy "
        "reguła? Sceny z silną społecznością mają mniej jednorazowców i dłuższy ogon rozkładu "
        "(wielu zawodników wracających regularnie przez lata)."
    ),
    16: (
        "Identyfikuje cykliczne serie zawodów przez usunięcie rocznika z nazwy (np. 'Warsaw Open 2023' "
        "→ 'Warsaw Open'). Siatka: wiersze = serie, kolumny = lata, komórka = liczba zawodników "
        "(— = brak edycji). Etykieta zawiera typowy miesiąc rozgrywania. Posortowane od "
        "najdłużej działających i według łącznej frekwencji. Kolor komórki = frekwencja "
        "(im ciemniej tym więcej zawodników). Szara pozioma linia = ogólna średnia."
    ),
    17: (
        "Liniowy wykres frekwencji dla top 10 cyklicznych serii, pokazujący zmiany z edycji "
        "na edycję. Pozwala zidentyfikować serie rosnące (coraz popularniejsze), malejące "
        "(tracące zawodników) lub stabilne. Luki w liniach = brak edycji w danym roku. "
        "Przydatne dla organizatorów i dla oceny które eventy budują lojalną publiczność."
    ),
    18: (
        "Poziomy wykres słupkowy 20 zawodów z największą bezwzględną liczbą debiutantów WCA. "
        "Kolory słupków = rok rozgrywania. Pokazuje które konkretne eventy najbardziej 'wprowadzają' "
        "nowych zawodników do sceny. Zazwyczaj są to duże imprezy (Mistrzostwa Polski, duże otwarte "
        "eventy) lub zawody w dużych miastach. Wysoka absolutna liczba nowicjuszy niekoniecznie "
        "oznacza wysoki % – event może mieć 50 nowicjuszy, ale i 500 doświadczonych zawodników."
    ),
    19: (
        "Top 20 zawodów według procentowego udziału nowicjuszy w łącznej frekwencji (minimalny próg: "
        "30 zawodników, żeby odfiltrować bardzo małe eventy). Pokazuje które zawody mają najbardziej "
        "'nowicjuszowy' charakter – często lokalne eventy rekrutacyjne, zawody w mniejszych miastach "
        "lub imprezy celowo skierowane do początkujących. Wysoki % (ponad 60%) może oznaczać event "
        "stricte rekrutacyjny."
    ),
    20: (
        "Wykres geograficzny na współrzędnych (długość i szerokość geograficzna). Każdy bąbel = miasto. "
        "Rozmiar bąbla = łączna liczba nowicjuszy ze wszystkich zawodów w tym mieście. Kolor = "
        "średnia liczba nowicjuszy na zawody. Top 20 miast jest oznaczonych. Rozkład polskich miast "
        "na wykresie tworzy rozpoznawalny kształt mapy Polski bez potrzeby nakładania tła kartograficznego."
    ),
    21: (
        "Podwójny wykres miesięczny: słupki (lewa oś) = średnia liczba nowicjuszy na zawody "
        "w danym miesiącu; linia (prawa oś) = średni % nowicjuszy. Rozróżnienie jest ważne: "
        "miesiąc może mieć dużo nowicjuszy absolutnie (bo jest dużo zawodów), ale niekoniecznie "
        "wysoki % jeśli jeżdżą też doświadczeni zawodnicy. Pokazuje sezonowość rekrutacji "
        "nowych zawodników do sceny speedcubingowej."
    ),
    22: (
        "Dla każdej dyscypliny WCA (3x3, 2x2, Pyraminx itd.): średni % nowicjuszy na zawodach, "
        "które tę dyscyplinę oferowały. Zielony = powyżej ogólnej średniej (linia przerywana), "
        "pomarańczowy = poniżej. Sugeruje korelację między zestawem dyscyplin a 'nowicjuszowością' "
        "eventu. UWAGA: to korelacja, nie przyczynowość – duże prestiżowe eventy często oferują "
        "więcej dyscyplin, ale niekoniecznie wyższy % nowicjuszy."
    ),
}

# ── PDF helpers ───────────────────────────────────────────────────────────────

def capture_fig(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    buf.seek(0)
    plt.close(fig)
    return buf


def add_title_page(pdf):
    fig = plt.figure(figsize=PAGE_P)
    fig.patch.set_facecolor("#2C3E50")
    fig.text(0.5, 0.62, "WCA Poland", ha="center", fontsize=38,
             fontweight="bold", color="white")
    fig.text(0.5, 0.53, "Statistics Report", ha="center", fontsize=26, color="#BDC3C7")
    fig.text(0.5, 0.40, "Statystyki speedcubingu w Polsce\n2005–2026", ha="center",
             fontsize=14, color="#ECF0F1", linespacing=1.8)
    fig.text(0.5, 0.25, f"Wygenerowano: {date.today().strftime('%d.%m.%Y')}",
             ha="center", fontsize=11, color="#95A5A6")
    fig.text(0.5, 0.20, "Dane: worldcubeassociation.org/export/results",
             ha="center", fontsize=10, color="#7F8C8D")
    pdf.savefig(fig)
    plt.close(fig)


def add_section_page(pdf, heading, period_label, n_comps, n_att):
    fig = plt.figure(figsize=PAGE_P)
    fig.patch.set_facecolor("#1A252F")
    fig.text(0.5, 0.62, heading, ha="center", fontsize=28,
             fontweight="bold", color="white")
    fig.text(0.5, 0.52, period_label, ha="center", fontsize=22, color="#3498DB")
    fig.text(0.5, 0.40,
             f"Zawody w Polsce: {n_comps}\nRekordy frekwencji: {n_att:,}",
             ha="center", fontsize=13, color="#BDC3C7", linespacing=1.8)
    pdf.savefig(fig)
    plt.close(fig)


def add_chart_page(pdf, buf, num, title, description):
    fig = plt.figure(figsize=PAGE_L)

    buf.seek(0)
    img_data = mpimg.imread(buf)
    ax_img = fig.add_axes([0.01, 0.26, 0.98, 0.70])
    ax_img.imshow(img_data)
    ax_img.axis("off")

    fig.text(0.5, 0.975, f"Wykres {num}: {title}",
             ha="center", va="top", fontsize=12, fontweight="bold", color="#2C3E50")

    sep = Line2D([0.02, 0.98], [0.255, 0.255], transform=fig.transFigure,
                 color="#BDC3C7", linewidth=0.8)
    fig.add_artist(sep)

    wrapped = textwrap.fill(description, width=135)
    fig.text(0.02, 0.245, wrapped, ha="left", va="top",
             fontsize=8.5, color="#2C3E50", linespacing=1.45)

    pdf.savefig(fig)
    plt.close(fig)


# ── Chart generation ──────────────────────────────────────────────────────────

def _ql(df, y="year", q="quarter"):
    return df[y].astype(str) + " Q" + df[q].astype(str)


def charts_competition_trends(comps_pl, att, period_label, YC):
    out = []
    ny = comps_pl["year"].nunique()

    q = comps_pl.groupby(["year", "quarter"]).size().reset_index(name="n")
    q["label"] = _ql(q)
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.bar(q["label"], q["n"], color="#4C72B0")
    ax.set(xlabel="Kwartał", ylabel="Liczba zawodów",
           title=f"Liczba zawodów WCA w Polsce per kwartał ({period_label})")
    ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    plt.xticks(rotation=45, ha="right"); plt.tight_layout()
    out.append((1, "Zawody per kwartał", capture_fig(fig)))

    fig, ax = plt.subplots(figsize=(12, 5))
    for yr, grp in comps_pl.groupby("year"):
        m = grp.groupby("month").size().reindex(range(1, 13), fill_value=0)
        ax.plot(m.index, m.values, marker="o", label=str(yr), color=YC.get(yr))
    ax.set_xticks(range(1, 13)); ax.set_xticklabels(MONTHS_PL)
    ax.set(xlabel="Miesiąc", ylabel="Liczba zawodów",
           title=f"Zawody WCA per miesiąc – porównanie lat ({period_label})")
    ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    ax.legend(title="Rok", ncol=max(1, ny // 10)); ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    out.append((2, "Zawody per miesiąc – lata nakładane", capture_fig(fig)))

    fig, ax = plt.subplots(figsize=(12, 5))
    for yr, grp in comps_pl.groupby("year"):
        m = grp.groupby("month").size().reindex(range(1, 13), fill_value=0).cumsum()
        ax.plot(m.index, m.values, marker="o", label=str(yr), color=YC.get(yr))
    ax.set_xticks(range(1, 13)); ax.set_xticklabels(MONTHS_PL)
    ax.set(xlabel="Miesiąc", ylabel="Łączna liczba zawodów (YTD)",
           title=f"Skumulowana liczba zawodów YTD ({period_label})")
    ax.legend(title="Rok", ncol=max(1, ny // 10)); ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    out.append((3, "Skumulowana liczba zawodów YTD", capture_fig(fig)))

    apc = (att.groupby("competition_id")["person_id"].nunique().reset_index(name="n")
           .merge(comps_pl[["id", "year", "quarter"]].rename(columns={"id": "competition_id"}),
                  on="competition_id"))
    qa = apc.groupby(["year", "quarter"])["n"].agg(mean="mean", median="median").reset_index()
    qa["label"] = _ql(qa)
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(qa["label"], qa["mean"],   marker="o", label="Średnia")
    ax.plot(qa["label"], qa["median"], marker="s", linestyle="--", label="Mediana")
    ax.set(xlabel="Kwartał", ylabel="Zawodnicy na zawodach",
           title=f"Średnia/mediana frekwencji per zawody per kwartał ({period_label})")
    plt.xticks(rotation=45, ha="right"); ax.legend(); ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    out.append((4, "Średnia/mediana frekwencji na zawodach", capture_fig(fig)))
    return out


def charts_competitor_activity(comps_pl, att, period_label):
    out = []
    years = sorted(att["year"].unique())

    q_uniq = att.groupby(["year", "quarter"])["person_id"].nunique().reset_index(name="n")
    q_uniq["label"] = _ql(q_uniq)
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.bar(q_uniq["label"], q_uniq["n"], color="#55A868")
    ax.set(xlabel="Kwartał", ylabel="Unikalni zawodnicy",
           title=f"Unikalni zawodnicy per kwartał ({period_label})")
    ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    plt.xticks(rotation=45, ha="right"); plt.tight_layout()
    out.append((5, "Unikalni zawodnicy per kwartał", capture_fig(fig)))

    qn = att[att.is_newcomer].groupby(["year", "quarter"])["person_id"].nunique().reset_index(name="newcomers")
    qr = att[~att.is_newcomer].groupby(["year", "quarter"])["person_id"].nunique().reset_index(name="returning")
    qc = qn.merge(qr, on=["year", "quarter"], how="outer").fillna(0).sort_values(["year", "quarter"])
    qc["label"] = _ql(qc)
    x = range(len(qc))
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.bar(x, qc["returning"], label="Powracający", color="#4C72B0")
    ax.bar(x, qc["newcomers"], bottom=qc["returning"], label="Nowicjusze", color="#DD8452")
    ax.set_xticks(list(x)); ax.set_xticklabels(qc["label"], rotation=45, ha="right")
    ax.set(ylabel="Zawodnicy",
           title=f"Nowicjusze vs powracający per kwartał ({period_label})")
    ax.legend(); plt.tight_layout()
    out.append((6, "Nowicjusze vs powracający – stacked bar", capture_fig(fig)))

    qc["pct_new"] = qc["newcomers"] / (qc["newcomers"] + qc["returning"]) * 100
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(list(x), qc["pct_new"], marker="o", color="#DD8452")
    ax.axhline(qc["pct_new"].mean(), linestyle="--", color="gray",
               label=f"Średnia {qc['pct_new'].mean():.1f}%")
    ax.set_xticks(list(x)); ax.set_xticklabels(qc["label"], rotation=45, ha="right")
    ax.set(ylabel="% nowicjuszy", ylim=(0, 100),
           title=f"Udział nowicjuszy per kwartał ({period_label})")
    ax.legend(); ax.grid(axis="y", alpha=0.3); plt.tight_layout()
    out.append((7, "% nowicjuszy per kwartał", capture_fig(fig)))

    cpp = att.groupby(["person_id", "year"])["competition_id"].nunique().reset_index(name="n_comps")
    n = len(years); ncols = min(n, 6); nrows = (n + ncols - 1) // ncols
    fig, ag = plt.subplots(nrows, ncols, figsize=(4 * ncols, 4 * nrows),
                            sharey=False, squeeze=False)
    af = ag.flatten()
    for i, yr in enumerate(years):
        ax = af[i]; data = cpp[cpp.year == yr]["n_comps"]
        ax.hist(data, bins=range(1, min(data.max() + 2, 21)),
                color="#4C72B0", edgecolor="white", align="left")
        med = data.median()
        ax.axvline(med, color="red", linestyle="--", label=f"Med: {med:.1f}")
        ax.set(title=str(yr), xlabel="Starty", ylabel="Zawodnicy")
        ax.legend(fontsize=8); ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    for ax in af[n:]:
        ax.set_visible(False)
    fig.suptitle(f"Rozkład startów per zawodnik per rok ({period_label})", y=1.02)
    plt.tight_layout()
    out.append((8, "Rozkład liczby startów per zawodnik per rok", capture_fig(fig)))

    qa2 = att.groupby(["person_id", "year"])["quarter"].nunique().reset_index(name="q_active")
    active = qa2[qa2.q_active >= 3].groupby("year").size().reset_index(name="n")
    fig, ax = plt.subplots(figsize=(max(8, len(years) * 0.6), 4))
    ax.bar(active["year"].astype(str), active["n"], color="#C44E52")
    ax.set(xlabel="Rok", ylabel="Zawodnicy",
           title=f"Zawodnicy aktywni w 3+ kwartałach roku ({period_label})")
    ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    plt.xticks(rotation=45, ha="right"); plt.tight_layout()
    out.append((9, "Stale aktywni (3+ kwartały w roku)", capture_fig(fig)))

    mt = cpp.groupby("year")["n_comps"].agg(
        mean="mean", median="median", q75=lambda x: x.quantile(0.75)
    ).reset_index()
    fig, ax = plt.subplots(figsize=(max(8, len(years) * 0.6), 4))
    ax.plot(mt["year"].astype(str), mt["mean"],   marker="o", label="Średnia")
    ax.plot(mt["year"].astype(str), mt["median"], marker="s", linestyle="--", label="Mediana")
    ax.plot(mt["year"].astype(str), mt["q75"],    marker="^", linestyle=":", label="75 percentyl")
    ax.set(xlabel="Rok", ylabel="Starty per zawodnik",
           title=f"Trend aktywności zawodników per rok ({period_label})")
    ax.legend(); ax.grid(axis="y", alpha=0.3)
    plt.xticks(rotation=45, ha="right"); plt.tight_layout()
    out.append((10, "Trend aktywności per rok", capture_fig(fig)))
    return out


def charts_newcomer_cohorts(comps_pl, att, period_label, YC):
    out = []
    ny = comps_pl["year"].nunique()

    debuts = (
        att[att.is_newcomer][["person_id", "competition_id", "date", "year", "quarter"]]
        .drop_duplicates("person_id")
        .rename(columns={"date": "debut_date", "year": "debut_year", "quarter": "debut_quarter"})
    )

    qn = debuts.groupby(["debut_year", "debut_quarter"]).size().reset_index(name="newcomers")
    qn["label"] = qn["debut_year"].astype(str) + " Q" + qn["debut_quarter"].astype(str)
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.bar(qn["label"], qn["newcomers"], color="#DD8452")
    ax.set(xlabel="Kwartał debiutu", ylabel="Nowicjusze",
           title=f"Nowicjusze WCA per kwartał – czyste debiuty ({period_label})")
    ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    plt.xticks(rotation=45, ha="right"); plt.tight_layout()
    out.append((11, "Nowicjusze per kwartał (debiuty)", capture_fig(fig)))

    dwm = att[att.is_newcomer][["person_id", "year", "month"]].drop_duplicates("person_id")
    fig, ax = plt.subplots(figsize=(12, 5))
    for yr, grp in dwm.groupby("year"):
        m = grp.groupby("month").size().reindex(range(1, 13), fill_value=0)
        ax.plot(m.index, m.values, marker="o", label=str(yr), color=YC.get(yr))
    ax.set_xticks(range(1, 13)); ax.set_xticklabels(MONTHS_PL)
    ax.set(xlabel="Miesiąc", ylabel="Nowicjusze",
           title=f"Nowicjusze per miesiąc – porównanie lat ({period_label})")
    ax.legend(title="Rok", ncol=max(1, ny // 10)); ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    out.append((12, "Nowicjusze per miesiąc – lata nakładane", capture_fig(fig)))

    followup = (
        att[att.person_id.isin(debuts.person_id)]
        .merge(debuts[["person_id", "debut_date", "debut_year", "debut_quarter"]], on="person_id")
    )
    followup["days_after"] = (followup["date"] - followup["debut_date"]).dt.days

    rows = []
    for (yr, qt), cd in debuts.groupby(["debut_year", "debut_quarter"]):
        n_total = len(cd); pids = set(cd.person_id)
        cfu = followup[(followup.person_id.isin(pids)) & (followup.days_after > 0)]
        row = {"year": yr, "quarter": qt, "newcomers": n_total}
        for days, key in [(90, "3m"), (180, "6m"), (365, "12m")]:
            ret = cfu[cfu.days_after <= days]["person_id"].nunique()
            row[f"ret_{key}"] = ret
            row[f"pct_{key}"] = round(ret / n_total * 100, 1) if n_total else 0.0
        rows.append(row)
    rdf = pd.DataFrame(rows).sort_values(["year", "quarter"])
    rdf["label"] = rdf["year"].astype(str) + " Q" + rdf["quarter"].astype(str)

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(rdf["label"], rdf["pct_3m"],  marker="o", label="3 miesiące")
    ax.plot(rdf["label"], rdf["pct_6m"],  marker="s", label="6 miesięcy")
    ax.plot(rdf["label"], rdf["pct_12m"], marker="^", label="12 miesięcy")
    ax.set(xlabel="Kwartał debiutu", ylabel="% nowicjuszy którzy wrócili",
           title=f"Retencja kohort nowicjuszy – % powrotów ({period_label})", ylim=(0, 100))
    plt.xticks(rotation=45, ha="right"); ax.legend(); ax.grid(axis="y", alpha=0.3)
    ax.annotate("⚠ Ostatnie kohorty mogą mieć niekompletne dane retencji 12m",
                xy=(0.99, 0.02), xycoords="axes fraction", ha="right", fontsize=8, color="gray")
    plt.tight_layout()
    out.append((13, "Retencja kohort – % powrotów (3m / 6m / 12m)", capture_fig(fig)))

    x = range(len(rdf)); w = 0.25
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.bar([i - w for i in x], rdf["ret_3m"],  width=w, label="3m",  color="#4C72B0")
    ax.bar([i      for i in x], rdf["ret_6m"],  width=w, label="6m",  color="#55A868")
    ax.bar([i + w for i in x], rdf["ret_12m"], width=w, label="12m", color="#8172B2")
    ax.plot(x, rdf["newcomers"], marker="o", color="black", linestyle="--", label="Łącznie nowicjuszy")
    ax.set_xticks(list(x)); ax.set_xticklabels(rdf["label"], rotation=45, ha="right")
    ax.set(ylabel="Zawodnicy",
           title=f"Retencja kohort – liczby bezwzględne ({period_label})")
    ax.legend(); plt.tight_layout()
    out.append((14, "Retencja kohort – liczby bezwzględne", capture_fig(fig)))

    rc = (followup[followup.days_after > 0].drop_duplicates(["person_id", "competition_id"])
          .groupby("person_id")["competition_id"].count().reset_index(name="returns"))
    never = pd.DataFrame({
        "person_id": list(set(debuts.person_id) - set(rc.person_id)), "returns": 0
    })
    all_r = pd.concat([rc, never], ignore_index=True)
    n_nev = (all_r["returns"] == 0).sum(); n_tot = len(all_r)
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.hist(all_r["returns"], bins=range(0, min(all_r["returns"].max() + 2, 26)),
            color="#8172B2", edgecolor="white", align="left")
    ax.axvline(0.5, color="red", linestyle="--", alpha=0.6)
    ax.set(xlabel="Liczba kolejnych zawodów w Polsce po debiucie", ylabel="Zawodnicy",
           title=f"Ile razy wrócili nowicjusze? ({period_label})\n"
                 f"Nigdy nie wróciło: {n_nev}/{n_tot} ({n_nev/n_tot*100:.1f}%)")
    ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True)); plt.tight_layout()
    out.append((15, "Rozkład liczby powrotów per nowicjusz", capture_fig(fig)))
    return out


def charts_recurring_series(comps_pl, att, period_label):
    out = []
    comps_pl = comps_pl.copy()

    apc = att.groupby("competition_id")["person_id"].nunique().reset_index(name="n_competitors")
    comps_pl["series_name"] = (
        comps_pl["name"].str.replace(r"\b\d{4}\b", "", regex=True)
        .str.strip().str.replace(r"\s+", " ", regex=True)
    )
    cwa = (comps_pl[["id", "name", "series_name", "year", "month"]]
           .rename(columns={"id": "competition_id"})
           .merge(apc, on="competition_id", how="left"))
    cwa["n_competitors"] = cwa["n_competitors"].fillna(0).astype(int)

    yps = cwa.groupby("series_name")["year"].nunique()
    rec = cwa[cwa.series_name.isin(yps[yps >= 3].index)].copy()

    if rec.empty:
        return out

    typ_m = rec.groupby("series_name")["month"].median().round().astype(int)

    def lbl(name):
        m = typ_m.get(name)
        return f"{name} ({MONTHS_PL[m - 1]})" if m else name

    pivot = (rec.pivot_table(index="series_name", columns="year",
                             values="n_competitors", aggfunc="sum")
             .fillna(0).astype(int))
    pivot.index = [lbl(n) for n in pivot.index]
    sk = pd.DataFrame({"editions": (pivot > 0).sum(axis=1), "total": pivot.sum(axis=1)},
                      index=pivot.index)
    pivot = pivot.loc[sk.sort_values(["editions", "total"], ascending=False).index]

    hm = pivot.head(30); mv = hm.values.max(); nc = len(hm.columns)
    fig, ax = plt.subplots(figsize=(max(10, nc * 0.7), max(6, len(hm) * 0.42)))
    im = ax.imshow(hm.values, aspect="auto", cmap="YlOrRd", vmin=0)
    for i in range(len(hm)):
        for j in range(nc):
            v = hm.iloc[i, j]
            col = "white" if v > mv * 0.65 else ("black" if v > 0 else "#bbbbbb")
            ax.text(j, i, str(v) if v > 0 else "—", ha="center", va="center",
                    fontsize=7.5, color=col)
    ax.set_xticks(range(nc)); ax.set_xticklabels(hm.columns, rotation=45, ha="right")
    ax.set_yticks(range(len(hm))); ax.set_yticklabels(hm.index, fontsize=8)
    plt.colorbar(im, ax=ax, label="Zawodnicy", shrink=0.55)
    ax.set_title(f"Cykliczne serie zawodów – frekwencja per edycja ({period_label})\n"
                 "(w nawiasie typowy miesiąc)")
    plt.tight_layout()
    out.append((16, "Heatmapa cyklicznych serii zawodów", capture_fig(fig)))

    top10 = pivot.head(10)
    fig, ax = plt.subplots(figsize=(12, 5))
    for sl, row in top10.iterrows():
        valid = row[row > 0]
        ax.plot(valid.index, valid.values, marker="o",
                label=sl if len(sl) <= 38 else sl[:35] + "...")
    ax.set(xlabel="Rok", ylabel="Zawodnicy",
           title=f"Frekwencja na cyklicznych zawodach – top 10 serii ({period_label})")
    ax.legend(fontsize=7.5, loc="upper left", bbox_to_anchor=(1, 1))
    ax.grid(axis="y", alpha=0.3); ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    plt.tight_layout()
    out.append((17, "Trend frekwencji top serii", capture_fig(fig)))
    return out


def charts_newcomer_attractors(comps_pl, att, period_label, YC):
    out = []
    MIN_C = 30; TOP_N = 20

    cs = (att.groupby("competition_id")
          .agg(total=("person_id", "nunique"), newcomers=("is_newcomer", "sum"))
          .reset_index())
    cs["pct_newcomers"] = cs["newcomers"] / cs["total"] * 100
    cs = cs.merge(
        comps_pl[["id", "name", "city_name", "year", "month",
                  "latitude_microdegrees", "longitude_microdegrees", "event_specs"]]
        .rename(columns={"id": "competition_id"}), on="competition_id")

    yl = [mpatches.Patch(color=c, label=str(y))
          for y, c in YC.items() if y in cs["year"].unique()]

    top_abs = cs.nlargest(TOP_N, "newcomers").sort_values("newcomers")
    fig, ax = plt.subplots(figsize=(12, 7))
    bars = ax.barh(top_abs["name"], top_abs["newcomers"],
                   color=top_abs["year"].map(YC))
    ax.bar_label(bars, padding=3, fontsize=8)
    ax.set(xlabel="Liczba nowicjuszy",
           title=f"Top {TOP_N} zawodów z największą liczbą nowicjuszy ({period_label})")
    ax.legend(handles=yl, title="Rok", loc="lower right"); plt.tight_layout()
    out.append((18, "Top zawody wg liczby nowicjuszy", capture_fig(fig)))

    top_pct = (cs[cs.total >= MIN_C].nlargest(TOP_N, "pct_newcomers")
               .sort_values("pct_newcomers"))
    fig, ax = plt.subplots(figsize=(12, 7))
    bars = ax.barh(top_pct["name"], top_pct["pct_newcomers"],
                   color=top_pct["year"].map(YC))
    ax.bar_label(bars, fmt="%.1f%%", padding=3, fontsize=8)
    ax.set(xlabel="% nowicjuszy",
           title=f"Top {TOP_N} zawodów wg udziału nowicjuszy (min. {MIN_C} zawodników, {period_label})")
    ax.legend(handles=yl, title="Rok", loc="lower right"); plt.tight_layout()
    out.append((19, "Top zawody wg % nowicjuszy", capture_fig(fig)))

    cs["lat"] = cs["latitude_microdegrees"] / 1e6
    cs["lon"] = cs["longitude_microdegrees"] / 1e6
    cg = (cs.groupby("city_name")
          .agg(total_newcomers=("newcomers", "sum"), avg_newcomers=("newcomers", "mean"),
               lat=("lat", "mean"), lon=("lon", "mean"))
          .reset_index())
    fig, ax = plt.subplots(figsize=(9, 8))
    sc = ax.scatter(cg["lon"], cg["lat"], s=cg["total_newcomers"] * 2.5,
                    c=cg["avg_newcomers"], cmap="YlOrRd", alpha=0.75,
                    edgecolors="#555", linewidths=0.5)
    plt.colorbar(sc, ax=ax, label="Śr. nowicjuszy na zawody", shrink=0.6)
    for _, row in cg.nlargest(20, "total_newcomers").iterrows():
        ax.annotate(row["city_name"], (row["lon"], row["lat"] + 0.06),
                    fontsize=7, ha="center", va="bottom")
    ax.set(xlabel="Długość geograficzna", ylabel="Szerokość geograficzna",
           title=f"Rozkład geograficzny nowicjuszy ({period_label})\n"
                 "Rozmiar = łączna liczba  |  Kolor = średnia na zawody")
    plt.tight_layout()
    out.append((20, "Mapa bąbelkowa nowicjuszy", capture_fig(fig)))

    mo = cs.groupby("month").agg(avg_count=("newcomers", "mean"),
                                  avg_pct=("pct_newcomers", "mean")).reset_index()
    fig, ax1 = plt.subplots(figsize=(12, 5)); ax2 = ax1.twinx()
    ax1.bar(mo["month"], mo["avg_count"], color="#DD8452", alpha=0.75, label="Śr. liczba")
    ax2.plot(mo["month"], mo["avg_pct"], marker="o", color="#4C72B0", linewidth=2, label="Śr. %")
    ax1.set_xticks(range(1, 13)); ax1.set_xticklabels(MONTHS_PL)
    ax1.set_ylabel("Śr. liczba nowicjuszy na zawody", color="#DD8452")
    ax2.set_ylabel("Śr. % nowicjuszy", color="#4C72B0")
    ax1.set_title(f"Nowicjusze per miesiąc – wzorzec sezonowy ({period_label})")
    h1, l1 = ax1.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc="upper left"); plt.tight_layout()
    out.append((21, "Nowicjusze per miesiąc – wzorzec sezonowy", capture_fig(fig)))

    ce = (cs[["competition_id", "pct_newcomers", "event_specs"]]
          .dropna(subset=["event_specs"])
          .assign(ev=lambda df: df["event_specs"].str.split())
          .explode("ev").rename(columns={"ev": "event_id"})
          .dropna(subset=["event_id"]))
    overall = cs["pct_newcomers"].mean()
    ea = (ce.groupby("event_id")
          .agg(avg_pct=("pct_newcomers", "mean"), n=("competition_id", "nunique"))
          .reset_index().sort_values("avg_pct", ascending=True))
    ea["event_name"] = ea["event_id"].map(EVENT_NAMES).fillna(ea["event_id"])
    fig, ax = plt.subplots(figsize=(10, max(5, len(ea) * 0.42)))
    cols = ["#55A868" if v >= overall else "#DD8452" for v in ea["avg_pct"]]
    bars = ax.barh(ea["event_name"], ea["avg_pct"], color=cols)
    ax.axvline(overall, color="gray", linestyle="--", label=f"Średnia ({overall:.1f}%)")
    ax.bar_label(bars, fmt="%.1f%%", padding=3, fontsize=8)
    ax.set(xlabel="Śr. % nowicjuszy na zawodach oferujących tę konkurencję",
           title=f"Nowicjusze a oferowane dyscypliny WCA ({period_label})\n"
                 "Zielony = powyżej średniej, pomarańczowy = poniżej")
    ax.legend(); plt.tight_layout()
    out.append((22, "Nowicjusze a oferowane dyscypliny WCA", capture_fig(fig)))
    return out


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(OUT / "raport_wca_polska.pdf"))
    cli = parser.parse_args()

    print("Loading data (this may take a moment)…")
    comps_all, att_all, persons, first_comp = load()
    print(f"  Total Polish competitions: {len(comps_all)}")

    PERIODS = [
        (None, "Pełna historia"),
        (5,    "Ostatnie 5 lat"),
    ]

    with PdfPages(cli.output) as pdf:
        add_title_page(pdf)

        for last_n, heading in PERIODS:
            mock = types.SimpleNamespace(last=last_n)
            comps_pl, att, period_label, _ = apply_filter(
                comps_all.copy(), att_all.copy(), mock
            )
            YC = make_year_colors(comps_pl["year"].unique())
            add_section_page(pdf, heading, period_label, len(comps_pl), len(att))
            print(f"\n  {heading} ({period_label})…")

            all_charts = (
                charts_competition_trends(comps_pl, att, period_label, YC)
                + charts_competitor_activity(comps_pl, att, period_label)
                + charts_newcomer_cohorts(comps_pl, att, period_label, YC)
                + charts_recurring_series(comps_pl, att, period_label)
                + charts_newcomer_attractors(comps_pl, att, period_label, YC)
            )

            for num, title, buf in all_charts:
                add_chart_page(pdf, buf, num, title, DESCRIPTIONS[num])
                print(f"    ✓ {num}: {title}")

    print(f"\nReport saved: {cli.output}")


if __name__ == "__main__":
    main()
