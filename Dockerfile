FROM alpine:3.20
WORKDIR /src
COPY . .
LABEL org.opencontainers.image.source="https://github.com/mafzalkalwardev/safer-carrier-extractor"
CMD ["sh", "-c", "echo 'safer-carrier-extractor source package' && ls -1"]
