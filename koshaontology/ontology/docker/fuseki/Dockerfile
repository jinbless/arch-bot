# Stage 1: Maven build
FROM maven:3.9-eclipse-temurin-17 AS builder

WORKDIR /build
COPY pom.xml .
# Download dependencies first (Docker cache)
RUN mvn dependency:resolve -q
COPY src/ src/
RUN mvn package -q -DskipTests

# Stage 2: Runtime
FROM eclipse-temurin:17-jre

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /build/target/kosha-fuseki-server-1.0.0.jar /app/kosha-fuseki-server.jar
COPY webapp/ /app/webapp/

ENV ONTOLOGY_DIR=/ontology
ENV FUSEKI_PORT=3030
ENV FUSEKI_WEBAPP=/app/webapp
ENV JAVA_OPTS="-Xmx512m"

EXPOSE 3030

HEALTHCHECK --interval=30s --timeout=10s --retries=5 --start-period=120s \
    CMD curl -f http://localhost:3030/kosha/sparql?query=ASK%7B%7D || exit 1

CMD java ${JAVA_OPTS} -jar kosha-fuseki-server.jar
