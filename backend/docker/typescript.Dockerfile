# Sandbox execution image for TypeScript. ts-node/typescript are installed
# here, at build time, because containers run with --network none - nothing
# can be `npm install`-ed at execution time.
FROM node:18.15.0-alpine
RUN npm install -g typescript@5.0.3 ts-node@10.9.2
