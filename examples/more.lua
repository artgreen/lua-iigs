-- Function to read the file and output its contents
function readAndOutputFile(filename)
    local file = io.open(filename, "r")
    if not file then
        print("Error: File not found.")
        return
    end

    local lineCount = 0
    for line in file:lines() do
        lineCount = lineCount + 1
        print(line)

        if lineCount % 23 == 0 then
            io.write("Press Enter to continue or 'q' to quit: ")
            local input = io.read()
            if input == "q" then
                break
            end
        end
    end

    file:close()
end

-- Main program
print("Please enter the file name:")
local filename = io.read()
readAndOutputFile(filename)
