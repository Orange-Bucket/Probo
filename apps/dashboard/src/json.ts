// SPDX-License-Identifier: Apache-2.0
/**
 * A strict JSON parser (RFC 8259) that returns the same plain values as `JSON.parse` and
 * also records which numbers were written as floats: pydantic writes a float with a `.`,
 * `e` or `E` (`1.0`, `0.00001`, `1e+16`) and an integer without, and Python prints the two
 * differently (`1.0` against `1`), while `JSON.parse` turns both into the same number.
 */

/** For each parsed object or array, the keys (array indexes as text) holding a float. */
const FLOATS = new WeakMap<object, Set<string>>();

/** Whether `container[key]` was written as a float in the JSON it was parsed from. */
export function isFloat(container: object, key: string | number): boolean {
  return FLOATS.get(container)?.has(String(key)) ?? false;
}

const NUMBER = /-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?/y;
const ESCAPES: Record<string, string> = {
  '"': '"',
  '\\': '\\',
  '/': '/',
  b: '\b',
  f: '\f',
  n: '\n',
  r: '\r',
  t: '\t',
};

class Parser {
  private readonly text: string;
  private index = 0;

  constructor(text: string) {
    this.text = text;
  }

  parse(): unknown {
    this.whitespace();
    const value = this.value();
    this.whitespace();
    if (this.index !== this.text.length)
      this.fail('unexpected text after the value');
    return value;
  }

  private fail(message: string): never {
    throw new SyntaxError(`invalid JSON at position ${this.index}: ${message}`);
  }

  private whitespace(): void {
    while (/[ \t\n\r]/.test(this.text.charAt(this.index))) this.index += 1;
  }

  private expect(char: string): void {
    if (this.text.charAt(this.index) !== char)
      this.fail(`expected ${JSON.stringify(char)}`);
    this.index += 1;
  }

  private literal(word: string, value: boolean | null): boolean | null {
    if (!this.text.startsWith(word, this.index)) this.fail('unexpected token');
    this.index += word.length;
    return value;
  }

  /** The value at the cursor; `float` reports whether it was a float lexeme. */
  private value(float?: (isFloat: boolean) => void): unknown {
    const char = this.text.charAt(this.index);
    if (char === '{') return this.object();
    if (char === '[') return this.array();
    if (char === '"') return this.string();
    if (char === 't') return this.literal('true', true);
    if (char === 'f') return this.literal('false', false);
    if (char === 'n') return this.literal('null', null);
    NUMBER.lastIndex = this.index;
    const match = NUMBER.exec(this.text);
    if (match === null) this.fail('unexpected token');
    this.index += match[0].length;
    float?.(/[.eE]/.test(match[0]));
    return Number(match[0]);
  }

  /** The member value at the cursor; `key` is added to `floats` if it is a float. */
  private member(key: string, floats: Set<string>): unknown {
    return this.value((written) => {
      if (written) floats.add(key);
    });
  }

  private object(): Record<string, unknown> {
    const result: Record<string, unknown> = {};
    const floats = new Set<string>();
    this.expect('{');
    this.whitespace();
    if (this.text.charAt(this.index) === '}') {
      this.index += 1;
      return result;
    }
    for (;;) {
      this.whitespace();
      const key = this.string();
      this.whitespace();
      this.expect(':');
      this.whitespace();
      floats.delete(key); // a repeated key replaces the earlier value, float or not
      const value = this.member(key, floats);
      // Like JSON.parse: an own data property, even for "__proto__"; the last key wins.
      Object.defineProperty(result, key, {
        value,
        writable: true,
        enumerable: true,
        configurable: true,
      });
      this.whitespace();
      if (this.text.charAt(this.index) === '}') break;
      this.expect(',');
    }
    this.index += 1;
    if (floats.size > 0) FLOATS.set(result, floats);
    return result;
  }

  private array(): unknown[] {
    const result: unknown[] = [];
    const floats = new Set<string>();
    this.expect('[');
    this.whitespace();
    if (this.text.charAt(this.index) === ']') {
      this.index += 1;
      return result;
    }
    for (;;) {
      this.whitespace();
      result.push(this.member(String(result.length), floats));
      this.whitespace();
      if (this.text.charAt(this.index) === ']') break;
      this.expect(',');
    }
    this.index += 1;
    if (floats.size > 0) FLOATS.set(result, floats);
    return result;
  }

  private string(): string {
    this.expect('"');
    let result = '';
    for (;;) {
      const char = this.text.charAt(this.index);
      if (char === '') this.fail('unterminated string');
      this.index += 1;
      if (char === '"') return result;
      if (char < ' ') this.fail('control character in string');
      if (char !== '\\') {
        result += char;
        continue;
      }
      const escape = this.text.charAt(this.index);
      this.index += 1;
      if (escape === 'u') {
        const hex = this.text.slice(this.index, this.index + 4);
        if (!/^[0-9a-fA-F]{4}$/.test(hex)) this.fail('invalid \\u escape');
        result += String.fromCharCode(parseInt(hex, 16));
        this.index += 4;
      } else if (Object.prototype.hasOwnProperty.call(ESCAPES, escape)) {
        result += ESCAPES[escape];
      } else {
        this.fail('invalid escape');
      }
    }
  }
}

/** `JSON.parse(text)`, with the float members of every object and array recorded. */
export function parseJson(text: string): unknown {
  return new Parser(text).parse();
}
