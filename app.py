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

# --- CONFIGURAÇÕES DE ACESSO ---
CODIGO_CADASTRO = "SESI2024"  # 🔑 Código para cadastro
ADMINS = ["admin", "diretor", "coordenador", "secretaria"]  # 👨‍💼 Administradores

# --- STATUS DE AGENDAMENTO ---
STATUS_PENDENTE = "Pendente"
STATUS_APROVADO = "Aprovado"
STATUS_REJEITADO = "Rejeitado"

# Cores para cada status
STATUS_COLORS = {
    STATUS_PENDENTE: "🟡",    # Amarelo
    STATUS_APROVADO: "🟢",    # Verde
    STATUS_REJEITADO: "🔴"    # Vermelho
}

# --- Conexão com o Banco de Dados ---
@st.cache_resource
def init_connection():
    """Inicializa a conexão com o banco de dados com tratamento de erro."""
    try:
        return st.connection("db_agendamentos", type="sql")
    except Exception as e:
        st.error(f"❌ Erro ao conectar com o banco de dados. Verifique as configurações de secrets.")
        st.error(f"Detalhes técnicos: {str(e)}")
        st.info("💡 Certifique-se de que as credenciais do Supabase estão configuradas corretamente no Streamlit Cloud.")
        st.stop()

# --- Funções de Verificação ---
def eh_admin(username):
    """Verifica se o usuário é administrador"""
    return username in ADMINS

def obter_tipo_usuario(username):
    """Retorna o tipo do usuário para exibição"""
    return "👨‍💼 Administrador" if eh_admin(username) else "👩‍🏫 Professor"

def obter_cor_status(status):
    """Retorna a cor/emoji do status"""
    return STATUS_COLORS.get(status, "⚪")

# --- Funções do Banco de Dados ---

def verificar_coluna_existe(conn, tabela, coluna):
    """Verifica se uma coluna existe na tabela"""
    try:
        with conn.session as s:
            result = s.execute(sqlalchemy.text(f"""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = '{tabela}' 
                AND column_name = '{coluna}'
                AND table_schema = 'public'
            """))
            return result.fetchone() is not None
    except:
        return False

def adicionar_coluna_seguro(conn, tabela, coluna, tipo, default=None):
    """Adiciona uma coluna de forma segura, verificando se já existe"""
    try:
        if not verificar_coluna_existe(conn, tabela, coluna):
            with conn.session as s:
                if default:
                    # Casos especiais para funções PostgreSQL (sem aspas)
                    if default.upper() in ['CURRENT_TIMESTAMP', 'NOW()', 'CURRENT_DATE']:
                        sql = f'ALTER TABLE {tabela} ADD COLUMN "{coluna}" {tipo} DEFAULT {default}'
                    else:
                        sql = f'ALTER TABLE {tabela} ADD COLUMN "{coluna}" {tipo} DEFAULT \'{default}\''
                else:
                    sql = f'ALTER TABLE {tabela} ADD COLUMN "{coluna}" {tipo}'
                
                s.execute(sqlalchemy.text(sql))
                s.commit()
                st.success(f"✅ Coluna '{coluna}' adicionada com sucesso!")
                return True
        else:
            st.info(f"ℹ️ Coluna '{coluna}' já existe.")
            return True
    except Exception as e:
        st.warning(f"⚠️ Problema ao adicionar coluna '{coluna}': {str(e)}")
        
        # Tenta versão mais simples sem DEFAULT
        if default:
            try:
                with conn.session as s:
                    sql = f'ALTER TABLE {tabela} ADD COLUMN "{coluna}" {tipo}'
                    s.execute(sqlalchemy.text(sql))
                    s.commit()
                    st.info(f"✅ Coluna '{coluna}' adicionada sem valor padrão.")
                    return True
            except Exception as e2:
                st.error(f"❌ Erro final ao adicionar coluna '{coluna}': {str(e2)}")
        
        return False

def inicializar_banco():
    """Cria as tabelas no banco de dados se elas não existirem."""
    try:
        conn = init_connection()
        
        # Verifica se as tabelas já existem
        with conn.session as s:
            result = s.execute(sqlalchemy.text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('usuarios', 'agendamentos')
            """))
            existing_tables = [row[0] for row in result.fetchall()]
            
            # Cria tabela usuarios se não existir
            if 'usuarios' not in existing_tables:
                s.execute(sqlalchemy.text('''
                    CREATE TABLE usuarios (
                        id SERIAL PRIMARY KEY,
                        username TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                '''))
                s.commit()
                st.success("✅ Tabela 'usuarios' criada com sucesso!")
                
            # Cria tabela agendamentos se não existir
            if 'agendamentos' not in existing_tables:
                s.execute(sqlalchemy.text('''
                    CREATE TABLE agendamentos (
                        id SERIAL PRIMARY KEY,
                        "Data" DATE NOT NULL,
                        "Disciplina" TEXT,
                        "Equipamentos" TEXT,
                        "Horario" TEXT,
                        "Turno" TEXT,
                        "Sala" TEXT,
                        "Professor" TEXT,
                        "Status" TEXT DEFAULT 'Pendente',
                        "Observacoes" TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                '''))
                s.commit()
                st.success("✅ Tabela 'agendamentos' criada com sucesso!")
            # else:
            #     # Tabela existe, verificar se precisa adicionar novas colunas
            #     st.info("ℹ️ Verificando estrutura da tabela agendamentos...")
                
            #     # Adiciona colunas uma por vez de forma segura
            #     adicionar_coluna_seguro(conn, 'agendamentos', 'Status', 'TEXT', 'Pendente')
            #     adicionar_coluna_seguro(conn, 'agendamentos', 'Observacoes', 'TEXT')
            #     # updated_at removido - não é necessário para funcionamento
                
            #     # Atualiza registros antigos que não têm status
            #     try:
            #         with conn.session as s:
            #             s.execute(sqlalchemy.text("""
            #                 UPDATE agendamentos 
            #                 SET "Status" = 'Pendente' 
            #                 WHERE "Status" IS NULL
            #             """))
            #             s.commit()
            #             st.info("ℹ️ Registros antigos atualizados com status padrão.")
            #     except Exception as e:
            #         st.warning(f"⚠️ Aviso ao atualizar registros: {str(e)}")
            
        return conn
            
    except Exception as e:
        st.error(f"❌ Erro ao inicializar banco de dados: {str(e)}")
        
        # Tenta recuperar mostrando opção de reset
        st.error("🔧 **Problema detectado na estrutura do banco!**")
        
        if st.button("🔄 Tentar Resetar Estrutura"):
            try:
                conn = init_connection()
                with conn.session as s:
                    # Remove tabela problemática e recria
                    s.execute(sqlalchemy.text("DROP TABLE IF EXISTS agendamentos_backup"))
                    s.execute(sqlalchemy.text("""
                        CREATE TABLE agendamentos_backup AS 
                        SELECT * FROM agendamentos
                    """))
                    s.execute(sqlalchemy.text("DROP TABLE agendamentos"))
                    s.execute(sqlalchemy.text('''
                        CREATE TABLE agendamentos (
                            id SERIAL PRIMARY KEY,
                            "Data" DATE NOT NULL,
                            "Disciplina" TEXT,
                            "Equipamentos" TEXT,
                            "Horario" TEXT,
                            "Turno" TEXT,
                            "Sala" TEXT,
                            "Professor" TEXT,
                            "Status" TEXT DEFAULT 'Pendente',
                            "Observacoes" TEXT,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                    '''))
                    
                    # Restaura dados
                    s.execute(sqlalchemy.text("""
                        INSERT INTO agendamentos 
                        ("Data", "Disciplina", "Equipamentos", "Horario", "Turno", "Sala", "Professor", created_at)
                        SELECT "Data", "Disciplina", "Equipamentos", "Horario", "Turno", "Sala", "Professor", created_at
                        FROM agendamentos_backup
                    """))
                    
                    s.execute(sqlalchemy.text("DROP TABLE agendamentos_backup"))
                    s.commit()
                    
                st.success("✅ Estrutura resetada com sucesso!")
                st.rerun()
                
            except Exception as reset_error:
                st.error(f"❌ Erro no reset: {str(reset_error)}")
        
        st.stop()

def hash_password(password):
    """Cria um hash seguro para a senha."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def verify_password(stored_hash, provided_password):
    """Verifica se a senha fornecida corresponde ao hash armazenado."""
    try:
        return bcrypt.checkpw(provided_password.encode('utf-8'), stored_hash.encode('utf-8'))
    except Exception as e:
        st.error(f"Erro na verificação de senha: {str(e)}")
        return False

def adicionar_usuario(username, password):
    """Adiciona um novo usuário ao banco de dados."""
    try:
        password_hash = hash_password(password)
        conn = init_connection()
        with conn.session as s:
            result = s.execute(sqlalchemy.text("SELECT * FROM usuarios WHERE username = :user"), {'user': username}).first()
            if result:
                return False
            
            s.execute(
                sqlalchemy.text("INSERT INTO usuarios (username, password_hash) VALUES (:user, :phash)"),
                {'user': username, 'phash': password_hash.decode('utf-8')}
            )
            s.commit()
        return True
    except Exception as e:
        st.error(f"Erro ao adicionar usuário: {str(e)}")
        return False

def buscar_usuario(username):
    """Busca um usuário pelo nome."""
    try:
        conn = init_connection()
        with conn.session as s:
            result = s.execute(sqlalchemy.text("SELECT * FROM usuarios WHERE username = :user"), {'user': username}).first()
            return result
    except Exception as e:
        st.error(f"Erro ao buscar usuário: {str(e)}")
        return None

def salvar_agendamento(data, disciplina, equipamentos, horario, turno, sala, professor):
    """Salva um novo agendamento no banco de dados com status pendente."""
    try:
        equipamentos_str = ", ".join(equipamentos)
        conn = init_connection()
        with conn.session as s:
            # Verifica se a coluna Status existe antes de usá-la
            if verificar_coluna_existe(conn, 'agendamentos', 'Status'):
                s.execute(
                    sqlalchemy.text('''INSERT INTO agendamentos 
                        ("Data", "Disciplina", "Equipamentos", "Horario", "Turno", "Sala", "Professor", "Status") 
                        VALUES (:data, :disc, :equip, :hor, :turno, :sala, :prof, :status)'''),
                    params=dict(data=data, disc=disciplina, equip=equipamentos_str, 
                              hor=horario, turno=turno, sala=sala, prof=professor, status=STATUS_PENDENTE)
                )
            else:
                # Fallback para tabelas antigas
                s.execute(
                    sqlalchemy.text('''INSERT INTO agendamentos 
                        ("Data", "Disciplina", "Equipamentos", "Horario", "Turno", "Sala", "Professor") 
                        VALUES (:data, :disc, :equip, :hor, :turno, :sala, :prof)'''),
                    params=dict(data=data, disc=disciplina, equip=equipamentos_str, 
                              hor=horario, turno=turno, sala=sala, prof=professor)
                )
            s.commit()
        return True
    except Exception as e:
        st.error(f"Erro ao salvar agendamento: {str(e)}")
        return False

def atualizar_status_agendamento(agendamento_id, novo_status, observacoes=""):
    """Atualiza o status de um agendamento."""
    try:
        conn = init_connection()
        with conn.session as s:
            # Verifica se as colunas existem
            if verificar_coluna_existe(conn, 'agendamentos', 'Status'):
                if verificar_coluna_existe(conn, 'agendamentos', 'Observacoes'):
                    s.execute(
                        sqlalchemy.text('''UPDATE agendamentos 
                            SET "Status" = :status, "Observacoes" = :obs
                            WHERE id = :id'''),
                        {'status': novo_status, 'obs': observacoes, 'id': agendamento_id}
                    )
                else:
                    s.execute(
                        sqlalchemy.text('''UPDATE agendamentos 
                            SET "Status" = :status
                            WHERE id = :id'''),
                        {'status': novo_status, 'id': agendamento_id}
                    )
                s.commit()
                return True
            else:
                st.error("❌ Tabela não possui coluna de Status. Execute a migração primeiro.")
                return False
    except Exception as e:
        st.error(f"Erro ao atualizar status: {str(e)}")
        return False

def carregar_dados(filtro_status=None, professor=None):
    """Carrega agendamentos do banco de dados com filtros opcionais."""
    try:
        conn = init_connection()
        
        # Verifica se a coluna Status existe
        tem_status = verificar_coluna_existe(conn, 'agendamentos', 'Status')
        
        if tem_status:
            query = 'SELECT * FROM agendamentos WHERE 1=1'
            params = {}
            
            if filtro_status:
                query += ' AND "Status" = :status'
                params['status'] = filtro_status
                
            if professor:
                query += ' AND "Professor" = :professor'
                params['professor'] = professor
                
            query += ' ORDER BY "Data" DESC, created_at DESC'
            
            if params:
                df = conn.query(query, params=params)
            else:
                df = conn.query(query)
        else:
            # Fallback para tabelas antigas sem Status
            query = 'SELECT *, \'Pendente\' as "Status" FROM agendamentos WHERE 1=1'
            
            if professor:
                query += ' AND "Professor" = :professor'
                df = conn.query(query, params={'professor': professor})
            else:
                df = conn.query(query)
                
            query += ' ORDER BY "Data" DESC, created_at DESC'
            
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados: {str(e)}")
        return pd.DataFrame()

def contar_agendamentos_por_status():
    """Conta agendamentos por status para estatísticas."""
    try:
        conn = init_connection()
        
        if verificar_coluna_existe(conn, 'agendamentos', 'Status'):
            with conn.session as s:
                result = s.execute(sqlalchemy.text('SELECT "Status", COUNT(*) FROM agendamentos GROUP BY "Status"'))
                contadores = dict(result.fetchall())
                
                return {
                    STATUS_PENDENTE: contadores.get(STATUS_PENDENTE, 0),
                    STATUS_APROVADO: contadores.get(STATUS_APROVADO, 0),
                    STATUS_REJEITADO: contadores.get(STATUS_REJEITADO, 0)
                }
        else:
            # Para tabelas antigas, considera tudo como pendente
            with conn.session as s:
                result = s.execute(sqlalchemy.text('SELECT COUNT(*) FROM agendamentos'))
                total = result.fetchone()[0]
                return {STATUS_PENDENTE: total, STATUS_APROVADO: 0, STATUS_REJEITADO: 0}
    except:
        return {STATUS_PENDENTE: 0, STATUS_APROVADO: 0, STATUS_REJEITADO: 0}

# --- Telas da Aplicação ---

def tela_professor():
    st.header(f"📅 Agendamento de Recursos - Bem-vindo(a), {st.session_state.username}!")
    
    # Verifica se o sistema tem recurso de aprovação
    conn = init_connection()
    tem_sistema_aprovacao = verificar_coluna_existe(conn, 'agendamentos', 'Status')
    
    if tem_sistema_aprovacao:
        st.markdown("Utilize o formulário abaixo para solicitar o uso de equipamentos e salas.")
    else:
        st.markdown("Utilize o formulário abaixo para agendar o uso de equipamentos e salas.")
        st.info("ℹ️ Sistema em modo básico. Para ativar aprovações, execute a migração do banco.")

    with st.form("form_agendamento", clear_on_submit=True):
        if tem_sistema_aprovacao:
            st.subheader("📝 Nova Solicitação de Agendamento")
        else:
            st.subheader("📝 Novo Agendamento")
            
        col1, col2 = st.columns(2)
        with col1:
            data_selecionada = st.date_input("🗓️ Selecione o Dia", min_value=datetime.today())
            disciplina = st.selectbox("📚 Disciplina", options=DISCIPLINAS)
            equipamentos = st.multiselect("💻 Equipamentos", options=EQUIPAMENTOS)
        with col2:
            horario = st.selectbox("⏰ Horário", options=HORARIOS)
            turno = st.selectbox("☀️ Turno", options=TURNOS)
            sala = st.selectbox("🚪 Sala", options=SALAS)
        
        botao_texto = "📤 Enviar Solicitação" if tem_sistema_aprovacao else "✅ Salvar Agendamento"
        
        if st.form_submit_button(botao_texto):
            if not equipamentos:
                st.warning("⚠️ Por favor, selecione pelo menos um equipamento.")
            else:
                if salvar_agendamento(data_selecionada, disciplina, equipamentos, horario, turno, sala, st.session_state.username):
                    if tem_sistema_aprovacao:
                        st.success(f"✅ Solicitação enviada! Aguarde aprovação do administrador.")
                        st.info("💡 Você pode acompanhar o status da sua solicitação abaixo.")
                    else:
                        st.success(f"✅ Agendamento para a sala {sala} no dia {data_selecionada.strftime('%d/%m/%Y')} salvo com sucesso!")

    st.markdown("---")
    
    if tem_sistema_aprovacao:
        st.subheader("📋 Minhas Solicitações de Agendamento")
        
        # Filtros para o professor
        col1, col2 = st.columns(2)
        with col1:
            filtro_status = st.selectbox(
                "🎯 Filtrar por Status:",
                options=["Todos", STATUS_PENDENTE, STATUS_APROVADO, STATUS_REJEITADO],
                key="professor_filtro"
            )
        
        # Carrega dados do professor
        if filtro_status == "Todos":
            df = carregar_dados(professor=st.session_state.username)
        else:
            df = carregar_dados(filtro_status=filtro_status, professor=st.session_state.username)
        
        if not df.empty:
            # Adiciona coluna com cor do status
            df_display = df.copy()
            if 'Status' in df_display.columns:
                df_display['Status_Display'] = df_display['Status'].apply(
                    lambda x: f"{obter_cor_status(x)} {x}"
                )
                
                # Estatísticas rápidas
                stats = df['Status'].value_counts()
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("🟡 Pendentes", stats.get(STATUS_PENDENTE, 0))
                with col2:
                    st.metric("🟢 Aprovados", stats.get(STATUS_APROVADO, 0))
                with col3:
                    st.metric("🔴 Rejeitados", stats.get(STATUS_REJEITADO, 0))
                
                # Reorganiza colunas para melhor visualização
                colunas_ordem = ['Data', 'Disciplina', 'Equipamentos', 'Horario', 'Turno', 'Sala', 'Status_Display']
                if 'Observacoes' in df_display.columns:
                    colunas_ordem.append('Observacoes')
                    
                df_display = df_display[colunas_ordem]
                df_display = df_display.rename(columns={'Status_Display': 'Status'})
                
                # Alertas baseados no status
                pendentes = stats.get(STATUS_PENDENTE, 0)
                if pendentes > 0:
                    st.info(f"⏳ Você tem {pendentes} solicitação(ões) aguardando aprovação.")
                    
            st.dataframe(df_display, use_container_width=True)
        else:
            st.info("ℹ️ Você ainda não possui solicitações de agendamento.")
    else:
        st.subheader("📋 Meus Agendamentos")
        df = carregar_dados(professor=st.session_state.username)
        if not df.empty:
            st.dataframe(df, use_container_width=True)
        else:
            st.info("ℹ️ Você ainda não possui agendamentos.")

def tela_admin():
    st.header("🔑 Painel Administrativo")
    
    # Verifica se o sistema tem recurso de aprovação
    conn = init_connection()
    tem_sistema_aprovacao = verificar_coluna_existe(conn, 'agendamentos', 'Status')
    
    if tem_sistema_aprovacao:
        st.markdown("Gerencie todas as solicitações de agendamento do sistema.")
        
        # Estatísticas gerais
        stats = contar_agendamentos_por_status()
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("📊 Total", sum(stats.values()))
        with col2:
            st.metric("🟡 Pendentes", stats[STATUS_PENDENTE])
        with col3:
            st.metric("🟢 Aprovados", stats[STATUS_APROVADO])
        with col4:
            st.metric("🔴 Rejeitados", stats[STATUS_REJEITADO])

        # Filtros administrativos
        st.subheader("🔍 Filtros e Ações")
        col1, col2 = st.columns(2)
        
        with col1:
            filtro_status_admin = st.selectbox(
                "🎯 Filtrar por Status:",
                options=["Todos", STATUS_PENDENTE, STATUS_APROVADO, STATUS_REJEITADO],
                key="admin_filtro"
            )
        
        with col2:
            if stats[STATUS_PENDENTE] > 0:
                st.warning(f"⚠️ {stats[STATUS_PENDENTE]} solicitação(ões) aguardando sua aprovação!")

        # Carrega e exibe dados
        if filtro_status_admin == "Todos":
            df = carregar_dados()
        else:
            df = carregar_dados(filtro_status=filtro_status_admin)

        if df.empty:
            st.info("ℹ️ Nenhuma solicitação encontrada com os filtros selecionados.")
            return

        st.subheader(f"📋 Solicitações de Agendamento - {filtro_status_admin}")
        
        # Interface de aprovação para itens pendentes
        if filtro_status_admin in ["Todos", STATUS_PENDENTE]:
            df_pendentes = df[df['Status'] == STATUS_PENDENTE] if filtro_status_admin == "Todos" else df
            
            if not df_pendentes.empty:
                st.markdown("### ⚡ Ações Rápidas - Pendentes")
                
                for idx, row in df_pendentes.iterrows():
                    with st.container():
                        col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])
                        
                        with col1:
                            st.write(f"**{row['Professor']}** - {row['Data']} - {row['Disciplina']}")
                            st.write(f"🚪 Sala {row['Sala']} | ⏰ {row['Horario']} ({row['Turno']}) | 💻 {row['Equipamentos']}")
                        
                        with col2:
                            st.write("🟡 Pendente")
                        
                        with col3:
                            if st.button("✅ Aprovar", key=f"aprovar_{row['id']}"):
                                if atualizar_status_agendamento(row['id'], STATUS_APROVADO):
                                    st.success("Aprovado!")
                                    st.rerun()
                        
                        with col4:
                            if st.button("❌ Rejeitar", key=f"rejeitar_{row['id']}"):
                                if atualizar_status_agendamento(row['id'], STATUS_REJEITADO):
                                    st.success("Rejeitado!")
                                    st.rerun()
                        
                        with col5:
                            if verificar_coluna_existe(conn, 'agendamentos', 'Observacoes'):
                                with st.popover("📝 Obs"):
                                    obs = st.text_area("Observações:", key=f"obs_{row['id']}", height=100)
                                    if st.button("💾 Salvar", key=f"salvar_obs_{row['id']}"):
                                        if atualizar_status_agendamento(row['id'], row['Status'], obs):
                                            st.success("Salvo!")
                        
                        st.divider()

        # Tabela completa
        st.markdown("### 📊 Visualização Completa")
        
        # Prepara dados para exibição
        df_display = df.copy()
        if 'Status' in df_display.columns:
            df_display['Status_Display'] = df_display['Status'].apply(
                lambda x: f"{obter_cor_status(x)} {x}"
            )
            
            # Reorganiza colunas
            colunas_ordem = ['Data', 'Professor', 'Disciplina', 'Equipamentos', 'Horario', 'Turno', 'Sala', 'Status_Display']
            if 'Observacoes' in df_display.columns:
                colunas_ordem.append('Observacoes')
                
            df_display = df_display[colunas_ordem]
            df_display = df_display.rename(columns={'Status_Display': 'Status'})
        
        st.dataframe(df_display, use_container_width=True)
        
    else:
        st.markdown("Visualize todos os agendamentos realizados no sistema.")
        st.warning("⚠️ Sistema em modo básico. Execute a migração para ativar o sistema de aprovação.")
        
        df = carregar_dados()
        if df.empty:
            st.info("ℹ️ Nenhum agendamento foi realizado ainda.")
        else:
            st.dataframe(df, use_container_width=True)

def tela_login():
    st.sidebar.image("https://images.unsplash.com/photo-1517245386807-bb43f82c33c4?q=80&w=2070&auto=format&fit=crop", use_container_width=True)
    st.sidebar.title("🔐 Login do Sistema")

    tab_login, tab_register = st.sidebar.tabs(["🔑 Login", "📝 Registrar-se"])

    with tab_login:
        username = st.text_input("👤 Usuário", key="login_user").lower().strip()
        password = st.text_input("🔑 Senha", type="password", key="login_pass")
        if st.button("🚀 Entrar"):
            if not username or not password:
                st.error("❌ Por favor, preencha todos os campos.")
            else:
                user_data = buscar_usuario(username)
                if user_data and verify_password(user_data.password_hash, password):
                    st.session_state.logged_in = True
                    st.session_state.username = user_data.username
                    st.success(f"✅ Login realizado como {obter_tipo_usuario(username)}!")
                    st.rerun()
                else:
                    st.error("❌ Usuário ou senha inválidos.")

    with tab_register:
        st.markdown("### 🔑 Cadastro Restrito")
        
        st.info(f"""
        💡 **Como se cadastrar:**
        
        🔑 **Código necessário:** `{CODIGO_CADASTRO}`
        
        **👨‍💼 Para ser ADMINISTRADOR:**
        Use um destes usernames: {', '.join(ADMINS)}
        
        **👩‍🏫 Para ser PROFESSOR:**
        Use qualquer outro username (ex: joao.silva, maria.santos)
        """)
        
        codigo_acesso = st.text_input("🔑 Código de Acesso")
        new_username = st.text_input("👤 Novo Usuário", key="reg_user").lower().strip()
        new_password = st.text_input("🔑 Nova Senha", type="password", key="reg_pass")
        
        if new_username:
            tipo_previsto = obter_tipo_usuario(new_username)
            if eh_admin(new_username):
                st.success(f"✅ Será cadastrado como: {tipo_previsto}")
            else:
                st.info(f"ℹ️ Será cadastrado como: {tipo_previsto}")
        
        if st.button("📝 Registrar"):
            if not codigo_acesso:
                st.error("❌ Digite o código de acesso!")
            elif codigo_acesso != CODIGO_CADASTRO:
                st.error("❌ Código de acesso inválido!")
            elif not new_username or not new_password:
                st.warning("⚠️ Por favor, preencha todos os campos.")
            elif len(new_password) < 4:
                st.warning("⚠️ A senha deve ter pelo menos 4 caracteres.")
            else:
                if adicionar_usuario(new_username, new_password):
                    tipo_usuario = obter_tipo_usuario(new_username)
                    st.success(f"✅ Usuário registrado como {tipo_usuario}!")
                    st.balloons()
                else:
                    st.error("❌ Este nome de usuário já existe.")
    
    if not st.session_state.get('logged_in', False):
        st.title("🎓 Sistema de Agendamento com Aprovação")
        st.markdown("### 📚 Sistema profissional para gestão de recursos educacionais")
        
        # Verifica se tem sistema de aprovação
        try:
            conn = init_connection()
            tem_aprovacao = verificar_coluna_existe(conn, 'agendamentos', 'Status')
            
            if tem_aprovacao:
                st.success("🆕 **Sistema com Aprovação de Agendamentos Ativo!**")
            else:
                st.info("ℹ️ Sistema em modo básico. Execute a migração para ativar aprovações.")
        except:
            pass
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.image("https://images.unsplash.com/photo-1522202176988-66273c2fd55f?q=80&w=2071&auto=format&fit=crop", caption="Gestão profissional de recursos")
            
        with col2:
            st.markdown("""
            ### 🚀 Funcionalidades do Sistema:
            
            **👩‍🏫 Para Professores:**
            - 📤 Enviar solicitações de agendamento
            - 👀 Acompanhar status das solicitações
            - 🟡 Ver pendentes | 🟢 Aprovados | 🔴 Rejeitados
            
            **👨‍💼 Para Administradores:**
            - ✅ Aprovar/rejeitar solicitações
            - 📊 Visualizar estatísticas completas
            - 📝 Adicionar observações aos agendamentos
            - 🔍 Filtrar por status e professor
            """)

# --- Lógica Principal ---
def main():
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'username' not in st.session_state:
        st.session_state.username = None

    if not st.session_state.logged_in:
        inicializar_banco()

    if not st.session_state.logged_in:
        tela_login()
    else:
        tipo_usuario = obter_tipo_usuario(st.session_state.username)
        st.sidebar.success(f"👋 **{st.session_state.username}**")
        st.sidebar.info(f"🎭 {tipo_usuario}")
        
        # Notificações na sidebar
        if eh_admin(st.session_state.username):
            try:
                stats = contar_agendamentos_por_status()
                if stats[STATUS_PENDENTE] > 0:
                    st.sidebar.warning(f"⚠️ {stats[STATUS_PENDENTE]} pendente(s)")
            except:
                pass
        
        if st.sidebar.button("🚪 Sair", type="primary"):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.success("✅ Logout realizado!")
            st.rerun()
        
        if eh_admin(st.session_state.username):
            tela_admin()
        else:
            tela_professor()

if __name__ == "__main__":
    main()