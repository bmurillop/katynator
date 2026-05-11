/**
 * Grouped category <select>.
 *
 * Default mode (filterMode=false):
 *   Parents with children appear as non-selectable <optgroup> headers; only
 *   leaf nodes are selectable. Parents without children are selectable directly.
 *
 * filterMode=true:
 *   All categories are selectable. Parents with children appear as plain
 *   <option>s followed by indented child <option>s, so the user can filter by
 *   either an entire group or a specific subcategory.
 */
export default function CategoryPicker({
  categories = [],
  value,
  onChange,
  className = 'select',
  placeholder = '— Sin categoría —',
  disabled = false,
  filterMode = false,
}) {
  const parents = categories.filter((c) => !c.parent_id)
  const childMap = {}
  categories.forEach((c) => {
    if (c.parent_id) {
      if (!childMap[c.parent_id]) childMap[c.parent_id] = []
      childMap[c.parent_id].push(c)
    }
  })

  return (
    <select className={className} value={value || ''} onChange={onChange} disabled={disabled}>
      <option value="">{placeholder}</option>
      {parents.map((parent) => {
        const children = (childMap[parent.id] || []).sort((a, b) =>
          a.name.localeCompare(b.name, 'es')
        )

        if (filterMode) {
          return [
            <option key={parent.id} value={parent.id}>
              {children.length > 0 ? `${parent.name} (todas)` : parent.name}
            </option>,
            ...children.map((child) => (
              <option key={child.id} value={child.id}>
                {'  └ '}{child.name}
              </option>
            )),
          ]
        }

        if (children.length > 0) {
          return (
            <optgroup key={parent.id} label={parent.name}>
              {children.map((child) => (
                <option key={child.id} value={child.id}>
                  {child.name}
                </option>
              ))}
            </optgroup>
          )
        }
        return (
          <option key={parent.id} value={parent.id}>
            {parent.name}
          </option>
        )
      })}
    </select>
  )
}
