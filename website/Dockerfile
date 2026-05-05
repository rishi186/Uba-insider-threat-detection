FROM node:18-alpine

WORKDIR /app

# Copy package files and install dependencies
COPY package*.json ./
RUN npm install

# Copy source code
COPY . .

# Expose Vite's default dev server port
EXPOSE 5173

# Run the dev server exposing it to the network so Docker can bridge it
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
