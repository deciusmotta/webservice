from datetime import datetime, timedelta
import sqlite3
import os
from flask import Flask, request, Response
from spyne import Application, rpc, ServiceBase, Unicode, Integer
from spyne.protocol.soap import Soap11
from spyne.server.wsgi import WsgiApplication

DB = "laudos.db"
HIGIENIZADOR_PREFIX = "017"

app = Flask(__name__)

def init_db():
    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS laudos (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            numero_completo TEXT UNIQUE,
                            data_emissao TEXT,
                            data_validade TEXT,
                            cpf_cnpj TEXT,
                            nome_cliente TEXT,
                            quantidade INTEGER,
                            modelo TEXT
                          )''')
        conn.commit()

init_db()

class LaudoService(ServiceBase):

    @rpc(Unicode, Unicode, Integer, Unicode, _returns=Unicode)
    def emitir_laudo(ctx, cpf_cnpj, nome_cliente, quantidade, modelo):
        with sqlite3.connect(DB) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM laudos")
            count = cursor.fetchone()[0]
            numero_completo = f"{HIGIENIZADOR_PREFIX}{count+1:06d}"
            data_emissao = datetime.now()
            data_validade = data_emissao + timedelta(days=15)

            cursor.execute('''INSERT INTO laudos
                            (numero_completo, data_emissao, data_validade,
                             cpf_cnpj, nome_cliente, quantidade, modelo)
                             VALUES (?, ?, ?, ?, ?, ?, ?)''',
                           (numero_completo,
                            data_emissao.strftime("%Y-%m-%d %H:%M:%S"),
                            data_validade.strftime("%Y-%m-%d %H:%M:%S"),
                            cpf_cnpj, nome_cliente, quantidade, modelo))
            conn.commit()

        return f"Laudo emitido com sucesso! Nº {numero_completo}"

soap_app = Application([LaudoService], tns="laudoservice",
                       in_protocol=Soap11(validator="lxml"),
                       out_protocol=Soap11())
wsgi_app = WsgiApplication(soap_app)

@app.route("/soap/LaudoService", methods=["POST"])
def soap_service():
    # WsgiApplication espera start_response padrão
    def start_response(status, response_headers, exc_info=None):
        response = Response(status=int(status.split()[0]),
                            headers=dict(response_headers))
        return response

    # Chamar WsgiApplication passando o ambiente WSGI do Flask
    response = wsgi_app(request.environ, lambda status, headers, exc_info=None: None)
    # Retornar bytes
    return Response(b"".join(response), mimetype="text/xml")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
