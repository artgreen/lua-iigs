// test_iface.c

#pragma path "src"
#pragma noroot

#include <stdlib.h>
#include "testiface.h"

Collection *newCollection(size_t size) {
    Collection *collection = (Collection *)malloc(sizeof(Collection));
    collection->data = (int *)calloc(size, sizeof(int));
    collection->size = size;
    return collection;
}

void freeCollection(Collection *collection) {
    free(collection->data);
    free(collection);
}

size_t getCollectionSize(Collection *collection) {
    return collection->size;
}

void setCollectionValue(Collection *collection, size_t index, int value) {
    collection->data[index] = value;
}

int getCollectionValue(Collection *collection, size_t index) {
    return collection->data[index];
}
