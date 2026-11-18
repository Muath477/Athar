import { describe, expect, it } from "vitest";
import { alerts, countAr, hectares, maps } from "./plural";

describe("countAr", () => {
  it("uses the dual and the singular forms for one and two", () => {
    expect(countAr(1, alerts)).toBe("تنبيه واحد");
    expect(countAr(2, alerts)).toBe("تنبيهان");
  });

  it("uses the plural from three to ten and the accusative singular above", () => {
    expect(countAr(3, hectares)).toBe("٣ هكتارات");
    expect(countAr(10, hectares)).toBe("١٠ هكتارات");
    expect(countAr(11, hectares)).toBe("١١ هكتارًا");
  });

  it("uses the genitive singular for round hundreds", () => {
    expect(countAr(100, maps)).toBe("١٠٠ مخطط");
    expect(countAr(102, maps)).toBe("١٠٢ مخطط");
    expect(countAr(103, maps)).toBe("١٠٣ مخططات");
  });

  it("has a wording for nothing when the form defines one", () => {
    expect(countAr(0, maps)).toBe("لا مخططات بعد");
    expect(countAr(0, hectares)).toBe("٠ هكتارًا");
  });
});
