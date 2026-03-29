-- Convert Pandoc Table nodes into IEEE-friendly LaTeX tabular blocks.
-- This avoids longtable output, which is incompatible with IEEE two-column mode.

local function get_inlines_text(inlines)
  return pandoc.utils.stringify(inlines)
end

local function escape_latex(s)
  s = s:gsub("\\", "\\textbackslash{}")
  s = s:gsub("([%%$#&_{}])", "\\%1")
  s = s:gsub("%^", "\\textasciicircum{}")
  s = s:gsub("~", "\\textasciitilde{}")
  return s
end

local function blocks_to_text(blocks)
  return escape_latex(pandoc.utils.stringify(blocks))
end

local function align_to_colspec(aligns)
  local cols = {}
  for _, a in ipairs(aligns) do
    if a == "AlignRight" then
      table.insert(cols, "r")
    elseif a == "AlignCenter" then
      table.insert(cols, "c")
    else
      table.insert(cols, "l")
    end
  end
  return table.concat(cols, "|")
end

function Table(tbl)
  local aligns = {}
  for i, col in ipairs(tbl.colspecs or {}) do
    aligns[i] = tostring(col[1])
  end
  local spec = align_to_colspec(aligns)
  if spec == "" then
    spec = "l"
  end

  local out = {}
  table.insert(out, "\\begin{table}[t]")
  table.insert(out, "\\centering")

  if tbl.caption and tbl.caption.long and #tbl.caption.long > 0 then
    table.insert(out, "\\caption{" .. escape_latex(get_inlines_text(tbl.caption.long)) .. "}")
  end

  table.insert(out, "\\begin{tabular}{" .. spec .. "}")
  table.insert(out, "\\hline")

  -- Header row(s)
  if tbl.head and tbl.head.rows then
    for _, row in ipairs(tbl.head.rows) do
      local cells = {}
      for _, cell in ipairs(row.cells or {}) do
        table.insert(cells, blocks_to_text(cell.contents or {}))
      end
      table.insert(out, table.concat(cells, " & ") .. " \\\\")
    end
    table.insert(out, "\\hline")
  end

  -- Body rows
  if tbl.bodies then
    for _, body in ipairs(tbl.bodies) do
      for _, row in ipairs(body.body or {}) do
        local cells = {}
        for _, cell in ipairs(row.cells or {}) do
          table.insert(cells, blocks_to_text(cell.contents or {}))
        end
        table.insert(out, table.concat(cells, " & ") .. " \\\\")
      end
    end
  end

  table.insert(out, "\\hline")
  table.insert(out, "\\end{tabular}")
  table.insert(out, "\\end{table}")

  return pandoc.RawBlock("latex", table.concat(out, "\n"))
end
