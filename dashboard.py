#pip install pandas dash_bootstrap_components dash plotly

import dash
from dash import dcc, html, Input, Output
from dash_bootstrap_components import themes
import plotly.express as px
import pandas as pd
import os
from datetime import datetime
import re

app = dash.Dash(__name__, external_stylesheets=[themes.BOOTSTRAP])
app.title = "Food Analytics - Infográfico"

# Função para carregar os dados (ajustada para rating)
def load_latest_data():
    data_dir = "psalmazzi.github.io/scraped_data"
    try:
        files = [f for f in os.listdir(data_dir) if f.startswith('ifood_final_') and f.endswith('.csv')]
        if not files:
            return pd.DataFrame()
        
        # Nova versão - para arquivos como ifood_final_20250506_1911.csv
        def extract_datetime(filename):
            # Pega a parte da data (20250506) e hora (1911)
            date_part = filename[12:20]  # 20250506
            time_part = filename[21:25]  # 1911
            return datetime.strptime(f"{date_part}{time_part}", "%Y%m%d%H%M")
        
        latest_file = max(files, key=extract_datetime)
        file_path = os.path.join(data_dir, latest_file)
        
        df = pd.read_csv(file_path, usecols=['search_term', 'rating', 'preco'], encoding='utf-8', on_bad_lines='warn')
        
        df['search_term'] = df['search_term'].replace(['hot dog','cachorro quente'], "Cachorro-Quente")
        df['search_term'] = df['search_term'].replace(['cheese salada','x salada'], "X Salada")
        
        return df
    
    except Exception as e:
        print(f"Erro ao carregar dados: {e}")
        return pd.DataFrame()
    
def converter_moeda(valor):
    if pd.isna(valor):
        return None
    try:
        # Remove R$, espaços não quebráveis e pontos de milhar
        valor_limpo = re.sub(r'[^\d,]', '', str(valor).replace('.', ''))
        # Substitui vírgula decimal por ponto
        return float(valor_limpo.replace(',', '.'))
    except:
        return None

# Layout simplificado

app.layout = html.Div([
    # Cabeçalho
    html.Header([        
        html.H1("🍔 Food Analytics", className="display-4 text-center mt-4"),
        html.P("cidade de Piracicaba-SP", className="text-center mb-4"),
    ], className="py-4"),
    
    html.Main([
        
        html.Div(className='row', children=[
            html.Div(className='col-8', children=[
                dcc.Graph(id='preco-distribution'),
            ]),
            html.Div(className='col-4', children=[
                
                html.Div(id='resumo-precos', style={'marginTop':'70px'}),
                
                html.Div([
                    dcc.Dropdown(
                        id='search-term-dropdown',
                        options=[''],
                        placeholder="Selecione um tipo de lanche...",
                        style={'width': '300px'}
                    )
                ], style={'textAlign': 'left', 'marginBottom': '30px'}),
                    
            ])
        ]),
        
        html.Div(className='row', children=[
            html.Div(className='col-12', children=[
                dcc.Graph(id='rating-distribution'),
            ]),       
        ]),
        
    ],className="container py-4"),

],style={
    'backgroundColor': '#193C40',  # Cor escura para o container
    'color': 'white'
},)

# Atualiza dropdown
@app.callback(
    Output('search-term-dropdown', 'options'),
    Input('search-term-dropdown', 'id')
)
def update_dropdown(_):
    df = load_latest_data()
    if not df.empty and 'search_term' in df.columns:
        return [{'label': term, 'value': term} for term in sorted(df['search_term'].unique())]
    return []

# Callback principal (apenas para rating)
@app.callback(
    [Output('rating-distribution', 'figure'),
    Output('preco-distribution', 'figure'),
    Output('resumo-precos', 'children')],
    [Input('search-term-dropdown', 'value')]
)
def update_rating_chart(selected_term):
    df = load_latest_data()
    
    df['rating'] = df['rating'].replace(['Não avaliado', 'Novidade'], pd.NA)
    df['rating'] = pd.to_numeric(df['rating'], errors='coerce')
    
    df['preco'] = df['preco'].apply(converter_moeda)
    df['preco'] = pd.to_numeric(df['preco'], errors='coerce')
    
    # DEBUG 1: Visualizar estrutura básica
    print("\n=== ESTRUTURA DO DATAFRAME ===")
    print(f"Total de linhas: {len(df)}")
    print("Primeiras 5 linhas:")
    print(df.head())
      
    # DEBUG 3: Verificar valores únicos na coluna rating
    print("\n=== VALORES ÚNICOS EM 'preco' ===")
    print(df['preco'].unique())
    
    # DEBUG 4: Verificar estatísticas descritivas
    print("\n=== ESTATÍSTICAS ===")
    print(df.describe(include='all'))  # Inclui colunas não numéricas
    
    # DEBUG 5: Verificar valores faltantes
    print("\n=== VALORES FALTANTES ===")
    print(df.isnull().sum())
    
    
    if df.empty:
        return (
            px.scatter(title="Dados não encontrados", 
                      labels={'x': 'Nenhum dado disponível'}),
            "Importe dados primeiro usando o script de scraping"
        )
    
    # Cria cópia e converte ratings
    filtered_df = df.copy()
    filtered_df = filtered_df.dropna(subset=['search_term','preco','rating'])
    filtered_df = filtered_df[filtered_df['rating'] > 4]
    filtered_df = filtered_df[filtered_df['preco'] <= 80]
    filtered_df = filtered_df[filtered_df['preco'] > 5]
    
    # Filtra por termo se selecionado
    if selected_term:
        filtered_df = filtered_df.loc[filtered_df['search_term'] == selected_term]
    
    # Criação segura do box    
    cores_personalizadas = ['#6bd300','#ff5f26']    
    
    fig1 = px.box(
        filtered_df,
        x='rating',
        y='preco',
        points="all",
        color="search_term",
        color_discrete_sequence=cores_personalizadas
    )
    
    fig1.update_layout(
        title={
            'text': "Amostragem do preço x nota no aplicativo",
            'font': {
                'color': 'white',  # Cor do título
                'size': 20
            }
        },
        
        legend=dict(
            x=0.98,
            y=0.95,
            xanchor='right',
            yanchor='top',
            title_text='termo de pesquisa:',
            font={'color': 'white'}
        ),
        
        plot_bgcolor='rgba(0,0,0,0)',  # Fundo do gráfico transparente
        paper_bgcolor='rgba(0,0,0,0)',  # Fundo externo transparente
               
        # Configurações dos eixos
        xaxis={
            'title': 'Nota',
            'color': 'white',  # Cor do texto do eixo X
            'gridcolor': 'rgba(255,255,255,0)',  # Cor da grade
            'linecolor': 'rgba(255,255,255,0.2)'  # Cor da linha do eixo
        },
        
        yaxis={
            'title': 'Preço',
            'color': 'white',  # Cor do texto do eixo Y
            'gridcolor': 'rgba(255,255,255,0)',  # Cor da grade
            'linecolor': 'rgba(255,255,255,0.2)'  # Cor da linha do eixo
        },
        
        font={
            'color': 'white'
        }
    )
    
    # Criação segura do histograma
    fig2 = px.box(
        filtered_df,
        y='preco',
        points="all",
        color="search_term",
        color_discrete_sequence=cores_personalizadas
    )
    
    fig2.update_layout(
        title={
            'text': "Amostragem do preço",
            'font': {
                'color': 'white',  # Cor do título
                'size': 20
            }
        },
        
        legend=dict(
            x=0.98,
            y=0.95,
            xanchor='right',
            yanchor='top',
            title_text='termo de pesquisa:',
            font={'color': 'white'}
        ),
        
        plot_bgcolor='rgba(0,0,0,0)',  # Fundo do gráfico transparente
        paper_bgcolor='rgba(0,0,0,0)',  # Fundo externo transparente
               
        # Configurações dos eixos
        xaxis={
            'color': 'white',  # Cor do texto do eixo X
            'gridcolor': 'rgba(255,255,255,0)',  # Cor da grade
            'linecolor': 'rgba(255,255,255,0.2)'  # Cor da linha do eixo
        },
        
        yaxis={
            'title': 'Preço',
            'color': 'white',  # Cor do texto do eixo Y
            'gridcolor': 'rgba(255,255,255,0)',  # Cor da grade
            'linecolor': 'rgba(255,255,255,0.2)'  # Cor da linha do eixo
        },
        
        font={
            'color': 'white'
        }
    )
    
    # Calcula estatísticas
    preco_medio = filtered_df['preco'].mean()
    preco_min = filtered_df['preco'].min()
    preco_max = filtered_df['preco'].max()
    qtd_itens = len(filtered_df)
    
    # Cria o texto resumo
    resumo = html.Div([
        html.H3("Resumo da amostragem"),
        html.P(f"Relacionados {qtd_itens} itens no cardápio."),
        html.P(f"Preço médio: R$ {preco_medio:.2f}"),
        html.P(f"Item mais barato: R$ {preco_min:.2f}"),
        html.P(f"Item mais caro: R$ {preco_max:.2f}"),
        html.P(f"Amostragem considerada primeiro resultado por loja"),
    ])
    
    return fig1, fig2, resumo

if __name__ == '__main__':
    app.run(debug=True, port=8050)