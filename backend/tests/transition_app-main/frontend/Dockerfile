FROM node:23-alpine

WORKDIR /app

# Install dependencies
COPY esa-chat-ui/package*.json ./
# Copy rest of source (in compose, this will be overridden by the mounted volume)
COPY esa-chat-ui/ .

# Install extra dependencies explicitly
RUN npm install keycloak-js axios ol echarts @turf/turf uuid && npm install


EXPOSE 8080
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["npm", "run", "dev"]
