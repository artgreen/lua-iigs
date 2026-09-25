-- Load the test_iface library
test_iface = require("test_iface")

-- Create a new collection object
collection = test_iface.newCollection(10)

-- Set some values in the collection
test_iface.setCollectionValue(collection, 0, 42)
test_iface.setCollectionValue(collection, 1, 23)
test_iface.setCollectionValue(collection, 2, 12)
test_iface.setCollectionValue(collection, 3, 99)

-- Get the size of the collection
size = test_iface.getCollectionSize(collection)
print("Collection size:", size)

-- Get some values from the collection
print("Values in collection:")
for i = 0, size - 1 do
    value = test_iface.getCollectionValue(collection, i)
    print(i, value)
end

-- Free the collection
test_iface.freeCollection(collection)

