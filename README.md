# Mapa acadêmico da apuração — Alagoas, 2026

Material independente para fins acadêmicos, com visualização municipal dos dados públicos de apuração para governador de Alagoas no primeiro turno de 2026. Não possui vínculo institucional com o TSE ou com o IBGE.

## Funcionalidades

- Mapa do percentual de seções totalizadas e consulta por município.
- Comparação de dois candidatos em votos e pontos percentuais dos votos válidos.
- Municípios em que cada selecionado está à frente do outro e soma dos saldos positivos.
- Dados de recebimento dos arquivos de urna e exportações CSV/JSON para conferência.

## Metodologia e limites

A diferença é calculada como votos do candidato 1 menos votos do candidato 2. A diferença em pontos percentuais usa o total de votos válidos do local. O saldo positivo municipal compara apenas os dois candidatos selecionados; não representa vitória sobre todos os concorrentes nem resultado definitivo.

EA15 informa o andamento da totalização; EA16 informa recebimento de arquivos de urna; EA20 fornece votos. Recebimento não confirma totalização. Os arquivos podem ter horários distintos, e a soma municipal pode diferir do total estadual por diferenças de atualização. A página mostra os horários dos arquivos e da captura. Resultados parciais não são projeções.

## Fontes

- [Documentação técnica de resultados do TSE](https://www.tse.jus.br/eleicoes/informacoes-tecnicas-sobre-a-divulgacao-de-resultados).
- Arquivos públicos EA15, EA16 e EA20 do TSE; links detalhados no rodapé do mapa.
- [Malha municipal do IBGE](https://servicodados.ibge.gov.br/api/v3/malhas/estados/27?formato=application/vnd.geo%2Bjson&qualidade=minima&intrarregiao=municipio).

## Uso e atualização

Abra index.html ou mapa_apuracao_al_2026.html. No GitHub Pages, publique a branch main a partir da pasta raiz (/).

Ao abrir a página, uma atualização é iniciada automaticamente, com JHC como candidato 1 e Renan Filho como candidato 2. O botão “Atualizar dados” permite repetir a consulta ao TSE no navegador e atualiza apenas a sessão atual, sujeito à disponibilidade e às permissões de acesso do servidor. O retrato publicado é mostrado inicialmente e permanece disponível se a consulta falhar. Os downloads CSV/JSON correspondem ao retrato salvo, não às consultas feitas apenas no navegador.

Para gerar outro retrato salvo, execute `python mapa_apuracao_al.py` com Python 3 e conexão à internet (somente biblioteca padrão), ou use atualizar_mapa.cmd no Windows. Depois publique os arquivos gerados em um novo commit. O template HTML preserva as funcionalidades nas novas gerações.

## Reprodução acadêmica

Ao citar uma análise, registre o endereço da página, o commit utilizado, a data e hora da captura, o local, os candidatos comparados e os horários EA20. Os arquivos CSV e JSON permitem conferir os cálculos do retrato publicado.
