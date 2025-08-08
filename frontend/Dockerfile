# Use an official Node runtime as a parent image
FROM node:18-alpine

# Set the working directory in the container
WORKDIR /app

# Copy workspace configuration files to leverage Docker layer caching.
# The build context is the 'frontend' directory.
COPY package.json package-lock.json ./
COPY tsconfig.json ./

# Create directories for packages and copy their package.json files
RUN mkdir -p packages/api-client && mkdir -p packages/aurite-studio
COPY packages/api-client/package.json ./packages/api-client/
COPY packages/aurite-studio/package.json ./packages/aurite-studio/

# Install all dependencies for the monorepo workspace.
RUN npm install

# Copy the rest of the frontend source code.
# This includes the source for both packages, which is necessary
# for the local file dependency ("@aurite/api-client": "file:../api-client") to work.
COPY . .

# The aurite-studio app runs on port 3000 by default with `craco start`
EXPOSE 3000

# Start the development server for aurite-studio using the npm workspace command.
# This will enable hot-reloading inside the container.
CMD ["npm", "start", "--workspace=@aurite/aurite-studio"]
