# Build stage
FROM node:20-alpine AS build

WORKDIR /app

# Install dependencies
COPY package.json package-lock.json ./
RUN npm ci

# Copy application and build
COPY . .
RUN npm run build

# Serve stage
FROM node:20-alpine

WORKDIR /app

# Install serve package globally
RUN npm install -g serve

# Copy built assets from the build stage
COPY --from=build /app/dist ./dist

# Expose port
EXPOSE 5173

# Start the simple static server supporting SPA routing
CMD ["serve", "-s", "dist", "-l", "5173"]
