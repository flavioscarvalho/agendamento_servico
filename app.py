# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
from datetime import datetime
import sqlalchemy
import bcrypt

# --- Configurações da Página ---
st.set_page_config(
    page_title="Sistema de Agendamento",
    page_icon="📅",
    layout="wide"
)

# --- Constantes ---
DISCIPLINAS = ["Matemática", "Física", "Química", "Português", "Inglês", "História", "Geografia", "Biologia"]
EQUIPAMENTOS = ["Notebook", "Celular", "Tablet", "Projetor", "Caixa de Som"]
HORARIOS = ["1º", "2º", "3º", "4º", "5º", "6º"]
TURNOS = ["Manhã", "Tarde"]
SALAS = ["205", "206"]

# --- Conexão com o Banco de Dados (usando st.connection) ---
# Garante que a conexão só seja estabelecida uma vez.
if 'conn' not in st.session_state:
    st.session_state.conn = st.connection("db_agendamentos", type="sql")
conn = st.session_state.conn

# --- Funções do Banco de Dados ---

def inicializar_banco():
    """Cria as tabelas no banco de dados se elas não existirem."""
    with conn.session as s:
        s.execute(sqlalchemy.text('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            );
        '''))
        s.execute(sqlalchemy.text('''
            CREATE TABLE IF NOT EXISTS agendamentos (
                id SERIAL PRIMARY KEY,
                "Data" DATE NOT NULL,
                "Disciplina" TEXT,
                "Equipamentos" TEXT,
                "Horario" TEXT,
                "Turno" TEXT,
                "Sala" TEXT,
                "Professor" TEXT
            );
        '''))
        s.commit()

def hash_password(password):
    """Cria um hash seguro para a senha."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def verify_password(stored_hash, provided_password):
    """Verifica se a senha fornecida corresponde ao hash armazenado."""
    return bcrypt.checkpw(provided_password.encode('utf-8'), stored_hash.encode('utf-8'))

def adicionar_usuario(username, password):
    """Adiciona um novo usuário ao banco de dados."""
    password_hash = hash_password(password)
    with conn.session as s:
        # Verifica se o usuário já existe
        result = s.execute(sqlalchemy.text("SELECT * FROM usuarios WHERE username = :user"), {'user': username}).first()
        if result:
            return False # Usuário já existe
        
        s.execute(
            sqlalchemy.text("INSERT INTO usuarios (username, password_hash) VALUES (:user, :phash)"),
            {'user': username, 'phash': password_hash.decode('utf-8')}
        )
        s.commit()
    return True

def buscar_usuario(username):
    """Busca um usuário pelo nome."""
    with conn.session as s:
        result = s.execute(sqlalchemy.text("SELECT * FROM usuarios WHERE username = :user"), {'user': username}).first()
        return result

def salvar_agendamento(data, disciplina, equipamentos, horario, turno, sala, professor):
    """Salva um novo agendamento no banco de dados."""
    equipamentos_str = ", ".join(equipamentos)
    with conn.session as s:
        s.execute(
            sqlalchemy.text('INSERT INTO agendamentos ("Data", "Disciplina", "Equipamentos", "Horario", "Turno", "Sala", "Professor") VALUES (:data, :disc, :equip, :hor, :turno, :sala, :prof)'),
            params=dict(data=data, disc=disciplina, equip=equipamentos_str, hor=horario, turno=turno, sala=sala, prof=professor)
        )
        s.commit()

def carregar_dados():
    """Carrega todos os agendamentos do banco de dados."""
    df = conn.query('SELECT * FROM agendamentos ORDER BY "Data" DESC')
    return df

# --- Telas da Aplicação ---

def tela_professor():
    st.header(f"📅 Agendamento de Recursos - Bem-vindo(a), {st.session_state.username}!")
    st.markdown("Utilize o formulário abaixo para agendar o uso de equipamentos e salas.")

    with st.form("form_agendamento", clear_on_submit=True):
        st.subheader("Novo Agendamento")
        col1, col2 = st.columns(2)
        with col1:
            data_selecionada = st.date_input("🗓️ Selecione o Dia", min_value=datetime.today())
            disciplina = st.selectbox("📚 Disciplina", options=DISCIPLINAS)
            equipamentos = st.multiselect("💻 Equipamentos", options=EQUIPAMENTOS)
        with col2:
            horario = st.selectbox("⏰ Horário", options=HORARIOS)
            turno = st.selectbox("☀️ Turno", options=TURNOS)
            sala = st.selectbox("🚪 Sala", options=SALAS)
        
        if st.form_submit_button("✅ Salvar Agendamento"):
            if not equipamentos:
                st.warning("Por favor, selecione pelo menos um equipamento.")
            else:
                salvar_agendamento(data_selecionada, disciplina, equipamentos, horario, turno, sala, st.session_state.username)
                st.success(f"Agendamento para a sala {sala} no dia {data_selecionada.strftime('%d/%m/%Y')} salvo!")

    st.markdown("---")
    st.subheader("Meus Próximos Agendamentos")
    df = carregar_dados()
    df_prof = df[df['Professor'] == st.session_state.username]
    if not df_prof.empty:
        st.dataframe(df_prof, use_container_width=True)
    else:
        st.info("Você ainda não possui agendamentos.")

def tela_admin():
    st.header("🔑 Painel Administrativo")
    st.markdown("Visualize todos os agendamentos realizados no sistema.")

    df = carregar_dados()
    if df.empty:
        st.info("Nenhum agendamento foi realizado ainda.")
        return

    df['Data'] = pd.to_datetime(df['Data'])
    df['Mês'] = df['Data'].dt.month
    df['Ano'] = df['Data'].dt.year
    
    meses_nomes = {1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril', 5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto', 9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'}
    
    st.subheader("Filtrar Agendamentos")
    col1, col2 = st.columns(2)
    with col1:
        anos_disponiveis = sorted(df['Ano'].unique(), reverse=True)
        if not anos_disponiveis:
            st.warning("Não há dados de anos para filtrar.")
            return
        ano_selecionado = st.selectbox("Selecione o Ano", options=anos_disponiveis)
    with col2:
        meses_disponiveis = sorted(df[df['Ano'] == ano_selecionado]['Mês'].unique())
        if not meses_disponiveis:
            st.warning("Não há dados de meses para este ano.")
            return
        mes_selecionado_nome = st.selectbox("Selecione o Mês", options=[meses_nomes[m] for m in meses_disponiveis])
    
    mes_selecionado_num = [k for k, v in meses_nomes.items() if v == mes_selecionado_nome][0]
    df_filtrado = df[(df['Mês'] == mes_selecionado_num) & (df['Ano'] == ano_selecionado)]
    st.dataframe(df_filtrado.drop(columns=['Mês', 'Ano']), use_container_width=True)

def tela_login():
    st.sidebar.image("https://images.unsplash.com/photo-1517245386807-bb43f82c33c4?q=80&w=2070&auto=format&fit=crop", use_container_width=True)
    st.sidebar.title("Login do Sistema")

    tab_login, tab_register = st.sidebar.tabs(["Login", "Registrar-se"])

    with tab_login:
        username = st.text_input("👤 Usuário", key="login_user").lower()
        password = st.text_input("🔑 Senha", type="password", key="login_pass")
        if st.button("Entrar"):
            user_data = buscar_usuario(username)
            if user_data and verify_password(user_data.password_hash, password):
                st.session_state.logged_in = True
                st.session_state.username = user_data.username
                st.rerun()
            else:
                st.error("Usuário ou senha inválidos.")

    with tab_register:
        new_username = st.text_input("👤 Novo Usuário", key="reg_user").lower()
        new_password = st.text_input("🔑 Nova Senha", type="password", key="reg_pass")
        if st.button("Registrar"):
            if not new_username or not new_password:
                st.warning("Por favor, preencha todos os campos.")
            else:
                if adicionar_usuario(new_username, new_password):
                    st.success("Usuário registrado com sucesso! Faça o login.")
                else:
                    st.error("Este nome de usuário já existe.")
    
    if not st.session_state.get('logged_in', False):
        st.title("Bem-vindo ao Sistema de Agendamento de Recursos 📅")
        st.info("Por favor, faça o login ou registre-se na barra lateral para continuar.")
        st.image("https://images.unsplash.com/photo-1522202176988-66273c2fd55f?q=80&w=2071&auto=format&fit=crop", caption="Ambiente de aprendizado moderno", width=700)

# --- Lógica Principal da Aplicação ---
def main():
    inicializar_banco()

    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        tela_login()
    else:
        if st.sidebar.button("Sair"):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.rerun()
        
        # O usuário "admin" continua com superpoderes
        if st.session_state.username == 'admin':
            tela_admin()
        else: # Todos os outros usuários são "professores"
            tela_professor()

if __name__ == "__main__":
    main()
