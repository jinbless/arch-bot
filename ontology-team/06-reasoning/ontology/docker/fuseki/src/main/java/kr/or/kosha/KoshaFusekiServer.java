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

        // Phase E.2: v2 ontology + disjoint + SHACL shapes로 전환.
        // Phase 3C 추가: subclass patch (Phase 3B의 169 sub 관계).
        // Phase 3 (이번 단계) 추가: 22대 사고유형 disjointness (별도 axioms TTL).
        // T2.B (F.3.4) 추가: F.3.2 candidate axiom SHACL shapes (sh:Info severity).
        // SWRL 파일은 의사코드라 제외 (Phase F.3에서 실행 가능 형식 변환 예정).
        String[][] sources = {
            {"/kosha-ontology-v2.owl",                   "RDF/XML", "OWL v2 (BFO+LKIF)"},
            {"/kosha-instances.ttl",                     "TURTLE",  "Instances (ABox)"},
            {"/kosha-disjoint-axioms.ttl",               "TURTLE",  "Industry disjoint axioms (vetted)"},
            {"/serving-validation-shapes-v3.ttl",        "TURTLE",  "SHACL shapes v3"},
            {"/kosha-ontology-v3-subclass-patch.ttl",    "TURTLE",  "Phase 3C subclass hierarchy"},
            {"/kosha-accident22-disjoint.ttl",           "TURTLE",  "KOSHA 22대 사고유형 disjoint"},
            {"/kb-candidates.ttl",                       "TURTLE",  "F.3.2 candidate axioms (SHACL sh:Info)"},
        };

        System.out.println("=== KOSHA Fuseki Server ===");
        System.out.println("Ontology dir: " + ontologyDir);
        for (String[] src : sources) {
            System.out.println("  - " + src[2] + ": " + ontologyDir + src[0] + " [" + src[1] + "]");
        }
        System.out.println("Port: " + port);
        System.out.println("Reasoner: " + reasonerMode);

        // 1. Base model 로드
        System.out.println("\n[1/3] Loading base model...");
        Model base = ModelFactory.createDefaultModel();

        long lastSize = 0;
        for (String[] src : sources) {
            String path = ontologyDir + src[0];
            String fmt = src[1];
            String label = src[2];
            if (new File(path).exists()) {
                base.read(path, fmt);
                long now = base.size();
                long delta = now - lastSize;
                System.out.printf("  %s loaded: %s  (+%d triples, total %d)%n", label, path, delta, now);
                lastSize = now;
            } else {
                System.out.println("  WARNING: " + label + " not found: " + path);
            }
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
