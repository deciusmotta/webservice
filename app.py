from datetime import datetime, timedelta
import sqlite3
import os
from flask import Flask, request, Response
from spyne import Application, rpc, ServiceBase, Unicode, Integer
from spyne.protocol.soap import Soap11
from spyne.server.wsgi import WsgiApplication

DB = 'laudos.db'
HIGIENIZADOR_PREFIX = "017"  # agora começa com 017 (BDF)
VALIDADE_DIAS = 15

def init_db():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute('''
    CREATE TABLE IF NOT EXISTS laudos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero_completo TEXT UNIQUE,
        data_emissao TEXT,
        data_validade TEXT,
        cpf_cnpj TEXT,
        nome_cliente TEXT,
        quantidade_caixas INTEGER,
        modelo_caixas TEXT,
        caixas_usadas INTEGER DEFAULT 0
    )''')
    conn.commit()
    conn.close()

def next_sequential_number():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT IFNULL(MAX(id),0) FROM laudos")
    maxid = cur.fetchone()[0]
    conn.close()
    return maxid + 1

def build_numero_completo():
    seq = next_sequential_number()
    seq_str = str(seq).zfill(9)
    return f"{HIGIENIZADOR_PREFIX}{seq_str}"

def insert_laudo(data_emissao, cpf_cnpj, nome_cliente, quantidade_caixas, modelo_caixas):
    numero = build_numero_completo()
    data_val = (datetime.fromisoformat(data_emissao) + timedelta(days=VALIDADE_DIAS)).isoformat()
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute('''
      INSERT INTO laudos (numero_completo, data_emissao, data_validade, cpf_cnpj, nome_cliente, quantidade_caixas, modelo_caixas)
      VALUES (?,?,?,?,?,?,?)
    ''', (numero, data_emissao, data_val, cpf_cnpj, nome_cliente, quantidade_caixas, modelo_caixas))
    conn.commit()
    conn.close()
    return numero, data_val

def get_laudo_by_numero(numero):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute('''
      SELECT numero_completo, data_emissao, data_validade, cpf_cnpj, nome_cliente, quantidade_caixas, modelo_caixas, caixas_usadas
      FROM laudos WHERE numero_completo = ?
    ''', (numero,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "numero_completo": row[0],
        "data_emissao": row[1],
        "data_validade": row[2],
        "cpf_cnpj": row[3],
        "nome_cliente": row[4],
        "quantidade_caixas": row[5],
        "modelo_caixas": row[6],
        "caixas_usadas": row[7]
    }

def increment_passagem(numero, quantidade=1):
    laudo = get_laudo_by_numero(numero)
    if laudo is None:
        return False, "Laudo não encontrado"
    new_used = laudo["caixas_usadas"] + quantidade
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("UPDATE laudos SET caixas_usadas = ? WHERE numero_completo = ?", (new_used, numero))
    conn.commit()
    conn.close()
    return True, new_used

def is_vencido(laudo):
    data_validade = datetime.fromisoformat(laudo["data_validade"])
    if datetime.now() > data_validade:
        return True, "Vencido por data"
    if laudo["caixas_usadas"] >= laudo["quantidade_caixas"]:
        return True, "Vencido por quantidade"
    return False, "Válido"

class LaudoService(ServiceBase):

    @rpc(Unicode, Unicode, Unicode, Integer, Unicode, _returns=Unicode)
    def criar_laudo(ctx, data_emissao_iso, cpf_cnpj, nome_cliente, quantidade_caixas, modelo_caixas):
        numero, data_validade = insert_laudo(data_emissao_iso, cpf_cnpj, nome_cliente, quantidade_caixas, modelo_caixas)
        return f"""<Laudo>
  <NumeroCompleto>{numero}</NumeroCompleto>
  <DataEmissao>{data_emissao_iso}</DataEmissao>
  <DataValidade>{data_validade}</DataValidade>
</Laudo>"""

    @rpc(Unicode, _returns=Unicode)
    def obter_laudo(ctx, numero_completo):
        laudo = get_laudo_by_numero(numero_completo)
        if laudo is None:
            return "<Error>Laudo não encontrado</Error>"
        venc, motivo = is_vencido(laudo)
        return f"""<Laudo>
  <NumeroCompleto>{laudo['numero_completo']}</NumeroCompleto>
  <DataEmissao>{laudo['data_emissao']}</DataEmissao>
  <DataValidade>{laudo['data_validade']}</DataValidade>
  <CPF_CNPJ>{laudo['cpf_cnpj']}</CPF_CNPJ>
  <NomeCliente>{laudo['nome_cliente']}</NomeCliente>
  <QuantidadeCaixas>{laudo['quantidade_caixas']}</QuantidadeCaixas>
  <ModeloCaixas>{laudo['modelo_caixas']}</ModeloCaixas>
  <CaixasUsadas>{laudo['caixas_usadas']}</CaixasUsadas>
  <SituacaoVencimento>{'Vencido' if venc else 'Válido'}</SituacaoVencimento>
  <MotivoVencimento>{motivo}</MotivoVencimento>
</Laudo>"""

    @rpc(Unicode, Integer, _returns=Unicode)
    def registrar_passagem(ctx, numero_completo, quantidade):
        ok, res = increment_passagem(numero_completo, quantidade)
        if not ok:
            return f"<Error>{res}</Error>"
        laudo = get_laudo_by_numero(numero_completo)
        venc, motivo = is_vencido(laudo)
        return f"<Result><CaixasUsadas>{res}</CaixasUsadas><Vencido>{'true' if venc else 'false'}</Vencido><Motivo>{motivo}</Motivo></Result>"""

app = Flask(__name__)

@app.route('/health')
def health():
    return "ok"

soap_app = Application([LaudoService], 'bdf.laudos.soap',
                       in_protocol=Soap11(validator='lxml'),
                       out_protocol=Soap11())
wsgi_app = WsgiApplication(soap_app)

@app.route('/soap/LaudoService', methods=['POST', 'GET'])
def soap_service():
    # Integrar corretamente o Spyne (WSGI) dentro do Flask
    def start_response(status, response_headers, exc_info=None):
        nonlocal_response = []

        def _write(data):
            nonlocal_response.append(data)
        return _write

    environ = request.environ
    response_data = []

    def _start_response(status, headers, exc_info=None):
        response_data.append((status, headers))
        def write(data):
            response_data.append(data)
        return write

    result = wsgi_app(environ, _start_response)
    status, headers = response_data[0]
    response_body = b"".join(result)
    return Response(response_body, status=int(status.split(" ")[0]), headers=dict(headers), mimetype="text/xml")

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
