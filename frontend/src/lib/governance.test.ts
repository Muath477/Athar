import { describe, expect, it } from "vitest";
import { EMPTY_FILTERS, auditActionAr, auditQuery } from "./governance";

describe("auditActionAr", () => {
  it("names known actions in Arabic", () => {
    expect(auditActionAr("map.approve")).toBe("اعتماد مخطط");
    expect(auditActionAr("user.deactivate")).toBe("إيقاف حساب");
  });

  it("falls back to the raw code for actions it does not know", () => {
    expect(auditActionAr("camera.move")).toBe("camera.move");
  });
});

describe("auditQuery", () => {
  it("is empty when no filter is set", () => {
    expect(auditQuery(EMPTY_FILTERS)).toBe("");
  });

  it("covers whole Riyadh days and keeps the other filters", () => {
    const query = new URLSearchParams(
      auditQuery({ actor: " inspector@ ", action: "map.", target_type: "", from: "2026-11-18", to: "2026-11-18" }, 2),
    );
    expect(query.get("actor")).toBe("inspector@");
    expect(query.get("action")).toBe("map.");
    expect(query.has("target_type")).toBe(false);
    expect(query.get("from")).toBe("2026-11-17T21:00:00.000Z");
    expect(query.get("to")).toBe("2026-11-18T21:00:00.000Z");
    expect(query.get("page")).toBe("2");
  });
});
