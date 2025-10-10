from flask import Flask, request, Response
from spyne import Application, rpc, ServiceBase, Unicode, Integer
from spyne.protocol.soap import Soap11
from spyne.server.wsgi import WsgiApplication
import logging

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

# --- Serviço SOAP ---
class LaudoService(ServiceBase):
    @rpc(Integer, _returns=Unicode)
    def gerar_laudo(ctx, numero):
        """
        Gera um laudo cujo identificador completo começa com 017
        """
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


@app.route("/soap", methods=['GET', 'POST'])
def soap_server():
    """Rota principal para requisições SOAP"""
    response = Response()
    response.headers["Content-Type"] = "text/xml; charset=utf-8"
    response.data = wsgi_app(request.environ, response.start_response)
    return response


@app.route("/soap?wsdl", methods=['GET', 'POST'])
def wsdl():
    """Gera e retorna o WSDL dinamicamente"""
    wsdl_content = soap_app.get_interface_document('wsdl')
    return Response(wsdl_content, mimetype='text/xml')


@app.route("/")
def home():
    return "LaudoService SOAP ativo em /soap e WSDL em /soap?wsdl"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
