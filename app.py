from flask import Flask, request, Response
from spyne import Application, rpc, ServiceBase, Unicode, Integer, Date, ComplexModel
from spyne.protocol.soap import Soap11
from spyne.server.wsgi import WsgiApplication
from io import BytesIO
import logging
import os
from datetime import timedelta

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

# --- Modelo de retorno ---
class LaudoResponse(ComplexModel):
    numero_laudo = Unicode
    data_emissao = Date
    data_validade = Date
    cpf_cnpj_cliente = Unicode
    nome_cliente = Unicode
    quantidade_caixas = Integer
    modelo_caixas = Unicode

# --- Serviço SOAP ---
class LaudoService(ServiceBase):
    @rpc(Integer, Date, _returns=LaudoResponse)
    def gerar_laudo(ctx, numero, data_emissao):
        """Gera um laudo a partir do número e da Data de Emissão"""
        # Número do laudo formatado
        numero_formatado = f"017{numero:06d}"

        # Data de validade (30 dias após emissão, por exemplo)
        data_validade = data_emissao + timedelta(days=30)

        # Exemplo de dados fictícios
        cpf_cnpj_cliente = "123.456.789-00"
        nome_cliente = "João da Silva"
        quantidade_caixas = 50
        modelo_caixas = "Modelo X"

        return LaudoResponse(
            numero_laudo=numero_formatado,
            data_emissao=data_emissao,
            data_validade=data_validade,
            cpf_cnpj_cliente=cpf_cnpj_cliente,
            nome_cliente=nome_cliente,
            quantidade_caixas=quantidade_caixas,
            modelo_caixas=modelo_caixas
        )

# --- Configuração do Spyne ---
soap_app = Application(
    [LaudoService],
    tns='http://laudoservice.onrender.com/soap',
    name='LaudoService',
    in_protocol=Soap11(validator='lxml'),
    out_protocol=Soap11()
)

wsgi_app = WsgiApplication(soap_app)

# --- Rota SOAP ---
@app.route("/soap", methods=['GET', 'POST'])
def soap_server():
    buf = BytesIO()

    def start_response(status, headers):
        buf.status = status
        buf.headers = headers
        return buf.write

    result = wsgi_app(request.environ, start_response)
    response_data = b"".join(result)
    return Response(response_data, mimetype="text/xml; charset=utf-8")

# --- Página inicial ---
@app.route("/")
def home():
    return "LaudoService SOAP ativo em /soap e WSDL em /soap?wsdl"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
