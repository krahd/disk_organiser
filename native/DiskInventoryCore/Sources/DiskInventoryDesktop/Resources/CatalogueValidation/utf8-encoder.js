/* Private parser-only UTF-8 encoding shim. No native bindings or browser APIs. */
(function () {
  "use strict";
  class ParserTextEncoder {
    encode(input = "") {
      if (typeof input !== "string" || input.length > 4 * 1024 * 1024)
        throw new Error("Unsupported parser input.");
      const bytes = new Uint8Array(input.length * 3);
      let used = 0;
      for (let i = 0; i < input.length; i++) {
        let scalar = input.charCodeAt(i);
        if (scalar >= 0xd800 && scalar <= 0xdbff) {
          const low = input.charCodeAt(i + 1);
          if (low >= 0xdc00 && low <= 0xdfff) {
            scalar = 0x10000 + ((scalar - 0xd800) << 10) + low - 0xdc00;
            i++;
          } else scalar = 0xfffd;
        } else if (scalar >= 0xdc00 && scalar <= 0xdfff) scalar = 0xfffd;
        if (scalar < 0x80) bytes[used++] = scalar;
        else if (scalar < 0x800) {
          bytes[used++] = 0xc0 | (scalar >> 6);
          bytes[used++] = 0x80 | (scalar & 0x3f);
        } else if (scalar < 0x10000) {
          bytes[used++] = 0xe0 | (scalar >> 12);
          bytes[used++] = 0x80 | ((scalar >> 6) & 0x3f);
          bytes[used++] = 0x80 | (scalar & 0x3f);
        } else {
          bytes[used++] = 0xf0 | (scalar >> 18);
          bytes[used++] = 0x80 | ((scalar >> 12) & 0x3f);
          bytes[used++] = 0x80 | ((scalar >> 6) & 0x3f);
          bytes[used++] = 0x80 | (scalar & 0x3f);
        }
      }
      return bytes.slice(0, used);
    }
  }
  Object.freeze(ParserTextEncoder.prototype);
  Object.freeze(ParserTextEncoder);
  Object.defineProperty(globalThis, "TextEncoder", {
    value: ParserTextEncoder,
    writable: false,
    configurable: false,
  });
})();
