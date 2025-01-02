FROM node:18-slim

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy frontend code
COPY . .

# Set environment variables
ENV REACT_APP_BACKEND_URL=http://localhost:9090
ENV WDS_SOCKET_PORT=0

EXPOSE 3000

CMD ["npm", "start"]