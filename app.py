# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
# import numpy as np # Não utilizado?
# import seaborn as sns # Não utilizado?
import plotly.express as px
import plotly.graph_objects as go
import os  # Para verificar caminho

# -----------------------------
# Funções auxiliares
# -----------------------------


@st.cache_data  # Cache para performance
def carregar_dados(caminho_csv):
    """Carrega e pré-processa os dados do CSV de medicamentos."""
    try:
        if not os.path.exists(caminho_csv):
            st.error(f"Erro Crítico: Arquivo '{caminho_csv}' não encontrado!")
            st.error(
                "Por favor, coloque o arquivo CSV na mesma pasta que o script Python.")
            return None  # Retorna None se o arquivo não existe

        df = pd.read_csv(caminho_csv)

        # Tratamento da coluna 'quantidade' - verificar se existe primeiro
        if 'quantidade' in df.columns:
            # Tentar converter, tratando possíveis erros
            try:
                # Remover espaços extras antes de substituir vírgula
                df['quantidade'] = df['quantidade'].astype(
                    str).str.strip().str.replace(',', '.', regex=False)
                # Tentar converter para float, forçando erros para NaN
                df['quantidade'] = pd.to_numeric(
                    df['quantidade'], errors='coerce')
                # Remover linhas onde a conversão falhou (NaN)
                df.dropna(subset=['quantidade'], inplace=True)
            except Exception as e:
                st.warning(
                    f"Não foi possível converter a coluna 'quantidade' completamente. Erro: {e}")
                # Opcional: retornar None ou o df sem a coluna convertida
                # return None
        else:
            st.warning("Coluna 'quantidade' não encontrada no arquivo CSV.")
            # Opcional: retornar None ou o df como está
            # return None

        # Remover duplicatas e linhas completamente vazias
        df = df.dropna(how='all').drop_duplicates()
        return df

    except pd.errors.EmptyDataError:
        st.error(f"Erro: O arquivo '{caminho_csv}' está vazio.")
        return None
    except Exception as e:
        st.error(f"Ocorreu um erro inesperado ao carregar os dados: {e}")
        return None


def filtrar_dados(df, distrito_selecionado):
    """Filtra o DataFrame pelo distrito selecionado."""
    if df is not None and 'distrito' in df.columns and distrito_selecionado:
        return df[df['distrito'] == distrito_selecionado]
    return pd.DataFrame()  # Retorna DataFrame vazio se a filtragem não for possível


def top_n_medicamentos_geral(df, n=10):
    """Calcula o top N medicamentos geral por quantidade."""
    if df is not None and 'produto' in df.columns and 'quantidade' in df.columns:
        return df.groupby('produto')['quantidade'].sum().nlargest(n).reset_index()
    # Retorna DataFrame vazio
    return pd.DataFrame({'produto': [], 'quantidade': []})

# Função top3 por distrito não usada diretamente nos gráficos, mas definida


def top3_medicamentos_por_distrito(df):
    """Calcula o top 3 medicamentos por distrito."""
    if df is not None and 'distrito' in df.columns and 'produto' in df.columns and 'quantidade' in df.columns:
        top3 = (
            df.groupby(['distrito', 'produto'])['quantidade']
            .sum()
            .reset_index()
            .sort_values(['distrito', 'quantidade'], ascending=[True, False])
        )
        return top3.groupby('distrito').head(3)
    return pd.DataFrame()


def categorizar(qtd):
    """Categoriza a quantidade em níveis de criticidade."""
    if pd.isna(qtd):  # Tratar NaNs que podem ter surgido
        return "Indefinido"
    if qtd == 0:
        return "Crítico"
    elif qtd <= 150:
        return "Alerta"
    else:
        return "Abastecido"


# -----------------------------
# Layout - Título e Carregamento
# -----------------------------
st.set_page_config(page_title="Medicamentos por Distrito",
                   layout="wide", page_icon="💊")
st.title("💊 Distribuição de Medicamentos por Unidade de Saúde")

# Carregar dados
df_principal = carregar_dados("medicamentos_por_unidade_de_saude.csv")

# Só continua se os dados foram carregados
if df_principal is not None:

    # --- Sidebar ---
    st.sidebar.header("Filtros de Análise")
    if 'distrito' in df_principal.columns:
        distritos = sorted(df_principal['distrito'].dropna().unique())
        distrito_selecionado = st.sidebar.selectbox(
            "Selecione um Distrito", distritos)
        # Filtrar dados por distrito para gráficos específicos
        df_distrito = filtrar_dados(df_principal, distrito_selecionado)
    else:
        st.sidebar.warning("Coluna 'distrito' não encontrada.")
        distrito_selecionado = None
        df_distrito = pd.DataFrame()

    # Texto introdutório
    st.markdown("""
    Esta visualização permite identificar, de forma clara, **quais distritos e unidades têm maior número
    de medicamentos com estoque crítico (zerado) ou em alerta (baixo)**, apoiando ações de
    redistribuição e planejamento mais eficiente da política de abastecimento.
    """)
    st.markdown("---")

    # --- Gráfico: Top 10 Medicamentos (Geral) ---
    st.header("Visão Geral da Rede")
    st.subheader("Top 10 Medicamentos Mais Disponíveis (Geral)")
    st.markdown("""
    Na rede de saúde analisada, os dados podem mostrar um foco em doenças crônicas. Medicamentos
    como Losartana, Enalapril e Metformina frequentemente lideram em quantidade.
    *(A análise abaixo é baseada na soma total no dataset)*.
    """)

    top10_df = top_n_medicamentos_geral(df_principal, n=10)

    if not top10_df.empty:
        fig_top10 = px.bar(
            top10_df,
            x='quantidade',
            y='produto',
            orientation='h',
            text='quantidade',
            color='produto',  # Pode gerar muitas cores, talvez remover ou usar valor
            # color='quantidade', # Alternativa: colorir pela quantidade
            # color_continuous_scale=px.colors.sequential.Viridis,
            title='Top 10 Medicamentos Mais Distribuídos (Quantidade Total na Rede)',
        )
        fig_top10.update_layout(
            xaxis_title='Quantidade Total',
            yaxis_title='Medicamento',
            yaxis={'categoryorder': 'total ascending'},  # Melhor ordenação
            template='plotly_white',  # Usar template claro
            height=500,
            showlegend=False  # Legenda desnecessária aqui
        )
        # Formatar texto para mostrar K (mil), M (milhão) etc.
        fig_top10.update_traces(
            texttemplate='%{text:.2s}', textposition='outside')
        st.plotly_chart(fig_top10, use_container_width=True)
    else:
        st.warning("Não foi possível gerar o gráfico Top 10 Geral.")

    st.markdown("---")

    # --- Gráfico: Top 10 por Distrito Selecionado ---
    st.header(f"Análise do Distrito: {distrito_selecionado or 'N/A'}")
    st.subheader("Top 10 Medicamentos Disponíveis no Distrito Selecionado")
    st.markdown("Use o filtro na barra lateral para explorar outros distritos.")

    if not df_distrito.empty and 'produto' in df_distrito.columns and 'quantidade' in df_distrito.columns:
        top10_distrito_df = (
            df_distrito.groupby('produto')['quantidade']
            .sum()
            .nlargest(10)  # Usar nlargest é mais direto
            .reset_index()
        )

        if not top10_distrito_df.empty:
            fig_top10_distrito = px.bar(
                top10_distrito_df,
                x='produto',
                y='quantidade',
                # color='produto', # Muitas cores podem poluir
                color_discrete_sequence=px.colors.qualitative.Pastel,  # Usar paleta
                text='quantidade',
                title=f"Top 10 Medicamentos no Distrito: {distrito_selecionado}"
            )
            fig_top10_distrito.update_layout(
                xaxis_title='Medicamento',
                yaxis_title='Quantidade Disponível',
                template='plotly_white',
                showlegend=False,
                xaxis={'categoryorder': 'total descending'}  # Ordenar barras
            )
            fig_top10_distrito.update_traces(
                texttemplate='%{text:.2s}', textposition='outside')
            st.plotly_chart(fig_top10_distrito, use_container_width=True)
        else:
            st.warning(
                f"Não há dados de medicamentos para o distrito '{distrito_selecionado}'.")
    elif not distrito_selecionado:
        st.warning("Selecione um distrito na barra lateral.")
    else:
        st.warning(
            f"Não foi possível gerar o gráfico Top 10 para o distrito '{distrito_selecionado}'. Verifique os dados.")

    st.markdown("---")

    # --- Análise de Criticidade ---
    st.header("Análise de Criticidade do Estoque")

    # Calcular estoque e criticidade por unidade/produto
    if 'unidade' in df_principal.columns and 'produto' in df_principal.columns and 'quantidade' in df_principal.columns:
        estoque_total_unid = df_principal.groupby(["unidade", "produto"])[
            "quantidade"].sum().reset_index()
        estoque_total_unid["criticidade"] = estoque_total_unid["quantidade"].apply(
            categorizar)

        # Merge para obter o distrito de cada unidade
        if 'distrito' in df_principal.columns:
            mapa_unidade_distrito = df_principal[[
                'unidade', 'distrito']].drop_duplicates()
            estoque_total_unid = estoque_total_unid.merge(
                mapa_unidade_distrito, on='unidade', how='left')
        else:
            # Placeholder
            estoque_total_unid['distrito'] = 'Distrito Desconhecido'

        # --- Gráficos de Unidades Críticas e em Alerta ---
        col_crit, col_alert = st.columns(2)

        with col_crit:
            st.subheader("Unidades com Mais Produtos Críticos")
            produtos_criticos = estoque_total_unid[estoque_total_unid["criticidade"] == "Crítico"]
            unidades_mais_criticas = (
                produtos_criticos.groupby("unidade")["produto"]
                .count()  # Contar produtos críticos por unidade
                .nlargest(10)
                .reset_index()
                .rename(columns={"produto": "qtd_produtos_criticos"})
                # Para barra horizontal
                .sort_values("qtd_produtos_criticos", ascending=True)
            )

            if not unidades_mais_criticas.empty:
                fig_unidades_criticas = px.bar(
                    unidades_mais_criticas,
                    x="qtd_produtos_criticos",
                    y="unidade",
                    orientation="h",
                    text="qtd_produtos_criticos",
                    color_discrete_sequence=["#FF4C4C"],  # vermelho
                    title="Top 10 Unidades (Mais Produtos Críticos)"
                )
                fig_unidades_criticas.update_layout(
                    template="plotly_white", height=400)
                fig_unidades_criticas.update_traces(textposition="outside")
                st.plotly_chart(fig_unidades_criticas,
                                use_container_width=True)
            else:
                st.info("Nenhuma unidade encontrada com produtos em estado crítico.")

        with col_alert:
            st.subheader("Unidades com Mais Produtos em Alerta")
            produtos_alerta = estoque_total_unid[estoque_total_unid["criticidade"] == "Alerta"]
            unidades_mais_alerta = (
                produtos_alerta.groupby("unidade")["produto"]
                .count()  # Contar produtos em alerta por unidade
                .nlargest(10)
                .reset_index()
                .rename(columns={"produto": "qtd_produtos_alerta"})
                # Para barra horizontal
                .sort_values("qtd_produtos_alerta", ascending=True)
            )

            if not unidades_mais_alerta.empty:
                fig_unidades_alerta = px.bar(
                    unidades_mais_alerta,
                    x="qtd_produtos_alerta",
                    y="unidade",
                    orientation="h",
                    text="qtd_produtos_alerta",
                    color_discrete_sequence=["#FFA500"],  # laranja
                    title="Top 10 Unidades (Mais Produtos em Alerta)"
                )
                fig_unidades_alerta.update_layout(
                    template="plotly_white", height=400)
                fig_unidades_alerta.update_traces(textposition="outside")
                st.plotly_chart(fig_unidades_alerta, use_container_width=True)
            else:
                st.info(
                    "Nenhuma unidade encontrada com produtos em estado de alerta.")

        st.markdown("---")
        # --- Tabela Interativa ---
        st.subheader("Detalhes do Estoque por Unidade e Criticidade")
        st.markdown(
            "Use os filtros na barra lateral para refinar a tabela abaixo.")

        # Filtros da Tabela na Sidebar
        st.sidebar.divider()
        st.sidebar.subheader("Filtros da Tabela Detalhada")

        unidades = sorted(estoque_total_unid['unidade'].dropna().unique())
        unidade_selecionada_tab = st.sidebar.selectbox(
            "Filtrar Tabela por Unidade", options=["Todas"] + unidades)

        criticidades = sorted(
            estoque_total_unid['criticidade'].dropna().unique())
        criticidade_selecionada_tab = st.sidebar.selectbox(
            "Filtrar Tabela por Criticidade", options=["Todas"] + criticidades)

        # Aplicar filtros na cópia do DataFrame
        df_filtrado_tabela = estoque_total_unid.copy()
        if unidade_selecionada_tab != "Todas":
            df_filtrado_tabela = df_filtrado_tabela[df_filtrado_tabela['unidade']
                                                    == unidade_selecionada_tab]
        if criticidade_selecionada_tab != "Todas":
            df_filtrado_tabela = df_filtrado_tabela[df_filtrado_tabela['criticidade']
                                                    == criticidade_selecionada_tab]

        # Mostrar DataFrame filtrado
        st.dataframe(df_filtrado_tabela[[
                     'distrito', 'unidade', 'produto', 'quantidade', 'criticidade']])  # Reordenar colunas

        st.markdown("---")
        # --- Criticidade por Distrito ---
        st.subheader("Distribuição de Criticidade por Distrito")
        criticidade_por_distrito = (
            estoque_total_unid.groupby(['distrito', 'criticidade'])['produto']
            .count()
            .reset_index()
            # Renomear para clareza
            .rename(columns={'produto': 'quantidade_produtos'})
        )

        if not criticidade_por_distrito.empty:
            fig_criticidade_dist = px.bar(
                criticidade_por_distrito,
                x='distrito',
                y='quantidade_produtos',
                color='criticidade',
                title='Número de Produtos por Nível de Criticidade em Cada Distrito',
                barmode='group',  # Barras agrupadas
                text='quantidade_produtos',
                color_discrete_map={  # Cores consistentes
                    "Crítico": "#FF4C4C",    # vermelho
                    "Alerta": "#FFA500",     # laranja
                    "Abastecido": "#2ECC71",  # verde
                    "Indefinido": "#808080"  # cinza para indefinido
                },
                category_orders={"criticidade": [
                    "Crítico", "Alerta", "Abastecido", "Indefinido"]}  # Ordem desejada
            )
            fig_criticidade_dist.update_layout(
                template='plotly_white',
                xaxis_title='Distrito Sanitário',
                yaxis_title='Número de Tipos de Medicamentos'
            )
            fig_criticidade_dist.update_traces(textposition='outside')
            st.plotly_chart(fig_criticidade_dist, use_container_width=True)
        else:
            st.warning("Não foi possível calcular a criticidade por distrito.")

    else:
        st.warning(
            "Não foi possível calcular a criticidade. Verifique se as colunas 'unidade', 'produto' e 'quantidade' existem.")

    st.markdown("---")
    # --- Conclusões ---
    st.header("💡 Conclusões e Recomendações")
    st.markdown("""
    A análise da distribuição de medicamentos nas unidades de saúde revela um cenário com importantes desafios e oportunidades para aprimorar a gestão do estoque.

    #### Principais Pontos:
    * **Foco em Crônicos:** Os medicamentos mais distribuídos confirmam a prioridade no tratamento de condições como hipertensão e diabetes.
    * **Desigualdade Distrital:** A concentração de produtos em estado "Crítico" ou "Alerta" em certos distritos e unidades específicas (visível nos gráficos de Top 10 e na distribuição por distrito) indica a necessidade de reavaliação da logística ou dos níveis de estoque mínimo definidos.
    * **Atenção Urgente:** As unidades listadas no "Top 10 Crítico" requerem atenção imediata para evitar a interrupção no fornecimento de medicamentos essenciais à população atendida.

    #### Recomendações / Próximas Ações:
    1.  **Remanejamento Inteligente:** Implementar um sistema (ou processo) ágil para redistribuir estoques entre unidades/distritos, usando os níveis de criticidade como guia (transferir de "Abastecido" para "Crítico"/"Alerta").
    2.  **Monitoramento Contínuo:** Utilizar dashboards como este para acompanhar a situação do estoque em tempo real ou frequente, permitindo ações proativas.
    3.  **Revisão de Níveis Mínimos:** Analisar o consumo histórico e perfil epidemiológico de cada distrito/unidade para ajustar as metas de estoque mínimo e máximo de forma mais precisa (Próximo passo).
    4.  **Priorização Logística:** Garantir que as unidades mais críticas recebam prioridade nos ciclos de reposição de estoque.

    Estas ações podem otimizar o uso de recursos e fortalecer a equidade no acesso a medicamentos na rede.
    """)
    st.markdown("---")

    # --- Equipe ---
    st.sidebar.divider()
    st.sidebar.subheader("Equipe:")
    st.sidebar.write("Alberto")
    st.sidebar.write("Ayanne")
    st.sidebar.write("Ayrton")
    st.sidebar.write("Carlos")
    st.sidebar.write("Petronio")


# Mensagem final se os dados não puderem ser carregados
elif df_principal is None:
    st.error("Execução interrompida pois os dados não puderam ser carregados. Verifique as mensagens de erro acima.")
