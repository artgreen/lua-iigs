-- An ASCII Mandelbrot postcard. Floating-point math, no graphics toolbox.
-- Coarse shading is intentional: emulator and SANE rounding can differ.
local width, height, limit = 39, 16, 32
local shades = ' .,:;ox%#@'
print('Mandelbrot: 39 x 16, 32 iterations')
for y = 0, height - 1 do
  local ci = -1.1 + 2.2 * y / (height - 1)
  local row = {}
  for x = 0, width - 1 do
    local cr = -2.1 + 3.1 * x / (width - 1)
    local zr, zi, n = 0, 0, 0
    while zr*zr + zi*zi <= 4 and n < limit do
      zr, zi = zr*zr - zi*zi + cr, 2*zr*zi + ci
      n = n + 1
    end
    local index = n == limit and #shades or (n % (#shades - 1) + 1)
    row[x+1] = shades:sub(index,index)
  end
  print(table.concat(row))
  io.flush()
end
print('Mandelbrot complete.')
