FROM node:20-alpine AS deps
WORKDIR /app
# Salin package-lock.json supaya `npm ci` deterministik dan --no-audit --no-fund
# menjaga citra image bersih dari noise advisori dan pesan funding.
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci --no-audit --no-fund

FROM node:20-alpine AS builder
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1

# NEXT_PUBLIC_API_URL di-inline Next.js saat build. Kosongkan di produksi
# supaya klien memakai jalur relatif (/api/v1/...), diteruskan Caddy/nginx.
# Di dev diisi http://localhost:8000 lewat compose build arg.
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

# Basis URL publik untuk metadataBase, og:image, sitemap, dan robots. Tanpa ini
# Next.js memakai localhost sehingga pratinjau tautan dan mesin pencari salah.
ARG NEXT_PUBLIC_SITE_URL
ENV NEXT_PUBLIC_SITE_URL=$NEXT_PUBLIC_SITE_URL

COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN --mount=type=cache,target=/app/.next/cache npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000
ENV HOSTNAME=0.0.0.0
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public/

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -q --spider http://127.0.0.1:3000 || exit 1

CMD ["node", "server.js"]