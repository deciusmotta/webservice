from flask import Flask, request
from spyne import Application, rpc, ServiceBase, Unicode, Integer, Date, Iterable
from spyne.protocol.soap import Soap11
from spyne.server.wsgi import WsgiApplication
import datetime

# --- Classe do WebService ---
class Iwbsfunctions_017(ServiceBase):

    @rpc(Unicode, Unicode, Unicode, Date, Unicode, _returns=Iterable(Unicode))
    def EmitirLaudo(ctx, CNPJEmpresa, NumeroLaudo, NomeCliente, DataExecucao, Observacoes):
        """
        Gera laudo técnico com prefixo 017 (Organizações Salomão Martins Ltda)
        Retorna número completo do laudo no formato 017-XXXXXX
        """
        prefixo = "017"
        numero_completo = f"{prefixo}-{NumeroLaudo}"
        mensagem = f"Laudo emitido com sucesso para {NomeCliente} em {DataExecucao}."
        codigo_retorno = "0"

        yield f"CodigoRetorno={codigo_retorno}"
        yield f"MensagemRetorno={mensagem}"
        yield f"NumeroLaudoCompleto={numero_completo}"

# --- Inicialização do Flask ---
app = Flask(__name__)

soap_app = Application(
    [Iwbsfunctions_017],
    tns='http://laudoservice.onrender.com/wsdl/Iwbsfunctions_017',
    in_protocol=Soap11(validator='lxml'),
    out_protocol=Soap11()
)

wsgi_app = WsgiApplication(soap_app)

@app.route('/soap', methods=['POST', 'GET'])
def soap_service():
    if request.method == 'GET':
        # Exibir WSDL
        return app.response_class(
            soap_app.wsdl11.string,
            content_type='text/xml'
        )
    elif request.method == 'POST':
        return wsgi_app(request.environ, start_response=lambda status, headers: None)

@app.route('/')
def home():
    return "<h2>🧾 LaudoService SOAP ativo</h2><p>Endpoint: /soap</p><p>WSDL: /soap?wsdl</p>"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
