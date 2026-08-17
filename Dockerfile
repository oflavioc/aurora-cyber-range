# A IMAGEM DO RANGE — peca 7 da Fase 4.
#
# UMA IMAGEM, DOIS PROCESSOS
# ---------------------------
# `range-api` e `academus-api` sao o MESMO codigo com raizes de composicao
# diferentes (`range_core.api.processo:criar` e
# `domains.academus.api.processo:criar`). Duas imagens seriam duas instalacoes
# do mesmo `pyproject.toml`, com a chance de divergirem em versao — e o
# `constraints.txt` existe para que isso nao aconteca nem entre commits.
#
# O CLIENTE E CONSTRUIDO AQUI, E NAO COPIADO DE FORA
# ---------------------------------------------------
# `pyproject.toml` leva `web/dist/<tela>/index.html` como `package-data`, e
# `dist/` esta no `.gitignore`: e artefato de build. Se a imagem esperasse que
# alguem tivesse rodado o build antes, ela subiria sem as telas quando esse
# alguem esquecesse — e `GET /sala` responderia 503 no telao da sala.
#
# Entao o estagio `cliente` constroi a partir da FONTE, com a mesma imagem de
# Node pinada por digest que o `docker-compose.yml` declara para o `web-build`.
# `scripts/check_pinned_images.py` cobra a igualdade dos dois digests: se
# alguem subir um e esquecer o outro, o gate reprova.
#
# O QUE ESTE ESTAGIO NAO FAZ: a prova negativa do gate do build. Ela planta um
# erro de tipo de proposito, e um build de imagem que reprovasse a si mesmo de
# proposito seria um passo que falha por desenho. A prova roda no CI e na
# maquina de quem desenvolve, pelo `web-build`; aqui roda `npm run build`, que
# JA COMECA por `tsc --noEmit` — se o TypeScript quebrar, a imagem nao existe.

FROM node:22.11.0-alpine@sha256:b64ced2e7cd0a4816699fe308ce6e8a08ccba463c757c00c14cd372e3d2c763e AS cliente

WORKDIR /web

# O lockfile ANTES da fonte: assim a camada de dependencia so e refeita quando
# ele muda, e nao a cada edicao de `.tsx`.
COPY range-core/web/package.json range-core/web/package-lock.json ./
RUN npm ci

COPY range-core/web/ ./
RUN npm run build


FROM python:3.12.7-slim@sha256:60d9996b6a8a3689d36db740b49f4327be3be09a21122bd02fb8895abb38b50d AS aplicacao

# `PYTHONDONTWRITEBYTECODE`: a arvore da imagem e imutavel, e `.pyc` gerado em
# runtime so ocupa camada de escrita. `PYTHONUNBUFFERED`: sem ele o log do
# uvicorn fica preso no buffer e `docker logs` mente sobre o que esta
# acontecendo — durante um exercicio, isso e a diferenca entre diagnosticar e
# adivinhar.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# A INSTALACAO E NAO EDITAVEL, e isso e o ponto. Instalacao editavel resolveria
# `range_core` pela arvore e mascararia qualquer erro de `package-data` — que e
# exatamente o que a P3-4 mediu no worktree de auditoria. Aqui, o que nao
# estiver declarado no `pyproject.toml` simplesmente nao existe.
COPY pyproject.toml constraints.txt alembic.ini ./
COPY alembic/ ./alembic/
COPY contracts/ ./contracts/
COPY range-core/ ./range-core/
COPY domains/ ./domains/

# As telas construidas entram ANTES do `pip install`, senao o wheel sai sem
# `web/dist/*/index.html` — a consequencia que a entrada de `package-data`
# declara em comentario, aqui aplicada.
COPY --from=cliente /web/dist ./range-core/web/dist

RUN pip install --no-cache-dir . -c constraints.txt

# NAO ROOT. O processo nao escreve em lugar nenhum da imagem: o estado vive em
# Postgres e Redis, e o pack chega por volume read-only.
RUN useradd --create-home --uid 10001 aurora
USER aurora

# `05` §6 pede bind em `127.0.0.1`, e o DEFAULT AQUI E ESSE — fechado. O
# container sobrescreve para `0.0.0.0` no compose, ao lado da linha que publica
# a porta apenas no loopback do HOST: dentro do namespace de rede do container,
# `127.0.0.1` tornaria o servico inalcancavel ate para o container vizinho. Ver
# a D21 no registro da fase.
ENV AURORA_BIND_HOST=127.0.0.1 \
    AURORA_BIND_PORT=8000

# Sem CMD: a imagem e uma so e os processos sao dois. Quem escolhe e o compose,
# e escolher aqui daria a um deles o estatuto de padrao.
