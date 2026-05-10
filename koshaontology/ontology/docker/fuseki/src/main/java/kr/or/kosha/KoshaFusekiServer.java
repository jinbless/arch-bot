package kr.or.kosha;

import openllet.jena.PelletReasonerFactory;
import org.apache.jena.fuseki.main.FusekiServer;
import org.apache.jena.query.Dataset;
import org.apache.jena.query.DatasetFactory;
import org.apache.jena.rdf.model.InfModel;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.reasoner.Reasoner;
import org.apache.jena.reasoner.ReasonerRegistry;

import java.io.File;

/**
 * KOSHA 온톨로지 Fuseki + 추론 서버.
 *
 * OWL T-Box + Turtle A-Box를 로드하고 추론 엔진을 적용한 후
 * Fuseki SPARQL 엔드포인트(포트 3030)를 시작한다.
 *
 * REASONER_MODE 환경변수:
 *   - "openllet" : Openllet OWL DL (메모리 집약적, 626K+ 트리플 시 6GB+ 필요)
 *   - "rdfs"     : Jena RDFS (subClassOf, domain, range 추론만)
 *   - "none"     : 추론 없음, raw SPARQL만 (기본값, 가장 빠름)
 */
public class KoshaFusekiServer {

    public static void main(String[] args) {
        String ontologyDir = System.getenv("ONTOLOGY_DIR");
        if (ontologyDir == null) ontologyDir = "/ontology";

        String portStr = System.getenv("FUSEKI_PORT");
        int port = (portStr != null) ? Integer.parseInt(portStr) : 3030;

        String reasonerMode = System.getenv("REASONER_MODE");
        if (reasonerMode == null) reasonerMode = "none";
        reasonerMode = reasonerMode.toLowerCase().trim();

        String owlFile = ontologyDir + "/kosha-ontology.owl";
        String ttlFile = ontologyDir + "/kosha-instances.ttl";

        System.out.println("=== KOSHA Fuseki Server ===");
        System.out.println("OWL: " + owlFile);
        System.out.println("TTL: " + ttlFile);
        System.out.println("Port: " + port);
        System.out.println("Reasoner: " + reasonerMode);

        // 1. Base model 로드
        System.out.println("\n[1/3] Loading base model...");
        Model base = ModelFactory.createDefaultModel();

        if (new File(owlFile).exists()) {
            base.read(owlFile);
            System.out.println("  OWL loaded: " + owlFile);
        } else {
            System.out.println("  WARNING: OWL file not found: " + owlFile);
        }

        if (new File(ttlFile).exists()) {
            base.read(ttlFile, "TURTLE");
            System.out.println("  TTL loaded: " + ttlFile);
        } else {
            System.out.println("  WARNING: TTL file not found: " + ttlFile);
        }

        long baseTriples = base.size();
        System.out.println("  Base triples: " + baseTriples);

        // 2. 추론 엔진 적용
        Model servingModel;
        System.out.println("\n[2/3] Applying reasoner (" + reasonerMode + ")...");

        switch (reasonerMode) {
            case "openllet": {
                Reasoner reasoner = PelletReasonerFactory.theInstance().create();
                InfModel infModel = ModelFactory.createInfModel(reasoner, base);
                infModel.prepare();
                long totalTriples = infModel.size();
                System.out.println("  Total triples (base + inferred): " + totalTriples);
                System.out.println("  Inferred triples: " + (totalTriples - baseTriples));
                servingModel = infModel;
                break;
            }
            case "rdfs": {
                Reasoner reasoner = ReasonerRegistry.getRDFSReasoner();
                InfModel infModel = ModelFactory.createInfModel(reasoner, base);
                infModel.prepare();
                long totalTriples = infModel.size();
                System.out.println("  Total triples (base + inferred): " + totalTriples);
                System.out.println("  Inferred triples: " + (totalTriples - baseTriples));
                servingModel = infModel;
                break;
            }
            default: {
                System.out.println("  No reasoner — serving raw triples only");
                System.out.println("  Total triples: " + baseTriples);
                servingModel = base;
                break;
            }
        }

        // 3. Model을 Dataset으로 래핑 + Fuseki 서버 시작
        System.out.println("\n[3/3] Starting Fuseki server on port " + port + "...");
        Dataset dataset = DatasetFactory.create(servingModel);

        // Read-only: allowUpdate=false → SPARQL UPDATE, Upload 차단
        FusekiServer.Builder builder = FusekiServer.create()
                .setPort(port)
                .add("/kosha", dataset, false)
                .enablePing(true)
                .enableStats(true);

        // Fuseki webapp UI (if available)
        String webappDir = System.getenv("FUSEKI_WEBAPP");
        if (webappDir != null && new File(webappDir).isDirectory()) {
            builder.setStaticFileBase(webappDir);
            System.out.println("  Web UI enabled from: " + webappDir);
        }

        FusekiServer server = builder.build();

        server.start();
        System.out.println("\n=== KOSHA Fuseki Server Started ===");
        System.out.println("SPARQL endpoint: http://0.0.0.0:" + port + "/kosha/sparql");
        System.out.println("Web UI:          http://0.0.0.0:" + port + "/");
        System.out.println("Press Ctrl+C to stop.");

        // JVM 종료 시 서버 정지
        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            System.out.println("\nShutting down Fuseki server...");
            server.stop();
        }));

        // 서버가 종료될 때까지 대기
        server.join();
    }
}
