# Metodologia

## 1. Fonte e recorte

A fonte é a base pública do **Cadastro Nacional da Pessoa Jurídica (CNPJ), Receita Federal**, competência **2026-08**.

O pipeline lê os arquivos `Estabelecimentos0.zip` a `Estabelecimentos9.zip`, filtra os registros de **Piracicaba/SP**, associa descrições das dimensões de municípios, CNAEs e motivos de situação cadastral e grava uma base municipal intermediária.

O recorte de varejo é feito pela divisão **CNAE 47 — Comércio varejista**.

## 2. Datas

- **Abertura:** `data_inicio_atividade`.
- **Baixa:** apenas registros com `situacao_cadastral = 08`; nesses casos `data_situacao_cadastral` é tratada como `data_fechamento`.
- **Data de referência do carrossel:** 08/08/2026.

Para calcular o estoque em uma data `t`, um estabelecimento é contado quando:

```text
data_inicio_atividade <= t
AND
(data_fechamento é nula OR data_fechamento > t)
```

Essa regra permite reconstruir estoques históricos usando abertura e baixa, em vez de usar apenas a situação cadastral observada em 2026.

## 3. Centro e Bairro Alto

O script original de preparação (`src/base_analitica_original.py`) cria `eh_centro` quando `bairro_normalizado` contém a palavra `CENTRO`.

Os números publicados no carrossel também incorporam registros de **Bairro Alto**, nas variantes encontradas na base:

- `BAIRRO ALTO`
- `B ALTO`
- `B.ALTO`
- `B. ALTO`
- `ALTO`

Por transparência, o script original é mantido sem alteração. A regra final utilizada nos indicadores está implementada em `src/reproduzir_carrossel.py` como `eh_centro_carrossel`.

## 4. Indicadores

### Slide 2 — participação do Centro nas novas lojas

Para cada período, calcula-se:

```text
novas lojas classificadas como Centro
-------------------------------------- × 100
novas lojas em Piracicaba
```

Períodos: 2000–2009, 2010–2019, 2020–2026 e o ano de 2025.

### Slide 3 — idade das lojas

A população é formada pelos estabelecimentos **não baixados** na base de referência.

A idade é calculada entre `data_inicio_atividade` e 08/08/2026. São apresentados:

- idade mediana;
- percentual com 15 anos ou mais;
- percentual aberto nos cinco anos anteriores à data de referência.

### Slide 4 — aberturas, baixas e saldo em 2025

As taxas usam como denominador o **estoque em 31/12/2024**:

```text
taxa de abertura = aberturas em 2025 / estoque em 31/12/2024
taxa de baixa    = baixas em 2025    / estoque em 31/12/2024
saldo            = aberturas - baixas
```

### Slide 5 — segmentos expostos ao e-commerce

O slide utiliza estabelecimentos classificados como **`Alta` exposição ao e-commerce**.

O crescimento do estoque compara 31/12/2019 com 08/08/2026. O saldo de 2025 é a diferença entre aberturas e baixas no ano.

### Slide 6 — participação territorial por segmento

Para cada segmento selecionado, calcula-se a participação do Centro no estoque total de Piracicaba em:

- 31/12/2010;
- 08/08/2026.

Segmentos exibidos: joalheria e relojoaria, eletroeletrônicos, moda e casa e decoração.

## 5. Validação dos números publicados

A execução de `src/reproduzir_carrossel.py` sobre a base analítica final reproduz, antes do arredondamento, os valores apresentados nos slides:

| Indicador | Centro | Outros bairros |
|---|---:|---:|
| Novas lojas, 2000–2009 | 26,6478% | — |
| Novas lojas, 2010–2019 | 16,1387% | — |
| Novas lojas, 2020–2026 | 9,0666% | — |
| Novas lojas, 2025 | 7,7576% | — |
| Idade mediana | 15,1735 anos | 7,4471 anos |
| 15 anos ou mais | 50,6413% | 27,1776% |
| Nascidas nos últimos 5 anos | 20,1173% | 36,1888% |
| Taxa de abertura em 2025 | 4,7076% | 11,0059% |
| Taxa de baixa em 2025 | 5,3328% | 8,3303% |
| Saldo em 2025 | -17 | +370 |
| Alta exposição: estoque 2019–2026 | +4,3121% | +46,2741% |
| Alta exposição: saldo 2025 | -21 | +172 |

Participação do Centro por segmento:

| Segmento | 2010 | 2026 |
|---|---:|---:|
| Joalheria e relojoaria | 62,2951% | 25,7028% |
| Eletroeletrônicos | 42,7861% | 22,0297% |
| Moda | 35,6539% | 18,8711% |
| Casa e decoração | 35,1885% | 16,6528% |

## 6. Limitações

Os dados representam **cadastros de estabelecimentos**, não volume de vendas, faturamento, empregos, fluxo de consumidores ou participação efetiva das vendas online.

A exposição ao e-commerce é uma classificação analítica dos CNAEs e não uma variável fornecida diretamente pela Receita Federal.

A base também depende da qualidade dos campos cadastrais, especialmente `bairro`, que possui variações de grafia. Por isso a definição territorial deve ser considerada operacional e reproduzível, e não uma delimitação cartográfica oficial.
