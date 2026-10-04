export interface DocTypeMeta {
  key: string
  label: string
  description: string
  /** Short reference code used in citation chips (IL1, DS1…). */
  code: string
  /** Name of the drawn symbol in symbols.ts. */
  symbol: string
}

export const DOC_TYPES: DocTypeMeta[] = [
  { key: 'SOP', code: 'SP', label: 'SOP', description: 'Standard operating procedures for start-up, normal operation and shutdown.', symbol: 'sop' },
  { key: 'OPL', code: 'OP', label: 'OPL', description: 'One Point Lessons: short guides and lessons from the field.', symbol: 'opl' },
  { key: 'DATASHEET', code: 'DS', label: 'Datasheet', description: 'Equipment technical specifications: capacity, materials and design data.', symbol: 'datasheet' },
  { key: 'PID', code: 'PI', label: 'P&ID', description: 'Piping and instrumentation diagrams with their tag registers.', symbol: 'pid' },
  { key: 'INTERLOCK', code: 'IL', label: 'Interlock', description: 'Cause & effect: trip setpoints, voting and start permissives.', symbol: 'interlock' },
  { key: 'MAINTENANCE', code: 'PM', label: 'Maintenance History', description: 'Failure history and SAP PM work orders with their root causes.', symbol: 'maintenance' },
  { key: 'PLOT_PLAN', code: 'PP', label: 'Plot Plan', description: 'Physical layout of equipment and areas in the plant.', symbol: 'plot_plan' },
  { key: 'GA_DRAWING', code: 'GA', label: 'GA Drawing', description: 'General arrangement: layout and dimension drawings of equipment.', symbol: 'ga_drawing' },
  { key: 'OTHER', code: 'XX', label: 'Other', description: 'Other technical documents that fit none of the categories above.', symbol: 'other' },
]

export function docTypeMeta(key: string): DocTypeMeta {
  return DOC_TYPES.find((t) => t.key === key) ?? DOC_TYPES[DOC_TYPES.length - 1]
}

export const typeCode = (key: string) => docTypeMeta(key).code
