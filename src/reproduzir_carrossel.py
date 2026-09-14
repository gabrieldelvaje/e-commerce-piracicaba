from pathlib import Path
import unicodedata
import pandas as pd

DATA = Path(__file__).resolve().parents[1] / "data" / "varejo_piracicaba_analise_ecommerce.csv.gz"
DATA_REFERENCIA = pd.Timestamp("2026-08-08")


def normalizar_texto(valor):
    if pd.isna(valor):
        return ""
    texto = str(valor).upper().strip()
    return "".join(
        c for c in unicodedata.normalize("NFKD", texto)
        if not unicodedata.combining(c)
    )


def carregar_base(caminho=DATA):
    df = pd.read_csv(caminho, sep=";", encoding="utf-8-sig", low_memory=False)
    for coluna in ["data_inicio_atividade", "data_fechamento"]:
        df[coluna] = pd.to_datetime(df[coluna], errors="coerce")

    bairro = df["bairro"].map(normalizar_texto)
    variantes_bairro_alto = {"BAIRRO ALTO", "B ALTO", "B.ALTO", "B. ALTO", "ALTO"}
    df["eh_centro_carrossel"] = bairro.str.contains("CENTRO", na=False) | bairro.isin(variantes_bairro_alto)
    df["regiao"] = df["eh_centro_carrossel"].map({True: "Centro", False: "Outros bairros"})
    return df


def estoque_em(df, data):
    data = pd.Timestamp(data)
    return df[
        (df["data_inicio_atividade"] <= data)
        & (df["data_fechamento"].isna() | (df["data_fechamento"] > data))
    ].copy()


def pct(valor):
    return f"{valor:.1f}%".replace(".", ",")


def slide_2(df):
    ano = df["data_inicio_atividade"].dt.year
    periodos = {
        "2000–2009": ano.between(2000, 2009),
        "2010–2019": ano.between(2010, 2019),
        "2020–2026": ano.between(2020, 2026),
        "2025": ano.eq(2025),
    }
    return {nome: 100 * df.loc[filtro, "eh_centro_carrossel"].mean() for nome, filtro in periodos.items()}


def slide_3(df):
    ativos = df[~df["baixada"].astype(str).str.lower().eq("true")].copy()
    ativos["idade"] = (DATA_REFERENCIA - ativos["data_inicio_atividade"]).dt.days / 365.2425
    ativos["ultimos_5_anos"] = ativos["data_inicio_atividade"] >= DATA_REFERENCIA - pd.DateOffset(years=5)

    saida = {}
    for regiao, grupo in ativos.groupby("regiao"):
        saida[regiao] = {
            "idade_mediana": grupo["idade"].median(),
            "15_anos_ou_mais": 100 * grupo["idade"].ge(15).mean(),
            "nascidas_ultimos_5_anos": 100 * grupo["ultimos_5_anos"].mean(),
        }
    return saida


def slide_4(df):
    estoque_2024 = estoque_em(df, "2024-12-31").groupby("regiao").size()
    aberturas = df[df["data_inicio_atividade"].dt.year.eq(2025)].groupby("regiao").size()
    baixas = df[df["data_fechamento"].dt.year.eq(2025)].groupby("regiao").size()

    saida = {}
    for regiao in ["Centro", "Outros bairros"]:
        saida[regiao] = {
            "aberturas": int(aberturas[regiao]),
            "baixas": int(baixas[regiao]),
            "taxa_abertura": 100 * aberturas[regiao] / estoque_2024[regiao],
            "taxa_baixa": 100 * baixas[regiao] / estoque_2024[regiao],
            "saldo": int(aberturas[regiao] - baixas[regiao]),
        }
    return saida


def slide_5(df):
    alta = df[df["exposicao_ecommerce"].astype(str).str.strip().eq("Alta")].copy()
    estoque_2019 = estoque_em(alta, "2019-12-31").groupby("regiao").size()
    estoque_2026 = estoque_em(alta, DATA_REFERENCIA).groupby("regiao").size()
    aberturas = alta[alta["data_inicio_atividade"].dt.year.eq(2025)].groupby("regiao").size()
    baixas = alta[alta["data_fechamento"].dt.year.eq(2025)].groupby("regiao").size()

    saida = {}
    for regiao in ["Centro", "Outros bairros"]:
        saida[regiao] = {
            "crescimento_estoque_2019_2026": 100 * (estoque_2026[regiao] / estoque_2019[regiao] - 1),
            "saldo_2025": int(aberturas[regiao] - baixas[regiao]),
        }
    return saida


def slide_6(df):
    segmentos = ["Joalheria e relojoaria", "Eletroeletrônicos", "Moda", "Casa e decoração"]
    saida = {}
    for segmento in segmentos:
        base = df[df["segmento_varejo"].astype(str).str.strip().eq(segmento)]
        s2010 = estoque_em(base, "2010-12-31")
        s2026 = estoque_em(base, DATA_REFERENCIA)
        saida[segmento] = {
            "2010": 100 * s2010["eh_centro_carrossel"].mean(),
            "2026": 100 * s2026["eh_centro_carrossel"].mean(),
        }
    return saida


def main():
    df = carregar_base()

    print("SLIDE 2 — participação do Centro nas novas lojas")
    for periodo, valor in slide_2(df).items():
        print(f"  {periodo}: {pct(valor)}")

    print("\nSLIDE 3 — perfil das lojas não baixadas em 08/08/2026")
    for regiao, valores in slide_3(df).items():
        print(f"  {regiao}: idade mediana {valores['idade_mediana']:.1f}; "
              f"15+ anos {pct(valores['15_anos_ou_mais'])}; "
              f"últimos 5 anos {pct(valores['nascidas_ultimos_5_anos'])}")

    print("\nSLIDE 4 — aberturas e baixas em 2025")
    for regiao, valores in slide_4(df).items():
        print(f"  {regiao}: abertura {pct(valores['taxa_abertura'])}; "
              f"baixa {pct(valores['taxa_baixa'])}; saldo {valores['saldo']:+d}")

    print("\nSLIDE 5 — segmentos com alta exposição ao e-commerce")
    for regiao, valores in slide_5(df).items():
        print(f"  {regiao}: estoque 2019–2026 {pct(valores['crescimento_estoque_2019_2026'])}; "
              f"saldo 2025 {valores['saldo_2025']:+d}")

    print("\nSLIDE 6 — participação do Centro no estoque da cidade")
    for segmento, valores in slide_6(df).items():
        print(f"  {segmento}: {pct(valores['2010'])} → {pct(valores['2026'])}")


if __name__ == "__main__":
    main()
