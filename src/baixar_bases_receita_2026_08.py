from pathlib import Path
import zipfile
import pandas as pd


# ============================================================
# CONFIGURAÇÕES
# ============================================================

PASTA = Path(
    r"C:\Users\ielde\OneDrive\Área de Trabalho\GABRIEL\e-commerce\bases_cnpj\bases_cnpj_receita-federal_202608"
)

ARQUIVO_SAIDA = PASTA / "cnpj_piracicaba_202608.csv"

CHUNKSIZE = 300_000


# ============================================================
# COLUNAS DA BASE ESTABELECIMENTOS
# ============================================================

COLUNAS_ESTABELECIMENTOS = [
    "cnpj_basico",
    "cnpj_ordem",
    "cnpj_dv",
    "identificador_matriz_filial",
    "nome_fantasia",
    "situacao_cadastral",
    "data_situacao_cadastral",
    "motivo_situacao_cadastral",
    "nome_cidade_exterior",
    "pais",
    "data_inicio_atividade",
    "cnae_fiscal_principal",
    "cnae_fiscal_secundaria",
    "tipo_logradouro",
    "logradouro",
    "numero",
    "complemento",
    "bairro",
    "cep",
    "uf",
    "codigo_municipio",
    "ddd1",
    "telefone1",
    "ddd2",
    "telefone2",
    "ddd_fax",
    "fax",
    "email",
    "situacao_especial",
    "data_situacao_especial",
]


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def localizar_zip(nome_base: str) -> Path:
    """
    Localiza o ZIP aceitando tanto 'Nome.zip' quanto diferenças
    de maiúsculas/minúsculas no nome do arquivo.
    """
    esperado = PASTA / f"{nome_base}.zip"

    if esperado.exists():
        return esperado

    for arquivo in PASTA.glob("*.zip"):
        if arquivo.stem.lower() == nome_base.lower():
            return arquivo

    raise FileNotFoundError(
        f"Não encontrei o arquivo '{nome_base}.zip' em:\n{PASTA}"
    )


def primeiro_arquivo_do_zip(caminho_zip: Path) -> str:
    """
    Retorna o primeiro arquivo real dentro do ZIP,
    ignorando diretórios internos.
    """
    with zipfile.ZipFile(caminho_zip, "r") as z:
        arquivos = [
            nome for nome in z.namelist()
            if not nome.endswith("/")
        ]

    if not arquivos:
        raise ValueError(f"O ZIP está vazio: {caminho_zip.name}")

    return arquivos[0]


def ler_dimensao(nome_base: str, nomes_colunas: list[str]) -> pd.DataFrame:
    """
    Lê uma dimensão pequena diretamente de dentro do ZIP.
    """
    caminho_zip = localizar_zip(nome_base)
    arquivo_interno = primeiro_arquivo_do_zip(caminho_zip)

    print(f"Lendo dimensão: {caminho_zip.name}")

    with zipfile.ZipFile(caminho_zip, "r") as z:
        with z.open(arquivo_interno) as arquivo:
            df = pd.read_csv(
                arquivo,
                sep=";",
                encoding="latin1",
                header=None,
                names=nomes_colunas,
                dtype=str,
                keep_default_na=False,
            )

    for coluna in df.columns:
        df[coluna] = df[coluna].astype(str).str.strip()

    return df


def descricao_situacao(valor: str) -> str:
    mapa = {
        "01": "NULA",
        "1": "NULA",
        "02": "ATIVA",
        "2": "ATIVA",
        "03": "SUSPENSA",
        "3": "SUSPENSA",
        "04": "INAPTA",
        "4": "INAPTA",
        "08": "BAIXADA",
        "8": "BAIXADA",
    }
    return mapa.get(str(valor).strip(), "")


# ============================================================
# PROGRAMA PRINCIPAL
# ============================================================

def main():

    print("=" * 72)
    print("CONSOLIDAÇÃO CNPJ - PIRACICABA/SP")
    print("=" * 72)

    if not PASTA.exists():
        raise FileNotFoundError(
            f"A pasta configurada não existe:\n{PASTA}"
        )

    # --------------------------------------------------------
    # 1. LER DIMENSÕES
    # --------------------------------------------------------

    municipios = ler_dimensao(
        "Municipios",
        ["codigo_municipio", "municipio"],
    )

    cnaes = ler_dimensao(
        "Cnaes",
        ["cnae_fiscal_principal", "descricao_cnae"],
    )

    motivos = ler_dimensao(
        "Motivos",
        ["motivo_situacao_cadastral", "descricao_motivo"],
    )

    # --------------------------------------------------------
    # 2. IDENTIFICAR O CÓDIGO DE PIRACICABA
    # --------------------------------------------------------

    filtro_piracicaba = (
        municipios["municipio"]
        .str.upper()
        .str.strip()
        .eq("PIRACICABA")
    )

    codigos_piracicaba = (
        municipios.loc[filtro_piracicaba, "codigo_municipio"]
        .drop_duplicates()
        .tolist()
    )

    if not codigos_piracicaba:
        raise ValueError(
            "Não encontrei PIRACICABA na dimensão Municipios."
        )

    print("\nCódigo(s) encontrado(s) para Piracicaba:")
    print(codigos_piracicaba)

    # Mantemos lista para o filtro ficar robusto.
    codigos_piracicaba = set(codigos_piracicaba)

    # --------------------------------------------------------
    # 3. PREPARAR DICIONÁRIOS DAS DIMENSÕES
    # --------------------------------------------------------

    mapa_municipios = dict(
        zip(
            municipios["codigo_municipio"],
            municipios["municipio"],
        )
    )

    mapa_cnaes = dict(
        zip(
            cnaes["cnae_fiscal_principal"],
            cnaes["descricao_cnae"],
        )
    )

    mapa_motivos = dict(
        zip(
            motivos["motivo_situacao_cadastral"],
            motivos["descricao_motivo"],
        )
    )

    # --------------------------------------------------------
    # 4. REMOVER SAÍDA ANTIGA
    # --------------------------------------------------------

    if ARQUIVO_SAIDA.exists():
        print(
            f"\nRemovendo saída anterior: "
            f"{ARQUIVO_SAIDA.name}"
        )
        ARQUIVO_SAIDA.unlink()

    primeiro_bloco_saida = True
    total_piracicaba = 0

    # --------------------------------------------------------
    # 5. PROCESSAR ESTABELECIMENTOS0 ... 9
    # --------------------------------------------------------

    for indice in range(10):

        nome_base = f"Estabelecimentos{indice}"
        caminho_zip = localizar_zip(nome_base)
        arquivo_interno = primeiro_arquivo_do_zip(caminho_zip)

        print("\n" + "=" * 72)
        print(f"Processando {caminho_zip.name}")
        print("=" * 72)

        total_arquivo = 0
        numero_chunk = 0

        with zipfile.ZipFile(caminho_zip, "r") as z:
            with z.open(arquivo_interno) as arquivo:

                leitor = pd.read_csv(
                    arquivo,
                    sep=";",
                    encoding="latin1",
                    header=None,
                    names=COLUNAS_ESTABELECIMENTOS,
                    dtype=str,
                    keep_default_na=False,
                    chunksize=CHUNKSIZE,
                )

                for chunk in leitor:

                    numero_chunk += 1

                    # Padronizar campos usados no filtro/join
                    chunk["codigo_municipio"] = (
                        chunk["codigo_municipio"]
                        .astype(str)
                        .str.strip()
                    )

                    chunk["uf"] = (
                        chunk["uf"]
                        .astype(str)
                        .str.strip()
                        .str.upper()
                    )

                    # Piracicaba + SP
                    filtro = (
                        chunk["codigo_municipio"].isin(
                            codigos_piracicaba
                        )
                        &
                        chunk["uf"].eq("SP")
                    )

                    filtrado = chunk.loc[filtro].copy()

                    if filtrado.empty:
                        print(
                            f"Chunk {numero_chunk}: "
                            f"0 registros"
                        )
                        continue

                    # ----------------------------------------
                    # CNPJ completo
                    # ----------------------------------------

                    filtrado["cnpj"] = (
                        filtrado["cnpj_basico"]
                        .str.zfill(8)
                        +
                        filtrado["cnpj_ordem"]
                        .str.zfill(4)
                        +
                        filtrado["cnpj_dv"]
                        .str.zfill(2)
                    )

                    # ----------------------------------------
                    # Dimensões
                    # ----------------------------------------

                    filtrado["municipio"] = (
                        filtrado["codigo_municipio"]
                        .map(mapa_municipios)
                    )

                    filtrado["descricao_cnae"] = (
                        filtrado["cnae_fiscal_principal"]
                        .map(mapa_cnaes)
                        .fillna("")
                    )

                    filtrado["descricao_motivo"] = (
                        filtrado["motivo_situacao_cadastral"]
                        .map(mapa_motivos)
                        .fillna("")
                    )

                    filtrado[
                        "descricao_situacao_cadastral"
                    ] = (
                        filtrado["situacao_cadastral"]
                        .map(descricao_situacao)
                    )

                    # ----------------------------------------
                    # Datas em formato amigável YYYY-MM-DD
                    # ----------------------------------------

                    for coluna_data in [
                        "data_situacao_cadastral",
                        "data_inicio_atividade",
                        "data_situacao_especial",
                    ]:
                        data_convertida = pd.to_datetime(
                            filtrado[coluna_data],
                            format="%Y%m%d",
                            errors="coerce",
                        )

                        filtrado[coluna_data] = (
                            data_convertida
                            .dt.strftime("%Y-%m-%d")
                            .fillna("")
                        )

                    # ----------------------------------------
                    # Campos úteis para análise histórica
                    # ----------------------------------------

                    data_situacao = pd.to_datetime(
                        filtrado["data_situacao_cadastral"],
                        errors="coerce",
                    )

                    data_inicio = pd.to_datetime(
                        filtrado["data_inicio_atividade"],
                        errors="coerce",
                    )

                    filtrado["ano_situacao_cadastral"] = (
                        data_situacao.dt.year.astype("Int64")
                    )

                    filtrado["mes_situacao_cadastral"] = (
                        data_situacao.dt.month.astype("Int64")
                    )

                    filtrado["ano_inicio_atividade"] = (
                        data_inicio.dt.year.astype("Int64")
                    )

                    # ----------------------------------------
                    # Reordenar principais colunas
                    # ----------------------------------------

                    principais = [
                        "cnpj",
                        "cnpj_basico",
                        "cnpj_ordem",
                        "cnpj_dv",
                        "identificador_matriz_filial",
                        "nome_fantasia",
                        "situacao_cadastral",
                        "descricao_situacao_cadastral",
                        "data_situacao_cadastral",
                        "ano_situacao_cadastral",
                        "mes_situacao_cadastral",
                        "motivo_situacao_cadastral",
                        "descricao_motivo",
                        "data_inicio_atividade",
                        "ano_inicio_atividade",
                        "cnae_fiscal_principal",
                        "descricao_cnae",
                        "cnae_fiscal_secundaria",
                        "municipio",
                        "codigo_municipio",
                        "uf",
                        "bairro",
                        "tipo_logradouro",
                        "logradouro",
                        "numero",
                        "complemento",
                        "cep",
                    ]

                    restantes = [
                        coluna
                        for coluna in filtrado.columns
                        if coluna not in principais
                    ]

                    filtrado = filtrado[
                        principais + restantes
                    ]

                    # ----------------------------------------
                    # ESCREVER DIRETO NO CSV
                    # Evita guardar tudo na memória
                    # ----------------------------------------

                    filtrado.to_csv(
                        ARQUIVO_SAIDA,
                        mode="w" if primeiro_bloco_saida else "a",
                        header=primeiro_bloco_saida,
                        index=False,
                        sep=";",
                        encoding="utf-8-sig",
                    )

                    primeiro_bloco_saida = False

                    encontrados = len(filtrado)
                    total_arquivo += encontrados
                    total_piracicaba += encontrados

                    print(
                        f"Chunk {numero_chunk}: "
                        f"{encontrados:,} registros | "
                        f"arquivo: {total_arquivo:,} | "
                        f"total: {total_piracicaba:,}"
                    )

        print(
            f"\n✓ {caminho_zip.name}: "
            f"{total_arquivo:,} registros de Piracicaba/SP"
        )

    # --------------------------------------------------------
    # 6. RESUMO
    # --------------------------------------------------------

    print("\n" + "=" * 72)
    print("FINALIZADO")
    print("=" * 72)

    print(
        f"Total de registros de Piracicaba/SP: "
        f"{total_piracicaba:,}"
    )

    if ARQUIVO_SAIDA.exists():
        tamanho_mb = (
            ARQUIVO_SAIDA.stat().st_size
            / (1024 ** 2)
        )

        print(f"Arquivo gerado:")
        print(ARQUIVO_SAIDA)

        print(
            f"Tamanho: {tamanho_mb:,.1f} MB"
        )
    else:
        print(
            "Nenhum registro foi encontrado e "
            "nenhum CSV foi criado."
        )


# ============================================================
# EXECUÇÃO
# ============================================================

if __name__ == "__main__":
    main()
