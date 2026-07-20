local function file_exists(path)
    local f = io.open(path, "rb")
    if f then
        f:close()
        return true
    end
    return false
end

local function get_script_dir()
    local info = debug.getinfo(1, "S")
    local source = info and info.source or ""

    if source:sub(1, 1) == "@" then
        local path = source:sub(2)
        return path:match("^(.*[\\/])") or "./"
    end

    return "./"
end

local input_path = arg and arg[1]
local output_path = arg and arg[2]

if not input_path or input_path == "" then
    print("Usage: lua dumper.lua <input> [output]")
    os.exit(1)
end

if not output_path or output_path == "" then
    output_path = "dumped_output.lua"
end

if not file_exists(input_path) then
    print("Input file not found: " .. tostring(input_path))
    os.exit(1)
end

local script_dir = get_script_dir()
local core_path = script_dir .. "pollesser_core.lua"

if not file_exists(core_path) then
    print("Failed to load pollesser_core.lua: file not found at " .. tostring(core_path))
    os.exit(1)
end

local ok_core, core_or_err = pcall(dofile, core_path)
if not ok_core then
    print("Failed to load pollesser_core.lua: " .. tostring(core_or_err))
    os.exit(1)
end

local core = core_or_err
if type(core) ~= "table" or type(core.dump_file) ~= "function" then
    print("pollesser_core.lua is invalid or missing dump_file")
    os.exit(1)
end

local ok_dump, result_a, result_b = pcall(function()
    return core.dump_file(input_path, output_path)
end)

if not ok_dump then
    print("Dump crashed: " .. tostring(result_a))
    os.exit(1)
end

local wrote_file = file_exists(output_path)

if result_a == true then
    if not wrote_file and type(result_b) == "string" and #result_b > 0 then
        local f = io.open(output_path, "wb")
        if not f then
            print("Could not write output file: " .. tostring(output_path))
            os.exit(1)
        end
        f:write(result_b)
        f:close()
        wrote_file = true
    end
elseif type(result_a) == "string" and #result_a > 0 then
    local f = io.open(output_path, "wb")
    if not f then
        print("Could not write output file: " .. tostring(output_path))
        os.exit(1)
    end
    f:write(result_a)
    f:close()
    wrote_file = true
else
    print("Dump failed: " .. tostring(result_b or result_a or "unknown error"))
    os.exit(1)
end

if not wrote_file then
    print("Dump finished but no output file was created")
    os.exit(1)
end

os.exit(0)