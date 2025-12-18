# streamlit_app.py

import os
import streamlit as st
from PIL import Image
import pandas as pd
from datetime import datetime, timedelta
import base64 
import streamlit_cookies_manager 
import json 
import locale
import warnings

# ==================== FILTRO DE AVISOS (Correção Visual) ====================
warnings.filterwarnings("ignore", message=".*st.cache is deprecated.*")

# Tenta configurar locale para pt-BR
try:
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_TIME, 'Portuguese_Brazil')
    except locale.Error:
        print("AVISO: Não foi possível definir o locale para pt-BR.")

# Importações dos módulos
from utils.loaders import load_main_base
from utils.filters import aplicar_filtros
from utils.format import normalize_dataframe

# Importação das páginas existentes (Crowley removido)
from pages import (
    inicio, 
    visao_geral, 
    clientes_faturamento, 
    perdas_ganhos, 
    cruzamentos_intersecoes, 
    top10, 
    relatorio_abc, 
    eficiencia
)

# ==================== CONFIGURAÇÕES GERAIS (COM FAVICON) ====================
icon_path = os.path.join("assets", "icone.png") 
favicon = None

if os.path.exists(icon_path):
    try:
        favicon = Image.open(icon_path)
    except Exception as e:
        print(f"Erro ao carregar favicon: {e}")

st.set_page_config(
    page_title="Dashboard Vendas Ribeirão Preto",
    page_icon=favicon, 
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== LÓGICA DE AUTENTICAÇÃO ====================

cookies = streamlit_cookies_manager.CookieManager()
if not cookies.ready():
    st.spinner("Carregando...")
    st.stop()

if not st.session_state.get("authenticated", False):
    auth_cookie = cookies.get("auth_token")
    if auth_cookie == "user_is_logged_in":
        st.session_state.authenticated = True
    else:
        st.session_state.authenticated = False

if "filters_loaded" not in st.session_state:
    filter_cookie = cookies.get("app_filters")
    if filter_cookie:
        try:
            saved_filters = json.loads(filter_cookie)
            for key, value in saved_filters.items():
                st.session_state[key] = value
        except Exception:
            pass 
    st.session_state.filters_loaded = True 

if not st.session_state.authenticated:
    hide_elements_style = """
        <style>
            [data-testid="stSidebar"] {display: none;}
            [data-testid="stHeader"] {display: none;}
            [data-testid="stToolbar"] {display: none;}
            .main {padding-top: 2rem;}
        </style>
    """
    st.markdown(hide_elements_style, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        logo_path = os.path.join("assets", "NOVABRASIL_TH+_LOGOS_VETORIAIS-07.png")
        if os.path.exists(logo_path):
            st.image(logo_path, width=200)
        
        st.markdown("#### 🔒 Acesso Restrito")
        
        with st.form(key="login_form"):
            password = st.text_input(
                "Por favor, insira a senha para acessar o dashboard:", 
                type="password",
                key="password_input"
            )
            submitted = st.form_submit_button("Entrar")

        if submitted:
            try:
                senha_correta = st.secrets["senha_app_ribeirao_preto"]
            except Exception:
                st.error("Erro Crítico: Senha não configurada no secrets.toml.")
                st.stop()

            if password.strip() == senha_correta:
                st.session_state.authenticated = True
                cookies["auth_token"] = "user_is_logged_in"
                cookies.save() 
                st.rerun() 
            else:
                st.error("Senha incorreta. Tente novamente.")
                st.session_state.authenticated = False
    st.stop()

# ==================== APP PRINCIPAL ====================

def local_css(file_name):
    if os.path.exists(file_name):
        with open(file_name, encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    else:
        st.warning(f"Arquivo de estilo não encontrado: {file_name}")

local_css("utils/style.css")

hide_default_format = """
    <style>
    [data-testid="stSidebarNav"] {display: none;}
    </style>
"""
st.markdown(hide_default_format, unsafe_allow_html=True)

# ==================== LOGO E PALETA ====================
PALETTE = ["#007dc3", "#00a8e0", "#7ad1e6", "#004b8d", "#0095d9"]
logo_path = os.path.join("assets", "NOVABRASIL_TH+_LOGOS_VETORIAIS-07.png")
if os.path.exists(logo_path):
    logo = Image.open(logo_path)
    st.sidebar.image(logo, width=160) 

# ==================== ROTEAMENTO E CONFIGURAÇÃO DE PÁGINAS ====================
query_params = st.query_params
nav_id = query_params.get("nav", ["0"])[0]

# Lista de chaves das páginas (Crowley Removido)
pages_keys = [
    "Início", 
    "Visão Geral", 
    "Clientes & Faturamento", 
    "Perdas & Ganhos", 
    "Cruzamentos & Interseções", 
    "Top 10", 
    "Relatório ABC", 
    "Eficiência"
]

try:
    idx_ativa = int(nav_id)
    if idx_ativa < 0 or idx_ativa >= len(pages_keys):
        idx_ativa = 0
except ValueError:
    idx_ativa = 0

pagina_ativa = pages_keys[idx_ativa]

# Menu de voltar (exceto Home)
if pagina_ativa != "Início":
    st.markdown("""
        <a href="?nav=0" target="_self" class="nav-back-link">
            ⬅ Voltar ao Menu Principal
        </a>
    """, unsafe_allow_html=True)

if pagina_ativa == "Início":
    pass 

# ==================== CARREGAMENTO DE DADOS (CONDICIONAL) ====================

# Inicializa variáveis
df = None
ultima_atualizacao = "N/A"

# Carrega base de vendas (Sempre, exceto se houver outra lógica futura)
df, ultima_atualizacao = load_main_base()

if (df is None or df.empty) and pagina_ativa != "Início": 
    st.warning("⚠️ Nenhuma base de dados encontrada.")
    st.stop()


# ==================== MENU LATERAL (SIDEBAR) ====================
pages = {
    "Início": inicio,
    "Visão Geral": visao_geral,
    "Clientes & Faturamento": clientes_faturamento,
    "Perdas & Ganhos": perdas_ganhos,
    "Cruzamentos & Interseções": cruzamentos_intersecoes,
    "Top 10": top10,
    "Relatório ABC": relatorio_abc,
    "Eficiência": eficiencia
}

page_display = {
    "Início": "Início",
    "Visão Geral": "Visão Geral",
    "Clientes & Faturamento": "Clientes & Faturamento",
    "Perdas & Ganhos": "Perdas & Ganhos",
    "Cruzamentos & Interseções": "Cruzamentos & Interseções",
    "Top 10": "Top 10",
    "Relatório ABC": "Relatório ABC",
    "Eficiência": "Eficiência / KPIs"
}

st.sidebar.markdown('<p style="font-size:0.85rem; font-weight:600; margin-bottom: 0.5rem; margin-left: 10px;">Selecione a página:</p>', unsafe_allow_html=True)

html_menu = []

# Gera os links internos
for idx, page_name in enumerate(pages_keys):
    is_active = "active" if page_name == pagina_ativa else ""
    display_name = page_display.get(page_name, page_name) 
    html_menu.append(
        f'<a class="sidebar-nav-btn {is_active}" href="?nav={idx}" target="_self">{display_name}</a>'
    )

# ADICIONA O LINK EXTERNO DO CROWLEY AO FINAL DA LISTA
html_menu.append(
    '<a class="sidebar-nav-btn" href="https://novabrasil-datadriven-crowley.streamlit.app" target="_blank">Relatório Crowley</a>'
)

st.sidebar.markdown(f'<div class="sidebar-nav-container">{"".join(html_menu)}</div>', unsafe_allow_html=True)
st.sidebar.divider()

# ==================== RENDERIZAÇÃO DAS PÁGINAS ====================

if pagina_ativa == "Início":
    pages[pagina_ativa].render(df) 

else:
    # --- PÁGINAS PADRÃO DE FATURAMENTO ---
    if df is not None:
        df_filtrado, anos_sel, emis_sel, exec_sel, cli_sel, mes_ini, mes_fim, show_labels, show_total = aplicar_filtros(df, cookies)
        
        if df_filtrado is None or df_filtrado.empty:
            st.warning("⚠️ Nenhum dado encontrado com os filtros aplicados.")
            st.stop()
        
        pages[pagina_ativa].render(df_filtrado, mes_ini, mes_fim, show_labels, show_total, ultima_atualizacao)
        
# ==================== POP-UPS e RODAPÉ ====================

@st.dialog("Banner de Boas-vindas", width="medium")
def modal_boas_vindas():
    st.markdown("""
        <div class="popup-title-styled">Dashboard Vendas Ribeirão Preto</div>
        <div class="popup-subtitle">Projeto Data Driven Novabrasil | Powered by Streamlit</div>
    """, unsafe_allow_html=True)

    with st.container(height=350, border=True):
        st.markdown("""
        ### Como Navegar:
        * **Menu Lateral:** Utilize os botões abaixo ou à esquerda na barra lateral para navegar entre as páginas.
        * **Filtros Globais:** No topo das páginas, selecione o filtro desejado para sua busca.
        * **Exportação:** Selecione no final das páginas para exportar tabelas ou gráficos.
        ---
        ### O que você vai encontrar:
        * **Visão Geral:** KPIs rápidos e metas.
        * **Clientes & Faturamento:** Análise detalhada.
        * **Perdas & Ganhos:** Churn e Novos Negócios.
        ---
        """)
        st.markdown("**Dúvidas:** (31) 9.9274-4574 - Silvia Freitas - Head de Inteligência de Mercado")

    st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True) 
    
    if st.button("Entendido", type="secondary"): 
        cookies["last_popup_view"] = datetime.now().isoformat()
        cookies.save()
        st.rerun()

@st.dialog("Aviso Importante: Dados", width="small")
def modal_aviso_dados():
    st.warning("⚠️ Atenção: Dados em Homologação")
    st.markdown("""
        Os dados exibidos neste ambiente são **temporários** e estão sendo utilizados apenas para fins de **testes e validação** da plataforma.
        
        Por favor, **não considere os valores como oficiais** ou definitivos para tomadas de decisão neste momento.
    """)
    st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)
    
    if st.button("Estou ciente", type="primary"):
        cookies["last_disclaimer_view"] = datetime.now().isoformat()
        cookies.save()
        st.rerun()

if st.session_state.authenticated:
    show_welcome = False
    last_view_str = cookies.get("last_popup_view")
    if not last_view_str:
        show_welcome = True
    else:
        try:
            last_view = datetime.fromisoformat(last_view_str)
            if datetime.now() - last_view > timedelta(hours=24):
                show_welcome = True
        except ValueError:
            show_welcome = True

    show_disclaimer = False
    last_disc_str = cookies.get("last_disclaimer_view")
    if not last_disc_str:
        show_disclaimer = True
    else:
        try:
            last_disc = datetime.fromisoformat(last_disc_str)
            if datetime.now() - last_disc > timedelta(hours=24):
                show_disclaimer = True
        except ValueError:
            show_disclaimer = True

    if show_welcome:
        modal_boas_vindas()
    elif show_disclaimer:
        modal_aviso_dados()

footer_html = """
<div class="footer-container">
    <p class="footer-text">Powered by Python | Interface Streamlit | Data Driven Novabrasil</p>
    <p class="footer-text">Conteúdo Confidencial. A distribuição a terceiros não autorizados é estritamente proibida.</p>
</div>
"""
st.markdown(footer_html, unsafe_allow_html=True)