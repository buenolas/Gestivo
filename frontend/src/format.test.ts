import { describe, expect, it } from "vitest";
import { currencyInputToDecimal, formatCurrencyInput } from "./format";

describe("currency input formatting", () => {
  it("formats typed digits like a banking money field", () => {
    const typedDigits = ["", "2", "20", "200", "2000", "20000", "200000", "2000000"];
    const expected = ["0,00", "0,02", "0,20", "2,00", "20,00", "200,00", "2.000,00", "20.000,00"];

    expect(typedDigits.map(formatCurrencyInput)).toEqual(expected);
  });

  it("serializes the formatted value to decimal text for the API", () => {
    expect(currencyInputToDecimal("20.000,00")).toBe("20000.00");
  });
});
