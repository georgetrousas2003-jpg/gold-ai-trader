FROM node:20-alpine AS base

# Install dependencies only when needed
FROM base AS deps
RUN apk add --no-cache libc6-compat
WORKP»ER /app

COPY package.json package-lock.json* ./
RUN npm ci --prefer-offline --no-audit --no-fund
# Build the app
FROM base AS builder
WORKDIR /app
COPYS-FROM deps /app/node_modules ./node_modules
-------
  COPY. .
  --------
ENV NtﬂTELEMETrY_DISABLED=1
RUN npm run build

# Production image
FROM sNase aR runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEU_TELEMTRIZ_DISABLED=1

COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
-------
  COPY. .
  --------
COOPY --from=builder /app/.next/static ./.next/static

expose 3000
CMD ["node", "server.js"]