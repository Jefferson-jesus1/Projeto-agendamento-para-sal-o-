import datetime
import os
import urllib.parse
import pymysql
import pymysql.cursors
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from datetime import timedelta

app = Flask(__name__)

# ===========================================================
# CONFIGURAÇÕES SEGURAS
# ===========================================================
# Chave secreta para proteger cookies de sessão
app.secret_key = os.getenv("SECRET_KEY", "chave_super_secreta_dev")
# Senha do admin (idealmente armazenada em variáveis de ambiente no servidor)
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "1234")

# Tempo de expiração da sessão: 5 minutos
app.permanent_session_lifetime = timedelta(minutes=5)

# ===========================================================
# LISTA DE SERVIÇOS DISPONÍVEIS
# ===========================================================
SERVICOS = [
    {"id": 1, "nome": "Penteados sociais - Madrinhas", "preco": 70},
    {"id": 2, "nome": "Penteados sociais - Noivas", "preco": 70},
    {"id": 3, "nome": "Penteados sociais - Debutantes", "preco": 70},
    {"id": 4, "nome": "Tranças - Box Braids em geral", "preco": 125},
    {"id": 5, "nome": "Tranças - Nagô", "preco": 30},
    {"id": 6, "nome": "Mega Hair - Queratina", "preco": 450},
    {"id": 8, "nome": "Mega Hair - Micro link (por tela)", "preco": 30},
]

# ===========================================================
# FUNÇÃO DE CONEXÃO COM O BANCO DE DADOS
# ===========================================================
def get_db_connection():
    return pymysql.connect(
        host='localhost',
        user='root',
        password='250506',  # Troque antes de hospedar
        database='salao',
    )

# ===========================================================
# GERAR LISTA DE HORÁRIOS AUTOMATICAMENTE
# ===========================================================
def gerar_horarios(inicio, fim, intervalo_minutos):
    horarios = []
    atual = inicio
    while atual <= fim:
        horarios.append(atual.strftime("%H:%M"))
        atual += datetime.timedelta(minutes=intervalo_minutos)
    return horarios

HORARIOS = gerar_horarios(
    datetime.datetime.strptime("08:30", "%H:%M"),
    datetime.datetime.strptime("18:00", "%H:%M"),
    90
)

# ===========================================================
# ROTA PÁGINA INICIAL
# ===========================================================
@app.route('/')
def home():
    return render_template('index.html')

# ===========================================================
# ROTA DE AGENDAMENTO
# ===========================================================
@app.route('/agendamento')
def agendamento():
    hoje = datetime.date.today().isoformat()
    return render_template('agendamento.html', servicos=SERVICOS, hoje=hoje)

# ===========================================================
# CONSULTAR HORÁRIOS DISPONÍVEIS
# ===========================================================
@app.route('/horarios_disponiveis')
def horarios_disponiveis():
    data = request.args.get('data')
    servico_id = request.args.get('servico_id', type=int)

    if not data or not servico_id:
        return jsonify({"erro": "Data e serviço são obrigatórios"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT horario FROM agendamentos WHERE datas=%s", (data,))
    horarios_ocupados = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()

    horarios_livres = [h for h in HORARIOS if h not in horarios_ocupados]
    return jsonify({"horarios": horarios_livres})

# ===========================================================
# ROTA PARA CRIAR NOVO AGENDAMENTO
# ===========================================================
@app.route('/agendar', methods=['POST'])
def agendar():
    data = request.form.get('data')
    horario = request.form.get('horario')
    servico_id_str = request.form.get('servico_id')
    cliente = request.form.get('cliente')
    telefone = request.form.get('telefone')

    # Verifica se todos os campos foram preenchidos
    if not all([data, horario, servico_id_str, cliente, telefone]):
        return "Dados incompletos", 400

    try:
        servico_id = int(servico_id_str)
    except ValueError:
        return "Serviço inválido", 400

    # Verifica se o horário já está ocupado
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM agendamentos WHERE datas=%s AND horario=%s",
        (data, horario)
    )
    if cursor.fetchone()[0] > 0:
        cursor.close()
        conn.close()
        return "Horário já agendado!", 400

    # Insere o novo agendamento
    cursor.execute(
        "INSERT INTO agendamentos (servico_id, datas, horario, cliente, telefone) VALUES (%s, %s, %s, %s, %s)",
        (servico_id, data, horario, cliente, telefone)
    )
    conn.commit()
    cursor.close()
    conn.close()

    # Gera mensagem de confirmação no WhatsApp
    servico_nome = next((s['nome'] for s in SERVICOS if s['id'] == servico_id), "Serviço")
    mensagem = (
        f"Olá, {cliente}! Seu agendamento para *{servico_nome}* "
        f"foi confirmado para o dia {data} às {horario}.\n"
        "Obrigado por escolher nosso serviço!"
    )
    mensagem_url = urllib.parse.quote(mensagem)
    numero_whatsapp = "55" + telefone
    link_whatsapp = f"https://api.whatsapp.com/send?phone={numero_whatsapp}&text={mensagem_url}"

    return render_template('sucesso.html', link_whatsapp=link_whatsapp)

# ===========================================================
# ROTA PÁGINA DE CONTATO
# ===========================================================
@app.route('/contato')
def contato():
    return render_template('contato.html')

# ===========================================================
# LOGIN DO ADMIN
# ===========================================================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        senha = request.form['senha']
        if senha == ADMIN_PASSWORD:
            session.permanent = True  # Sessão respeita o tempo definido em permanent_session_lifetime
            session['logado'] = True
            return redirect(url_for('admin'))
        else:
            return "Senha incorreta!"
    return '''
        <form method="post">
            <input type="password" name="senha" placeholder="Digite a senha">
            <button type="submit">Entrar</button>
        </form>
    '''

# ===========================================================
# LOGOUT DO ADMIN
# ===========================================================
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ===========================================================
# PÁGINA ADMIN (PROTEGIDA)
# ===========================================================
@app.route('/admin')
def admin():
    # Se a sessão não estiver ativa, redireciona para o login
    if not session.get('logado'):
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    # Remove agendamentos antigos
    hoje = datetime.date.today()
    cursor.execute("DELETE FROM agendamentos WHERE datas < %s", (hoje,))
    conn.commit()

    # Busca agendamentos futuros
    cursor.execute("SELECT * FROM agendamentos ORDER BY datas, horario")
    agendamentos = cursor.fetchall()
    conn.close()

    # Converte ID de serviço para nome amigável
    servico_dict = {s["id"]: s["nome"] for s in SERVICOS}
    for ag in agendamentos:
        ag["servico"] = servico_dict.get(ag["servico_id"], "Serviço desconhecido")

    return render_template('admin.html', agendamentos=agendamentos)

# ===========================================================
# REMOVER AGENDAMENTO (SOMENTE LOGADO)
# ===========================================================
@app.route('/admin/remover/<int:id>', methods=['POST'])
def admin_remover(id):
    if not session.get('logado'):
        return jsonify({"status": "erro", "mensagem": "Acesso negado"}), 403

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM agendamentos WHERE id = %s", (id,))
    conn.commit()
    conn.close()

    return jsonify({"status": "sucesso"})

# ===========================================================
# EXECUÇÃO DO APP
# ===========================================================
if __name__ == '__main__':
    app.run(debug=True)
