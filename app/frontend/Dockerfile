FROM node:20-bullseye

WORKDIR /app

# Copia package.json e package-lock.json primeiro
COPY package*.json ./

# Instala todas as dependências (dev + prod)
RUN npm install

# Copia o restante do projeto
COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev"]
