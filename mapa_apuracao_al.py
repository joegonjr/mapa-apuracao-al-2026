"""Cria um retrato verificável da apuração de governador em AL (TSE, 2026)."""

from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
import csv
import gzip
import json
import time
import urllib.request


PASTA = Path(__file__).resolve().parent
BASE = "https://resultados.tse.jus.br/oficial"
IBGE = "https://servicodados.ibge.gov.br/api/v3/malhas/estados/27?formato=application/vnd.geo+json&qualidade=minima&intrarregiao=municipio"
PLEITO = "3220"
ELEICAO = "6259"


def obter_json(url):
    ultimo_erro = None
    for tentativa in range(3):
        try:
            requisicao = urllib.request.Request(url, headers={"User-Agent": "Mapa-Apuracao-AL/1.0", "Accept": "application/json, application/vnd.geo+json"})
            with urllib.request.urlopen(requisicao, timeout=30) as resposta:
                bruto = resposta.read()
                if resposta.headers.get("Content-Encoding", "").lower() == "gzip" or bruto.startswith(b"\x1f\x8b"):
                    bruto = gzip.decompress(bruto)
                return json.loads(bruto)
        except Exception as erro:
            ultimo_erro = erro
            if tentativa < 2:
                time.sleep(0.7 * (tentativa + 1))
    raise RuntimeError(f"Falha ao acessar {url}: {ultimo_erro}")


def endereco_arquivo(tipo, municipio=None, zona=None, secao=None):
    prefixo = f"{BASE}/ele2026"
    if tipo == "acompanhamento":
        return f"{prefixo}/{ELEICAO}/dados/al/al-e{int(ELEICAO):06d}-ab.json"
    if tipo == "municipios":
        return f"{prefixo}/{ELEICAO}/config/mun-e{int(ELEICAO):06d}-cm.json"
    if tipo == "secoes":
        return f"{prefixo}/arquivo-urna/{PLEITO}/config/al/al-p{int(PLEITO):06d}-cs.json"
    if tipo == "resultado":
        codigo = f"al{municipio}" if municipio else "al"
        return f"{prefixo}/{ELEICAO}/dados/al/{codigo}-c0003-e{int(ELEICAO):06d}-u.json"
    raise ValueError(tipo)


def extrair_votos(dados):
    cargos = [cargo for cargo in dados["carg"] if str(cargo["cd"]) == "3"]
    assert len(cargos) == 1, (dados["cdabr"], "cargo governador")
    votos = {}
    nomes = {}
    for agrupamento in cargos[0].get("agr", []):
        for partido in agrupamento.get("par", []):
            for candidato in partido.get("cand", []):
                numero = str(candidato["n"])
                assert numero not in votos, (dados["cdabr"], numero)
                votos[numero] = int(candidato["vap"])
                nomes[numero] = candidato["nmu"]
    total_validos = int(dados["v"]["vv"])
    assert sum(votos.values()) == total_validos, (dados["cdabr"], "votos válidos")
    return votos, nomes


def projetar_malha(geojson):
    # Projeção simples adequada para o mapa local de AL, com geometria IBGE.
    coordenadas = []
    for feicao in geojson["features"]:
        poligonos = feicao["geometry"]["coordinates"]
        if feicao["geometry"]["type"] == "Polygon":
            poligonos = [poligonos]
        for poligono in poligonos:
            for anel in poligono:
                coordenadas.extend(anel)
    xmin = min(x for x, _ in coordenadas)
    xmax = max(x for x, _ in coordenadas)
    ymin = min(y for _, y in coordenadas)
    ymax = max(y for _, y in coordenadas)
    escala = min(900 / (xmax - xmin), 590 / (ymax - ymin))
    margem_x = (940 - (xmax - xmin) * escala) / 2
    margem_y = (650 - (ymax - ymin) * escala) / 2

    def ponto(par):
        x, y = par
        return f"{margem_x + (x - xmin) * escala:.2f},{margem_y + (ymax - y) * escala:.2f}"

    saida = {}
    for feicao in geojson["features"]:
        poligonos = feicao["geometry"]["coordinates"]
        if feicao["geometry"]["type"] == "Polygon":
            poligonos = [poligonos]
        partes = []
        for poligono in poligonos:
            for anel in poligono:
                partes.append("M" + " L".join(ponto(par) for par in anel) + " Z")
        saida[str(feicao["properties"]["codarea"])] = " ".join(partes)
    return saida


def escrever_csv(registros, arquivo, campos):
    with (PASTA / arquivo).open("w", encoding="utf-8-sig", newline="") as destino:
        escritor = csv.DictWriter(destino, fieldnames=campos, delimiter=";", extrasaction="ignore")
        escritor.writeheader()
        escritor.writerows(registros)


def formatar_percentual(votos, total):
    return f"{100 * votos / total:.2f}%".replace(".", ",") if total else ""


def main():
    inicio = datetime.now().astimezone().isoformat(timespec="seconds")
    urls = {"acompanhamento": endereco_arquivo("acompanhamento"),
            "municipios": endereco_arquivo("municipios"),
            "secoes": endereco_arquivo("secoes"),
            "estadual": endereco_arquivo("resultado"), "malha": IBGE}
    with ThreadPoolExecutor(max_workers=5) as executor:
        futuros = {executor.submit(obter_json, url): nome for nome, url in urls.items()}
        bases = {futuros[futuro]: futuro.result() for futuro in as_completed(futuros)}
    assert all(bases[k].get("f", "o").lower() == "o" for k in ("acompanhamento", "municipios", "secoes", "estadual"))
    acompanhamento = bases["acompanhamento"]
    municipios_config = next(x for x in bases["municipios"]["abr"] if x["cd"] == "al")["mu"]
    secoes_config = bases["secoes"]["abr"][0]["mu"]
    codigos = {m["cd"] for m in municipios_config}
    assert len(codigos) == len(municipios_config) == 102
    assert {x["cdabr"] for x in acompanhamento["abr"] if x["tpabr"] == "mun"} == codigos

    resultados = {}
    with ThreadPoolExecutor(max_workers=8) as executor:
        futuros = {executor.submit(obter_json, endereco_arquivo("resultado", m)): m for m in codigos}
        for futuro in as_completed(futuros):
            resultados[futuros[futuro]] = futuro.result()
    print(f"Resultados municipais obtidos: {len(resultados)}")

    linhas_secao = []
    for municipio in secoes_config:
        for zona in municipio["zon"]:
            for secao in zona["sec"]:
                if "nsp" in secao:
                    continue  # Agregada: sua votação está na seção principal.
                registro = {"codigo_tse": municipio["cd"], "municipio": municipio["nm"],
                            "zona": zona["cd"], "secao": secao["ns"],
                            "agregadas": ", ".join(secao.get("nsa", [])),
                            "arquivo_recebido": "sim" if secao.get("da") else "não",
                            "data_recebimento": secao.get("da", ""),
                            "hora_recebimento": secao.get("ha", "")}
                linhas_secao.append(registro)
    assert len(linhas_secao) == sum(int(x["s"]["ts"]) for x in acompanhamento["abr"] if x["tpabr"] == "mun")
    print(f"Seções principais: {len(linhas_secao)}; arquivos recebidos: {sum(r['arquivo_recebido'] == 'sim' for r in linhas_secao)}")

    nomes = {m["cd"]: m for m in municipios_config}
    secoes_por_municipio = defaultdict(list)
    for secao in linhas_secao:
        secoes_por_municipio[secao["codigo_tse"]].append(secao)
    resumo_tse = {m["cdabr"]: m for m in acompanhamento["abr"] if m["tpabr"] == "mun"}
    municipais = []
    candidatos_estaduais, nomes_candidatos = extrair_votos(bases["estadual"])
    for codigo in sorted(codigos, key=lambda c: nomes[c]["nm"]):
        municipio = nomes[codigo]
        resultado = resultados[codigo]
        resumo = resumo_tse[codigo]
        lista = secoes_por_municipio[codigo]
        votos, nomes_locais = extrair_votos(resultado)
        assert all(nomes_candidatos.get(n, nome) == nome for n, nome in nomes_locais.items())
        total = int(resumo["s"]["ts"])
        apuradas = int(resumo["s"]["st"])
        pendentes = int(resumo["s"]["snt"])
        assert total == len(lista) == apuradas + pendentes
        com_arquivo = sum(r["arquivo_recebido"] == "sim" for r in lista)
        municipais.append({"codigo_tse": codigo, "codigo_ibge": municipio["cdi"],
                           "municipio": municipio["nm"], "secoes_total": total,
                           "secoes_totalizadas": apuradas, "secoes_pendentes": pendentes,
                           "secoes_com_arquivo_recebido": com_arquivo,
                           "secoes_sem_arquivo_recebido": total - com_arquivo,
                           "secoes_no_arquivo_de_votos": int(resultado["s"]["st"]),
                           "data_resultado": resultado.get("dg", ""),
                           "hora_resultado": resultado.get("hg", ""),
                           "votos_total": int(resultado["v"]["tv"]),
                           "votos_validos": int(resultado["v"]["vv"]),
                           "votos_brancos": int(resultado["v"]["vb"]),
                           "votos_nulos": int(resultado["v"]["vn"]),
                           "votos_por_candidato": votos,
                           "secoes": sorted(lista, key=lambda r: (r["zona"], r["secao"]))})
        if int(resultado["s"]["ts"]) != total:
            raise AssertionError((codigo, "total de seções EA15/EA20"))

    estadual = bases["estadual"]
    print("AL EA20", estadual["dg"], estadual["hg"], estadual["s"]["ts"], estadual["s"]["st"], estadual["s"]["snt"])
    print("EA15", acompanhamento["dg"], acompanhamento["hg"])
    print("EA16", bases["secoes"]["dg"], bases["secoes"]["hg"])

    dados = {"captura_inicio": inicio, "captura_fim": datetime.now().astimezone().isoformat(timespec="seconds"),
             "geracao_acompanhamento": f"{acompanhamento['dg']} {acompanhamento['hg']}",
             "geracao_secoes": f"{bases['secoes']['dg']} {bases['secoes']['hg']}",
             "geracao_estadual": f"{estadual['dg']} {estadual['hg']}",
             "estadual": {"total": int(next(x for x in acompanhamento["abr"] if x["tpabr"] == "uf")["s"]["ts"]),
                          "totalizadas": int(next(x for x in acompanhamento["abr"] if x["tpabr"] == "uf")["s"]["st"]),
                          "pendentes": int(next(x for x in acompanhamento["abr"] if x["tpabr"] == "uf")["s"]["snt"]),
                          "secoes_no_arquivo_de_votos": int(estadual["s"]["st"]),
                          "votos_por_candidato": candidatos_estaduais,
                          "votos_total": int(estadual["v"]["tv"]),
                          "votos_validos": int(estadual["v"]["vv"]),
                          "votos_brancos": int(estadual["v"]["vb"]),
                          "votos_nulos": int(estadual["v"]["vn"])},
             "candidatos": [{"numero": n, "nome": nomes_candidatos[n]} for n in sorted(nomes_candidatos, key=int)],
             "municipios": municipais, "fontes": urls,
             "malha_svg": projetar_malha(bases["malha"])}
    (PASTA / "dados_apuracao_al_2026.json").write_text(json.dumps(dados, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    escrever_csv([{k: r[k] for k in ("codigo_tse", "municipio", "secoes_total", "secoes_totalizadas", "secoes_pendentes", "secoes_com_arquivo_recebido", "secoes_sem_arquivo_recebido", "secoes_no_arquivo_de_votos", "data_resultado", "hora_resultado", "votos_total", "votos_validos", "votos_brancos", "votos_nulos")} for r in municipais],
                 "apuracao_municipios_al_2026.csv",
                 ["codigo_tse", "municipio", "secoes_total", "secoes_totalizadas", "secoes_pendentes", "secoes_com_arquivo_recebido", "secoes_sem_arquivo_recebido", "secoes_no_arquivo_de_votos", "data_resultado", "hora_resultado", "votos_total", "votos_validos", "votos_brancos", "votos_nulos"])
    escrever_csv(linhas_secao, "recebimento_secoes_al_2026.csv", ["codigo_tse", "municipio", "zona", "secao", "agregadas", "arquivo_recebido", "data_recebimento", "hora_recebimento"])
    votos_csv = []
    for municipio in municipais:
        for candidato in dados["candidatos"]:
            votos_candidato = municipio["votos_por_candidato"].get(candidato["numero"], 0)
            votos_csv.append({"codigo_tse": municipio["codigo_tse"], "municipio": municipio["municipio"],
                              "numero": candidato["numero"], "candidato": candidato["nome"],
                              "votos": votos_candidato,
                              "percentual_total_apurado": formatar_percentual(votos_candidato, municipio["votos_total"]),
                              "percentual_votos_validos": formatar_percentual(votos_candidato, municipio["votos_validos"]),
                              "votos_total": municipio["votos_total"],
                              "votos_validos": municipio["votos_validos"],
                              "secoes_no_arquivo_de_votos": municipio["secoes_no_arquivo_de_votos"],
                              "secoes_total": municipio["secoes_total"]})
    escrever_csv(votos_csv, "votos_governador_municipios_al_2026.csv",
                 ["codigo_tse", "municipio", "numero", "candidato", "votos", "percentual_total_apurado", "percentual_votos_validos", "votos_total", "votos_validos", "secoes_no_arquivo_de_votos", "secoes_total"])
    html = (PASTA / "mapa_apuracao_al_2026_template.html").read_text(encoding="utf-8")
    html = html.replace("/*DADOS_JSON*/", json.dumps(dados, ensure_ascii=False).replace("</", "<\\/"))
    (PASTA / "mapa_apuracao_al_2026.html").write_text(html, encoding="utf-8")
    print("Arquivos gravados na pasta", PASTA)


if __name__ == "__main__":
    main()
