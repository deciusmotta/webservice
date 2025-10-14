from flask import Flask, request
from spyne import Application, rpc, ServiceBase, Unicode, Integer, Date, Iterable
from spyne.protocol.soap import Soap11
from spyne.server.wsgi import WsgiApplication
from datetime import datetime, timedelta
import json
import os

app = Flask(__name__)

# --- Estrutura de retorno do Laudo ---
from spyne import ComplexModel

class LaudoResponse(ComplexModel):
    numero_laudo = Unicode
    data_emissao = Unicode
    data_validade = Unicode
    cpf_cnpj_cliente = Unicode
    nome_cliente = Unicode
    quantidade_caixas = Unicode
    modelo_caixas = Unicode


# --- Serviço principal ---
class LaudoService(ServiceBase):

    @rpc(Unicode, Unicode, Unicode, Unicode, Unicode, _returns=LaudoResponse)
    def gerar_laudo(ctx, nome_cliente, cpf_cnpj_cliente, quantidade_caixas, modelo_caixas, numero_laudo):
        """
        Gera um novo laudo e salva no arquivo laudos_gerados.json
        """
        data_emissao = datetime.now().strftime("%d/%m/%Y")
        data_validade = (datetime.now() + timedelta(days=15)).strftime("%d/%m/%Y")

        laudo = {
            "numero_laudo": numero_laudo,
            "data_emissao": data_emissao,
            "data_validade": data_validade,
            "cpf_cnpj_cliente": cpf_cnpj_cliente,
            "nome_cliente": nome_cliente,
            "quantidade_caixas": quantidade_caixas,
            "modelo_caixas": modelo_caixas
        }

        # Caminho do arquivo JSON
        arquivo_json = "laudos_gerados.json"

        # Cria o arquivo se não existir
        if not os.path.exists(arquivo_json):
            with open(arquivo_json, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=4)

        # Lê e adiciona o novo laudo
        with open(arquivo_json, "r", encoding="utf-8") as f:
            dados = json.load(f)

        dados.append(laudo)

        # Grava o novo conteúdo
        with open(arquivo_json, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=4)

        return LaudoResponse(**laudo)


    @rpc(_returns=[LaudoResponse])
    def listar_laudos(ctx):
        """
        Retorna todos os laudos gravados em laudos_gerados.json
        """
        arquivo_json = "laudos_gerados.json"

        if not os.path.exists(arquivo_json):
            return []

        with open(arquivo_json, "r", encoding="utf-8") as f:
            laudos_data = json.load(f)

        laudos = []
        for item in laudos_data:
            laudo = LaudoResponse(
                numero_laudo=item.get("numero_laudo", ""),
                data_emissao=item.get("data_emissao", ""),
                data_validade=item.get("data_validade", ""),
                cpf_cnpj_cliente=item.get("cpf_cnpj_cliente", ""),
                nome_cliente=item.get("nome_cliente", ""),
                quantidade_caixas=item.get("quantidade_caixas", ""),
                modelo_caixas=item.get("modelo_caixas", "")
            )
            laudos.append(laudo)
        return laudos


# --- Configuração SOAP ---
soap_app = Application(
    [LaudoService],
    tns="http://laudoservice.onrender.com/soap",
    in_protocol=Soap11(validator="lxml"),
    out_protocol=Soap11()
)

wsgi_app = WsgiApplication(soap_app)
app.wsgi_app = wsgi_app


# --- Rota de teste simples ---
@app.route("/")
def home():
    return "Serviço SOAP de Laudos ativo e funcional!"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
