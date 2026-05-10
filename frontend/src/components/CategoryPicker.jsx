/**
 * Grouped category <select> that shows parents as <optgroup> labels
 * and only leaf nodes as selectable <option>s.
 *
 * Categories without children are selectable directly (they are their own leaf).
 * Categories with children are shown as group headers; only the children appear
 * as options.
 */
export default function CategoryPicker({
  categories = [],
  value,
  onChange,
  className = 'select',
  placeholder = '— Sin categoría —',
  disabled = false,
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
