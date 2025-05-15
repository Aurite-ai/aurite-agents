# Stage 1: Build
FROM node:lts-alpine as builder
WORKDIR /app
COPY package.json yarn.lock ./
RUN yarn install --frozen-lockfile
COPY . .
# If you have a build step for production, add it here
# RUN yarn build

# Stage 2: Development server
FROM node:lts-alpine
WORKDIR /app
COPY --from=builder /app ./
# Ensure vite is a dependency, or install globally if needed for dev
# RUN npm install -g vite # Or ensure it's in devDependencies
EXPOSE 5173
CMD ["yarn", "dev", "--host", "0.0.0.0"]
