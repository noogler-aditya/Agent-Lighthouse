FROM node:20-alpine

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci

# Copy source
COPY . .

# Drop root privileges for runtime.
RUN chown -R node:node /app
USER node

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "--port", "5173"]
