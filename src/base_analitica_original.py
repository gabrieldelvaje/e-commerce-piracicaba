from pathlib import Path
import pandas as pd
import re
import unicodedata


# ============================================================
# CAMINHOS
# ============================================================

PASTA = Path(
    r"C:\Users\ielde\OneDrive\Área de Trabalho\GABRIEL\e-commerce\bases_cnpj\bases_cnpj_receita-federal_202608"
)

ARQUIVO_CNPJ = PASTA / "cnpj_piracicaba_202608.csv"

ARQUIVO_CLASSIFICACAO = (
    PASTA / "classificacao_cnae_segmento_ecommerce.csv"
)

ARQUIVO_SAIDA = (
    PASTA / "varejo_piracicaba_analise_ecommerce.csv"
)


# ============================================================
# FUNÇÕES
# ============================================================

def somente_numeros(valor):

    if pd.isna(valor):
        return ""

    return re.sub(
        r"\D",
        "",
        str(valor)
    )


def normalizar_texto(valor):

    if pd.isna(valor):
        return ""

    texto = str(valor).upper().strip()

    texto = "".join(
        c
        for c in unicodedata.normalize("NFKD", texto)
        if not unicodedata.combining(c)
    )

    return texto


# ============================================================
# CARREGAR CNPJ
# ============================================================

print("Carregando CNPJs...")

df = pd.read_csv(
    ARQUIVO_CNPJ,
    sep=";",
    encoding="utf-8-sig",
    dtype=str,
    low_memory=False
)


# ============================================================
# CNAE
# ============================================================

df["cnae_normalizado"] = (
    df["cnae_fiscal_principal"]
    .apply(somente_numeros)
)

df["cnae_divisao"] = (
    df["cnae_normalizado"]
    .str[:2]
)

df["cnae_classe"] = (
    df["cnae_normalizado"]
    .str[:4]
)


# ============================================================
# MANTER SOMENTE VAREJO
# CNAE 47
# ============================================================

df = df[
    df["cnae_divisao"] == "47"
].copy()

print(
    f"Estabelecimentos varejistas: {len(df):,}"
)


# ============================================================
# CLASSIFICAÇÃO CNAE
# ============================================================

classificacao = pd.read_csv(
    ARQUIVO_CLASSIFICACAO,
    sep=";",
    encoding="utf-8-sig",
    dtype=str
)


# Queremos somente as regras específicas do varejo
dim_varejo = classificacao[
    classificacao["nivel_classificacao"]
    == "CLASSE_VAREJO"
].copy()


dim_varejo = dim_varejo[
    [
        "prefixo_cnae",
        "segmento_detalhado",
        "exposicao_ecommerce"
    ]
].rename(
    columns={
        "prefixo_cnae": "cnae_classe",
        "segmento_detalhado": "segmento_varejo"
    }
)


# ============================================================
# MERGE
# ============================================================

df = df.merge(
    dim_varejo,
    how="left",
    on="cnae_classe"
)


df["exposicao_ecommerce"] = (
    df["exposicao_ecommerce"]
    .fillna("Não classificado")
)


# ============================================================
# CENTRO
# ============================================================

df["bairro_normalizado"] = (
    df["bairro"]
    .apply(normalizar_texto)
)


# Qualquer bairro que contenha CENTRO
df["eh_centro"] = (
    df["bairro_normalizado"]
    .str.contains(
        "CENTRO",
        na=False
    )
)


# ============================================================
# DATAS
# ============================================================

df["data_inicio_atividade"] = pd.to_datetime(
    df["data_inicio_atividade"],
    errors="coerce"
)

df["data_situacao_cadastral"] = pd.to_datetime(
    df["data_situacao_cadastral"],
    errors="coerce"
)


# ============================================================
# SITUAÇÃO CADASTRAL
# ============================================================

df["situacao_cadastral"] = (
    df["situacao_cadastral"]
    .astype(str)
    .str.strip()
    .str.zfill(2)
)


# Receita Federal:
# 08 = BAIXADA
df["baixada"] = (
    df["situacao_cadastral"] == "08"
)


# ============================================================
# DATA DE FECHAMENTO
# ============================================================

df["data_fechamento"] = pd.NaT

df.loc[
    df["baixada"],
    "data_fechamento"
] = df.loc[
    df["baixada"],
    "data_situacao_cadastral"
]


# ============================================================
# ANO E MÊS
# ============================================================

df["ano_fechamento"] = (
    df["data_fechamento"]
    .dt.year
    .astype("Int64")
)

df["mes_fechamento"] = (
    df["data_fechamento"]
    .dt.month
    .astype("Int64")
)


# ============================================================
# FECHAMENTO A PARTIR DE 2000
# ============================================================

df["fechou_desde_2000"] = (
    df["baixada"]
    &
    df["ano_fechamento"].ge(2000)
)


# ============================================================
# PERÍODO PARA ANÁLISE
# ============================================================

def classificar_periodo(ano):

    if pd.isna(ano):
        return ""

    ano = int(ano)

    if 2000 <= ano <= 2009:
        return "2000-2009"

    elif 2010 <= ano <= 2015:
        return "2010-2015"

    elif 2016 <= ano <= 2019:
        return "2016-2019"

    elif 2020 <= ano <= 2021:
        return "2020-2021"

    elif ano >= 2022:
        return "2022-2026"

    return "Antes de 2000"


df["periodo_fechamento"] = (
    df["ano_fechamento"]
    .apply(classificar_periodo)
)


# ============================================================
# SOMENTE COLUNAS NECESSÁRIAS
# ============================================================

colunas = [

    "cnpj",

    "nome_fantasia",

    "cnae_fiscal_principal",
    "descricao_cnae",

    "segmento_varejo",
    "exposicao_ecommerce",

    "bairro",
    "bairro_normalizado",
    "eh_centro",

    "data_inicio_atividade",

    "situacao_cadastral",
    "descricao_situacao_cadastral",

    "baixada",

    "data_fechamento",
    "ano_fechamento",
    "mes_fechamento",

    "periodo_fechamento",

    "fechou_desde_2000"
]


df_final = df[
    colunas
].copy()


# ============================================================
# EXPORTAR
# ============================================================

df_final.to_csv(
    ARQUIVO_SAIDA,
    sep=";",
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# RESUMO
# ============================================================

print("\nArquivo criado:")
print(ARQUIVO_SAIDA)

print(
    f"\nTotal varejistas: "
    f"{len(df_final):,}"
)

print(
    f"Baixados desde 2000: "
    f"{df_final['fechou_desde_2000'].sum():,}"
)

print(
    f"No Centro: "
    f"{df_final['eh_centro'].sum():,}"
)

print("\nExposição:")

print(
    df_final[
        "exposicao_ecommerce"
    ]
    .value_counts(
        dropna=False
    )
)
