--
-- crappy test script
--
print("Starting test")

-- type tests
print()
print("Type tests")
print("Number type == " .. type(42)) -- Type is `number`
print("String type == " .. type("Lua Tutorial")) -- Type is `string`
print("Boolean type == " .. type(false)) -- Type is `boolean`
print("Nil type == " .. type(var)) -- Type is `nil`, because `var` is not defined

-- Arithmetic tests
print()
print("Arithmetic tests")
print('1.0 + 2.0 == ' .. 1.0 + 2.0) -- evaluates to the value `3`
print('1 + 2 == ' .. 1 + 2) -- evaluates to the value `3`
a = -1; b = -2; print('a + b == ' .. a + b .. ' a=-1,b=-2') -- evaluates to -3

-- Conditional tests
print()
print("Conditional tests")
a = 100; b = 200
if b < a then
    print('Fail 200 < 100')
elseif b > a then
    print('Pass 200 > 100')
else
    print('Fail 200 == 100')
end

-- Loop tests
print()
print("Loop tests")

a = 0
start = 1; stop = 10
for n = start, stop do
    a = a + 1
end
if a == 10 then print("Basic for loop... passed") else print("Basic for loop... failed") end

-- Explicitly set step to `2`
step = 2; start = 1; stop = 10
for n = start, stop, step do
    a = a + 1
end
if a == 15 then print("Basic for loop with step... passed") else print("Basic for loop with step... failed") end

-- With a negative step, swap start and end to count in descending order
step = -2; start = 1; stop = -10
for n = start, stop, step do
    a = a - 1
end
if a == 10 then print("Basic for loop with neg step... passed") else print("Basic for loop with neg step... failed") end

-- Define list of years
decades = {1910, 1920, 1930, 1940, 1950, 1960, 1970, 1980, 1990}
-- Access the individual years using an iterator
for index, year in ipairs(decades) do
  print(index, year)
end

-- String tests
print()
print("String tests")
print('WalterWhite == ' .. 'Walter' .. 'White') -- evaluates to `WalterWhite`
-- String concatenation with the automation conversion of a number in Lua
print('The 3 Musketeers == ' ..  'The ' .. 3 .. ' Musketeers') -- evaluates to The 3 Musketeers

-- Function Test
print()
print("Function tests")
function hello(name)
  print("Hello", name)
end
print("Say hello there 5 times...\n");
for i = 1, 5 do
    hello("there");
end
print("Function with a single return value")
function square(number)
  -- the expression `number * number` is evaluated
  -- and its value returned
  return number * number
end
-- Square number
print("81 == " .. square(9)) -- `81`

print("Print all parameters of a function")
print("String 42 true")
function var_args(...)
  for index, arg  in ipairs({...}) do
    print(index, arg)
  end
end
var_args('String', 42, true)

print("Function with multiple return values")
function first_and_last(list)
  -- return first and last element of the list
  -- individual return values are separated by a comma `,`
  return list[1], list[#list]
end
people = {"Jim", "Jack", "John"}
-- Assignment of return values to multiple variables
first, last = first_and_last(people)
print("Jim and Jack")
print("The first is", first)
print("The last is", last)

-- Logic tests
print()
print("Logic tests")
print(7 == '7')
print('small' == string.lower('SMALL')) -- evaluates to `true`
-- Dynamic type information
print(type(var) == 'nil') -- evaluates to `true`, because `var` is not defined

print()
print("Ending test")
