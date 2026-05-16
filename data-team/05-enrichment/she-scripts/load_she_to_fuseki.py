"""Phase 2.3 — SHE catalog → Fuseki A-Box TTL 적재.

PG `she_catalog` (status='approved_auto', active만) → TTL → Fuseki SPARQL UPDATE INSERT.

전략: 기존 v2 dataset (kosha-fuseki-v2:3031)에 SHE 추가.
- v1 production은 건드리지 않음 (변경 risk 회피)
- v2는 multi-SR pilot 42 + R-2 영구화 + SHE 645 추가

검증:
  PA-12 chain query 1줄로 SHE → SR/Penalty 응답
  feature dim 검색 (예: 8 dim filter로 SHE 후보 좁힘)
  risk:hasFeature 물질화 트리플로 추상 feature 검색 지원

Usage:
  PYTHONUTF8=1 python data-team/05-enrichment/she-scripts/load_she_to_fuseki.py
  PYTHONUTF8=1 python data-team/05-enrichment/she-scripts/load_she_to_fuseki.py --endpoint http://localhost:3030/kosha
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import psycopg2
import httpx

ROOT = Path(__file__).resolve().parents[3]
PG_DSN = "dbname=kosha user=kosha password=1229 host=localhost port=5432"

# v2 Fuseki — multi-SR pilot + SHE pilot 적재처 (v1 production 보호)
DEFAULT_ENDPOINT = "http://localhost:3031/kosha"

# OWL feature value → URI fragment mapping
WORK_ACTIVITY_TO_URI = {
    "MAINTENANCE": "Maintenance", "INSPECTION": "Inspection",
    "INSTALLATION": "Installation", "DISMANTLE": "Dismantle",
    "TRANSPORT": "Transport", "REPAIR": "Repair",
    "COMMISSIONING": "Commissioning", "ANALYSIS_TESTING": "AnalysisTesting",
    "ROUTINE_OPERATION": "RoutineOperation", "EMERGENCY_RESPONSE": "EmergencyResponse",
    "OTHER": "OtherActivity",
}
WORK_CONTEXT_TO_URI = {
    "SCAFFOLD": "Scaffold", "CONFINED_SPACE": "ConfinedSpace",
    "EXCAVATION": "Excavation", "MACHINE": "Machine", "VEHICLE": "Vehicle",
    "CRANE": "Crane", "CONVEYOR": "Conveyor", "ROBOT": "Robot",
    "CONSTRUCTION_EQUIP": "ConstructionEquip", "RAIL": "Rail",
    "PRESSURE_VESSEL": "PressureVessel", "STEELWORK": "Steelwork",
    "MATERIAL_HANDLING": "MaterialHandling",
    "GENERAL_WORKPLACE": "GeneralWorkplace", "DEMOLITION": "Demolition",
    "PAINTING": "Painting", "GRINDING": "Grinding",
    "ROPE_ACCESS": "RopeAccess", "ELECTRICAL_WORK": "ElectricalWork",
    "CHEMICAL_WORK": "ChemicalWork", "WELDING": "Welding",
    "LADDER": "Ladder", "KITCHEN_COOKING": "KitchenCooking",
    "FOOD_PREP": "FoodPrep", "DEEP_FRYING": "DeepFrying",
    "GAS_APPLIANCE": "GasAppliance", "HOT_BEVERAGE": "HotBeverage",
    "CLEANING_WET": "CleaningWet", "COLD_STORAGE": "ColdStorage",
    "SERVING_FLOOR": "ServingFloor", "DELIVERY_RIDER": "DeliveryRider",
    "STORAGE_SHELF": "StorageShelf", "LIFT_WORK": "LiftWork",
    "OIL_DRAIN": "OilDrain", "TIRE_CHANGE": "TireChange",
    "WELDING_REPAIR": "WeldingRepair", "EV_BATTERY": "EvBattery",
    "HAIR_CHEMICAL": "HairChemical", "NAIL_CHEMICAL": "NailChemical",
    "HOT_TOOL": "HotTool", "SKIN_DEVICE": "SkinDevice",
    "HAIR_WASH": "HairWash", "SHELF_STOCKING": "ShelfStocking",
    "NIGHT_SOLO": "NightSolo", "COLD_DISPLAY": "ColdDisplay",
    "BOX_HANDLING": "BoxHandling", "CASHIER_AREA": "CashierArea",
    "SAWING": "Sawing", "SANDING": "Sanding",
    "PAINTING_WOODWORK": "PaintingWoodwork",
    "LADDER_INTERIOR": "LadderInterior", "NAIL_GUN": "NailGun",
    "DRY_CLEANING_SOLVENT": "DryCleaningSolvent",
    "PRESS_MACHINE": "PressMachine", "WASHING_MACHINE": "WashingMachine",
    "STEAM_IRON": "SteamIron", "CHEMICAL_SPOTTING": "ChemicalSpotting",
    "GARMENT_SORTING": "GarmentSorting",
    "HIGH_PRESSURE_WASH": "HighPressureWash",
    "CHEMICAL_APPLICATION": "ChemicalApplication",
    "WAX_POLISHING": "WaxPolishing", "CONVEYOR_WASH": "ConveyorWash",
    "INTERIOR_CLEANING": "InteriorCleaning",
    "WET_FLOOR_WORK": "WetFloorWork", "DOG_GROOMING": "DogGrooming",
    "CAT_HANDLING": "CatHandling", "PET_BATHING": "PetBathing",
    "DRYER_OPERATION": "DryerOperation", "CAGE_CLEANING": "CageCleaning",
    "ANIMAL_FEEDING": "AnimalFeeding",
    "FORKLIFT_OPERATION": "ForkliftOperation",
    "HEAVY_LIFTING": "HeavyLifting", "HIGH_SHELF_WORK": "HighShelfWork",
    "LOADING_DOCK": "LoadingDock", "PACKAGE_SORTING": "PackageSorting",
    "CONVEYOR_BELT": "ConveyorBelt", "PESTICIDE_SPRAY": "PesticideSpray",
    "FARM_MACHINERY": "FarmMachinery", "GREENHOUSE_WORK": "GreenhouseWork",
    "HARVEST_WORK": "HarvestWork", "IRRIGATION": "Irrigation",
    "FERTILIZER_HANDLING": "FertilizerHandling",
    "ELECTRICAL_OVERLOAD": "ElectricalOverload",
    "FIRE_EVACUATION": "FireEvacuation",
    "VENTILATION_POOR": "VentilationPoor", "CLEANING_NIGHT": "CleaningNight",
    "CROWD_MANAGEMENT": "CrowdManagement",
    "NOISE_EXPOSURE": "NoiseExposure",
    "FUEL_DISPENSING": "FuelDispensing",
    "STATIC_ELECTRICITY": "StaticElectricity",
    "FUEL_SPILL": "FuelSpill", "UNDERGROUND_TANK": "UndergroundTank",
    "VAPOR_EXPOSURE": "VaporExposure",
    "NIGHT_SOLO_WORK": "NightSoloWork",
    # OTHER는 OWL에 없어 skip
}
HAZARDOUS_AGENT_TO_URI = {
    "CHEMICAL": "Chemical", "DUST": "Dust", "TOXIC": "Toxic",
    "CORROSION": "Corrosion", "RADIATION": "Radiation", "FIRE": "Fire",
    "ELECTRICITY": "Electricity", "ARC_FLASH": "ArcFlash", "NOISE": "Noise",
    "HEAT_COLD": "HeatCold", "BIOLOGICAL": "Biological",
}
ACCIDENT_TYPE_TO_URI = {
    "FALL": "Fall", "SLIP": "Slip", "COLLISION": "Collision",
    "FALLING_OBJECT": "FallingObject", "CRUSH": "Crush", "CUT": "Cut",
    "COLLAPSE": "Collapse", "ERGONOMIC": "Ergonomic",
    "BURN": "Burn", "ELECTRIC_SHOCK": "ElectricShock",
    "EXPLOSION": "Explosion", "CHEMICAL_EXPOSURE": "ChemicalExposure",
    "COLD_EXPOSURE": "ColdExposure",
    "FOOD_CONTAMINATION": "FoodContamination",
}
AGENT_STATE_TO_URI = {
    "ACTIVE_SOLO": "ActiveSolo", "ACTIVE_PAIR": "ActivePair",
    "ACTIVE_CREW": "ActiveCrew", "STANDING_OBSERVATION": "StandingObservation",
    "OTHER": "OtherAgentState",
}
PPE_STATE_TO_URI = {
    "HELMET_WORN": "HelmetWorn", "HELMET_MISSING": "HelmetMissing",
    "HARNESS_TIED": "HarnessTied", "HARNESS_UNTIED": "HarnessUntied",
    "HARNESS_WORN": "HarnessWorn", "HARNESS_MISSING": "HarnessMissing",
    "GLOVE_WORN": "GloveWorn", "GLOVES_MISSING": "GlovesMissing",
    "MASK_WORN": "MaskWorn", "MASK_MISSING": "MaskMissing",
    "GOGGLES_WORN": "GogglesWorn", "GOGGLES_MISSING": "GogglesMissing",
    "VEST_WORN": "VestWorn", "VEST_MISSING": "VestMissing",
    "SAFETY_SHOES_WORN": "SafetyShoesWorn",
    "SAFETY_SHOES_MISSING": "SafetyShoesMissing",
    "OTHER": "OtherPPEState",
}
ENVIRONMENTAL_TO_URI = {
    "WET_SURFACE": "WetSurface", "OIL_CONTAMINATION": "OilContamination",
    "HIGH_ELEVATION": "HighElevation", "LOW_LIGHT": "LowLight",
    "CLUTTERED": "Cluttered", "WINDY_WEATHER": "WindyWeather",
    "EXTREME_TEMPERATURE": "ExtremeTemperature",
    "NARROW_SPACE": "NarrowSpace", "UNSTABLE_GROUND": "UnstableGround",
    "OTHER": "OtherEnvironmental",
}
TEMPORAL_STAGE_TO_URI = {
    "BEFORE_WORK": "BeforeWork", "DURING_WORK": "DuringWork",
    "AFTER_WORK": "AfterWork", "EMERGENCY_STAGE": "EmergencyStage",
    "OTHER": "OtherTemporal",
}

DIM_TO_PROPERTY_AND_MAP = {
    "work_activity":   ("hasWorkActivity",   WORK_ACTIVITY_TO_URI,   "ctx"),
    "work_context":    ("hasWorkContext",    WORK_CONTEXT_TO_URI,    "ctx"),
    "hazardous_agent": ("hasHazardousAgent", HAZARDOUS_AGENT_TO_URI, "agent"),
    "accident_type":   ("hasAccidentType",   ACCIDENT_TYPE_TO_URI,   "haz"),
    "agent_state":     ("hasAgentState",     AGENT_STATE_TO_URI,     "ctx"),
    "ppe_state":       ("hasPPEState",       PPE_STATE_TO_URI,       "ctx"),
    "environmental":   ("hasEnvironmental",  ENVIRONMENTAL_TO_URI,   "ctx"),
    "temporal_stage":  ("hasTemporalStage",  TEMPORAL_STAGE_TO_URI,  "ctx"),
}

PREFIXES_TTL = """@prefix risk: <https://cashtoss.info/ontology/risk#> .
@prefix she: <https://cashtoss.info/ontology/risk/situation#> .
@prefix sr: <https://cashtoss.info/ontology/sr#> .
@prefix core: <https://cashtoss.info/ontology#> .
@prefix guide: <https://cashtoss.info/ontology/guide#> .
@prefix ctx: <https://cashtoss.info/ontology/risk/context#> .
@prefix agent: <https://cashtoss.info/ontology/risk/agent#> .
@prefix haz: <https://cashtoss.info/ontology/risk/hazard#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
"""


def escape_ttl_string(s: str) -> str:
    """TTL string literal escape (\\, \" only)."""
    return s.replace("\\", "\\\\").replace('"', '\\"')


def normalize_visual_triggers(visual_triggers, fallback_name: str) -> list[str]:
    if isinstance(visual_triggers, str):
        visual_triggers = [visual_triggers]
    values = []
    for item in visual_triggers or []:
        if isinstance(item, dict):
            value = item.get("text") or item.get("triggerText") or item.get("label") or ""
        else:
            value = str(item)
        value = value.strip()
        if value:
            values.append(value)
    return values or ([fallback_name] if fallback_name else [])


def she_to_ttl_block(
    she_id: str,
    name: str,
    features: dict,
    sr_ids: list[str],
    visual_triggers=None,
    ci_ids: list[str] | None = None,
) -> str:
    """1 SHE → TTL triples block."""
    lines = [f"she:{she_id} a she:SituationalHazardPattern ;"]
    if name:
        lines.append(f'    rdfs:label "{escape_ttl_string(name)}"@ko ;')

    # 8 dim features
    materialized_features: list[str] = []
    for dim, value in features.items():
        if dim not in DIM_TO_PROPERTY_AND_MAP:
            continue
        prop_local, value_map, ns_prefix = DIM_TO_PROPERTY_AND_MAP[dim]
        uri_frag = value_map.get(value)
        if uri_frag is None:
            continue  # OWL에 미정의 (예: work_context OTHER)
        feature_ref = f"{ns_prefix}:{uri_frag}"
        lines.append(f"    she:{prop_local} {feature_ref} ;")
        materialized_features.append(feature_ref)

    for feature_ref in sorted(set(materialized_features)):
        lines.append(f"    risk:hasFeature {feature_ref} ;")

    triggers = normalize_visual_triggers(visual_triggers, name)
    trigger_ids = [f"VT-{she_id}-{idx + 1}" for idx, _ in enumerate(triggers)]
    for trigger_id in trigger_ids:
        lines.append(f"    she:hasVisualTrigger she:{trigger_id} ;")

    for ci_id in ci_ids or []:
        lines.append(f"    she:relatedChecklistCue guide:{ci_id} ;")

    # appliesSR
    sr_uris = [f"sr:{sr_id}" for sr_id in sr_ids]
    if sr_uris:
        lines.append(f"    she:appliesSR {', '.join(sr_uris)} .")
    else:
        # Guard: SR 없으면 마지막 ; → .
        if lines[-1].endswith(";"):
            lines[-1] = lines[-1].rstrip(" ;") + " ."
        else:
            lines.append("    .")

    blocks = ["\n".join(lines)]
    for trigger_id, trigger_text in zip(trigger_ids, triggers):
        blocks.append(
            f'she:{trigger_id} a she:VisualTrigger ;\n'
            f'    she:triggerText "{escape_ttl_string(trigger_text)}"@ko .'
        )
    return "\n\n".join(blocks)


def fetch_active_she_from_pg() -> list[dict]:
    """PG she_catalog에서 active SHE 645 + sr_ids."""
    conn = psycopg2.connect(PG_DSN)
    cur = conn.cursor()
    cur.execute("""
        SELECT
            c.she_id,
            c.name,
            c.features,
            c.visual_triggers,
            c.source_sr_ids,
            COALESCE(json_agg(DISTINCT m.ci_id) FILTER (WHERE m.ci_id IS NOT NULL), '[]'::json) AS ci_ids
        FROM she_catalog c
        LEFT JOIN she_ci_mapping m ON m.she_id = c.she_id
        WHERE c.status = 'approved_auto'
          AND c.superseded_by IS NULL
        GROUP BY c.she_id, c.name, c.features, c.visual_triggers, c.source_sr_ids
        ORDER BY c.she_id
    """)
    rows = []
    for she_id, name, features, visual_triggers, source_sr_ids, ci_ids in cur.fetchall():
        if isinstance(features, str):
            features = json.loads(features)
        if isinstance(visual_triggers, str):
            visual_triggers = json.loads(visual_triggers)
        if isinstance(source_sr_ids, str):
            source_sr_ids = json.loads(source_sr_ids)
        if isinstance(ci_ids, str):
            ci_ids = json.loads(ci_ids)
        rows.append({
            "she_id": she_id,
            "name": name or "",
            "features": features or {},
            "visual_triggers": visual_triggers or [],
            "source_sr_ids": source_sr_ids or [],
            "ci_ids": ci_ids or [],
        })
    cur.close()
    conn.close()
    return rows


def build_full_ttl(shes: list[dict]) -> str:
    """All SHE → 1 TTL string."""
    blocks = [PREFIXES_TTL]
    for she in shes:
        blocks.append(she_to_ttl_block(
            she["she_id"], she["name"], she["features"], she["source_sr_ids"],
            she.get("visual_triggers", []), she.get("ci_ids", [])
        ))
        blocks.append("")
    return "\n".join(blocks)


def insert_via_sparql_update(endpoint: str, ttl_block: str) -> None:
    """Fuseki SPARQL UPDATE: INSERT DATA { ... }.

    TTL prefixes를 SPARQL prefixes로 변환 + INSERT DATA 감싸기.
    """
    # SPARQL UPDATE 형식
    sparql_prefixes = """PREFIX risk: <https://cashtoss.info/ontology/risk#>
PREFIX she: <https://cashtoss.info/ontology/risk/situation#>
PREFIX sr: <https://cashtoss.info/ontology/sr#>
PREFIX core: <https://cashtoss.info/ontology#>
PREFIX guide: <https://cashtoss.info/ontology/guide#>
PREFIX ctx: <https://cashtoss.info/ontology/risk/context#>
PREFIX agent: <https://cashtoss.info/ontology/risk/agent#>
PREFIX haz: <https://cashtoss.info/ontology/risk/hazard#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
"""
    # ttl_block에서 @prefix 제거 (SPARQL은 별도 PREFIX)
    ttl_no_prefix = "\n".join(
        line for line in ttl_block.splitlines()
        if not line.strip().startswith("@prefix")
    )
    update_query = f"{sparql_prefixes}\nINSERT DATA {{\n{ttl_no_prefix}\n}}"

    update_endpoint = endpoint + "/update"
    r = httpx.post(
        update_endpoint,
        data={"update": update_query},
        timeout=120.0,
    )
    r.raise_for_status()
    return


def verify_pa12_chain(endpoint: str, sample_she_id: str) -> int:
    """PA-12 chain query: SHE → SR → derivedFromNS → hasPenaltyRule → hasSanction.

    Note: SHE만 있고 pen:hasPenaltyRule이 활성 NS에만 연결될 수 있어 결과 0건도 OK.
    여기선 SR 존재 검증만 (chain 동작 확인).
    """
    sparql = f"""PREFIX she: <https://cashtoss.info/ontology/risk/situation#>
PREFIX sr: <https://cashtoss.info/ontology/sr#>

SELECT ?sr WHERE {{
  she:{sample_she_id} she:appliesSR ?sr .
}} LIMIT 5"""
    r = httpx.post(
        endpoint + "/sparql",
        data={"query": sparql},
        headers={"Accept": "application/sparql-results+json"},
        timeout=30.0,
    )
    r.raise_for_status()
    return len(r.json().get("results", {}).get("bindings", []))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT,
                        help="Fuseki dataset endpoint (예: http://localhost:3031/kosha)")
    parser.add_argument("--ttl-out", type=Path,
                        default=ROOT / "koshaontology" / "data" / "she" / "she-instances-v1.ttl",
                        help="TTL output path (audit/backup용)")
    parser.add_argument("--batch-size", type=int, default=50,
                        help="SPARQL UPDATE batch size (TTL block per request)")
    parser.add_argument("--clear-first", action="store_true",
                        help="기존 SHE 모두 DELETE 후 INSERT")
    args = parser.parse_args()

    print(f"[INFO] PG → fetch active SHE")
    shes = fetch_active_she_from_pg()
    print(f"[INFO]   {len(shes)} active SHE retrieved")

    # TTL export
    args.ttl_out.parent.mkdir(parents=True, exist_ok=True)
    full_ttl = build_full_ttl(shes)
    args.ttl_out.write_text(full_ttl, encoding="utf-8")
    print(f"[OK]   TTL export: {args.ttl_out} ({len(full_ttl):,} chars)")

    # Fuseki INSERT
    print(f"[INFO] Fuseki target: {args.endpoint}")

    if args.clear_first:
        print(f"[STEP] DELETE existing SHE")
        clear_query = """PREFIX she: <https://cashtoss.info/ontology/risk/situation#>
DELETE WHERE { ?s a she:SituationalHazardPattern . ?s ?p ?o }"""
        r = httpx.post(args.endpoint + "/update", data={"update": clear_query}, timeout=60.0)
        r.raise_for_status()
        print(f"[INFO]   cleared")

    # Batch INSERT (큰 ttl 한 번에 보내면 timeout 위험)
    print(f"[STEP] Insert {len(shes)} SHE in batches of {args.batch_size}")
    inserted = 0
    for i in range(0, len(shes), args.batch_size):
        batch = shes[i:i + args.batch_size]
        batch_ttl = "\n".join(
            she_to_ttl_block(
                s["she_id"], s["name"], s["features"], s["source_sr_ids"],
                s.get("visual_triggers", []), s.get("ci_ids", [])
            )
            for s in batch
        )
        try:
            insert_via_sparql_update(args.endpoint, batch_ttl)
            inserted += len(batch)
            print(f"  batch {i // args.batch_size + 1}: +{len(batch)} (total {inserted})")
        except Exception as e:
            print(f"  batch {i // args.batch_size + 1} ERROR: {str(e)[:200]}")
            break

    # Verify
    print(f"\n[STEP] Verify")
    sparql = """PREFIX she: <https://cashtoss.info/ontology/risk/situation#>
SELECT (COUNT(*) AS ?cnt) WHERE { ?s a she:SituationalHazardPattern }"""
    r = httpx.post(args.endpoint + "/sparql",
                   data={"query": sparql},
                   headers={"Accept": "application/sparql-results+json"},
                   timeout=60.0)
    n_loaded = int(r.json()["results"]["bindings"][0]["cnt"]["value"])
    print(f"[VERIFY] she:SituationalHazardPattern count: {n_loaded}")

    if shes:
        sample_id = shes[0]["she_id"]
        n_sr = verify_pa12_chain(args.endpoint, sample_id)
        print(f"[VERIFY] PA-12 chain (sample {sample_id} → SR): {n_sr} bindings")

    # 8 dim coverage 검증
    sparql_dim = """PREFIX she: <https://cashtoss.info/ontology/risk/situation#>
SELECT ?prop (COUNT(?s) AS ?cnt) WHERE {
  ?s a she:SituationalHazardPattern ; ?prop ?val .
  FILTER(STRSTARTS(STR(?prop), "https://cashtoss.info/ontology/risk/situation#has"))
} GROUP BY ?prop ORDER BY DESC(?cnt)"""
    r = httpx.post(args.endpoint + "/sparql",
                   data={"query": sparql_dim},
                   headers={"Accept": "application/sparql-results+json"},
                   timeout=60.0)
    print(f"\n[VERIFY] Dim coverage:")
    for b in r.json()["results"]["bindings"]:
        prop = b["prop"]["value"].split("#")[-1]
        cnt = b["cnt"]["value"]
        print(f"  she:{prop:25s} {cnt}")


if __name__ == "__main__":
    main()

