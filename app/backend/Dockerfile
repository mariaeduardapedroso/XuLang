FROM node:20-bullseye

# Instalar ferramentas do sistema (python3, pip3 e build tools including gcc)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      python3 python3-pip build-essential ca-certificates && \
    # ensure "python" command exists and points to python3
    ln -sf /usr/bin/python3 /usr/bin/python && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .

# Instalar dependências Python necessárias
RUN pip3 install --no-cache-dir ply

EXPOSE 3000
ENV PYTHON=python3
CMD ["node", "server.js"]
