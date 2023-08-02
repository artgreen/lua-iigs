
-- Function to read and display the content of a file
local function catFile(params, filenames)
    for _, filename in ipairs(filenames) do
        local file = io.open(filename, "r")
        if file then
            local content = file:read("*a")
            io.close(file)

            -- Check if "--number" is specified in the parameters
            if params["number"] then
                local lineNumber = 1
                for line in content:gmatch("[^\r\n]+") do
                    print(string.format("%4d  %s", lineNumber, line))
                    lineNumber = lineNumber + 1
                end
            else
                print(content)
            end
        else
            print("Error: Cannot open file '" .. filename .. "'")
        end
    end
end

-- Function to echo the parameters to the console
local function echoParams(params, filenames)
    local output = {}

    -- Add parameters to the output table
    for param, value in pairs(params) do
        table.insert(output, param .. "=" .. value)
    end

    -- Add filenames to the output table
    for _, filename in ipairs(filenames) do
        table.insert(output, filename)
    end

    -- Print everything on one line
    print(table.concat(output, " "))
end

-- Function to parse the user's input into a command, parameters, and optional filenames
local function parseInput(input)
    local command, rest = input:match("([%w_]+)%s*(.*)")

    local parsedParams = {}
    local filenames = {}

    for part in rest:gmatch("%S+") do
        -- Check if the part starts with "-" or "--" to identify parameters
        if part:sub(1, 1) == "-" then
            local param, val = part:match("([%-%-]?[%w_]+)=(.*)")
            if param then
                param = param:sub(1, 2) == "--" and param:sub(3) or param:sub(2)
                parsedParams[param] = val
            else
                param = part:sub(1, 2) == "--" and part:sub(3) or part:sub(2)
                parsedParams[param] = true
            end
        else
            table.insert(filenames, part)
        end
    end

    return command, parsedParams, filenames
end

local function runCLI()
    print("Welcome to the CLI! Type 'exit' to quit.")

    while true do
        io.write("> ")
        io.flush()

        local input = io.read()
        if input == "exit" then
            break
        else
            local command, params, filenames = parseInput(input)
            -- Handle the "cat" command
            if command == "cat" then
                catFile(params, filenames)
            -- Handle the "echo" command
            elseif command == "echo" then
                echoParams(params, filenames)
            else
                print("Invalid input. Please try again.")
            end
        end
    end

    print("Goodbye!")
end

runCLI()

