import pandas as pd
from .auxiliary_functions import *
import editdistance
import numpy as np
from .extract import *
from datetime import datetime
from tqdm import tqdm
# Suprimir o aviso SettingWithCopyWarning
pd.set_option('mode.chained_assignment', None)

##############################FUNÇÕES AUXILIARES GERAIS ###############################################################################################
def selecionar_csv_por_produto_local(produto, local):
    """
    Seleciona o arquivo CSV correspondente ao produto e local especificados.

    Args:
        produto (str): O produto desejado.
        local (str): O local desejado.

    Returns:
        str: O nome do arquivo CSV correspondente ao produto e local. Retorna None se nenhum arquivo for encontrado.
    """
    dic = [
        ["asfalto", "município", "vendas-anuais-de-asfalto-por-municipio.csv"], #kg
        ["biodiesel b100 m3", "n/a", "vendas-biodiesel-b100-m3.csv"],
        ["combustíveis m3", "n/a", "vendas-combustiveis-m3-1990-2024.csv"],
        ["combustíveis segmento m3", "n/a", "vendas-combustiveis-segmento-m3-2012-2024.csv"],
        ["etanolhidratado", "estado", "vendas_etanol_hidratado_por_estado_1980-1989.csv"], #m3
        ["etanolhidratado", "município", "vendas-anuais-de-etanol-hidratado-por-municipio.csv"], #litro
        ["gasolinac", "estado", "vendas_gasolina_c_por_estado_1947-1989.csv"], #m3
        ["gasolinac", "município", "vendas-anuais-de-gasolina-c-por-municipio.csv"], #litro
        ["gasolinadeaviacao", "estado", "vendas_gasolina_aviacao_por_estado_1947-1989.csv"], #m3
        ["gasolinadeaviacao", "município", "vendas-anuais-de-gasolina-de-aviacao-por-municipio.csv"], #litro
        ["glp", "estado", "vendas_glp_por_estado_1953-1989.csv"], #tonelada
        ["glp", "município", "vendas-anuais-de-glp-por-municipio.csv"], #kg
        ["glp tipo vasilhame m3", "n/a", "vendas-glp-tipo-vasilhame-m3-2010-2024.csv"], #
        ["querosenedeaviacao", "estado", "vendas_querosene_aviacao_por_estado_1959-1989.csv"], #m3
        ["querosenedeaviacao", "município", "vendas-anuais-de-querosene-de-aviacao-por-municipio.csv"], #litro
        ["queroseneiluminante", "estado", "vendas_querosene_iluminante_por_estado_1947-1989.csv"], #m3
        ["queroseneiluminante", "município", "vendas-anuais-de-querosene-iluminante-por-municipio.csv"], #litro
        ["oleocombustivel", "estado", "vendas_oleo_combustivel_por_estado_1947-1989.csv"], #tonelada
        ["oleocombustivel", "município", "vendas-anuais-de-oleo-combustivel-por-municipio.csv"], #kg
        ["oleodiesel", "estado", "vendas_oleo_diesel_por_estado_1947-1989.csv"],  #m3
        ["oleodiesel", "município", "vendas-anuais-de-oleo-diesel-por-municipio.csv"], #litro
        ["oleodiesel tipo m3", "estado", "vendas_oleo_diesel_tipo_m3_2013-2024.csv"]  #m3
    ]

    for elemento in dic:
        if elemento[0] == produto and elemento[1] == local:
            return elemento[2]
    
    # Se nenhum arquivo for encontrado, retorna None
    return None

def agregar_datas_duplicadas(grupo):
    """
    Agrega as datas duplicadas dentro de um grupo de dados.

    Args:
        grupo (DataFrame): Um grupo de dados contendo datas e valores.

    Returns:
        float: O valor agregado das datas no grupo.

    Notes:
        Se todas as datas dentro do grupo forem iguais, retorna a metade da soma dos valores.
        Se as datas forem diferentes, mas a diferença entre elas for pequena, retorna a soma total dos valores.
        Se as datas forem diferentes e a diferença entre elas for grande, retorna o valor máximo.
    """
    if grupo['m3'].diff().sum() == 0: # Números iguais, seleciona apenas 1
        return grupo['m3'].sum() / 2
    elif grupo['m3'].diff().sum() <= 999999: # Números diferentes de magnitude muito diferente, soma os dois
        return grupo['m3'].sum()
    else: # Números de magnitude muito pequena, seleciona o maior
        return grupo['m3'].max()

#############################################################################################################################

##############################FUNÇÕES PARA CORREÇÃO DE NOMES DE MUNICÍPIOS###################################################

def custom_agg(series):
    """
    Realiza uma agregação personalizada em uma série de dados.

    Args:
        series (Series): A série de dados a ser agregada.

    Returns:
        dict: Um dicionário contendo as listas de valores únicos e as contagens de ocorrências na série.
    """
    unique_values = series.unique()
    occurrences = series.value_counts().to_dict()
    return {'unique_values': unique_values.tolist(), 'occurrences': occurrences}

def agrupar_cidades_por_codigo(df, municipio_col, data_col, ibge_col, uf_col):
    """
    Agrupa os dados do DataFrame por código IBGE, agregando as colunas 'municipio_col' e 'data_col'.

    Args:
        df (DataFrame): O DataFrame contendo os dados.
        municipio_col (str): O nome da coluna que contém os nomes dos municípios.
        data_col (str): O nome da coluna que contém os dados de datas.
        ibge_col (str): O nome da coluna que contém os códigos IBGE.
        uf_col (str): O nome da coluna que contém as siglas dos estados.

    Returns:
        DataFrame: Um DataFrame contendo os dados agrupados por código IBGE, com as informações de 'municipio_col' e 'data_col' agregadas.
    """
    df['m_p'] = df[uf_col].apply(parse_string) + '-' + df[municipio_col].apply(parse_string)
    c = df.groupby(ibge_col).agg({'m_p': custom_agg, data_col: custom_agg}).reset_index()
    return c

def corrigir_municipios(df, municipio_col, uf_col, ibge_col):
    """
    Corrige os nomes de municípios no DataFrame com base nos códigos IBGE.

    Args:
        df (DataFrame): O DataFrame contendo os dados.
        municipio_col (str): O nome da coluna que contém os nomes dos municípios.
        uf_col (str): O nome da coluna que contém as siglas dos estados.
        ibge_col (str): O nome da coluna que contém os códigos IBGE.

    Returns:
        DataFrame: Um DataFrame com os nomes de municípios corrigidos.
    """
    df_copia = df.copy()
    df_copia['uf_municipio'] = df_copia[uf_col].apply(parse_string) + '-' + df_copia[municipio_col].apply(parse_string)
    df_copia['new_municipio'] = df_copia[uf_col].apply(parse_string) + '-' + df_copia[municipio_col].apply(parse_string)
    df_copia['ibge_sem_ultimo_digito'] = df_copia[ibge_col].astype(str).str[:-1].astype(int)
    agg = df_copia.groupby('ibge_sem_ultimo_digito')['uf_municipio'].agg(custom_agg).reset_index()
    for _, row in agg.iterrows():
        dicionario_ocorrencias = row['uf_municipio']['occurrences']
        codigo_ibge = row.to_dict()['ibge_sem_ultimo_digito']
        if len(dicionario_ocorrencias) > 1:
            palavra_mais_longa = max(dicionario_ocorrencias, key=len)
            for palavra in dicionario_ocorrencias:
                if palavra != palavra_mais_longa:
                    if (
                        editdistance.eval(palavra_mais_longa, palavra) <= 2 or
                        palavra in palavra_mais_longa or
                        palavra[3::] + palavra[0:3:] in palavra_mais_longa[3::] + palavra_mais_longa[0:3:]
                    ):
                        df_copia.loc[(df_copia['ibge_sem_ultimo_digito'] == codigo_ibge) & (df_copia['uf_municipio'] == palavra), 'new_municipio'] = palavra_mais_longa

    df_copia['MUNICÍPIO'] = df_copia['new_municipio'].str.slice(start=3)
    return df_copia

#############################################################################################################################

############################## FUNÇÕES PARA INTERPOLAÇÃO DE DADOS FALTANTES #################################################

def fill_missing_dates(df, date_column, measurement_column, min_date, max_date):
    """
    Preenche as datas ausentes em um DataFrame, adicionando entradas com valores de medição faltantes.

    Args:
        df (DataFrame): O DataFrame contendo os dados.
        date_column (str): O nome da coluna que contém as datas.
        measurement_column (str): O nome da coluna que contém os valores de medição.
        min_date (str): A data mínima.
        max_date (str): A data máxima.

    Returns:
        DataFrame: O DataFrame com as datas ausentes preenchidas e ordenadas.
    """
    # Detecta o formato da data (anual ou mensal)
    df[date_column] = df[date_column].astype(str)
    sample_date = df[date_column].iloc[0]
    date_format = '%Y' if len(sample_date) == 4 else '%Y%m'
    
    # Ajusta a ausência potencial de hífen em min_date e max_date
    df[date_column] = pd.to_datetime(df[date_column].str.replace("-", ""), format=date_format)
    
    # Gera o intervalo completo de datas
    start, end = pd.to_datetime(min_date, format=date_format), pd.to_datetime(max_date, format=date_format)
    if date_format == '%Y':
        date_range = pd.date_range(start=start, end=end, freq='YS')
    else:  # Mensal
        date_range = pd.date_range(start=start, end=end, freq='MS')
    
    # Encontra as datas ausentes
    existing_dates = df[date_column].dt.to_period('M' if date_format == '%Y%m' else 'Y')
    all_dates = date_range.to_period('M' if date_format == '%Y%m' else 'Y')
    missing_dates = all_dates.difference(existing_dates)
    
    # Adiciona datas ausentes com medição -1
    missing_rows = pd.DataFrame([{date_column: md.to_timestamp(), measurement_column: -1} for md in missing_dates])
    df = pd.concat([df, missing_rows], ignore_index=True)
    
    # Converte a coluna de datas de volta para string no formato original
    df[date_column] = df[date_column].dt.strftime(date_format)
    
    return df.sort_values(by=date_column).reset_index(drop=True)

def interpolar_valores_faltantes(df, metodo='slinear'):
    """
    Interpola os valores faltantes em um DataFrame.

    Args:
        df (DataFrame): O DataFrame contendo os dados.
        metodo (str): O método de interpolação a ser usado. Padrão é 'slinear'.

    Returns:
        DataFrame: O DataFrame com os valores faltantes interpolados.
    """
    df['m3'] = df['m3'].replace(-1, np.nan)
    
    # Se o primeiro valor for nulo, preenche-o com o primeiro valor não nulo seguinte
    if pd.isnull(df['m3'].iloc[0]):
        primeiro_valor = first_non_nan_value(df, 'm3')
        df.at[0, 'm3'] = primeiro_valor
    
    # Se o último valor for nulo, preenche-o com o último valor não nulo anterior
    if pd.isnull(df['m3'].iloc[-1]):
        ultimo_valor = last_non_nan_value(df, 'm3')
        df.at[df.index[-1], 'm3'] = ultimo_valor
    
    # Interpola os valores faltantes
    df['m3'] = df['m3'].interpolate(method=metodo).round(4)
    return df

#############################################################################################################################

############################## FUNÇÕES PARA TRATAMENTO DE OUTLIERS ##########################################################
def outlier_detection(series, window):
  series = np.array(series)
  outliers_idx = []
  outliers_values = []
  for i in range(0, len(series)-window, window):
    subsequence = series[i:i+window]
    Q1 = np.percentile(subsequence, 25, method = 'midpoint')
    Q3 = np.percentile(subsequence, 75, method = 'midpoint')

    IQR = Q3 - Q1
    low_lim = Q1 - 4 * IQR
    up_lim = Q3 + 4 * IQR

    for j in range(len(subsequence)):
      if subsequence[j] > up_lim or subsequence[j] < low_lim:
        outliers_idx.append(i+j)
        outliers_values.append(subsequence[j])
  return outliers_idx, outliers_values

def remove_outliers(series, outliers_idx):
  for i in outliers_idx:
    if i == 0: # caso seja a primeira observação da série
      series[i] = series[i+1]
    elif i == len(series): # caso seja a última observação da série
      series[i] = series[i-1]
    else:
      series[i] = (series[i-1] + series[i+1])/2
  return series

#############################################################################################################################

############################## FUNÇÕES PARA SELEÇÃO DE SÈRIES ###############################################################
def cortar_sequencias_vazias(df):
    """
    Remove sequências vazias do DataFrame, identificadas pelos valores -1 na coluna 'm3'.

    Args:
        df (DataFrame): O DataFrame contendo os dados.

    Returns:
        DataFrame: O DataFrame sem as sequências vazias.
    """
    df2 = df.copy()
    df2 = df2[df2['m3'] == -1]
    max_date, min_date = obter_max_min_datas(df, 'timestamp', 'ano')
    if len(df2) > 0:
        _, _, timestamps_faltantes = calcular_tamanho_gaps_series(df2)
        sequencia1_removida = df
        if min_date in timestamps_faltantes:
            sequencia1_removida = df[~df['timestamp'].astype(int).isin(find_first_sequence(timestamps_faltantes))]
        _, _, timestamps_faltantes = calcular_tamanho_gaps_series(sequencia1_removida)
        if max_date in timestamps_faltantes:
            sequencia1_removida = sequencia1_removida[~sequencia1_removida['timestamp'].astype(int).isin(find_last_sequence(timestamps_faltantes))]
    return sequencia1_removida

def calcular_tamanho_gaps_series(df):
    """
    Calcula o tamanho dos gaps no DataFrame onde 'm3' é igual a -1.

    Args:
        df (DataFrame): O DataFrame contendo os dados.

    Returns:
        tuple: Uma tupla contendo um dicionário com a contagem de tamanhos de gaps, uma lista dos tamanhos de gaps e uma lista de timestamps faltantes.
    """
    # Identifica onde 'm3' não é -1 e cria uma série booleana
    not_gap = df['m3'] != -1

    # Calcula o fim dos gaps deslocando a série de não-gaps e identificando mudanças
    gap_ends = not_gap.ne(not_gap.shift())

    # Identifica as posições de início dos gaps e atribui um número único (identificador de grupo) a cada gap
    df['gap_group'] = gap_ends.cumsum()

    # Filtra as linhas onde 'm3' é -1 para trabalhar apenas com gaps
    gaps_only = df[df['m3'] == -1]

    # Calcula os tamanhos dos gaps contando ocorrências dentro de cada 'gap_group'
    gap_sizes = gaps_only.groupby('gap_group').size()

    # Conta a frequência de cada tamanho de gap
    gap_counts = gap_sizes.value_counts().sort_index()

    # Converte em dicionário
    gaps_dict = gap_counts.to_dict()

    # Limpeza: Remove a coluna 'gap_group' do DataFrame original, se necessário
    try:
        df.drop(columns=['gap_group'], inplace=True)
    except KeyError:
        pass
    
    # Retorna um dicionário com a contagem de tamanhos de gaps, uma lista dos tamanhos de gaps e uma lista de timestamps faltantes
    return gaps_dict, list(gaps_dict.keys()), df[df['m3'] == -1]['timestamp'].astype(int).tolist()

#################################################################################################################################################

####################################### FUNÇÕES PRINCIPAIS ######################################################################################


#processa o arquivo raw_data/venda/vendas-combustiveis-m3-1990-2024.csv
def processar_dpee_mes_estado(download_path="./", filenames=[],correct_outliers=True, outlier_window=12):
    # Carregar dados
    load_path = os.path.join('dados', 'raw_data', 'sales')
    file_path = get_default_download_dir()
    load_path = os.path.join(file_path, load_path)
    series_lines = []

    nome_arquivo = 'fuel_sales_state_monthly.tsf'
    tsf_path = os.path.join(download_path, nome_arquivo)

    for filename in filenames:
        df = pd.read_csv(os.path.join(load_path, filename), sep=';')
        

        df['timestamp'] = df['ANO'].astype(str) + '-' + df['MÊS'].apply(mes_para_numero).astype(str)
        

        max_date, min_date = obter_max_min_datas(df, 'timestamp', 'mes')
        

        df['m3'] = df['VENDAS'].astype(str).str.replace(",", ".").astype(float)
        for column in ['GRANDE REGIÃO', 'UNIDADE DA FEDERAÇÃO', 'PRODUTO']:
            df[column] = df[column].apply(parse_string)
        

        df = df.sort_values(by='timestamp')
        

        combinacoes = combinar_valores_unicos_colunas(df, ['UNIDADE DA FEDERAÇÃO', 'PRODUTO'])
        
        
        for i, combinacao in enumerate(combinacoes, start=1):
            uf, produto = (combinacao[0], combinacao[1])
            df_filtrado = df[(df['UNIDADE DA FEDERAÇÃO'] == uf) & (df['PRODUTO'] == produto)][['timestamp', 'm3']]
            
            if not df_filtrado.empty:
                df_filtrado = fill_missing_dates(df_filtrado, 'timestamp', 'm3', min_date, max_date)
                
                if correct_outliers:
                    outliers_idx, outliers_values = outlier_detection(df_filtrado['m3'], outlier_window)
                    df_filtrado['m3'] = remove_outliers(df_filtrado['m3'], outliers_idx)
            
                # series_name = f"{estado_para_sigla(uf)}_{produto}".lower().replace(" ", "")
                series_name = f"T{i}"
                state = estado_para_sigla(uf).upper()
                fuel_type = fuel_pt_to_en(produto)
                # start_timestamp = pd.to_datetime(df_filtrado['timestamp'].iloc[0][:4] + '-' + df_filtrado['timestamp'].iloc[0][4:], format='%Y-%m').strftime('%Y-%m')
                start_timestamp = datetime.strptime(df_filtrado['timestamp'].iloc[0], '%Y%m').strftime('%Y-%m-%d %H-%M-%S')
                end_timestamp = datetime.strptime(df_filtrado['timestamp'].iloc[-1], '%Y%m').strftime('%Y-%m-%d %H-%M-%S')
                values = ",".join(map(str, df_filtrado['m3'].tolist()))
                series_lines.append(f"{series_name}:{start_timestamp}:{end_timestamp}:{state}:{fuel_type}:{values}")

    
    header = """# Dataset Information
# This dataset contains 216 monthly time series provided by ANP and cleaned by CISIA.
#
# For more details, please refer to
# Makridakis, S., Spiliotis, E., Assimakopoulos, V., 2020. The m4 competition: 100,000 time series and 61 forecasting methods. International Journal of Forecasting 36 (1), 54–74.
# Makridakis, S., Spiliotis, E., Assimakopoulos, V., 2018. The m4 competition: results, findings, conclusion and way forward, International Journal of Forecasting 34 (4), 802–808.
#
@relation CISIA-ANP
@attribute series_name string
@attribute start_timestamp date
@attribute end_timestamp date
@attribute state_code string
@attribute fuel_type string
@frequency monthly
@horizon 12
@missing false
@equallength true
@data"""

    with open(tsf_path, 'w') as f:
        f.write(header + "\n")
        f.writelines("\n".join(series_lines))
    
    print(f"dataset downloaded at: {tsf_path}")
    return tsf_path

#processa o arquivo raw_data/venda/vendas-combustiveis-m3-1990-2023.csv
def processar_dpee_ano_estado(download_path="./", filenames=[],correct_outliers=True, outlier_window=12):

    load_path = os.path.join('dados', 'raw_data', 'sales')
    file_path = get_default_download_dir()
    load_path = os.path.join(file_path, load_path)

    filenames, isUpdated = download_anp_data(data_type="sales", location_type="state", frequency="monthly")
    
    series_lines = []

    nome_arquivo = 'fuel_sales_state_yearly.tsf'
    tsf_path = os.path.join(download_path, nome_arquivo)
    i = 0
    df = pd.read_csv(os.path.join(load_path, filenames[0]), sep=';')

    df['timestamp'] = df['ANO'].astype(str)
    for column in ['GRANDE REGIÃO', 'UNIDADE DA FEDERAÇÃO', 'PRODUTO']:
        df[column] = df[column].apply(parse_string)
    df['m3'] = df['VENDAS'].astype(str).str.replace(",", ".").astype(float)
    combinacoes = combinar_valores_unicos_colunas(df, ['UNIDADE DA FEDERAÇÃO', 'PRODUTO'])
    max_date = obter_max_min_datas(df, 'timestamp', 'ano')[0]

    for combinacao in combinacoes:
        uf, produto = (combinacao[0],combinacao[1])
        df_filtrado = df[(df['UNIDADE DA FEDERAÇÃO'] == uf) & (df['PRODUTO'] == produto)][['timestamp', 'm3']]
        if not df.empty:
            df_agg = df_filtrado.groupby('timestamp').agg({'m3': 'sum'}).reset_index()
            
            arquivo_historico = selecionar_csv_por_produto_local(produto, 'estado')
            df_historico = pd.read_csv(os.path.join(load_path, arquivo_historico), sep =';')

            for column in ['GRANDE REGIÃO', 'ESTADO', 'PRODUTO']:
                df_historico[column] = df_historico[column].apply(parse_string)
            df_historico['timestamp'] = df_historico['ANO'].astype(str)
            min_date = obter_max_min_datas(df_historico, 'timestamp', 'ano')[1]
            df_historico['m3'] = df_historico['VENDAS'].astype(str).str.replace(",", ".").astype(float)
            df_historico = df_historico[(df_historico['ESTADO'] == uf) & (df_historico['PRODUTO'] == produto)][['timestamp', 'm3']]
            # if produto in ['glp', 'oleocombustivel']:
            #     df_historico['m3'] = df_historico['m3'].apply(lambda kg: kg_to_m3(produto, kg*1000)) #Estão em toneladas
            df_complete = pd.concat([df_historico, df_agg])
            df_complete = df_complete.sort_values(by='timestamp')
            df_complete = fill_missing_dates(df_complete, 'timestamp', 'm3', max_date, min_date)
            

            # df_complete.to_csv(os.path.join(path, nome_arquivo), sep=';', index=False)

            if correct_outliers:
                outliers_idx, outliers_values = outlier_detection(df_complete['m3'], outlier_window)
                df_complete['m3'] = remove_outliers(df_complete['m3'], outliers_idx)
            # path = ensure_folder_exists(['dados', 'sales', 'anual', 'uf', produto])
            i+=1
            series_name = f"T{i}"
            state = estado_para_sigla(uf).upper()
            fuel_type = fuel_pt_to_en(produto)
            # start_timestamp = pd.to_datetime(df_filtrado['timestamp'].iloc[0][:4] + '-' + df_filtrado['timestamp'].iloc[0][4:], format='%Y-%m').strftime('%Y-%m')
            start_timestamp = datetime.strptime(df_complete['timestamp'].iloc[0] + '-01-01 00-00-00', '%Y-%m-%d %H-%M-%S')
            end_timestamp = datetime.strptime(df_complete['timestamp'].iloc[-1] + '-01-01 00-00-00', '%Y-%m-%d %H-%M-%S')
            start_timestamp = start_timestamp.strftime('%Y-%m-%d %H-%M-%S')
            end_timestamp = end_timestamp.strftime('%Y-%m-%d %H-%M-%S')
            
            values = ",".join(map(str, df_complete['m3'].tolist()))
            series_lines.append(f"{series_name}:{start_timestamp}:{end_timestamp}:{state}:{fuel_type}:{values}")

    header = """# Dataset Information
# This dataset contains 216 yearly time series provided by ANP and cleaned by CISIA.
#
# For more details, please refer to
# Makridakis, S., Spiliotis, E., Assimakopoulos, V., 2020. The m4 competition: 100,000 time series and 61 forecasting methods. International Journal of Forecasting 36 (1), 54–74.
# Makridakis, S., Spiliotis, E., Assimakopoulos, V., 2018. The m4 competition: results, findings, conclusion and way forward, International Journal of Forecasting 34 (4), 802–808.
#
@relation CISIA-ANP
@attribute series_name string
@attribute start_timestamp date
@attribute end_timestamp date
@attribute state_code string
@attribute fuel_type string
@frequency monthly
@horizon 5
@missing false
@equallength true
@data"""

    with open(tsf_path, 'w') as f:
        f.write(header + "\n")
        f.writelines("\n".join(series_lines))
    
    print(f"dataset downloaded at: {tsf_path}")
    return tsf_path
  

def processar_derivados_municipio_ano(download_path = "./", filenames=[] ,correct_outliers = True, outlier_window = 5, min_series_length= 5):
    load_path = os.path.join('dados', 'raw_data', 'sales')
    file_path = get_default_download_dir()
    load_path = os.path.join(file_path, load_path)
    
    # derivados = {'asphalt':'asfalto', 'ethanol':'etanolhidratado', 'gasoline-r': 'gasolinac', 'gasoline-a':'gasolinadeaviacao', 'kerosene-a':'querosenedeaviacao', 'kerosene-i':'queroseneiluminante', 'oil':'oleocombustivel', 'diesel':'oleodiesel'}
    dic_series_excluidas = {'uf':[], 'produto': [], 'municipio': [], 'dados_faltantes':[]}
    dic_series_inputadas = {'uf':[], 'produto': [], 'municipio': [], 'timestamps_faltantes':[]}
    series_lines = []   
    
    nome_arquivo = 'fuel_sales_city_yearly.tsf'
    tsf_path = os.path.join(download_path, nome_arquivo)   
    
    if os.path.exists(tsf_path):
        print("Cleaning old tsf file.")
        os.remove(tsf_path)
    
    i = 0
    for filename in tqdm(filenames, desc="Preparing datasets"):
        #ex: sales_yearly_city_oleocombustivel_04-01-2024.csv
        derivado = filename.split("_")[3]
        
        arquivo = filename
        
        local_path = os.path.join(load_path, arquivo)
        local_path = os.path.join(get_default_download_dir(), local_path)
        
        df = pd.read_csv(local_path, sep=';')
        df = corrigir_municipios(df, 'MUNICÍPIO', 'UF', 'CÓDIGO IBGE')
        if derivado == 'glp':
            df['m3'] = df['P13'].astype(float) + df['OUTROS'].astype(float) *0.001 #convert to m3
        else:
            df['m3'] = df['VENDAS'].replace(",", ".", regex=True).astype(float) *0.001 #convert to m3

        if derivado in ['asfalto', 'glp', 'oleocombustivel']: #estão em kgs
                df['m3'] = df['m3'].apply(lambda kg: kg_to_m3(derivado, kg)).round(4)

        df['timestamp'] = df['ANO']
        df[['GRANDE REGIÃO', 'UF', 'PRODUTO', 'MUNICÍPIO']] = df[['GRANDE REGIÃO', 'UF', 'PRODUTO', 'MUNICÍPIO']].map(parse_string)
        max_date, min_date = obter_max_min_datas(df, 'timestamp', 'ano')
        combinacoes = combinar_valores_unicos_colunas(df, ['UF', 'PRODUTO', 'MUNICÍPIO'])
        
        for uf, produto, municipio in combinacoes:
            # print(f"Processando: UF={uf}, Produto={produto}, Município={municipio}")
            if municipio == '':
                continue
            df_filtrado = df[(df['UF'] == uf) & (df['PRODUTO'] == produto) & (df['MUNICÍPIO'] == municipio)][['timestamp', 'm3']]

            if not df_filtrado.empty:
                nome_arquivo = f'anual_{municipio}_{uf}_{produto}.csv'
                # registrar_meses_duplicados(df_filtrado, produto, municipio+"-"+uf, 'anual')
                df_filtrado = df_filtrado.groupby('timestamp').agg({'m3': 'max'}).reset_index()
                df_filled = fill_missing_dates(df_filtrado, 'timestamp', 'm3', min_date, max_date)
                # path = ensure_folder_exists(['dados', 'venda_tratamento_parcial', 'anual', 'municipio', produto])
                # df_filled.to_csv(os.path.join(path, nome_arquivo), sep=';', index=False)
                tem_valores_faltantes = len(df_filled[df_filled['m3']== -1])>0
                if tem_valores_faltantes:
                    df_filled = cortar_sequencias_vazias(df_filled).reset_index(drop=True)
                    _, gaps, _ = calcular_tamanho_gaps_series(df_filled)
                    if any(gap == 20 for gap in gaps) or len(df_filled)<min_series_length:
                        dic_series_excluidas['uf'].append(uf)
                        dic_series_excluidas['produto'].append(produto)
                        dic_series_excluidas['municipio'].append(municipio)
                        dic_series_excluidas['dados_faltantes'].append(len(df_filled[df_filled['m3']==-1]))
                        continue
                    if len(df_filled[df_filled['m3']== -1])>0:
                        dic_series_inputadas['uf'].append(uf)
                        dic_series_inputadas['produto'].append(produto)
                        dic_series_inputadas['municipio'].append(municipio)
                        datas_faltantes =  ",".join(df_filled.loc[df_filled['m3'] == -1, 'timestamp'].tolist())
                        dic_series_inputadas['timestamps_faltantes'].append(datas_faltantes)
                        df_filled = interpolar_valores_faltantes(df_filled)
                # path = ensure_folder_exists(['dados', 'venda_com_outliers', 'anual', 'municipio', produto])
                # df_filled.to_csv(os.path.join(path, nome_arquivo), sep=';', index=False)
                # print(uf, produto, municipio)
                if correct_outliers:
                    outliers_idx, outliers_values = outlier_detection(df_filled['m3'], outlier_window)
                    df_filled['m3'] = remove_outliers(df_filled['m3'], outliers_idx)
                # path = ensure_folder_exists(['dados', 'sales', 'anual', 'municipio', produto])
                # df_filled.to_csv(os.path.join(path, nome_arquivo), sep=';', index=False)
                
                
                start_timestamp = datetime.strptime(df_filled['timestamp'].iloc[0] + '-01-01 00-00-00', '%Y-%m-%d %H-%M-%S')
                end_timestamp = datetime.strptime(df_filled['timestamp'].iloc[-1] + '-01-01 00-00-00', '%Y-%m-%d %H-%M-%S')
                
                #pego somente as series que tem inicio e fim sem quebras
                years = df_filled['timestamp'].astype(int)
                start_year = years.iloc[0]
                end_year = years.iloc[-1]
                
                expected_years = list(range(start_year, end_year + 1))
                actual_years = years.tolist()
                
                if actual_years == expected_years:
                    start_timestamp = start_timestamp.strftime('%Y-%m-%d %H-%M-%S')
                    end_timestamp = end_timestamp.strftime('%Y-%m-%d %H-%M-%S')
                    serie_lista = df_filled['m3'].tolist()
                    values = ",".join(map(str, serie_lista))
                    i+=1
                    series_name = f"T{i}"
                    fuel_type = fuel_pt_to_en(produto)
                    series_lines.append(f"{series_name}:{start_timestamp}:{end_timestamp}:{uf.upper()}:{municipio}:{fuel_type}:{values}")
                
    
    header = """# Dataset Information
# This dataset contains 29.118 yearly time series from cities in BRAZIL related to derivatives petroleum sales provided by ANP and cleaned by CISIA.
#
# For more details, please refer to
# Makridakis, S., Spiliotis, E., Assimakopoulos, V., 2020. The m4 competition: 100,000 time series and 61 forecasting methods. International Journal of Forecasting 36 (1), 54–74.
# Makridakis, S., Spiliotis, E., Assimakopoulos, V., 2018. The m4 competition: results, findings, conclusion and way forward, International Journal of Forecasting 34 (4), 802–808.
#
@relation CISIA-ANP
@attribute series_name string
@attribute start_timestamp date
@attribute end_timestamp date
@attribute state_code string
@attribute city string
@attribute fuel_type string
@frequency yearly
@horizon 5
@missing false
@equallength false
@data"""

    with open(tsf_path, 'w') as f:
        f.write(header + "\n")
        f.writelines("\n".join(series_lines))
    
    print(f"dataset download at: {tsf_path}")     
    return tsf_path
    
    # pd.DataFrame(dic_series_excluidas).to_csv(os.path.join('dados', 'sales', 'series_municipio_anuais_excluidas.csv'), sep=';', index=False)
    # pd.DataFrame(dic_series_inputadas).to_csv(os.path.join('dados', 'sales', 'series_municipio_anuais_datas_inputadas.csv'), sep=';', index=False)

def processar_derivados_municipio_mes():
    path_municipio = os.path.join('dados', 'sales', 'monthly', 'municipio')
    ensure_folder_exists(path_municipio)
    df_full = pd.read_csv(os.path.join('dados', 'sales', 'vendas_mensais_municipio_completo.csv'), sep=';')
    df_full = corrigir_municipios(df_full, 'municipio', 'uf', 'cod_ibge')
    print(df_full.columns)
    df_full.loc[df_full['municipio'] == '*', 'municipio'] = df_full['cod_ibge']
    df_full= df_full[df_full['M3'] != ' -   '] 
    df_full['timestamp'] = df_full['data']
    df_full['m3'] = df_full['M3'].astype(str).str.replace(".", "").astype(float)
    df_full[['municipio', 'derivado', 'uf']] = df_full[['municipio', 'derivado', 'uf']].map(parse_string)

    combinar_valores_unicos_colunas(df_full, ['municipio', 'derivado', 'uf'])

    max_date, min_date = obter_max_min_datas(df_full, 'timestamp', 'mes')
    combinacoes = combinar_valores_unicos_colunas(df_full, ['uf', 'derivado', 'municipio'])
    total_combinations = len(combinacoes)  # Total number of combinations
    for index, (uf, produto, municipio) in enumerate(combinacoes, start=1):
        df_filtrado = df_full[(df_full['uf'] == uf) & (df_full['derivado'] == produto) & (df_full['municipio'] == municipio)][['timestamp', 'm3']]
        if not df_filtrado.empty:
            print(f"{uf} {produto} {municipio} {index}/{total_combinations}")
            path = ensure_folder_exists(['dados', 'sales', 'monthly', 'municipio', produto])
            nome_arquivo = f'mensal_{municipio}_{uf}_{produto}.csv'
            registrar_meses_duplicados(df_filtrado, produto, municipio+"-"+uf, 'monthly')
            df_filtrado = df_filtrado.groupby('timestamp').agg({'m3': 'sum'}).reset_index()
            df_filled = fill_missing_dates(df_filtrado, 'timestamp', 'm3', min_date, max_date)
            df_filled.to_csv(os.path.join(path, nome_arquivo), sep=';', index=False)

#processar_dpee_mes_estado()
#processar_dpee_ano_estado()
# processar_derivados_municipio_ano()