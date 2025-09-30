from datetime import datetime, timedelta
import sqlite3
import os
from flask import Flask, request, Response
from spyne import Application, rpc, ServiceBase, Unicode, Integer, DateTime
from spyne.protocol.soap import Soap11
from spyne.server.wsgi import WsgiApplication

# Configuração do banco
DB = "laudos.db"
HIGIENIZADOR_PREFIX = "017"  # agora começa com 017 (BDF Comércio e Reciclagem LTDA)

# Inicializa app Flask
app = Flask(__name__)

# Criação da tabela no banco
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

# Serviço SOAP
class LaudoService(ServiceBase):

    @rpc(Unicode, Unicode, Integer, Unicode, _returns=Unicode)
    def emitir_laudo(ctx, cpf_cnpj, nome_cliente, quantidade, modelo):
        """Emite um novo laudo seguindo as regras de negócio"""
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

    @rpc(Unicode, _returns=Unicode)
    def consultar_laudo(ctx, numero_completo):
        """Consulta um laudo existente pelo número completo"""
        with sqlite3.connect(DB) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM laudos WHERE numero_completo=?",
                           (numero_completo,))
            laudo = cursor.fetchone()

            if not laudo:
                return "Laudo não encontrado."

            # Monta XML de retorno
            return f"""
<Laudo>
  <NumeroCompleto>{laudo[1]}</NumeroCompleto>
  <DataEmissao>{laudo[2]}</DataEmissao>
  <DataValidade>{laudo[3]}</DataValidade>
  <CPFCNPJ>{laudo[4]}</CPFCNPJ>
  <NomeCliente>{laudo[5]}</NomeCliente>
  <Quantidade>{laudo[6]}</Quantidade>
  <Modelo>{laudo[7]}</Modelo>
</Laudo>
"""

# Aplicação SOAP
soap_app = Application(
    [LaudoService],
    tns="laudoservice",
    in_protocol=Soap11(validator="lxml"),
    out_protocol=Soap11()
)
wsgi_app = WsgiApplication(soap_app)

# Endpoint Flask
@app.route("/soap/LaudoService", methods=["GET", "POST"])
def soap_service():
    if request.method == "GET":
        # Retorna WSDL
        wsdl = soap_app.get_interface("wsdl")
        return Response(wsdl, mimetype="text/xml")
    else:
        # Processa requisições SOAP
        return Response(wsgi_app(request.environ, lambda s, h: None),
                        mimetype="text/xml")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
