// test_iface.h

#ifndef TEST_IFACE_H
#define TEST_IFACE_H

#pragma path "src"
#include "lua.h"

#include <stdio.h>

// Define a struct to represent the collection of data
typedef struct {
    int *data;
    size_t size;
} Collection;

// Function to create a new collection object
Collection *newCollection(size_t size);

// Function to free a collection object
void freeCollection(Collection *collection);

// Function to get the size of a collection
size_t getCollectionSize(Collection *collection);

// Function to set a value in a collection
void setCollectionValue(Collection *collection, size_t index, int value);

// Function to get a value from a collection
int getCollectionValue(Collection *collection, size_t index);

// Function to initialize the module
int luaopen_test_iface(lua_State *L);
#endif
