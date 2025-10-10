from flask import Flask, request, Response
from spyne import Application, rpc, ServiceBase, Unicode, Integer
from spyne.protocol.soap import Soap11
from spyne.server.wsgi import WsgiApplication
import logging
import os

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

# --- Serviço SOAP ---
class LaudoService(ServiceBase):
    @rpc(Integer, _returns=Unicode)
    def gerar_laudo(ctx, numero):
        return f"017-{numero:06d}"

# --- Configuração do Spyne ---
soap_app = Application(
    [LaudoService],
    tns='http://laudoservice.onrender.com/soap',
    name='LaudoService',
    in_protocol=Soap11(validator='lxml'),
    out_protocol=Soap11()
)

wsgi_app = WsgiApplication(soap_app)

# --- Rota principal SOAP (GET/POST) ---
@app.route("/soap", methods=['GET', 'POST'])
def soap_server():
    response = Response()
    response.headers["Content-Type"] = "text/xml; charset=utf-8"
    response.data = b"".join(wsgi_app(request.environ, response.start_response))
    return response

# --- Página inicial ---
@app.route("/")
def home():
    return "LaudoService SOAP ativo em /soap e WSDL em /soap?wsdl"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
