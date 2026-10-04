/**
 * Drawn symbol set in the vocabulary of P&ID / ISA 5.1 drawings. Every symbol sits on a 48x48 grid and is
 * stroked with currentColor, so colour comes from context. Static markup only; rendered by Symbol.svelte.
 */
const T = 'fill="currentColor" stroke="none" font-family="inherit" font-weight="600" text-anchor="middle"'

export const SYMBOLS: Record<string, string> = {
  // --- equipment ---
  pump: '<circle cx="22" cy="28" r="13"/><path d="M22 15H44M2 28H9M17 21 31 28 17 35Z"/>',
  compressor: '<circle cx="24" cy="24" r="14"/><path d="M14.5 14.5 34 20M14.5 33.5 34 28M2 24H10M38 24H46"/>',
  dryer: '<path d="M12 6H36V30L28 42H20L12 30ZM12 24H36M24 42V47"/>',
  reactor: '<path d="M14 10Q14 6 24 6Q34 6 34 10V36Q34 42 24 42Q14 42 14 36ZM24 2V30M17 30H31"/>',
  exchanger: '<circle cx="24" cy="24" r="14"/><path d="M10 24H16L20 18 28 30 32 24H38M24 10V4M24 38V44"/>',
  control_valve: '<path d="M10 24 24 32 10 40ZM38 24 24 32 38 40ZM24 32V16M14 16A10 10 0 0 1 34 16Z"/>',
  valve: '<path d="M10 22 24 30 10 38ZM38 22 24 30 38 38ZM24 30V14M17 14H31"/>',
  cooling_tower: '<path d="M8 42H40L36 16H12ZM14 10H34M24 10V16M13 26H35M11 34H37"/>',
  column: '<path d="M16 6Q16 3 24 3Q32 3 32 6V42Q32 45 24 45Q16 45 16 42ZM16 14H32M16 22H32M16 30H32M16 38H32"/>',
  vessel: '<path d="M10 14H38Q44 14 44 24Q44 34 38 34H10Q4 34 4 24Q4 14 10 14ZM24 34V44"/>',
  system: '<path d="M6 12H42V36H6ZM6 20H42M14 28H24"/>',
  other: '<path d="M10 4H30L38 12V44H10ZM30 4V12H38"/>',

  // --- instruments ---
  bubble: '<circle cx="24" cy="24" r="16"/><path d="M8 24H40"/>',
  logic: `<path d="M24 4 44 24 24 44 4 24Z"/><text x="24" y="30" font-size="16" ${T}>&amp;</text>`,

  // --- document types ---
  sop: '<path d="M14 3H34V13H14ZM24 13V19M24 19 36 28 24 37 12 28ZM24 37V43M36 28H44"/>',
  opl: '<circle cx="24" cy="12" r="6"/><path d="M24 18V30M10 30H38V44H10ZM16 37H32"/>',
  datasheet: '<path d="M8 4H40V44H8ZM8 14H40M8 22H40M8 30H40M24 14V30M8 36H40M24 36V44"/>',
  pid: '<path d="M4 14H14V36H4ZM34 14H44V36H34ZM14 25H34M19 21 24 25 19 29ZM29 21 24 25 29 29ZM24 25V16"/><circle cx="24" cy="11" r="5"/>',
  interlock: '<path d="M24 3 44 24 24 45 4 24Z"/><path d="M14 24H34M24 14V34"/>',
  maintenance: '<path d="M12 8H36L40 14V44H8V14ZM14 26H34M14 32H34M14 38H26"/><circle cx="24" cy="15" r="3"/>',
  plot_plan: '<path d="M4 4H44V44H4ZM10 10H20V20H10ZM28 14H38V26H28ZM38 40V32M35 35 38 32 41 35"/><circle cx="16" cy="34" r="5"/>',
  ga_drawing: '<path d="M10 12H34V34H10ZM10 40H34M10 37V43M34 37V43M40 12V34M37 12H43M37 34H43"/>',

  // --- landing entries ---
  'bubble-qa': `<circle cx="24" cy="24" r="20"/><path d="M4 24H44"/><text x="24" y="21" font-size="14" ${T}>Q</text><text x="24" y="39" font-size="14" ${T}>A</text>`,
  history: '<path d="M5 7H43V41H5ZM5 24H43M17 7V41M30 7V41M8 33 15 31 20 34 25 12 30 35 36 30 40 31"/>',
  sheets: '<path d="M16 2H42V34M12 6H38V38M8 10H34V42H8ZM15 34 20 25 25 34Z"/>',
}

/** Split an ISA instrument tag into its function letters and loop number ("PSLL-1201" -> PSLL / 1201). */
export function isaParts(tag: string): [string, string] {
  const m = tag.match(/^([A-Za-z]+)[-\s]?(.*)$/)
  return m ? [m[1].toUpperCase(), m[2]] : [tag, '']
}
