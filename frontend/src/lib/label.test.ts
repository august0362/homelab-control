import { describe, expect, it } from "vitest";
import { LABEL_MAX_LENGTH, validateLabel } from "./label";

describe("validateLabel", () => {
  it("trims and accepts up to the limit, counting code points", () => {
    expect(validateLabel("  Dell server ")).toEqual({ label: "Dell server" });
    expect(validateLabel("x".repeat(LABEL_MAX_LENGTH))).toEqual({ label: "x".repeat(LABEL_MAX_LENGTH) });
    expect(validateLabel("☕".repeat(LABEL_MAX_LENGTH))).toHaveProperty("label");
    expect(validateLabel("Phòng khách")).toEqual({ label: "Phòng khách" });
  });

  it("rejects empty, too long and control characters", () => {
    for (const bad of ["", "   ", "x".repeat(LABEL_MAX_LENGTH + 1), "a\nb", "tab\there", "nul\u0000", "a b"]) {
      expect(validateLabel(bad)).toHaveProperty("error");
    }
  });
});
