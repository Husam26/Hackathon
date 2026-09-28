FROM node:22-alpine AS dependencies
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:22-alpine AS builder
WORKDIR /app
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
COPY --from=dependencies /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:22-alpine AS runtime
ENV NODE_ENV=production
WORKDIR /app
RUN addgroup -S sentinel && adduser -S sentinel -G sentinel
COPY --from=builder --chown=sentinel:sentinel /app/package.json /app/package-lock.json ./
COPY --from=builder --chown=sentinel:sentinel /app/node_modules ./node_modules
COPY --from=builder --chown=sentinel:sentinel /app/.next ./.next
COPY --from=builder --chown=sentinel:sentinel /app/public ./public
USER sentinel
EXPOSE 3000
CMD ["npm", "start", "--", "-H", "0.0.0.0", "-p", "3000"]
