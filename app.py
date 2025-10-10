from flask import Flask, request
from spyne import Application, rpc, ServiceBase, Unicode, Date, Iterable
from spyne.protocol.soap import Soap11
from spyne.server.wsgi import WsgiApplication
from io import BytesIO

class Iwbsfunctions_017(ServiceBase):
    @rpc(Unicode, Unicode, Unicode, Date, Unicode, _returns=Iterable(Unicode))
    def EmitirLaudo(ctx, CNPJEmpresa, NumeroLaudo, NomeCliente, DataExecucao, Observacoes):
        prefixo = "017"
        numero_completo = f"{prefixo}-{NumeroLaudo}"
        mensagem = f"Laudo emitido com sucesso para {NomeCliente} em {DataExecucao}."
        codigo_retorno = "0"
        yield f"CodigoRetorno={codigo_retorno}"
        yield f"MensagemRetorno={mensagem}"
        yield f"NumeroLaudoCompleto={numero_completo}"

app = Flask(__name__)

soap_app = Application(
    [Iwbsfunctions_017],
    tns='http://laudoservice.onrender.com/wsdl/Iwbsfunctions_017',
    in_protocol=Soap11(validator='lxml'),
    out_protocol=Soap11()
)

wsgi_app = WsgiApplication(soap_app)

@app.route('/soap', methods=['GET', 'POST'])
def soap_service():
    if request.method == 'GET':
        wsdl_xml = soap_app.wsdl11.build_interface_document('https://laudoservice.onrender.com/soap')
        return app.response_class(wsdl_xml, content_type='text/xml; charset=utf-8')
    elif request.method == 'POST':
        response = BytesIO()
        wsgi_app(request.environ, response.write)
        return app.response_class(response.getvalue(), content_type='text/xml; charset=utf-8')

@app.route('/')
def home():
    return "<h2>🧾 LaudoService SOAP ativo</h2><p>Endpoint: /soap</p><p>WSDL: /soap?wsdl</p>"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
